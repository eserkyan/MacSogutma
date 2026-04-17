from __future__ import annotations

from dataclasses import dataclass

from apps.core.constants import CircuitSelect, TestPhase
from apps.core.services.tag_registry import TagRegistryService
from apps.recipes.services.phase_limits import has_active_limit, phase_limit
from apps.tests.models import TestRecord, TestSample


@dataclass(slots=True)
class LimitExcursion:
    parameter_code: str
    parameter_name: str
    unit: str
    phase_value: int
    phase_name: str
    elapsed_seconds: float
    sample_value: float
    limit_type: str
    limit_value: float
    message: str


class LimitAnalysisService:
    def __init__(self) -> None:
        self.registry = TagRegistryService()

    def analyze(self, test_record: TestRecord) -> list[LimitExcursion]:
        excursions: list[LimitExcursion] = []
        started_at = test_record.started_at
        if not started_at:
            return excursions

        parameter_definitions = self.registry.get_parameter_definitions(include_limits_only=True)
        for sample in test_record.samples.order_by("timestamp_unix", "sequence_no"):
            elapsed_seconds = float(sample.timestamp_unix) - float(started_at.timestamp())
            phase_name = TestPhase(int(sample.test_phase)).name.title()
            for parameter_code in self._parameter_codes(CircuitSelect(test_record.selected_circuit)):
                if parameter_code not in parameter_definitions or not self._is_valid(sample, parameter_code):
                    continue
                raw_limit = test_record.limits_snapshot_json.get(parameter_code, {})
                limit = phase_limit(raw_limit, int(sample.test_phase))
                if not has_active_limit(raw_limit, int(sample.test_phase)):
                    continue
                sample_value = sample.get_value(parameter_code)
                if sample_value is None:
                    continue
                numeric_value = float(sample_value)
                parameter_name = str(parameter_definitions[parameter_code]["label"])
                unit = str(parameter_definitions[parameter_code]["unit"])
                min_limit = limit.get("min_value")
                max_limit = limit.get("max_value")
                if limit.get("min_enabled") and min_limit is not None and numeric_value < float(min_limit):
                    excursions.append(
                        LimitExcursion(
                            parameter_code=parameter_code,
                            parameter_name=parameter_name,
                            unit=unit,
                            phase_value=int(sample.test_phase),
                            phase_name=phase_name,
                            elapsed_seconds=elapsed_seconds,
                            sample_value=numeric_value,
                            limit_type="MIN",
                            limit_value=float(min_limit),
                            message=f"{numeric_value:.2f} < {float(min_limit):.2f}",
                        )
                    )
                if limit.get("max_enabled") and max_limit is not None and numeric_value > float(max_limit):
                    excursions.append(
                        LimitExcursion(
                            parameter_code=parameter_code,
                            parameter_name=parameter_name,
                            unit=unit,
                            phase_value=int(sample.test_phase),
                            phase_name=phase_name,
                            elapsed_seconds=elapsed_seconds,
                            sample_value=numeric_value,
                            limit_type="MAX",
                            limit_value=float(max_limit),
                            message=f"{numeric_value:.2f} > {float(max_limit):.2f}",
                        )
                    )
        return excursions

    def marker_map(self, test_record: TestRecord) -> dict[str, list[dict[str, object]]]:
        markers: dict[str, list[dict[str, object]]] = {}
        for item in self.analyze(test_record):
            markers.setdefault(item.parameter_code, []).append(
                {
                    "elapsed_seconds": item.elapsed_seconds,
                    "sample_value": item.sample_value,
                    "phase_value": item.phase_value,
                    "phase_name": item.phase_name,
                    "limit_type": item.limit_type,
                    "limit_value": item.limit_value,
                    "message": item.message,
                }
            )
        return markers

    def _is_valid(self, sample: TestSample, parameter_code: str) -> bool:
        bit_index = self.registry.get_validity_tag_map().get(parameter_code)
        if bit_index is None:
            return True
        return bool(int(sample.validity_word1) & (1 << bit_index))

    def _parameter_codes(self, circuit: CircuitSelect) -> list[str]:
        codes = set(self.registry.get_parameter_codes_for_scope("shared"))
        if circuit in {CircuitSelect.CIRCUIT_1, CircuitSelect.BOTH}:
            codes.update(self.registry.get_parameter_codes_for_scope("circuit1"))
        if circuit in {CircuitSelect.CIRCUIT_2, CircuitSelect.BOTH}:
            codes.update(self.registry.get_parameter_codes_for_scope("circuit2"))
        return sorted(codes)
