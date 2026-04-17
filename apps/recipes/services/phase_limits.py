from __future__ import annotations

from typing import Any

from apps.core.constants import EvaluationPhase, TestPhase

PHASE_SLUGS: tuple[str, ...] = ("start", "stable", "stop")


def empty_limit() -> dict[str, bool | float | None]:
    return {
        "min_enabled": False,
        "min_value": None,
        "max_enabled": False,
        "max_value": None,
    }


def normalize_limit_config(raw: dict[str, Any] | None) -> dict[str, dict[str, bool | float | None]]:
    payload = raw or {}
    if any(key in payload for key in PHASE_SLUGS):
        normalized: dict[str, dict[str, bool | float | None]] = {}
        for phase_slug in PHASE_SLUGS:
            phase_payload = payload.get(phase_slug, {}) if isinstance(payload.get(phase_slug, {}), dict) else {}
            normalized[phase_slug] = {
                "min_enabled": bool(phase_payload.get("min_enabled")),
                "min_value": phase_payload.get("min_value"),
                "max_enabled": bool(phase_payload.get("max_enabled")),
                "max_value": phase_payload.get("max_value"),
            }
        return normalized
    legacy = {
        "min_enabled": bool(payload.get("min_enabled")),
        "min_value": payload.get("min_value"),
        "max_enabled": bool(payload.get("max_enabled")),
        "max_value": payload.get("max_value"),
    }
    return {
        "start": empty_limit(),
        "stable": legacy,
        "stop": empty_limit(),
    }


def phase_slug_for_value(phase_value: int | TestPhase) -> str:
    value = int(phase_value)
    if value == int(TestPhase.START):
        return "start"
    if value == int(TestPhase.STOP):
        return "stop"
    return "stable"


def phase_limit(raw: dict[str, Any] | None, phase: str | int | TestPhase | EvaluationPhase) -> dict[str, bool | float | None]:
    normalized = normalize_limit_config(raw)
    if isinstance(phase, str):
        return normalized.get(phase.lower(), empty_limit())
    return normalized.get(phase_slug_for_value(phase), empty_limit())


def has_active_limit(raw: dict[str, Any] | None, phase: str | int | TestPhase | EvaluationPhase) -> bool:
    limit = phase_limit(raw, phase)
    return bool(limit.get("min_enabled")) or bool(limit.get("max_enabled"))
