from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from apps.core.constants import TestPhase
from apps.tests.models import TestRecord


@dataclass(slots=True)
class PhaseDecision:
    phase: TestPhase
    changed: bool


class TestStateMachineService:
    def determine_phase(self, test_record: TestRecord) -> PhaseDecision:
        now = timezone.now()
        if not test_record.started_at:
            return PhaseDecision(phase=TestPhase.IDLE, changed=False)
        if not test_record.stable_started_at:
            if now >= test_record.started_at + timedelta(seconds=test_record.start_duration_sec_snapshot):
                test_record.stable_started_at = now
                test_record.save(update_fields=["stable_started_at", "updated_at"])
                return PhaseDecision(phase=TestPhase.STABLE, changed=True)
            return PhaseDecision(phase=TestPhase.START, changed=False)
        if not test_record.stop_started_at:
            if now >= test_record.stable_started_at + timedelta(seconds=test_record.stable_duration_sec_snapshot):
                test_record.stop_started_at = now
                test_record.save(update_fields=["stop_started_at", "updated_at"])
                return PhaseDecision(phase=TestPhase.STOP, changed=True)
            return PhaseDecision(phase=TestPhase.STABLE, changed=False)
        return PhaseDecision(phase=TestPhase.STOP, changed=False)
