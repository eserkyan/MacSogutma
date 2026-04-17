from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from apps.core.constants import CircuitSelect, PlcEventType, TestPhase, TestStatus
from apps.plc.models import PlcEventLog, PlcRuntimeState
from apps.plc.services.live_history import get_live_history
from apps.plc.services.modbus_client import PlcModbusClient
from apps.tests.models import TestRecord
from apps.tests.services.evaluation import TestEvaluationService
from apps.tests.services.test_state_machine import TestStateMachineService


@dataclass(slots=True)
class StartTestInput:
    company_id: int
    product_model_id: int
    recipe_id: int
    circuit: int
    operator_name: str
    notes: str


class TestRunnerService:
    def __init__(self, client: PlcModbusClient | None = None) -> None:
        self.client = client or PlcModbusClient()
        self.state_machine = TestStateMachineService()
        self.evaluation_service = TestEvaluationService()

    @transaction.atomic
    def start_test(self, data: StartTestInput) -> TestRecord:
        from apps.companies.models import Company
        from apps.products.models import ProductModel
        from apps.recipes.models import Recipe

        if TestRecord.active().exists():
            raise RuntimeError("An active test already exists.")
        recipe = Recipe.objects.select_related("product_model").get(pk=data.recipe_id)
        started_at = timezone.now()
        local_started_at = timezone.localtime(started_at)
        prestart_samples = self._collect_prestart_samples(started_at, recipe.phase_context_sec)
        record = TestRecord.objects.create(
            test_no=f"T-{local_started_at:%Y%m%d-%H%M%S}",
            company=Company.objects.get(pk=data.company_id),
            product_model=ProductModel.objects.get(pk=data.product_model_id),
            recipe=recipe,
            operator_name=data.operator_name,
            selected_circuit=data.circuit,
            status=TestStatus.START_REQUESTED,
            started_at=started_at,
            recipe_name_snapshot=recipe.recipe_name,
            recipe_code_snapshot=recipe.recipe_code,
            recipe_revision_snapshot=recipe.revision_no,
            start_duration_sec_snapshot=recipe.start_duration_sec,
            stable_duration_sec_snapshot=recipe.stable_duration_sec,
            stop_duration_sec_snapshot=recipe.stop_duration_sec,
            phase_context_sec_snapshot=recipe.phase_context_sec,
            prestart_samples_json=prestart_samples,
            limits_snapshot_json=recipe.limits_json,
            notes=data.notes,
        )
        self.client.write_test_command(
            circuit=CircuitSelect(data.circuit),
            start_request=True,
            stop_request=False,
            abort_request=False,
            phase=TestPhase.START,
            test_active=True,
        )
        record.status = TestStatus.RUNNING
        record.save(update_fields=["status", "updated_at"])
        return record

    @staticmethod
    def _collect_prestart_samples(started_at, context_sec: int) -> list[dict[str, object]]:
        started_unix = started_at.timestamp()
        earliest_unix = started_unix - max(0, int(context_sec))
        samples: list[dict[str, object]] = []
        for item in get_live_history():
            timestamp_unix = float(item.get("timestamp_unix") or 0)
            if earliest_unix <= timestamp_unix < started_unix:
                snapshot = dict(item)
                snapshot["test_phase"] = int(TestPhase.IDLE)
                samples.append(snapshot)
        return samples

    def supervise_active_test(self) -> TestRecord | None:
        test_record = TestRecord.active().first()
        if not test_record:
            return None
        runtime = PlcRuntimeState.load()
        if runtime.plc_fault:
            return self.abort_test(test_record, reason="PLC fault detected.")
        if runtime.communication_loss_since and (timezone.now() - runtime.communication_loss_since).total_seconds() > 5:
            return self.abort_test(test_record, reason="Communication loss exceeded 5 seconds.")
        decision = self.state_machine.determine_phase(test_record)
        self.client.write_test_command(
            circuit=CircuitSelect(test_record.selected_circuit),
            start_request=False,
            stop_request=decision.phase == TestPhase.STOP,
            abort_request=False,
            phase=decision.phase,
            test_active=True,
        )
        if decision.phase == TestPhase.STOP and test_record.stop_started_at:
            elapsed = (timezone.now() - test_record.stop_started_at).total_seconds()
            if elapsed >= test_record.stop_duration_sec_snapshot:
                return self.complete_test(test_record)
        return test_record

    def complete_test(self, test_record: TestRecord) -> TestRecord:
        from apps.reports.tasks import generate_excel_task, generate_pdf_task

        if not test_record.ended_at:
            test_record.ended_at = timezone.now()
            test_record.save(update_fields=["ended_at", "updated_at"])
        self.client.write_test_command(
            circuit=CircuitSelect(test_record.selected_circuit),
            start_request=False,
            stop_request=True,
            abort_request=False,
            phase=TestPhase.STOP,
            test_active=False,
        )
        self.evaluation_service.evaluate(test_record)
        for language in ("tr", "en"):
            generate_pdf_task.delay(test_record.pk, language=language)
            generate_excel_task.delay(test_record.pk, language=language)
        return test_record

    def abort_test(self, test_record: TestRecord, reason: str) -> TestRecord:
        test_record.status = TestStatus.ABORTED
        test_record.abort_reason = reason
        test_record.ended_at = timezone.now()
        test_record.result_passed = False
        test_record.save(update_fields=["status", "abort_reason", "ended_at", "result_passed", "updated_at"])
        self.client.write_test_command(
            circuit=CircuitSelect(test_record.selected_circuit),
            start_request=False,
            stop_request=False,
            abort_request=True,
            phase=TestPhase.ABORTED,
            test_active=False,
        )
        PlcEventLog.objects.create(
            test_record=test_record,
            event_type=PlcEventType.FAULT,
            event_code="TEST_ABORTED",
            message=reason,
        )
        return test_record
