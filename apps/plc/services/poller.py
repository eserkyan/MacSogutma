from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from django.conf import settings
from django.utils import timezone

from apps.core.constants import PlcEventType, TestPhase
from apps.dashboard.services import DashboardPushService
from apps.plc.models import PlcEventLog, PlcRuntimeState
from apps.plc.services.live_history import append_live_history
from apps.plc.services.modbus_client import ModbusClientError, PlcModbusClient
from apps.plc.services.parser import PlcParserService
from apps.tests.models import TestRecord, TestSample

logger = logging.getLogger(__name__)


class PlcPollingService:
    def __init__(self, client: PlcModbusClient | None = None) -> None:
        self.client = client or PlcModbusClient()

    def fast_poll(self) -> PlcRuntimeState:
        runtime = PlcRuntimeState.load()
        was_connection_ok = runtime.connection_ok
        try:
            payload = self.client.fast_poll()
            parsed_live = PlcParserService.parse_record(payload.live_record)
            active_test = TestRecord.active().first()
            if active_test:
                parsed_live.test_phase = int(self._effective_phase_for_sample(active_test, parsed_live.timestamp_unix))
            runtime.plc_ready = bool(payload.status.get("PlcReady"))
            runtime.plc_fault = bool(payload.status.get("PlcFault"))
            runtime.buf_write_index = int(payload.status.get("Buf_WriteIndex", 0))
            runtime.buf_record_count = int(payload.status.get("Buf_RecordCount", 0))
            runtime.buf_buffer_size = int(payload.status.get("Buf_BufferSize", 300))
            runtime.buf_last_sequence_no = int(payload.status.get("Buf_LastSequenceNo", 0))
            runtime.plc_current_unix = int(payload.status.get("PlcCurrentUnix", 0))
            runtime.live_record_json = parsed_live.to_json()
            runtime.status_json = payload.status
            runtime.last_seen_at = timezone.now()
            runtime.connection_ok = True
            runtime.stale_data = False
            runtime.monitoring_active = True
            runtime.last_error = ""
            runtime.communication_loss_since = None
            runtime.save()
            if not was_connection_ok:
                self._log_connection_event(
                    event_code="PLC_RECONNECTED",
                    message="PLC communication restored.",
                    details_json={
                        "host": settings.PLC_CONFIG["host"],
                        "port": settings.PLC_CONFIG["port"],
                    },
                )
            append_live_history(parsed_live.to_json())
            DashboardPushService().broadcast_runtime_update(runtime)
            self._persist_live_sample_if_needed(parsed_live)
        except ModbusClientError as exc:
            logger.exception("PLC fast poll failed")
            loss_started_at = runtime.communication_loss_since or timezone.now()
            runtime.connection_ok = False
            runtime.last_error = str(exc)
            runtime.stale_data = True
            runtime.communication_loss_since = loss_started_at
            runtime.save(update_fields=["connection_ok", "last_error", "stale_data", "communication_loss_since", "updated_at"])
            if was_connection_ok:
                self._log_connection_event(
                    event_code="PLC_CONNECTION_LOST",
                    message="PLC communication lost.",
                    details_json={
                        "error": str(exc),
                        "host": settings.PLC_CONFIG["host"],
                        "port": settings.PLC_CONFIG["port"],
                        "loss_started_at": loss_started_at.isoformat(),
                    },
                )
            DashboardPushService().broadcast_runtime_update(runtime)
        return runtime

    def history_sync(self) -> int:
        runtime = PlcRuntimeState.load()
        active_test = TestRecord.active().first()
        if not settings.PLC_CONFIG["history_sync_enabled"] or not runtime.connection_ok or not active_test:
            return 0
        last_seq = active_test.samples.order_by("-sequence_no").values_list("sequence_no", flat=True).first() or 0
        current_seq = runtime.buf_last_sequence_no
        missing = max(0, current_seq - last_seq)
        if missing > runtime.buf_buffer_size:
            PlcEventLog.objects.create(
                test_record=active_test,
                event_type=PlcEventType.OVERRUN,
                event_code="PLC_HISTORY_OVERRUN",
                message="PLC history overrun detected.",
                details_json={"missing": missing, "buffer_size": runtime.buf_buffer_size},
            )
            runtime.last_overrun_at = timezone.now()
        batch = min(
            missing,
            settings.PLC_CONFIG["history_sync_batch_size"],
            settings.PLC_CONFIG["max_history_records_per_cycle"],
        )
        if batch <= 0:
            runtime.last_history_sync_at = timezone.now()
            runtime.save(update_fields=["last_history_sync_at", "last_overrun_at", "updated_at"])
            return 0
        try:
            for raw in self.client.read_history_records(start_index=last_seq, count=batch):
                parsed = PlcParserService.parse_record(raw)
                parsed.test_phase = int(self._effective_phase_for_sample(active_test, parsed.timestamp_unix))
                if not active_test.samples.filter(sequence_no=parsed.sequence_no).exists():
                    TestSample.objects.create_from_parsed(active_test, parsed)
            runtime.last_history_sync_at = timezone.now()
            runtime.save(update_fields=["last_history_sync_at", "last_overrun_at", "updated_at"])
            return batch
        except ModbusClientError as exc:
            logger.exception("PLC history sync failed")
            runtime.connection_ok = False
            runtime.stale_data = True
            runtime.last_error = str(exc)
            runtime.communication_loss_since = runtime.communication_loss_since or timezone.now()
            runtime.save(
                update_fields=[
                    "connection_ok",
                    "stale_data",
                    "last_error",
                    "communication_loss_since",
                    "last_overrun_at",
                    "updated_at",
                ]
            )
            DashboardPushService().broadcast_runtime_update(runtime)
            return 0

    def _persist_live_sample_if_needed(self, parsed_live: object) -> None:
        active_test = TestRecord.active().first()
        if not active_test:
            return
        if active_test.samples.filter(sequence_no=parsed_live.sequence_no).exists():
            return
        TestSample.objects.create_from_parsed(active_test, parsed_live)

    def _effective_phase_for_sample(self, test_record: TestRecord, timestamp_unix: int) -> TestPhase:
        if not test_record.started_at:
            return TestPhase.IDLE
        sample_time = datetime.fromtimestamp(timestamp_unix, tz=UTC)
        start_end = test_record.started_at + timedelta(seconds=test_record.start_duration_sec_snapshot)
        stable_end = start_end + timedelta(seconds=test_record.stable_duration_sec_snapshot)
        stop_end = stable_end + timedelta(seconds=test_record.stop_duration_sec_snapshot)

        if sample_time < start_end:
            return TestPhase.START
        if sample_time < stable_end:
            return TestPhase.STABLE
        if sample_time < stop_end:
            return TestPhase.STOP
        return TestPhase.STOP

    @staticmethod
    def _log_connection_event(event_code: str, message: str, details_json: dict[str, object]) -> None:
        PlcEventLog.objects.create(
            event_type=PlcEventType.COMMUNICATION,
            event_code=event_code,
            message=message,
            details_json=details_json,
        )
