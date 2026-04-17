from __future__ import annotations

import logging
from dataclasses import dataclass

from django.conf import settings
from django.utils import timezone

from apps.core.constants import PlcEventType
from apps.plc.models import PlcEventLog, PlcRuntimeState
from apps.plc.services.modbus_client import PlcModbusClient

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TimeSyncResult:
    performed: bool
    drift_seconds: int


class PlcTimeSyncService:
    def __init__(self, client: PlcModbusClient | None = None) -> None:
        self.client = client or PlcModbusClient()

    def run(self, force: bool = False) -> TimeSyncResult:
        runtime = PlcRuntimeState.load()
        if not settings.PLC_CONFIG["time_sync_enabled"] and not force:
            return TimeSyncResult(performed=False, drift_seconds=0)
        python_unix = int(timezone.now().timestamp())
        drift = python_unix - runtime.plc_current_unix if runtime.plc_current_unix else 0
        if force or abs(drift) >= settings.PLC_CONFIG["time_sync_drift_threshold_sec"]:
            self.client.sync_time(python_unix)
            runtime.last_time_sync_at = timezone.now()
            runtime.last_time_sync_drift_sec = drift
            runtime.save(update_fields=["last_time_sync_at", "last_time_sync_drift_sec", "updated_at"])
            PlcEventLog.objects.create(
                event_type=PlcEventType.TIME_SYNC,
                event_code="PLC_TIME_SYNC",
                message="PLC time synchronization executed.",
                details_json={"drift_seconds": drift, "forced": force},
            )
            logger.info("PLC time sync performed", extra={"drift": drift})
            return TimeSyncResult(performed=True, drift_seconds=drift)
        return TimeSyncResult(performed=False, drift_seconds=drift)
