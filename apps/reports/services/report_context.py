from __future__ import annotations

import base64
from html import escape

from apps.core.constants import SAMPLE_META_FIELDS, TestPhase
from apps.core.constants import TestStatus
from apps.core.services.tag_registry import TagRegistryService
from apps.core.services.status_labels import get_test_status_label
from apps.core.ui_translations import get_text
from apps.recipes.services.phase_limits import has_active_limit, phase_limit
from apps.reports.services.chart_builder import ChartBuilderService
from apps.tests.models import TestRecord
from apps.tests.services.evaluation import TestEvaluationService
from apps.tests.services.limit_analysis import LimitAnalysisService


class ReportContextService:
    def build(self, test_record: TestRecord, language: str = "tr") -> dict[str, object]:
        evaluation_service = TestEvaluationService()
        test_record = evaluation_service.reconcile_completed_result(test_record)
        limit_service = LimitAnalysisService()
        registry = TagRegistryService()
        parameter_definitions = registry.get_parameter_definitions(language=language)
        parameter_codes = self._parameter_codes_for_test(test_record, registry)
        excursions = limit_service.analyze(test_record)

        phase_result_map = {(result.parameter_code, str(result.phase_used)): result for result in test_record.evaluation_results.all()}
        evaluation_rows = []
        for parameter_code in parameter_codes:
            definition = parameter_definitions.get(parameter_code)
            if not definition:
                continue
            result = phase_result_map.get((parameter_code, "STABLE"))
            stats = evaluation_service.stable_stats(test_record, parameter_code)
            stable_limit = phase_limit(test_record.limits_snapshot_json.get(parameter_code, {}), 2)
            evaluation_rows.append(
                {
                    "parameter_name": str(definition.get("label", parameter_code)),
                    "parameter_code": parameter_code,
                    "unit": str(definition.get("unit", "")),
                    "measured_min": stats["min_value"],
                    "avg_value": result.avg_value if result else stats["avg_value"],
                    "measured_max": stats["max_value"],
                    "limit_min": (
                        result.min_limit
                        if result and result.min_enabled
                        else stable_limit.get("min_value")
                        if stable_limit.get("min_enabled")
                        else None
                    ),
                    "limit_max": (
                        result.max_limit
                        if result and result.max_enabled
                        else stable_limit.get("max_value")
                        if stable_limit.get("max_enabled")
                        else None
                    ),
                    "passed": result.passed if result else None,
                    "message": self._build_stable_row_message(test_record, parameter_code, result, stats["avg_value"], language),
                }
            )

        phase_stat_sections = [
            {
                "slug": "start",
                "title": get_text("tests.start_stats", language),
                "rows": self._phase_stat_rows(test_record, parameter_codes, parameter_definitions, 1, phase_result_map, language),
            },
            {
                "slug": "stop",
                "title": get_text("tests.stop_stats", language),
                "rows": self._phase_stat_rows(test_record, parameter_codes, parameter_definitions, 3, phase_result_map, language),
            },
        ]

        limit_rows = [
            {
                "parameter_name": item.parameter_name,
                "parameter_code": item.parameter_code,
                "phase_name": self._phase_label(item.phase_value, language),
                "elapsed_seconds": item.elapsed_seconds,
                "sample_value": item.sample_value,
                "unit": item.unit,
                "limit_type": item.limit_type,
                "limit_value": item.limit_value,
                "message": self._localize_limit_message(item.limit_type, item.sample_value, item.limit_value, language),
            }
            for item in excursions
        ]

        sample_columns = list(SAMPLE_META_FIELDS) + [
            (field_name, f"{definition['label']} ({definition['unit']})")
            for field_name, definition in parameter_definitions.items()
        ]
        export_sample_columns = [
            ("timestamp_unix", "Timestamp Unix"),
            ("elapsed_seconds", "Elapsed Sec"),
            ("phase_name", "Phase"),
        ] + [
            (field_name, f"{definition['label']} ({definition['unit']})")
            for field_name, definition in parameter_definitions.items()
        ]

        samples_by_phase = {
            "start": self._sample_rows(test_record, 1, language, parameter_definitions),
            "stable": self._sample_rows(test_record, 2, language, parameter_definitions),
            "stop": self._sample_rows(test_record, 3, language, parameter_definitions),
        }

        return {
            "language": language,
            "test_record": test_record,
            "test_status_label": get_test_status_label(test_record.status, language),
            "overall_result_label": self._overall_result_label(test_record, language),
            "overall_result_class": self._overall_result_class(test_record),
            "generated_at": test_record.pdf_generated_at,
            "evaluation_rows": evaluation_rows,
            "phase_stat_sections": phase_stat_sections,
            "limit_rows": limit_rows,
            "sample_columns": sample_columns,
            "export_sample_columns": export_sample_columns,
            "samples_by_phase": samples_by_phase,
            "all_samples": self._all_sample_rows(test_record, language, parameter_definitions),
            "chart_sections": self._build_chart_sections(test_record, language),
            "labels": self._labels(language),
        }

    def _sample_rows(
        self,
        test_record: TestRecord,
        phase_value: int,
        language: str,
        parameter_definitions: dict[str, dict[str, str]] | None = None,
    ) -> list[dict[str, object]]:
        parameter_definitions = parameter_definitions or TagRegistryService().get_parameter_definitions(language=language)
        return [
            self._sample_to_row(sample, test_record, language, parameter_definitions)
            for sample in test_record.samples.filter(test_phase=phase_value).order_by("timestamp_unix", "sequence_no")
        ]

    def _all_sample_rows(
        self,
        test_record: TestRecord,
        language: str,
        parameter_definitions: dict[str, dict[str, str]] | None = None,
    ) -> list[dict[str, object]]:
        parameter_definitions = parameter_definitions or TagRegistryService().get_parameter_definitions(language=language)
        return [
            self._sample_to_row(sample, test_record, language, parameter_definitions)
            for sample in test_record.samples.order_by("timestamp_unix", "sequence_no")
        ]

    def _sample_to_row(
        self,
        sample: object,
        test_record: TestRecord,
        language: str,
        parameter_definitions: dict[str, dict[str, str]],
    ) -> dict[str, object]:
        elapsed_seconds = None
        if test_record.started_at:
            elapsed_seconds = float(sample.timestamp_unix) - float(test_record.started_at.timestamp())
        row = {
            "sequence_no": sample.sequence_no,
            "timestamp_unix": sample.timestamp_unix,
            "elapsed_seconds": elapsed_seconds,
            "phase_name": self._phase_label(int(sample.test_phase), language),
            "status_word": sample.status_word,
            "validity_word1": sample.validity_word1,
            "validity_word2": sample.validity_word2,
        }
        for field_name in parameter_definitions:
            row[field_name] = sample.get_value(field_name)
        return row

    @staticmethod
    def _phase_label(phase_value: int, language: str) -> str:
        mapping = {
            0: get_text("tests.phase_idle", language),
            1: get_text("tests.phase_start", language),
            2: get_text("tests.phase_stable", language),
            3: get_text("tests.phase_stop", language),
            4: get_text("tests.phase_manual", language),
            5: get_text("tests.phase_aborted", language),
        }
        return mapping.get(int(phase_value), str(phase_value))

    @staticmethod
    def _format_number(value: object) -> str:
        if value is None or value == "":
            return "-"
        return f"{float(value):.2f}"

    def _localize_evaluation_message(self, result: object, language: str) -> str:
        if result.avg_value is None:
            return get_text("tests.msg_no_valid_stable", language)
        if result.min_enabled and result.min_limit is not None and result.avg_value < result.min_limit:
            return get_text("tests.msg_avg_below", language).format(
                value=self._format_number(result.avg_value),
                limit=self._format_number(result.min_limit),
            )
        if result.max_enabled and result.max_limit is not None and result.avg_value > result.max_limit:
            return get_text("tests.msg_avg_above", language).format(
                value=self._format_number(result.avg_value),
                limit=self._format_number(result.max_limit),
            )
        return get_text("tests.msg_passed", language)

    def _localize_limit_message(self, limit_type: str, sample_value: float, limit_value: float, language: str) -> str:
        if limit_type == "MIN":
            return get_text("tests.msg_limit_below", language).format(
                value=self._format_number(sample_value),
                limit=self._format_number(limit_value),
            )
        return get_text("tests.msg_limit_above", language).format(
            value=self._format_number(sample_value),
            limit=self._format_number(limit_value),
        )

    def _build_stable_row_message(
        self,
        test_record: TestRecord,
        parameter_code: str,
        result: object | None,
        avg_value: object,
        language: str,
    ) -> str:
        if result is not None:
            return self._localize_evaluation_message(result, language)
        if avg_value is None:
            return get_text("tests.msg_no_valid_stable", language)
        raw_limit = test_record.limits_snapshot_json.get(parameter_code, {})
        if not has_active_limit(raw_limit, 2):
            return get_text("tests.msg_no_limit_defined", language)
        return "-"

    @staticmethod
    def _labels(language: str) -> dict[str, str]:
        return {
            "report_title": "HVAC Test Raporu" if language == "tr" else "HVAC Test Report",
            "report_subtitle": (
                "Teknik test dokumantasyonu ve kabul ozeti"
                if language == "tr"
                else "Technical test documentation and acceptance summary"
            ),
            "generated_at": "Olusturma Zamani" if language == "tr" else "Generated at",
            "test_general_info": get_text("tests.general_info", language),
            "test_no": get_text("tests.test_no", language),
            "company": get_text("tests.company", language),
            "model": get_text("products.name", language),
            "recipe": get_text("tests.recipe", language),
            "operator": get_text("form.operator_name", language),
            "revision": get_text("recipes.rev", language),
            "circuit": get_text("form.circuit", language),
            "phase_durations": "Faz Sureleri" if language == "tr" else "Phase Durations",
            "start": get_text("tests.phase_start", language),
            "stable": get_text("tests.phase_stable", language),
            "stop": get_text("tests.phase_stop", language),
            "sec": "sn" if language == "tr" else "sec",
            "recipe_info": get_text("recipes.info", language),
            "recipe_code": "Recete Kodu" if language == "tr" else "Recipe Code",
            "notes": get_text("form.notes", language),
            "general_result": "Genel Sonuc" if language == "tr" else "General Result",
            "status_pass": "Gecti" if language == "tr" else "PASS",
            "status_fail": "Kaldi" if language == "tr" else "FAIL",
            "status_aborted": "Iptal Edildi" if language == "tr" else "ABORTED",
            "status_na": "YOK" if language == "tr" else "N/A",
            "traceability_line_1": (
                "Tum fazlar teknik izlenebilirlik icin rapora dahil edilmistir."
                if language == "tr"
                else "All phases are included for technical traceability."
            ),
            "traceability_line_2": (
                "Aktif limiti olan fazlar kendi faz ortalama degerleri ile degerlendirilir."
                if language == "tr"
                else "Acceptance criteria are evaluated using phase average values for phases with active limits."
            ),
            "abort_info": "Abort Bilgisi" if language == "tr" else "Abort Information",
            "parameter": get_text("common.parameter", language),
            "unit": get_text("common.unit", language),
            "status": get_text("common.status", language),
            "measured_min": get_text("tests.measured_min", language),
            "measured_max": get_text("tests.measured_max", language),
            "limit_min": get_text("tests.limit_min", language),
            "limit_max": get_text("tests.limit_max", language),
            "message": get_text("tests.message", language),
            "limit_excursions": get_text("tests.limit_excursions", language),
            "phase_name": get_text("tests.phase_name", language),
            "elapsed_time": get_text("tests.elapsed_time", language),
            "measured_value": get_text("tests.measured_value", language),
            "limit_type": get_text("tests.limit_type", language),
            "limit_value": get_text("tests.limit_value", language),
            "stable_eval": get_text("tests.stable_eval", language),
            "no_limit_excursion": get_text("tests.no_limit_excursion", language),
            "whole_test_charts": get_text("tests.whole_test_charts", language),
            "start_phase_charts": get_text("tests.start_phase_charts", language),
            "stable_phase_charts": get_text("tests.stable_phase_charts", language),
            "stop_phase_charts": get_text("tests.stop_phase_charts", language),
        }

    def _phase_stat_rows(
        self,
        test_record: TestRecord,
        parameter_codes: list[str],
        parameter_definitions: dict[str, dict[str, str]],
        phase_value: int,
        phase_result_map: dict[tuple[str, str], object],
        language: str,
    ) -> list[dict[str, object]]:
        evaluation_service = TestEvaluationService()
        rows: list[dict[str, object]] = []
        phase_key = "START" if phase_value == 1 else "STOP" if phase_value == 3 else "STABLE"
        for parameter_code in parameter_codes:
            definition = parameter_definitions.get(parameter_code)
            if not definition:
                continue
            limit = phase_limit(test_record.limits_snapshot_json.get(parameter_code, {}), phase_value)
            stats = evaluation_service.phase_stats(test_record, parameter_code, TestPhase(phase_value))
            has_limit = has_active_limit(test_record.limits_snapshot_json.get(parameter_code, {}), phase_value)
            result = phase_result_map.get((parameter_code, phase_key))
            rows.append(
                {
                    "parameter_code": parameter_code,
                    "parameter_name": str(definition.get("label", parameter_code)),
                    "unit": str(definition.get("unit", "")),
                    "min_enabled": bool(limit.get("min_enabled")),
                    "min_limit": limit.get("min_value"),
                    "max_enabled": bool(limit.get("max_enabled")),
                    "max_limit": limit.get("max_value"),
                    "stats": {
                        "min_value": float(stats["min_value"]) if stats["min_value"] is not None else None,
                        "avg_value": float(stats["avg_value"]) if stats["avg_value"] is not None else None,
                        "max_value": float(stats["max_value"]) if stats["max_value"] is not None else None,
                    },
                    "avg_value": result.avg_value if result else stats["avg_value"],
                    "passed": result.passed if result else None,
                    "has_limit": has_limit,
                    "message": self._build_phase_row_message(
                        test_record,
                        parameter_code,
                        result,
                        stats["avg_value"],
                        language,
                        TestPhase(phase_value),
                    ),
                }
            )
        return rows

    def _build_phase_row_message(
        self,
        test_record: TestRecord,
        parameter_code: str,
        result: object | None,
        avg_value: object,
        language: str,
        phase: TestPhase,
    ) -> str:
        if result is not None:
            if result.avg_value is None:
                phase_name = self._phase_label(int(phase), language)
                return get_text("tests.msg_no_valid_phase", language).format(phase=phase_name)
            return self._localize_evaluation_message(result, language)
        if avg_value is None:
            if phase == TestPhase.STABLE:
                return get_text("tests.msg_no_valid_stable", language)
            phase_name = self._phase_label(int(phase), language)
            return get_text("tests.msg_no_valid_phase", language).format(phase=phase_name)
        raw_limit = test_record.limits_snapshot_json.get(parameter_code, {})
        if not has_active_limit(raw_limit, int(phase)):
            return get_text("tests.msg_no_limit_defined", language)
        return "-"

    @staticmethod
    def _overall_result_class(test_record: TestRecord) -> str:
        if test_record.status == TestStatus.COMPLETED_PASS:
            return "pass"
        return "fail"

    @staticmethod
    def _overall_result_label(test_record: TestRecord, language: str) -> str:
        if test_record.status == TestStatus.COMPLETED_PASS:
            return "Gecti" if language == "tr" else "PASS"
        if test_record.status == TestStatus.ABORTED:
            return "Iptal Edildi" if language == "tr" else "ABORTED"
        return "Kaldi" if language == "tr" else "FAILED"

    def _parameter_codes_for_test(self, test_record: TestRecord, registry: TagRegistryService) -> list[str]:
        circuit = int(test_record.selected_circuit)
        codes = set(registry.get_parameter_codes_for_scope("shared"))
        if circuit in {1, 3}:
            codes.update(registry.get_parameter_codes_for_scope("circuit1"))
        if circuit in {2, 3}:
            codes.update(registry.get_parameter_codes_for_scope("circuit2"))
        return sorted(codes)

    def _build_chart_sections(self, test_record: TestRecord, language: str) -> list[dict[str, object]]:
        chart_data = ChartBuilderService().build_phase_series(test_record, language=language)
        charts = chart_data.get("charts", [])
        sections = [
            {
                "title": self._labels(language)["whole_test_charts"],
                "charts": [],
            },
            {
                "title": self._labels(language)["start_phase_charts"],
                "charts": [],
            },
            {
                "title": self._labels(language)["stable_phase_charts"],
                "charts": [],
            },
            {
                "title": self._labels(language)["stop_phase_charts"],
                "charts": [],
            },
        ]
        for chart in charts:
            chart_id = str(chart.get("chart_id", ""))
            svg = self._chart_to_svg(chart)
            svg_bytes = svg.encode("utf-8")
            svg_data_uri = f"data:image/svg+xml;base64,{base64.b64encode(svg_bytes).decode('ascii')}"
            item = {
                "title": chart.get("title", chart_id),
                "svg": svg,
                "svg_data_uri": svg_data_uri,
            }
            if chart_id.startswith("start-"):
                sections[1]["charts"].append(item)
            elif chart_id.startswith("stable-"):
                sections[2]["charts"].append(item)
            elif chart_id.startswith("stop-"):
                sections[3]["charts"].append(item)
            else:
                sections[0]["charts"].append(item)
        return [section for section in sections if section["charts"]]

    def _chart_to_svg(self, chart: dict[str, object]) -> str:
        width = 900
        height = 330
        padding_left = 52
        padding_right = 28
        compressor_rows = list((chart.get("compressor_run_bands") or {}).get("rows", []))
        compressor_segments = list((chart.get("compressor_run_bands") or {}).get("segments", []))
        padding_top = 24 + (len(compressor_rows) * 14)
        padding_bottom = 112
        plot_right = width - padding_right
        plot_bottom = height - padding_bottom
        labels = [float(item) for item in chart.get("labels", [])]
        datasets = chart.get("datasets", [])
        all_values = [
            float(value["y"] if isinstance(value, dict) else value)
            for dataset in datasets
            for value in dataset.get("data", [])
            if value is not None and (not isinstance(value, dict) or value.get("y") is not None)
        ]
        if len(labels) < 2 or not all_values:
            return (
                f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">'
                '<rect width="100%" height="100%" fill="#ffffff"/>'
                '<text x="20" y="40" font-size="14" fill="#475569">No chart data</text>'
                "</svg>"
            )
        min_x, max_x = min(labels), max(labels)
        min_y, max_y = min(all_values), max(all_values)
        if min_x == max_x:
            max_x += 1
        if min_y == max_y:
            max_y += 1
        chart_width = width - padding_left - padding_right
        chart_height = height - padding_top - padding_bottom
        dash_patterns = ["", "8 4", "3 3", "10 4 2 4", "2 4", "12 4"]
        marker_shapes = ["circle", "square", "triangle", "diamond", "cross", "ring"]

        def map_x(value: float) -> float:
            return padding_left + ((value - min_x) / (max_x - min_x)) * chart_width

        def map_y(value: float) -> float:
            return height - padding_bottom - ((value - min_y) / (max_y - min_y)) * chart_height

        y_ticks = 4
        x_ticks = min(6, max(2, len(labels)))
        lines = [
            '<rect width="100%" height="100%" fill="#ffffff"/>',
            f'<line x1="{padding_left}" y1="{plot_bottom}" x2="{plot_right}" y2="{plot_bottom}" stroke="#94a3b8" stroke-width="1"/>',
            f'<line x1="{padding_left}" y1="{padding_top}" x2="{padding_left}" y2="{plot_bottom}" stroke="#94a3b8" stroke-width="1"/>',
        ]
        for index in range(y_ticks + 1):
            ratio = index / y_ticks
            y_value = min_y + ((max_y - min_y) * ratio)
            y = map_y(y_value)
            lines.append(
                f'<line x1="{padding_left}" y1="{y:.2f}" x2="{plot_right}" y2="{y:.2f}" stroke="#e2e8f0" stroke-width="1"/>'
            )
            lines.append(
                f'<text x="{padding_left - 8}" y="{y + 4:.2f}" text-anchor="end" font-size="10" fill="#475569">{y_value:.2f}</text>'
            )
        if x_ticks > 1:
            for index in range(x_ticks):
                ratio = index / (x_ticks - 1)
                x_value = min_x + ((max_x - min_x) * ratio)
                x = map_x(x_value)
                lines.append(
                    f'<line x1="{x:.2f}" y1="{padding_top}" x2="{x:.2f}" y2="{plot_bottom}" stroke="#f1f5f9" stroke-width="1"/>'
                )
                lines.append(
                    f'<text x="{x:.2f}" y="{height - 16}" text-anchor="middle" font-size="10" fill="#475569">{x_value:.1f}s</text>'
                )
        for marker in chart.get("phase_markers", []):
            x = map_x(float(marker.get("position", 0)))
            label = escape(str(marker.get("label", "")))
            lines.append(
                f'<line x1="{x:.2f}" y1="{padding_top}" x2="{x:.2f}" y2="{plot_bottom}" stroke="#334155" stroke-dasharray="6 4" stroke-width="1.5"/>'
            )
            lines.append(
                f'<text x="{x + 4:.2f}" y="{padding_top + 12}" font-size="10" fill="#334155">{label}</text>'
            )

        if compressor_rows:
            row_gap = 12
            base_y = max(12, padding_top - (len(compressor_rows) * row_gap) - 4)
            for index, row in enumerate(compressor_rows):
                y = base_y + (index * row_gap)
                row_color = escape(str(row.get("color", "#2563eb")))
                row_label = escape(str(row.get("label", "")))
                lines.append(
                    f'<line x1="{padding_left}" y1="{y:.2f}" x2="{plot_right}" y2="{y:.2f}" stroke="#cbd5e1" stroke-width="2"/>'
                )
                lines.append(
                    f'<text x="{padding_left}" y="{y - 3:.2f}" font-size="9" fill="{row_color}">{row_label}</text>'
                )
            for segment in compressor_segments:
                row_index = int(segment.get("row", 0))
                y = base_y + (row_index * row_gap)
                x_start = map_x(float(segment.get("start", min_x)))
                x_end = map_x(float(segment.get("end", min_x)))
                color = escape(str(segment.get("color", "#2563eb")))
                lines.append(
                    f'<line x1="{x_start:.2f}" y1="{y:.2f}" x2="{max(x_start + 2, x_end):.2f}" y2="{y:.2f}" stroke="{color}" stroke-width="4.5" stroke-linecap="round"/>'
                )

        deferred_alerts: list[str] = []
        for index, dataset in enumerate(datasets):
            points = [
                f"{map_x(float(labels[index])):.2f},{map_y(float(value)):.2f}"
                for index, value in enumerate(dataset.get("data", []))
                if value is not None
            ]
            color = escape(str(dataset.get("borderColor", "#2563eb")))
            dash = dash_patterns[index % len(dash_patterns)]
            marker = marker_shapes[index % len(marker_shapes)]
            if points:
                lines.append(
                    f'<polyline fill="none" stroke="{color}" stroke-width="2.4" stroke-dasharray="{dash}" points="{" ".join(points)}" />'
                )
            data_values = dataset.get("data", [])
            visible_indexes = [
                item_index
                for item_index, value in enumerate(data_values)
                if value is not None
            ]
            if visible_indexes:
                marker_indexes = []
                if len(visible_indexes) <= 6:
                    marker_indexes = visible_indexes
                else:
                    step = max(1, len(visible_indexes) // 5)
                    marker_indexes = visible_indexes[::step]
                    if visible_indexes[-1] not in marker_indexes:
                        marker_indexes.append(visible_indexes[-1])
                for marker_index in marker_indexes:
                    x = map_x(float(labels[marker_index]))
                    y = map_y(float(data_values[marker_index]))
                    lines.extend(self._marker_svg(marker, x, y, color))
            for alert in dataset.get("alert_points", []):
                deferred_alerts.extend(
                    self._alert_badge_svg(
                        map_x(float(alert["x"])),
                        map_y(float(alert["y"])),
                    )
                )

        lines.extend(deferred_alerts)

        legend_items = []
        legend_top = plot_bottom + 28
        legend_left = padding_left
        legend_item_width = 250
        legend_row_height = 18
        legend_columns = max(1, chart_width // legend_item_width)
        for index, dataset in enumerate(datasets):
            color = escape(str(dataset.get("borderColor", "#2563eb")))
            label = escape(str(dataset.get("label", "")))
            row = index // legend_columns
            col = index % legend_columns
            item_x = legend_left + (col * legend_item_width)
            y = legend_top + (row * legend_row_height)
            dash = dash_patterns[index % len(dash_patterns)]
            marker = marker_shapes[index % len(marker_shapes)]
            legend_items.append(
                f'<line x1="{item_x}" y1="{y}" x2="{item_x + 18}" y2="{y}" stroke="{color}" stroke-width="3" stroke-dasharray="{dash}"/>'
            )
            legend_items.extend(self._marker_svg(marker, item_x + 9, y, color, size=3.5))
            legend_items.append(
                f'<text x="{item_x + 26}" y="{y + 4}" font-size="10" fill="#0f172a">{label}</text>'
            )

        return f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">{"".join(lines)}{"".join(legend_items)}</svg>'

    @staticmethod
    def _alert_badge_svg(x: float, y: float) -> list[str]:
        return [
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4.2" fill="#dc2626" stroke="#ffffff" stroke-width="1"/>',
            f'<text x="{x + 5.5:.2f}" y="{y - 5.0:.2f}" font-size="9" font-weight="700" fill="#b91c1c">!</text>',
        ]

    @staticmethod
    def _marker_svg(shape: str, x: float, y: float, color: str, size: float = 4.5) -> list[str]:
        if shape == "square":
            return [f'<rect x="{x - size:.2f}" y="{y - size:.2f}" width="{size * 2:.2f}" height="{size * 2:.2f}" fill="{color}" stroke="#ffffff" stroke-width="0.8"/>']
        if shape == "triangle":
            return [f'<polygon points="{x:.2f},{y - size:.2f} {x + size:.2f},{y + size:.2f} {x - size:.2f},{y + size:.2f}" fill="{color}" stroke="#ffffff" stroke-width="0.8"/>']
        if shape == "diamond":
            return [f'<polygon points="{x:.2f},{y - size:.2f} {x + size:.2f},{y:.2f} {x:.2f},{y + size:.2f} {x - size:.2f},{y:.2f}" fill="{color}" stroke="#ffffff" stroke-width="0.8"/>']
        if shape == "cross":
            return [
                f'<line x1="{x - size:.2f}" y1="{y - size:.2f}" x2="{x + size:.2f}" y2="{y + size:.2f}" stroke="{color}" stroke-width="1.5"/>',
                f'<line x1="{x - size:.2f}" y1="{y + size:.2f}" x2="{x + size:.2f}" y2="{y - size:.2f}" stroke="{color}" stroke-width="1.5"/>',
            ]
        if shape == "ring":
            return [f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{size:.2f}" fill="#ffffff" stroke="{color}" stroke-width="1.8"/>']
        return [f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{size:.2f}" fill="{color}" stroke="#ffffff" stroke-width="0.8"/>']
