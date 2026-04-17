from __future__ import annotations

import hashlib
import json

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.cache import cache
from django.utils import timezone

from apps.plc.models import PlcRuntimeState
from apps.plc.services.live_history import get_live_history
from apps.tests.models import TestRecord


class DashboardPushService:
    group_name = "dashboard_live"
    throttle_seconds = 2.0
    last_hash_cache_key = "dashboard_push:last_hash"
    last_sent_cache_key = "dashboard_push:last_sent_ts"

    def broadcast_runtime_update(self, runtime: PlcRuntimeState) -> None:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        active_test = TestRecord.active().order_by("-created_at").first()
        recent_tests = list(
            TestRecord.objects.select_related("company", "product_model", "recipe")
            .order_by("-created_at")[:10]
        )
        live_history = get_live_history()
        payload = {
            "type": "dashboard.update",
            "connection_ok": runtime.connection_ok,
            "plc_ready": runtime.plc_ready,
            "plc_fault": runtime.plc_fault,
            "monitoring_active": runtime.monitoring_active,
            "stale_data": runtime.stale_data,
            "last_seen_at": runtime.last_seen_at.isoformat() if runtime.last_seen_at else None,
            "data_age_seconds": int((timezone.now() - runtime.last_seen_at).total_seconds()) if runtime.last_seen_at else None,
            "live_record": runtime.live_record_json or {},
            "live_history": live_history,
            "status_json": runtime.status_json or {},
            "has_active_test": active_test is not None,
            "active_test_id": active_test.pk if active_test else None,
            "active_test_no": active_test.test_no if active_test else None,
            "active_test_summary": {
                "company_name": active_test.company.name if active_test else "",
                "model_name": active_test.product_model.model_name if active_test else "",
                "recipe_name": active_test.recipe_name_snapshot if active_test else "",
                "status": active_test.status if active_test else "",
                "selected_circuit": int(active_test.selected_circuit) if active_test else 0,
                "current_phase": int(active_test.current_phase.value) if active_test else 0,
            },
            "recent_tests": [
                {
                    "id": item.pk,
                    "test_no": item.test_no,
                    "status": item.status,
                    "company_name": item.company.name,
                    "model_name": item.product_model.model_name,
                    "is_active": item.status in TestRecord.active_statuses(),
                }
                for item in recent_tests
            ],
            "active_test_meta": {
                "started_at": active_test.started_at.isoformat() if active_test and active_test.started_at else None,
                "stable_started_at": active_test.stable_started_at.isoformat()
                if active_test and active_test.stable_started_at
                else None,
                "stop_started_at": active_test.stop_started_at.isoformat() if active_test and active_test.stop_started_at else None,
                "start_duration_sec": active_test.start_duration_sec_snapshot if active_test else 0,
                "stable_duration_sec": active_test.stable_duration_sec_snapshot if active_test else 0,
                "stop_duration_sec": active_test.stop_duration_sec_snapshot if active_test else 0,
                "current_phase": int(active_test.current_phase.value) if active_test else 0,
            },
            "ui_state": {
                "has_active_test": active_test is not None,
                "active_test": {
                    "id": active_test.pk if active_test else None,
                    "test_no": active_test.test_no if active_test else "",
                    "status": active_test.status if active_test else "",
                    "selected_circuit": int(active_test.selected_circuit) if active_test else 0,
                    "current_phase": int(active_test.current_phase.value) if active_test else 0,
                    "company_name": active_test.company.name if active_test else "",
                    "model_name": active_test.product_model.model_name if active_test else "",
                    "recipe_name": active_test.recipe_name_snapshot if active_test else "",
                },
            },
        }
        if not self._should_broadcast(payload):
            return
        async_to_sync(channel_layer.group_send)(
            self.group_name,
            {"type": "dashboard_update", "payload": payload},
        )

    def _should_broadcast(self, payload: dict[str, object]) -> bool:
        now_ts = timezone.now().timestamp()
        payload_hash = hashlib.sha1(
            json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        last_hash = cache.get(self.last_hash_cache_key)
        last_sent_ts = float(cache.get(self.last_sent_cache_key, 0.0) or 0.0)

        if (now_ts - last_sent_ts) < self.throttle_seconds:
            return False

        if payload_hash == last_hash:
            return False

        cache.set(self.last_hash_cache_key, payload_hash, timeout=None)
        cache.set(self.last_sent_cache_key, now_ts, timeout=None)
        return True
