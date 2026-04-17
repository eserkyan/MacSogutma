from __future__ import annotations

import logging
import math
import random
import time
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.db.utils import OperationalError, ProgrammingError
from pymodbus.client import ModbusTcpClient

from apps.core.constants import CircuitSelect, TestPhase
from apps.core.models import PlcSchemaConfig
from apps.core.services.tag_registry import TagRegistryService

logger = logging.getLogger(__name__)


class ModbusClientError(RuntimeError):
    pass


@dataclass(slots=True)
class FastPollPayload:
    status: dict[str, Any]
    live_record: list[int]


class PlcModbusClient:
    def __init__(self) -> None:
        self.config = self._effective_config()

    @staticmethod
    def _effective_config() -> dict[str, Any]:
        config = dict(settings.PLC_CONFIG)
        try:
            schema = PlcSchemaConfig.load()
            config["host"] = schema.plc_host or config["host"]
            config["port"] = int(schema.plc_port or config["port"])
            config["unit_id"] = int(schema.modbus_unit_id or config["unit_id"])
        except (OperationalError, ProgrammingError):
            pass
        return config

    def fast_poll(self) -> FastPollPayload:
        if self.config["simulation_enabled"]:
            return self._hybrid_fast_poll()
        return self._read_fast_poll_from_plc()

    def read_history_records(self, start_index: int, count: int) -> list[list[int]]:
        if self.config["simulation_enabled"]:
            return self._hybrid_history_records(start_index=start_index, count=count)
        return self._read_history_records_from_plc(start_index=start_index, count=count)

    def write_test_command(
        self,
        *,
        circuit: CircuitSelect,
        start_request: bool,
        stop_request: bool,
        abort_request: bool,
        phase: TestPhase,
        test_active: bool,
    ) -> None:
        logger.info(
            "PLC command issued",
            extra={
                "circuit": int(circuit),
                "start_request": start_request,
                "stop_request": stop_request,
                "abort_request": abort_request,
                "phase": int(phase),
                "test_active": test_active,
            },
        )

    def sync_time(self, unix_ts: int) -> None:
        logger.info("PLC time sync requested", extra={"unix_ts": unix_ts})

    def _hybrid_fast_poll(self) -> FastPollPayload:
        now_unix = int(time.time())
        simulated_payload = FastPollPayload(
            status=self._simulated_status(now_unix),
            live_record=self._build_record(sequence_no=now_unix),
        )
        active_tags = [tag for tag in TagRegistryService().get_tags() if tag["is_active"]]
        active_real_tags = [tag for tag in active_tags if not tag.get("simulation_enabled", True)]
        if not active_real_tags:
            return simulated_payload

        status = simulated_payload.status
        live_record = simulated_payload.live_record
        try:
            status = self._read_status_from_plc()
        except ModbusClientError:
            logger.warning("PLC status read failed during hybrid polling; simulated status kept")

        try:
            real_payload = self._read_fast_poll_from_plc()
            live_record = self._overlay_simulated_tags(real_payload.live_record, simulated_payload.live_record, active_tags)
            status = real_payload.status
        except ModbusClientError:
            logger.warning("PLC live record read failed during hybrid polling; simulated fallback kept")
            real_word_map: dict[int, list[int]] = {}
            for tag in active_real_tags:
                try:
                    real_word_map[int(tag["tag_id"])] = self._read_tag_words(tag)
                except ModbusClientError:
                    logger.warning(
                        "PLC read failed for tag, simulation fallback used",
                        extra={"tag_id": int(tag["tag_id"])},
                    )
            if real_word_map:
                live_record = self._build_record(sequence_no=now_unix, real_word_map=real_word_map)

        return FastPollPayload(
            status=status,
            live_record=live_record,
        )

    def _hybrid_history_records(self, start_index: int, count: int) -> list[list[int]]:
        simulated_records = [self._build_record(sequence_no=start_index + idx + 1) for idx in range(count)]
        active_tags = [tag for tag in TagRegistryService().get_tags() if tag["is_active"]]
        if not any(not tag.get("simulation_enabled", True) for tag in active_tags):
            return simulated_records
        try:
            real_records = self._read_history_records_from_plc(start_index=start_index, count=count)
        except ModbusClientError:
            logger.warning("PLC history read failed during hybrid polling; simulated history kept")
            return simulated_records
        return [
            self._overlay_simulated_tags(real_record, simulated_record, active_tags)
            for real_record, simulated_record in zip(real_records, simulated_records, strict=False)
        ]

    def _read_fast_poll_from_plc(self) -> FastPollPayload:
        layout = TagRegistryService().get_register_layout()
        return FastPollPayload(
            status=self._read_status_from_plc(),
            live_record=self._read_registers(
                address=int(layout["live_record_address"]),
                count=int(layout["live_record_count"]),
                register_type="holding",
            ),
        )

    def _read_history_records_from_plc(self, start_index: int, count: int) -> list[list[int]]:
        layout = TagRegistryService().get_register_layout()
        base_address = int(layout["history_base_address"])
        record_words = int(layout["history_record_words"])
        capacity = max(1, int(layout["history_capacity"]))
        records: list[list[int]] = []
        for index in range(count):
            slot = (start_index + index) % capacity
            records.append(
                self._read_registers(
                    address=base_address + (slot * record_words),
                    count=record_words,
                    register_type="holding",
                )
            )
        return records

    def _build_record(self, sequence_no: int, real_word_map: dict[int, list[int]] | None = None) -> list[int]:
        timestamp_unix = int(time.time())
        wave_fast = math.sin(sequence_no / 3.0)
        wave_slow = math.sin(sequence_no / 11.0)
        tags = [tag for tag in TagRegistryService().get_tags() if tag["is_active"]]
        max_offset = max((int(tag["register_offset"]) + self._word_count_for_tag(tag) for tag in tags), default=0)
        values = [0] * max_offset
        sim_phase, status_word = self._simulated_test_state(timestamp_unix)
        validity_word1 = 0
        validity_word2 = 0

        for tag in tags:
            tag_id = int(tag["tag_id"])
            offset = int(tag["register_offset"])
            words = (real_word_map or {}).get(tag_id)
            if words is None:
                wave = wave_fast if tag["simulation_wave"] == "fast" else wave_slow
                simulated_value = self._simulated_tag_value(tag, wave, status_word)
                words = self._encode_simulated_words(tag, simulated_value)
            for index, word in enumerate(words):
                jitter = random.randint(-2, 2) if words is not None and tag.get("simulation_enabled", True) and index == len(words) - 1 else 0
                if offset + index < len(values):
                    values[offset + index] = max(0, int(word) + jitter)
            validity_bit = tag.get("validity_bit")
            if validity_bit is not None:
                bit_index = int(validity_bit)
                if bit_index < 16:
                    validity_word1 |= 1 << bit_index
                else:
                    validity_word2 |= 1 << (bit_index - 16)

        record = [
            (sequence_no >> 16) & 0xFFFF,
            sequence_no & 0xFFFF,
            (timestamp_unix >> 16) & 0xFFFF,
            timestamp_unix & 0xFFFF,
            sim_phase,
            status_word,
            validity_word1,
            validity_word2,
            *values,
        ]
        target_count = int(TagRegistryService().get_register_layout()["live_record_count"])
        if len(record) < target_count:
            record.extend([0] * (target_count - len(record)))
        return record[:target_count]

    @staticmethod
    def _simulated_tag_value(tag: dict[str, Any], wave: float, status_word: int) -> int:
        legacy_code = str(tag.get("legacy_code") or "")
        simulated_value = int(tag["simulation_base"]) + int(int(tag["simulation_amplitude"]) * wave)
        comp1_running = bool(status_word & (1 << 2))
        comp2_running = bool(status_word & (1 << 3))
        comp1_zero_fields = {
            "comp1_current",
            "comp1_active_power",
            "comp1_reactive_power",
            "comp1_apparent_power",
            "comp1_power_factor",
            "comp1_frequency",
        }
        comp2_zero_fields = {
            "comp2_current",
            "comp2_active_power",
            "comp2_reactive_power",
            "comp2_apparent_power",
            "comp2_power_factor",
            "comp2_frequency",
        }
        if legacy_code in comp1_zero_fields and not comp1_running:
            return 0
        if legacy_code in comp2_zero_fields and not comp2_running:
            return 0
        return simulated_value

    @staticmethod
    def _simulated_test_state(timestamp_unix: int) -> tuple[int, int]:
        from apps.tests.models import TestRecord

        active_test = TestRecord.active().first()
        if not active_test or not active_test.started_at:
            return int(TestPhase.IDLE), 0

        elapsed = float(timestamp_unix) - float(active_test.started_at.timestamp())
        start_end = float(active_test.start_duration_sec_snapshot)
        stable_end = start_end + float(active_test.stable_duration_sec_snapshot)
        stop_end = stable_end + float(active_test.stop_duration_sec_snapshot)

        if elapsed < 0:
            phase = TestPhase.IDLE
        elif elapsed < start_end:
            phase = TestPhase.START
        elif elapsed < stable_end:
            phase = TestPhase.STABLE
        elif elapsed < stop_end:
            phase = TestPhase.STOP
        else:
            phase = TestPhase.STOP

        status_word = 0
        if phase in {TestPhase.START, TestPhase.STABLE, TestPhase.STOP}:
            status_word |= 1 << 0

        selected_circuit = int(active_test.selected_circuit)
        compressors_running = phase in {TestPhase.START, TestPhase.STABLE}
        if compressors_running and selected_circuit in {int(CircuitSelect.CIRCUIT_1), int(CircuitSelect.BOTH)}:
            status_word |= 1 << 2
        if compressors_running and selected_circuit in {int(CircuitSelect.CIRCUIT_2), int(CircuitSelect.BOTH)}:
            status_word |= 1 << 3
        return int(phase), status_word

    def _simulated_status(self, now_unix: int) -> dict[str, Any]:
        history_capacity = int(TagRegistryService().get_register_layout()["history_capacity"])
        return {
            "PlcReady": True,
            "PlcFault": False,
            "Buf_WriteIndex": now_unix % history_capacity,
            "Buf_RecordCount": min(history_capacity, 80 + now_unix % 20),
            "Buf_BufferSize": history_capacity,
            "Buf_LastSequenceNo": now_unix,
            "TimeSyncDone": True,
            "PlcCurrentUnix": now_unix,
        }

    def _read_status_from_plc(self) -> dict[str, Any]:
        layout = TagRegistryService().get_register_layout()
        registers = self._read_registers(
            address=int(layout["status_address"]),
            count=int(layout["status_count"]),
            register_type="holding",
        )
        if len(registers) < 12:
            raise ModbusClientError("PLC status block is shorter than expected.")
        return {
            "PlcReady": bool(registers[0]),
            "PlcFault": bool(registers[2]),
            "Buf_WriteIndex": int(registers[4]),
            "Buf_RecordCount": int(registers[5]),
            "Buf_BufferSize": int(registers[6]),
            "Buf_LastSequenceNo": ((int(registers[7]) & 0xFFFF) << 16) | (int(registers[8]) & 0xFFFF),
            "TimeSyncDone": bool(registers[9]),
            "PlcCurrentUnix": ((int(registers[10]) & 0xFFFF) << 16) | (int(registers[11]) & 0xFFFF),
        }

    def _read_tag_words(self, tag: dict[str, Any]) -> list[int]:
        return self._read_registers(
            address=int(tag["modbus_address"]),
            count=self._word_count_for_tag(tag),
            register_type=str(tag.get("register_type") or "holding"),
        )

    def _overlay_simulated_tags(
        self,
        real_record: list[int],
        simulated_record: list[int],
        active_tags: list[dict[str, Any]],
    ) -> list[int]:
        merged = list(real_record)
        for tag in active_tags:
            if not tag.get("simulation_enabled", True):
                continue
            offset = 8 + int(tag["register_offset"])
            word_count = self._word_count_for_tag(tag)
            for index in range(word_count):
                source_index = offset + index
                if source_index < len(merged) and source_index < len(simulated_record):
                    merged[source_index] = simulated_record[source_index]
            validity_bit = tag.get("validity_bit")
            if validity_bit is None:
                continue
            bit_index = int(validity_bit)
            if bit_index < 16 and len(merged) > 6 and len(simulated_record) > 6:
                merged[6] |= simulated_record[6] & (1 << bit_index)
            elif bit_index >= 16 and len(merged) > 7 and len(simulated_record) > 7:
                merged[7] |= simulated_record[7] & (1 << (bit_index - 16))
        return merged

    @staticmethod
    def _word_count_for_tag(tag: dict[str, Any]) -> int:
        return 2 if str(tag.get("data_type") or "int16") in {"int32", "uint32", "float32"} else 1

    @staticmethod
    def _encode_simulated_words(tag: dict[str, Any], raw_value: int) -> list[int]:
        data_type = str(tag.get("data_type") or "int16")
        if data_type in {"int32", "uint32", "float32"}:
            normalized = max(0, raw_value) & 0xFFFFFFFF
            high_word = (normalized >> 16) & 0xFFFF
            low_word = normalized & 0xFFFF
            if str(tag.get("word_order") or "high_low") == "low_high":
                return [low_word, high_word]
            return [high_word, low_word]
        return [raw_value & 0xFFFF]

    def _read_registers(self, *, address: int, count: int, register_type: str) -> list[int]:
        client = ModbusTcpClient(
            host=self.config["host"],
            port=int(self.config["port"]),
            timeout=float(self.config["timeout_sec"]),
        )
        try:
            if not client.connect():
                raise ModbusClientError(f"PLC connection failed: {self.config['host']}:{self.config['port']}")
            if register_type == "input":
                response = client.read_input_registers(address=address, count=count, slave=int(self.config["unit_id"]))
            else:
                response = client.read_holding_registers(address=address, count=count, slave=int(self.config["unit_id"]))
            if response.isError():
                raise ModbusClientError(f"Modbus read failed for address {address} count {count}")
            return list(response.registers or [])
        except ModbusClientError:
            raise
        except Exception as exc:
            raise ModbusClientError(str(exc)) from exc
        finally:
            client.close()
