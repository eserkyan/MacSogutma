from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import struct
from typing import Any

from apps.core.services.tag_registry import TagRegistryService


def _u32(high_word: int, low_word: int) -> int:
    return ((high_word & 0xFFFF) << 16) | (low_word & 0xFFFF)


def _s16(value: int) -> int:
    return value - 0x10000 if value & 0x8000 else value


def _u16(value: int) -> int:
    return value & 0xFFFF


def _s32(high_word: int, low_word: int) -> int:
    value = _u32(high_word, low_word)
    return value - 0x100000000 if value & 0x80000000 else value


def _f32(high_word: int, low_word: int) -> float:
    packed = struct.pack(">HH", high_word & 0xFFFF, low_word & 0xFFFF)
    return struct.unpack(">f", packed)[0]


def scale_x10(value: int) -> float:
    return round(_s16(value) / 10.0, 3)


def scale_x100(value: int) -> float:
    return round(_s16(value) / 100.0, 3)


def scale_x1000(value: int) -> float:
    return round(_s16(value) / 1000.0, 3)


STATUS_BIT_MAP: dict[str, int] = {
    "test_active": 0,
    "alarm_active": 1,
    "comp1_rng": 2,
    "comp2_rng": 3,
}


def combined_validity_value(validity_word1: int, validity_word2: int | None) -> int:
    return (int(validity_word1) & 0xFFFF) | ((int(validity_word2 or 0) & 0xFFFF) << 16)


def validity_bit_is_set(validity_word1: int, validity_word2: int | None, bit_index: int) -> bool:
    return bool(combined_validity_value(validity_word1, validity_word2) & (1 << int(bit_index)))


@dataclass(slots=True)
class ParsedSample:
    sequence_no: int
    timestamp_unix: int
    test_phase: int
    status_word: int
    validity_word1: int
    validity_word2: int | None
    values: dict[str, float | None] = field(default_factory=dict)
    validity: dict[str, bool] = field(default_factory=dict)
    validity_details: dict[str, dict[str, Any]] = field(default_factory=dict)
    status_flags: dict[str, bool] = field(default_factory=dict)

    @property
    def timestamp(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp_unix, tz=UTC)

    def to_json(self) -> dict[str, Any]:
        return {
            "sequence_no": self.sequence_no,
            "timestamp_unix": self.timestamp_unix,
            "test_phase": self.test_phase,
            "status_word": self.status_word,
            "validity_word1": self.validity_word1,
            "validity_word2": self.validity_word2,
            "values": self.values,
            "validity": self.validity,
            "validity_details": self.validity_details,
            "status_flags": self.status_flags,
            "timestamp": self.timestamp.isoformat(),
        }


class PlcParserService:
    SCALE_MAP = {
        "none": lambda value: round(float(value), 3),
        "x10": scale_x10,
        "x100": scale_x100,
        "x1000": scale_x1000,
    }

    @classmethod
    def decode_validity_bits(cls, validity_word1: int, validity_word2: int | None, mapping: dict[str, int]) -> dict[str, bool]:
        return {
            name: validity_bit_is_set(validity_word1, validity_word2, bit)
            for name, bit in mapping.items()
        }

    @classmethod
    def decode_status_bits(cls, word: int, mapping: dict[str, int]) -> dict[str, bool]:
        return {name: bool(word & (1 << bit)) for name, bit in mapping.items()}

    @classmethod
    def parse_record(cls, registers: list[int]) -> ParsedSample:
        sequence_no = _u32(registers[0], registers[1])
        timestamp_unix = _u32(registers[2], registers[3])
        test_phase = registers[4]
        status_word = registers[5]
        validity_word1 = registers[6]
        validity_word2 = registers[7] if len(registers) > 7 else None
        tags = [tag for tag in TagRegistryService().get_tags() if tag["is_active"]]
        values: dict[str, float | None] = {}
        for tag in tags:
            values[tag["code"]] = cls._parse_tag_value(registers, tag)
        validity_map = TagRegistryService().get_validity_tag_map()
        validity = cls.decode_validity_bits(validity_word1, validity_word2, validity_map)
        validity_details = {
            tag["code"]: {
                "label": str(tag.get("label")),
                "label_en": str(tag.get("label_en") or tag.get("label")),
                "valid": validity.get(tag["code"], True),
                "reference": cls._validity_reference(validity_map.get(tag["code"])),
            }
            for tag in tags
        }
        return ParsedSample(
            sequence_no=sequence_no,
            timestamp_unix=timestamp_unix,
            test_phase=test_phase,
            status_word=status_word,
            validity_word1=validity_word1,
            validity_word2=validity_word2,
            values=values,
            validity=validity,
            validity_details=validity_details,
            status_flags=cls.decode_status_bits(status_word, STATUS_BIT_MAP),
        )

    @classmethod
    def _parse_tag_value(cls, registers: list[int], tag: dict[str, Any]) -> float | None:
        offset = 8 + int(tag["register_offset"])
        data_type = str(tag.get("data_type") or "int16")
        word_order = str(tag.get("word_order") or "high_low")
        scale = str(tag.get("scale") or "none")
        raw_value: int | float

        if data_type in {"int32", "uint32", "float32"}:
            if len(registers) <= offset + 1:
                return None
            word_a = registers[offset]
            word_b = registers[offset + 1]
            high_word, low_word = (word_a, word_b) if word_order == "high_low" else (word_b, word_a)
            if data_type == "int32":
                raw_value = _s32(high_word, low_word)
            elif data_type == "uint32":
                raw_value = _u32(high_word, low_word)
            else:
                raw_value = _f32(high_word, low_word)
                divisor = {"none": 1.0, "x10": 10.0, "x100": 100.0, "x1000": 1000.0}.get(scale, 1.0)
                return round(raw_value / divisor, 3)
        else:
            if len(registers) <= offset:
                return None
            word = registers[offset]
            raw_value = _u16(word) if data_type == "uint16" else _s16(word)

        divisor = {"none": 1.0, "x10": 10.0, "x100": 100.0, "x1000": 1000.0}.get(scale, 1.0)
        return round(float(raw_value) / divisor, 3)

    @staticmethod
    def _validity_reference(bit_index: int | None) -> str:
        if bit_index is None:
            return "-"
        if int(bit_index) < 16:
            return f"word1.bit{int(bit_index)}"
        return f"word2.bit{int(bit_index) - 16}"
