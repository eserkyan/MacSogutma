from __future__ import annotations

import json
from django.utils import timezone
from django.views.generic import TemplateView

from apps.core.services.tag_registry import TagRegistryService
from apps.core.ui_translations import get_text
from apps.plc.models import PlcEventLog, PlcRuntimeState
from apps.plc.services.live_history import get_live_history
from apps.tests.models import TestRecord


class DashboardView(TemplateView):
    template_name = "dashboard/index.html"

    STATUS_FLAG_LABELS = {
        "test_active": {"tr": "Test Aktif", "en": "Test Active"},
        "alarm_active": {"tr": "Alarm Aktif", "en": "Alarm Active"},
        "comp1_rng": {"tr": "Comp1 RNG", "en": "Comp1 RNG"},
        "comp2_rng": {"tr": "Comp2 RNG", "en": "Comp2 RNG"},
    }

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        context = super().get_context_data(**kwargs)
        runtime = PlcRuntimeState.load()
        registry = TagRegistryService()
        live_record = runtime.live_record_json or {}
        values = live_record.get("values", {})
        validity = live_record.get("validity", {})
        status_flags = live_record.get("status_flags", {})
        context["runtime"] = runtime
        language = self.request.session.get("ui_language", "tr")
        context["recent_tests"] = TestRecord.objects.select_related("company", "product_model", "recipe")[:10]
        context["active_test_statuses"] = TestRecord.active_statuses()
        context["active_test"] = TestRecord.active().select_related("company", "product_model", "recipe").first()
        context["commanded_circuit_label"] = (
            self._circuit_label(int(context["active_test"].selected_circuit), language)
            if context["active_test"] else "-"
        )
        context["comp1_rng"] = bool(status_flags.get("comp1_rng"))
        context["comp2_rng"] = bool(status_flags.get("comp2_rng"))
        live_history = get_live_history()
        trend_series_map = self._build_row_trend_series(context["active_test"], live_history, registry)
        context["recent_events"] = PlcEventLog.objects.select_related("test_record")[:8]
        context["dashboard_sections"] = self._build_sections(values, validity, language, trend_series_map, registry)
        context["live_status_flags"] = [
            (self.STATUS_FLAG_LABELS.get(str(key), {}).get(language, str(key)), value)
            for key, value in status_flags.items()
        ]
        context["live_meta"] = [
            ("Sira Numarasi", live_record.get("sequence_no")),
            ("Zaman Damgasi", live_record.get("timestamp_unix")),
            ("Kayit Fazi", live_record.get("test_phase")),
            ("Durum Word", live_record.get("status_word")),
            ("Validity Word 1", live_record.get("validity_word1")),
            ("Validity Word 2", live_record.get("validity_word2")),
            ("Son Veri Zamani (Yerel Saat)", self._local_display(runtime.last_seen_at, language)),
            ("PLC Zaman Damgasi", runtime.plc_current_unix),
            ("Zaman Senkron Sapmasi", runtime.last_time_sync_drift_sec),
        ]
        context["status_meta"] = [
            ("Hazir", runtime.plc_ready),
            ("Ariza", runtime.plc_fault),
            ("Comp1 RNG", bool(status_flags.get("comp1_rng"))),
            ("Comp2 RNG", bool(status_flags.get("comp2_rng"))),
            ("Komutlanan Devre", context["commanded_circuit_label"]),
            ("Baglanti Durumu", runtime.connection_ok),
            ("Bayat Veri", runtime.stale_data),
            ("Izleme Aktif", runtime.monitoring_active),
            ("Yazma Indeksi", runtime.buf_write_index),
            ("Kayit Sayisi", runtime.buf_record_count),
            ("Buffer Boyutu", runtime.buf_buffer_size),
            ("Son Sekans", runtime.buf_last_sequence_no),
        ]
        context["show_data_error"] = (
            not runtime.connection_ok
            or runtime.stale_data
            or not live_record
            or runtime.last_seen_at is None
        )
        context["data_error_message"] = self._build_error_message(runtime, live_record, language)
        context["data_age_seconds"] = self._data_age_seconds(runtime)
        return context

    def _build_sections(
        self,
        values: dict[str, object],
        validity: dict[str, bool],
        language: str,
        trend_series_map: dict[str, dict[str, object]],
        registry: TagRegistryService,
    ) -> list[dict[str, object]]:
        parameter_definitions = registry.get_parameter_definitions(language=language)
        sections: list[dict[str, object]] = []
        for group in registry.get_chart_groups(language=language):
            rows = []
            for dataset in group["datasets"]:
                key = str(dataset["key"])
                meta = parameter_definitions.get(key, {"label": key, "unit": ""})
                rows.append(
                    {
                        "code": key,
                        "label": meta["label"],
                        "unit": meta["unit"],
                        "value": values.get(key),
                        "valid": validity.get(key),
                        "trend_labels_json": json.dumps(trend_series_map.get(key, {}).get("labels", [])),
                        "trend_series_json": json.dumps(trend_series_map.get(key, {}).get("series", [])),
                        "trend_color": trend_series_map.get(key, {}).get("color", "#2563eb"),
                    }
                )
            sections.append({"title": self._group_title(group, language), "rows": rows})
        return sections

    def _build_error_message(self, runtime: PlcRuntimeState, live_record: dict[str, object], language: str) -> str:
        if not runtime.connection_ok:
            return runtime.last_error or get_text("dashboard.error_connection", language)
        if runtime.stale_data:
            return get_text("dashboard.error_stale", language)
        if not live_record:
            return get_text("dashboard.error_live_record", language)
        if runtime.plc_fault:
            return get_text("dashboard.error_fault", language)
        return ""

    def _data_age_seconds(self, runtime: PlcRuntimeState) -> int | None:
        if runtime.last_seen_at is None:
            return None
        return int((timezone.now() - runtime.last_seen_at).total_seconds())

    @staticmethod
    def _local_display(value: object, language: str = "tr") -> str:
        if value is None:
            return "-"
        if hasattr(value, "astimezone"):
            localized = timezone.localtime(value)
            if language == "en":
                return localized.strftime("%Y-%m-%d %H:%M:%S")
            return localized.strftime("%d.%m.%Y %H:%M:%S")
        return str(value)

    def _build_row_trend_series(
        self,
        active_test: TestRecord | None,
        live_history: list[dict[str, object]],
        registry: TagRegistryService,
    ) -> dict[str, dict[str, object]]:
        labels, values_map = self._extract_trend_source(active_test, live_history, registry)
        if not labels:
            return {}
        color_map = {tag["code"]: tag["chart_color"] for tag in registry.get_tags()}
        parameter_codes = list(registry.get_parameter_definitions(language="tr").keys())
        trend_map: dict[str, dict[str, object]] = {}
        for code in parameter_codes:
            trend_map[code] = {
                "labels": labels,
                "series": values_map.get(code, []),
                "color": color_map.get(code, "#2563eb"),
            }
        return trend_map

    def _extract_trend_source(
        self,
        active_test: TestRecord | None,
        live_history: list[dict[str, object]],
        registry: TagRegistryService,
    ) -> tuple[list[int], dict[str, list[float | None]]]:
        if active_test:
            samples = list(active_test.samples.order_by("-timestamp_unix", "-sequence_no")[:20])
            samples.reverse()
            if samples:
                labels = [sample.sequence_no for sample in samples]
                values_map = {
                    code: [float(sample.get_value(code)) if sample.get_value(code) is not None else None for sample in samples]
                    for code in registry.get_parameter_definitions()
                }
                return labels, values_map
        if not live_history:
            return [], {}
        labels = [int(item.get("sequence_no", index + 1)) for index, item in enumerate(live_history)]
        values_map = {
            code: [
                float((item.get("values") or {}).get(code)) if (item.get("values") or {}).get(code) is not None else None
                for item in live_history
            ]
            for code in registry.get_parameter_definitions()
        }
        return labels, values_map

    @staticmethod
    def _group_title(group: dict[str, object], language: str) -> str:
        slug = str(group.get("chart_id", "")).replace("Chart", "")
        mapping = {
            "pressure": get_text("dashboard.pressure", language),
            "temperature": get_text("dashboard.temperature", language),
            "ambient": get_text("dashboard.ambient", language),
            "comp1Electrical": get_text("dashboard.comp1", language),
            "comp2Electrical": get_text("dashboard.comp2", language),
        }
        return mapping.get(slug, str(group.get("title", slug)))

    @staticmethod
    def _circuit_label(value: int, language: str) -> str:
        labels = {
            0: {"tr": "-", "en": "-"},
            1: {"tr": "Devre 1", "en": "Circuit 1"},
            2: {"tr": "Devre 2", "en": "Circuit 2"},
            3: {"tr": "Devre 1 + Devre 2", "en": "Circuit 1 + Circuit 2"},
        }
        return labels.get(int(value), {"tr": str(value), "en": str(value)}).get(language, str(value))
