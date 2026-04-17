from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from apps.core.constants import CircuitSelect
from apps.core.constants import TestPhase
from apps.core.services.tag_registry import TagRegistryService
from apps.tests.models import TestRecord
from apps.tests.services.limit_analysis import LimitAnalysisService


@dataclass(slots=True)
class PhaseWindow:
    phase_value: int
    phase_slug: str
    phase_title: str
    relative_zero_sec: float
    start_sec: float
    end_sec: float
    window_start_sec: float
    window_end_sec: float


class ChartBuilderService:
    PHASE_GROUPS: list[tuple[int, str, str]] = [
        (int(TestPhase.START), "start", "Start"),
        (int(TestPhase.STABLE), "stable", "Stable"),
        (int(TestPhase.STOP), "stop", "Stop"),
    ]

    def build_phase_series(self, test_record: TestRecord, language: str = "tr") -> dict[str, object]:
        ordered_samples = list(test_record.samples.order_by("timestamp_unix", "sequence_no"))
        marker_map = LimitAnalysisService().marker_map(test_record)
        selected_circuit = int(test_record.selected_circuit)
        return {
            "charts": self._build_chart_entries(
                test_record,
                ordered_samples,
                marker_map,
                language=language,
                selected_circuit=selected_circuit,
            ),
            "phase_labels": self._phase_labels(),
        }

    def chart_definitions(self, language: str = "tr", selected_circuit: int | None = None) -> Iterable[dict[str, object]]:
        cards = [
            self._to_card(group["chart_id"], group["title"])
            for group in self._active_test_groups(language, selected_circuit=selected_circuit)
        ]
        for _, phase_slug, phase_title in self.PHASE_GROUPS:
            for group in self._active_test_groups(language, selected_circuit=selected_circuit):
                cards.append(
                    self._to_card(
                        f"{phase_slug}-{group['chart_id']}",
                        f"{phase_title} - {group['title']}",
                        phase_slug=phase_slug,
                    )
                )
        return cards

    def detail_chart_definitions(self, language: str = "tr", selected_circuit: int | None = None) -> list[dict[str, object]]:
        detail_cards: list[dict[str, object]] = []
        for card in self.chart_definitions(language, selected_circuit=selected_circuit):
            detail_cards.append(
                {
                    "chart_id": f"detail-{card['chart_id']}",
                    "source_chart_id": card["chart_id"],
                    "title": card["title"],
                    "phase_slug": card.get("phase_slug", ""),
                }
            )
        return detail_cards

    @staticmethod
    def _phase_labels() -> dict[int, str]:
        return {int(phase.value): phase.name.title() for phase in TestPhase}

    def _build_chart_entries(
        self,
        test_record: TestRecord,
        ordered_samples: list[object],
        marker_map: dict[str, list[dict[str, object]]],
        language: str,
        selected_circuit: int,
    ) -> list[dict[str, object]]:
        prestart_samples = self._prestart_samples(test_record)
        charts: list[dict[str, object]] = []
        charts.extend(
            self._build_chart_entries_for_samples(
                test_record,
                [*prestart_samples, *ordered_samples],
                marker_map,
                language=language,
                prefix="",
                phase_markers=self._overall_phase_markers(test_record),
                axis_min=-float(getattr(test_record, "phase_context_sec_snapshot", 0) or 0),
                axis_max=self._total_duration_sec(test_record),
                relative_zero_sec=0.0,
                selected_circuit=selected_circuit,
            )
        )

        for window in self._phase_windows(test_record):
            source_samples = ordered_samples
            if window.phase_slug == "start":
                source_samples = [*prestart_samples, *ordered_samples]
            phase_samples = [
                sample
                for sample in source_samples
                if window.window_start_sec <= self._sample_elapsed_seconds(test_record, sample) <= window.window_end_sec
            ]
            charts.extend(
                self._build_chart_entries_for_samples(
                    test_record,
                    phase_samples,
                    marker_map,
                    language=language,
                    prefix=f"{window.phase_slug}-",
                    phase_markers=[
                        {
                            "position": 0.0,
                            "label": window.phase_title,
                        }
                    ],
                    window=window,
                    axis_min=-float(getattr(test_record, "phase_context_sec_snapshot", 0) or 0),
                    axis_max=max(0.0, window.end_sec - window.relative_zero_sec),
                    relative_zero_sec=window.relative_zero_sec,
                    selected_circuit=selected_circuit,
                )
            )
        return charts

    def _build_chart_entries_for_samples(
        self,
        test_record: TestRecord,
        ordered_samples: list[object],
        marker_map: dict[str, list[dict[str, object]]],
        language: str,
        prefix: str,
        phase_markers: list[dict[str, object]] | None = None,
        window: PhaseWindow | None = None,
        axis_min: float | None = None,
        axis_max: float | None = None,
        relative_zero_sec: float = 0.0,
        selected_circuit: int = int(CircuitSelect.BOTH),
    ) -> list[dict[str, object]]:
        labels: list[float] = []
        phases: list[int] = []
        values_map: dict[str, list[float | None]] = {}
        active_groups = self._active_test_groups(language, selected_circuit=selected_circuit)
        validity_map = TagRegistryService().get_validity_tag_map()

        for group in active_groups:
            for dataset in group["datasets"]:
                values_map[dataset["key"]] = []

        for sample in ordered_samples:
            elapsed_seconds = self._sample_elapsed_seconds(test_record, sample) - relative_zero_sec
            labels.append(round(elapsed_seconds, 3))
            phases.append(self._sample_phase(sample))
            for key in values_map:
                values_map[key].append(self._sample_numeric_value(sample, key, validity_map))

        charts: list[dict[str, object]] = []
        for group in active_groups:
            charts.append(
                {
                    "chart_id": f"{prefix}{group['chart_id']}",
                    "title": group["title"],
                    "labels": labels,
                    "phases": phases,
                    "datasets": [
                        {
                            "key": dataset["key"],
                            "label": dataset["label"],
                            "borderColor": dataset["color"],
                            "backgroundColor": dataset["color"],
                            "data": values_map[dataset["key"]],
                            "alert_points": self._alert_points(
                                marker_map.get(dataset["key"], []),
                                relative_zero_sec=relative_zero_sec,
                                axis_min=axis_min,
                                axis_max=axis_max,
                            ),
                        }
                        for dataset in group["datasets"]
                    ],
                    "phase_markers": phase_markers or [],
                    "window_start_sec": window.window_start_sec if window else 0.0,
                    "window_end_sec": window.window_end_sec if window else self._total_duration_sec(test_record),
                    "phase_start_sec": window.start_sec if window else None,
                    "phase_offset_sec": relative_zero_sec,
                    "axis_min": axis_min,
                    "axis_max": axis_max,
                    "compressor_run_bands": self._compressor_run_bands(
                        test_record,
                        ordered_samples,
                        relative_zero_sec=relative_zero_sec,
                        axis_min=axis_min,
                        axis_max=axis_max,
                        selected_circuit=selected_circuit,
                        language=language,
                    ),
                }
            )
        return charts

    @staticmethod
    def _compressor_run_bands(
        test_record: TestRecord,
        ordered_samples: list[object],
        relative_zero_sec: float,
        axis_min: float | None,
        axis_max: float | None,
        selected_circuit: int,
        language: str,
    ) -> dict[str, object]:
        rows: list[dict[str, object]] = []
        if selected_circuit in {int(CircuitSelect.CIRCUIT_1), int(CircuitSelect.BOTH)}:
            rows.append(
                {
                    "key": "comp1_rng",
                    "label": "Comp1 RNG" if language == "en" else "Comp1 RNG",
                    "color": "#16a34a",
                }
            )
        if selected_circuit in {int(CircuitSelect.CIRCUIT_2), int(CircuitSelect.BOTH)}:
            rows.append(
                {
                    "key": "comp2_rng",
                    "label": "Comp2 RNG" if language == "en" else "Comp2 RNG",
                    "color": "#dc2626",
                }
            )

        segments: list[dict[str, object]] = []
        states: dict[str, bool] = {row["key"]: False for row in rows}
        starts: dict[str, float | None] = {row["key"]: None for row in rows}
        last_x = axis_min or 0.0
        row_map = {row["key"]: index for index, row in enumerate(rows)}

        for sample in ordered_samples:
            sample_x = ChartBuilderService._sample_elapsed_seconds(test_record, sample) - relative_zero_sec
            if axis_min is not None and sample_x < axis_min:
                continue
            if axis_max is not None and sample_x > axis_max:
                continue
            last_x = sample_x
            for row in rows:
                key = str(row["key"])
                is_running = ChartBuilderService._sample_status_flag(sample, key)
                if is_running and not states[key]:
                    states[key] = True
                    starts[key] = sample_x
                elif not is_running and states[key]:
                    segments.append(
                        {
                            "row": row_map[key],
                            "label": row["label"],
                            "color": row["color"],
                            "start": round(float(starts[key] if starts[key] is not None else sample_x), 3),
                            "end": round(float(sample_x), 3),
                        }
                    )
                    states[key] = False
                    starts[key] = None

        for row in rows:
            key = str(row["key"])
            if states[key]:
                end_value = axis_max if axis_max is not None else last_x
                segments.append(
                    {
                        "row": row_map[key],
                        "label": row["label"],
                        "color": row["color"],
                        "start": round(float(starts[key] if starts[key] is not None else end_value), 3),
                        "end": round(float(end_value), 3),
                    }
                )

        return {
            "rows": rows,
            "segments": segments,
            "last_flags": {key: bool(value) for key, value in states.items()},
            "last_x": round(float(last_x), 3),
        }

    def _phase_windows(self, test_record: TestRecord) -> list[PhaseWindow]:
        start_duration = float(test_record.start_duration_sec_snapshot)
        stable_duration = float(test_record.stable_duration_sec_snapshot)
        stop_duration = float(test_record.stop_duration_sec_snapshot)
        context_sec = float(getattr(test_record, "phase_context_sec_snapshot", 0) or 0)

        start_start = 0.0
        stable_start = start_duration
        stop_start = start_duration + stable_duration
        total_end = start_duration + stable_duration + stop_duration

        return [
            PhaseWindow(
                phase_value=int(TestPhase.START),
                phase_slug="start",
                phase_title="Start",
                relative_zero_sec=0.0,
                start_sec=start_start,
                end_sec=stable_start,
                window_start_sec=-context_sec,
                window_end_sec=stable_start,
            ),
            PhaseWindow(
                phase_value=int(TestPhase.STABLE),
                phase_slug="stable",
                phase_title="Stable",
                relative_zero_sec=stable_start,
                start_sec=stable_start,
                end_sec=stop_start,
                window_start_sec=max(0.0, stable_start - context_sec),
                window_end_sec=stop_start,
            ),
            PhaseWindow(
                phase_value=int(TestPhase.STOP),
                phase_slug="stop",
                phase_title="Stop",
                relative_zero_sec=stop_start,
                start_sec=stop_start,
                end_sec=total_end,
                window_start_sec=max(0.0, stop_start - context_sec),
                window_end_sec=total_end,
            ),
        ]

    def _overall_phase_markers(self, test_record: TestRecord) -> list[dict[str, object]]:
        start_duration = float(test_record.start_duration_sec_snapshot)
        stable_duration = float(test_record.stable_duration_sec_snapshot)
        return [
            {"position": 0.0, "label": "Start"},
            {"position": start_duration, "label": "Stable"},
            {"position": start_duration + stable_duration, "label": "Stop"},
        ]

    @staticmethod
    def _alert_points(
        markers: list[dict[str, object]],
        relative_zero_sec: float,
        axis_min: float | None,
        axis_max: float | None,
    ) -> list[dict[str, object]]:
        alert_points: list[dict[str, object]] = []
        for item in markers:
            x_value = float(item["elapsed_seconds"]) - relative_zero_sec
            if axis_min is not None and x_value < axis_min:
                continue
            if axis_max is not None and x_value > axis_max:
                continue
            alert_points.append(
                {
                    "x": round(x_value, 3),
                    "y": float(item["sample_value"]),
                    "phase_name": item["phase_name"],
                    "limit_type": item["limit_type"],
                    "limit_value": float(item["limit_value"]),
                    "message": item["message"],
                }
            )
        return alert_points

    @staticmethod
    def _total_duration_sec(test_record: TestRecord) -> float:
        return float(
            test_record.start_duration_sec_snapshot
            + test_record.stable_duration_sec_snapshot
            + test_record.stop_duration_sec_snapshot
        )

    @staticmethod
    def _sample_elapsed_seconds(test_record: TestRecord, sample: object) -> float:
        if not test_record.started_at:
            return 0.0
        sample_timestamp = float(ChartBuilderService._sample_value(sample, "timestamp_unix", 0))
        test_started_unix = float(test_record.started_at.timestamp())
        return sample_timestamp - test_started_unix

    @staticmethod
    def _sample_value(sample: object, key: str, default: object = None) -> object:
        if isinstance(sample, dict):
            return sample.get(key, default)
        return getattr(sample, key, default)

    @staticmethod
    def _sample_numeric_value(
        sample: object,
        key: str,
        validity_map: dict[str, int] | None = None,
    ) -> float | None:
        if validity_map and not ChartBuilderService._sample_is_valid(sample, key, validity_map):
            return None
        if isinstance(sample, dict):
            values = sample.get("values", {})
            raw_value = values.get(key)
        else:
            raw_value = sample.get_value(key)
        return float(raw_value) if raw_value is not None else None

    @staticmethod
    def _sample_is_valid(sample: object, key: str, validity_map: dict[str, int]) -> bool:
        bit_index = validity_map.get(str(key))
        if bit_index is None:
            return True
        if isinstance(sample, dict):
            validity = sample.get("validity", {})
            if isinstance(validity, dict) and str(key) in validity:
                return bool(validity.get(str(key)))
            validity_word1 = int(sample.get("validity_word1") or 0)
            return bool(validity_word1 & (1 << bit_index))
        validity_word1 = int(getattr(sample, "validity_word1", 0) or 0)
        return bool(validity_word1 & (1 << bit_index))

    @staticmethod
    def _sample_phase(sample: object) -> int:
        return int(ChartBuilderService._sample_value(sample, "test_phase", int(TestPhase.IDLE)))

    @staticmethod
    def _sample_status_flag(sample: object, key: str) -> bool:
        if isinstance(sample, dict):
            status_flags = sample.get("status_flags", {})
            if isinstance(status_flags, dict) and key in status_flags:
                return bool(status_flags.get(key))
            status_word = int(sample.get("status_word") or 0)
        else:
            status_flags = getattr(sample, "status_flags", None)
            if isinstance(status_flags, dict) and key in status_flags:
                return bool(status_flags.get(key))
            status_word = int(getattr(sample, "status_word", 0) or 0)
        bit_map = {"comp1_rng": 2, "comp2_rng": 3}
        bit_index = bit_map.get(str(key))
        if bit_index is None:
            return False
        return bool(status_word & (1 << bit_index))

    @staticmethod
    def _prestart_samples(test_record: TestRecord) -> list[dict[str, object]]:
        samples = test_record.prestart_samples_json or []
        if not isinstance(samples, list):
            return []
        return sorted(samples, key=lambda item: (item.get("timestamp_unix", 0), item.get("sequence_no", 0)))

    @staticmethod
    def _active_test_groups(language: str = "tr", selected_circuit: int | None = None) -> list[dict[str, object]]:
        groups = TagRegistryService().get_chart_groups(language=language)
        if selected_circuit is None:
            return groups
        registry = TagRegistryService()
        allowed_codes = set(registry.get_parameter_codes_for_scope("shared"))
        if selected_circuit in {int(CircuitSelect.CIRCUIT_1), int(CircuitSelect.BOTH)}:
            allowed_codes.update(registry.get_parameter_codes_for_scope("circuit1"))
        if selected_circuit in {int(CircuitSelect.CIRCUIT_2), int(CircuitSelect.BOTH)}:
            allowed_codes.update(registry.get_parameter_codes_for_scope("circuit2"))
        filtered_groups: list[dict[str, object]] = []
        for group in groups:
            datasets = [dataset for dataset in group["datasets"] if str(dataset["key"]) in allowed_codes]
            if datasets:
                filtered_groups.append({**group, "datasets": datasets})
        return filtered_groups

    @staticmethod
    def _to_card(chart_id: str, title: str, phase_slug: str = "") -> dict[str, object]:
        return {"chart_id": chart_id, "title": title, "phase_slug": phase_slug}
