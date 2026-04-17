from __future__ import annotations

from enum import IntEnum, StrEnum

from apps.core.tag_schema import parameter_codes_for_scope, parameter_definitions


class CircuitSelect(IntEnum):
    NONE = 0
    CIRCUIT_1 = 1
    CIRCUIT_2 = 2
    BOTH = 3

    @classmethod
    def choices(cls) -> list[tuple[int, str]]:
        return [(member.value, member.label) for member in cls]

    @property
    def label(self) -> str:
        labels = {
            CircuitSelect.NONE: "None",
            CircuitSelect.CIRCUIT_1: "Circuit 1",
            CircuitSelect.CIRCUIT_2: "Circuit 2",
            CircuitSelect.BOTH: "Circuit 1 + Circuit 2",
        }
        return labels[self]


class TestPhase(IntEnum):
    IDLE = 0
    START = 1
    STABLE = 2
    STOP = 3
    MANUAL = 4
    ABORTED = 5

    @classmethod
    def choices(cls) -> list[tuple[int, str]]:
        return [(member.value, member.name.title()) for member in cls]


class TestStatus(StrEnum):
    DRAFT = "DRAFT"
    START_REQUESTED = "START_REQUESTED"
    RUNNING = "RUNNING"
    COMPLETED_PASS = "COMPLETED_PASS"
    COMPLETED_FAIL = "COMPLETED_FAIL"
    ABORTED = "ABORTED"
    FAILED_TO_START = "FAILED_TO_START"

    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        return [(member.value, member.value.replace("_", " ").title()) for member in cls]


class PlcEventType(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    FAULT = "FAULT"
    OVERRUN = "OVERRUN"
    COMMUNICATION = "COMMUNICATION"
    TIME_SYNC = "TIME_SYNC"

    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        return [(member.value, member.value.title()) for member in cls]


class EvaluationPhase(StrEnum):
    START = "START"
    STABLE = "STABLE"
    STOP = "STOP"

    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        return [(member.value, member.value.title()) for member in cls]

    @classmethod
    def from_test_phase(cls, phase: TestPhase | int) -> "EvaluationPhase":
        value = int(phase)
        if value == int(TestPhase.START):
            return cls.START
        if value == int(TestPhase.STOP):
            return cls.STOP
        return cls.STABLE


PARAMETER_DEFINITIONS = parameter_definitions()

SAMPLE_META_FIELDS: tuple[tuple[str, str], ...] = (
    ("sequence_no", "Sequence"),
    ("timestamp_unix", "Timestamp Unix"),
    ("elapsed_seconds", "Elapsed Sec"),
    ("phase_name", "Phase"),
    ("status_word", "Status Word"),
    ("validity_word1", "Validity Word 1"),
    ("validity_word2", "Validity Word 2"),
)

SHARED_PARAMETERS = parameter_codes_for_scope("shared")
CIRCUIT_1_PARAMETERS = parameter_codes_for_scope("circuit1")
CIRCUIT_2_PARAMETERS = parameter_codes_for_scope("circuit2")
