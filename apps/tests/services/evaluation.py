from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from apps.core.constants import CircuitSelect, EvaluationPhase, TestPhase, TestStatus
from apps.core.services.tag_registry import TagRegistryService
from apps.recipes.services.phase_limits import has_active_limit, phase_limit
from apps.plc.services.parser import validity_bit_is_set
from apps.tests.models import TestEvaluationResult, TestRecord, TestSample


@dataclass(slots=True)
class EvaluationSummary:
    passed: bool
    message: str


class TestEvaluationService:
    EVALUATED_PHASES: tuple[TestPhase, ...] = (TestPhase.START, TestPhase.STABLE, TestPhase.STOP)

    def __init__(self) -> None:
        self.registry = TagRegistryService()

    def evaluate(self, test_record: TestRecord) -> EvaluationSummary:
        parameter_definitions = self.registry.get_parameter_definitions(include_limits_only=True)
        TestEvaluationResult.objects.filter(test_record=test_record).delete()
        failures: list[str] = []

        for phase in self.EVALUATED_PHASES:
            evaluation_phase = EvaluationPhase.from_test_phase(phase)
            for parameter_code in self._parameter_codes(CircuitSelect(test_record.selected_circuit)):
                if parameter_code not in parameter_definitions:
                    continue
                raw_limit = test_record.limits_snapshot_json.get(parameter_code, {})
                if not has_active_limit(raw_limit, evaluation_phase):
                    continue
                limit = phase_limit(raw_limit, evaluation_phase)
                values = self.phase_valid_values(test_record, parameter_code, phase)
                avg_value = self._average(values)
                passed, message = self._evaluate_single(limit, avg_value, evaluation_phase)
                TestEvaluationResult.objects.create(
                    test_record=test_record,
                    parameter_code=parameter_code,
                    parameter_name=str(parameter_definitions[parameter_code]["label"]),
                    phase_used=evaluation_phase,
                    avg_value=avg_value,
                    min_enabled=bool(limit.get("min_enabled")),
                    min_limit=limit.get("min_value"),
                    max_enabled=bool(limit.get("max_enabled")),
                    max_limit=limit.get("max_value"),
                    passed=passed,
                    message=message,
                )
                if passed is False:
                    failures.append(f"{evaluation_phase.value}:{parameter_code}: {message}")

        if failures:
            test_record.status = TestStatus.COMPLETED_FAIL
            test_record.result_passed = False
            test_record.fail_reason_summary = "\n".join(failures)
        else:
            test_record.status = TestStatus.COMPLETED_PASS
            test_record.result_passed = True
            test_record.fail_reason_summary = ""
        test_record.save(update_fields=["status", "result_passed", "fail_reason_summary", "updated_at"])
        return EvaluationSummary(passed=not failures, message=test_record.fail_reason_summary or "Passed.")

    def reconcile_completed_result(self, test_record: TestRecord) -> TestRecord:
        if test_record.status not in {TestStatus.COMPLETED_PASS, TestStatus.COMPLETED_FAIL}:
            return test_record
        self.evaluate(test_record)
        test_record.refresh_from_db()
        return test_record

    def stable_stats(self, test_record: TestRecord, parameter_code: str) -> dict[str, Decimal | None]:
        values = self.phase_valid_values(test_record, parameter_code, TestPhase.STABLE)
        if not values:
            return {"min_value": None, "avg_value": None, "max_value": None}
        return {
            "min_value": min(values),
            "avg_value": self._average(values),
            "max_value": max(values),
        }

    def phase_stats(self, test_record: TestRecord, parameter_code: str, phase: TestPhase) -> dict[str, Decimal | None]:
        values = self.phase_valid_values(test_record, parameter_code, phase)
        if not values:
            return {"min_value": None, "avg_value": None, "max_value": None}
        return {
            "min_value": min(values),
            "avg_value": self._average(values),
            "max_value": max(values),
        }

    def phase_valid_values(self, test_record: TestRecord, parameter_code: str, phase: TestPhase) -> list[Decimal]:
        queryset = test_record.samples.filter(test_phase=phase).order_by("timestamp_unix", "sequence_no")
        values: list[Decimal] = []
        for sample in queryset:
            if not self._is_valid(sample, parameter_code):
                continue
            raw_value = sample.get_value(parameter_code)
            if raw_value is None:
                continue
            values.append(Decimal(str(raw_value)))
        return values

    def _is_valid(self, sample: TestSample, parameter_code: str) -> bool:
        bit_index = self.registry.get_validity_tag_map().get(parameter_code)
        if bit_index is None:
            return True
        return validity_bit_is_set(sample.validity_word1, sample.validity_word2, bit_index)

    @staticmethod
    def _average(values: list[Decimal]) -> Decimal | None:
        if not values:
            return None
        return sum(values) / Decimal(len(values))

    def _evaluate_single(
        self,
        limit: dict[str, object],
        avg_value: Decimal | None,
        phase: EvaluationPhase,
    ) -> tuple[bool | None, str]:
        phase_name = phase.value.title()
        if avg_value is None:
            return None, f"No valid {phase_name} samples were available."
        if limit.get("min_enabled") and limit.get("min_value") is not None:
            if avg_value < Decimal(str(limit["min_value"])):
                return False, f"Average {avg_value} is below minimum limit {limit['min_value']}."
        if limit.get("max_enabled") and limit.get("max_value") is not None:
            if avg_value > Decimal(str(limit["max_value"])):
                return False, f"Average {avg_value} is above maximum limit {limit['max_value']}."
        return True, "Passed."

    def _parameter_codes(self, circuit: CircuitSelect) -> list[str]:
        codes = set(self.registry.get_parameter_codes_for_scope("shared"))
        if circuit in {CircuitSelect.CIRCUIT_1, CircuitSelect.BOTH}:
            codes.update(self.registry.get_parameter_codes_for_scope("circuit1"))
        if circuit in {CircuitSelect.CIRCUIT_2, CircuitSelect.BOTH}:
            codes.update(self.registry.get_parameter_codes_for_scope("circuit2"))
        return sorted(codes)
