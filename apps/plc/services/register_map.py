from __future__ import annotations

from dataclasses import dataclass

from apps.core.tag_schema import PLC_REGISTER_LAYOUT


@dataclass(frozen=True, slots=True)
class RegisterBlock:
    address: int
    count: int


class PlcRegisterMap:
    STATUS = RegisterBlock(address=PLC_REGISTER_LAYOUT["status"].address, count=PLC_REGISTER_LAYOUT["status"].count)
    LIVE_RECORD = RegisterBlock(
        address=PLC_REGISTER_LAYOUT["live_record"].address,
        count=PLC_REGISTER_LAYOUT["live_record"].count,
    )
    HISTORY_BASE = PLC_REGISTER_LAYOUT["history_base"]
    HISTORY_RECORD_WORDS = PLC_REGISTER_LAYOUT["history_record_words"]
    HISTORY_CAPACITY = PLC_REGISTER_LAYOUT["history_capacity"]

    CMD_CIRCUIT_SELECT = PLC_REGISTER_LAYOUT["command_registers"]["circuit_select"]
    CMD_START_REQUEST = PLC_REGISTER_LAYOUT["command_registers"]["start_request"]
    CMD_STOP_REQUEST = PLC_REGISTER_LAYOUT["command_registers"]["stop_request"]
    CMD_ABORT_REQUEST = PLC_REGISTER_LAYOUT["command_registers"]["abort_request"]
    CMD_TEST_PHASE = PLC_REGISTER_LAYOUT["command_registers"]["test_phase"]
    CMD_TEST_ACTIVE = PLC_REGISTER_LAYOUT["command_registers"]["test_active"]
    CMD_TIME_SYNC_REQUEST = PLC_REGISTER_LAYOUT["command_registers"]["time_sync_request"]
    CMD_TIME_SYNC_UNIX_HIGH = PLC_REGISTER_LAYOUT["command_registers"]["time_sync_unix_high"]
    CMD_TIME_SYNC_UNIX_LOW = PLC_REGISTER_LAYOUT["command_registers"]["time_sync_unix_low"]
