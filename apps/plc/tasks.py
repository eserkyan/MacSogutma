from __future__ import annotations

from celery import shared_task

from apps.plc.services.poller import PlcPollingService
from apps.plc.services.time_sync import PlcTimeSyncService


@shared_task
def fast_poll_task() -> dict[str, object]:
    runtime = PlcPollingService().fast_poll()
    return {
        "connection_ok": runtime.connection_ok,
        "last_seen_at": runtime.last_seen_at.isoformat() if runtime.last_seen_at else None,
    }


@shared_task
def history_sync_task() -> int:
    return PlcPollingService().history_sync()


@shared_task
def periodic_time_sync_task() -> dict[str, object]:
    result = PlcTimeSyncService().run()
    return {"performed": result.performed, "drift_seconds": result.drift_seconds}
