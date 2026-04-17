from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TagDefinition:
    tag_id: int
    field_name: str
    label: str
    label_en: str
    unit: str
    scale: str
    register_type: str
    source_block: str
    data_type: str
    word_order: str
    modbus_address: int
    register_offset: int
    circuit_scope: str
    chart_group: str
    chart_color: str
    validity_bit: int | None = None
    simulation_enabled: bool = True
    simulation_base: int = 0
    simulation_amplitude: int = 0
    simulation_wave: str = "slow"


@dataclass(frozen=True, slots=True)
class ChartGroupDefinition:
    slug: str
    chart_id: str
    title: str


@dataclass(frozen=True, slots=True)
class RegisterBlockDefinition:
    address: int
    count: int


TAG_DEFINITIONS: tuple[TagDefinition, ...] = (
    TagDefinition(101, "circuit1_hp", "Circuit 1 HP", "Circuit 1 HP", "bar", "x10", "holding", "live", "int16", "high_low", 108, 0, "circuit1", "pressure", "#2563eb", 0, True, 255, 12, "slow"),
    TagDefinition(102, "circuit1_lp", "Circuit 1 LP", "Circuit 1 LP", "bar", "x10", "holding", "live", "int16", "high_low", 109, 1, "circuit1", "pressure", "#1d4ed8", 1, True, 65, 5, "fast"),
    TagDefinition(103, "circuit2_hp", "Circuit 2 HP", "Circuit 2 HP", "bar", "x10", "holding", "live", "int16", "high_low", 110, 2, "circuit2", "pressure", "#0891b2", 2, True, 248, 10, "fast"),
    TagDefinition(104, "circuit2_lp", "Circuit 2 LP", "Circuit 2 LP", "bar", "x10", "holding", "live", "int16", "high_low", 111, 3, "circuit2", "pressure", "#0f766e", 3, True, 60, 4, "slow"),
    TagDefinition(105, "temp_1", "Temperature 1", "Temperature 1", "C", "x10", "holding", "live", "int16", "high_low", 112, 4, "shared", "temperature", "#f97316", 4, True, 295, 18, "fast"),
    TagDefinition(106, "temp_2", "Temperature 2", "Temperature 2", "C", "x10", "holding", "live", "int16", "high_low", 113, 5, "shared", "temperature", "#ea580c", 5, True, 240, 8, "slow"),
    TagDefinition(107, "temp_3", "Temperature 3", "Temperature 3", "C", "x10", "holding", "live", "int16", "high_low", 114, 6, "shared", "temperature", "#fb7185", 6, True, 245, 7, "fast"),
    TagDefinition(108, "temp_4", "Temperature 4", "Temperature 4", "C", "x10", "holding", "live", "int16", "high_low", 115, 7, "shared", "temperature", "#e11d48", 7, True, 255, 6, "slow"),
    TagDefinition(109, "humidity", "Humidity", "Humidity", "RH", "x10", "holding", "live", "int16", "high_low", 116, 8, "shared", "ambient", "#7c3aed", 8, True, 450, 25, "fast"),
    TagDefinition(110, "air_velocity", "Air Velocity", "Air Velocity", "m/s", "x10", "holding", "live", "int16", "high_low", 117, 9, "shared", "ambient", "#a855f7", 9, True, 32, 4, "slow"),
    TagDefinition(111, "comp1_voltage", "Compressor 1 Voltage", "Compressor 1 Voltage", "V", "x10", "holding", "live", "int16", "high_low", 118, 10, "circuit1", "comp1_electrical", "#16a34a", None, True, 2300, 20, "fast"),
    TagDefinition(112, "comp1_current", "Compressor 1 Current", "Compressor 1 Current", "A", "x100", "holding", "live", "int16", "high_low", 119, 11, "circuit1", "comp1_electrical", "#15803d", 10, True, 1260, 90, "slow"),
    TagDefinition(113, "comp1_active_power", "Compressor 1 Active Power", "Compressor 1 Active Power", "kW", "x10", "holding", "live", "int16", "high_low", 120, 12, "circuit1", "comp1_electrical", "#22c55e", 11, True, 42, 5, "fast"),
    TagDefinition(114, "comp1_reactive_power", "Compressor 1 Reactive Power", "Compressor 1 Reactive Power", "kVAr", "x10", "holding", "live", "int16", "high_low", 121, 13, "circuit1", "comp1_electrical", "#84cc16", None, True, 10, 2, "slow"),
    TagDefinition(115, "comp1_apparent_power", "Compressor 1 Apparent Power", "Compressor 1 Apparent Power", "kVA", "x10", "holding", "live", "int16", "high_low", 122, 14, "circuit1", "comp1_electrical", "#65a30d", None, True, 44, 5, "fast"),
    TagDefinition(116, "comp1_power_factor", "Compressor 1 PF", "Compressor 1 PF", "PF", "x1000", "holding", "live", "int16", "high_low", 123, 15, "circuit1", "comp1_electrical", "#4d7c0f", None, True, 980, 8, "slow"),
    TagDefinition(117, "comp1_frequency", "Compressor 1 Frequency", "Compressor 1 Frequency", "Hz", "x10", "holding", "live", "int16", "high_low", 124, 16, "circuit1", "comp1_electrical", "#0f766e", None, True, 500, 5, "fast"),
    TagDefinition(118, "comp1_energy", "Compressor 1 Energy", "Compressor 1 Energy", "kWh", "x10", "holding", "live", "int16", "high_low", 125, 17, "circuit1", "comp1_electrical", "#0d9488", None, True, 130, 2, "slow"),
    TagDefinition(119, "comp2_voltage", "Compressor 2 Voltage", "Compressor 2 Voltage", "V", "x10", "holding", "live", "int16", "high_low", 126, 18, "circuit2", "comp2_electrical", "#dc2626", None, True, 2295, 18, "slow"),
    TagDefinition(120, "comp2_current", "Compressor 2 Current", "Compressor 2 Current", "A", "x100", "holding", "live", "int16", "high_low", 127, 19, "circuit2", "comp2_electrical", "#ef4444", 12, True, 715, 25, "fast"),
    TagDefinition(121, "comp2_active_power", "Compressor 2 Active Power", "Compressor 2 Active Power", "kW", "x10", "holding", "live", "int16", "high_low", 128, 20, "circuit2", "comp2_electrical", "#f97316", 13, True, 34, 4, "slow"),
    TagDefinition(122, "comp2_reactive_power", "Compressor 2 Reactive Power", "Compressor 2 Reactive Power", "kVAr", "x10", "holding", "live", "int16", "high_low", 129, 21, "circuit2", "comp2_electrical", "#fb7185", None, True, 9, 2, "fast"),
    TagDefinition(123, "comp2_apparent_power", "Compressor 2 Apparent Power", "Compressor 2 Apparent Power", "kVA", "x10", "holding", "live", "int16", "high_low", 130, 22, "circuit2", "comp2_electrical", "#e11d48", None, True, 37, 4, "slow"),
    TagDefinition(124, "comp2_power_factor", "Compressor 2 PF", "Compressor 2 PF", "PF", "x1000", "holding", "live", "int16", "high_low", 131, 23, "circuit2", "comp2_electrical", "#be123c", None, True, 975, 6, "fast"),
    TagDefinition(125, "comp2_frequency", "Compressor 2 Frequency", "Compressor 2 Frequency", "Hz", "x10", "holding", "live", "int16", "high_low", 132, 24, "circuit2", "comp2_electrical", "#b91c1c", None, True, 500, 5, "slow"),
    TagDefinition(126, "comp2_energy", "Compressor 2 Energy", "Compressor 2 Energy", "kWh", "x10", "holding", "live", "int16", "high_low", 133, 25, "circuit2", "comp2_electrical", "#7f1d1d", None, True, 128, 2, "fast"),
)

CHART_GROUP_DEFINITIONS: tuple[ChartGroupDefinition, ...] = (
    ChartGroupDefinition("pressure", "pressureChart", "Basinc Grafikleri"),
    ChartGroupDefinition("temperature", "temperatureChart", "Sicaklik Grafikleri"),
    ChartGroupDefinition("ambient", "ambientChart", "Ortam Grafikleri"),
    ChartGroupDefinition("comp1_electrical", "comp1ElectricalChart", "Kompresor 1 Elektriksel"),
    ChartGroupDefinition("comp2_electrical", "comp2ElectricalChart", "Kompresor 2 Elektriksel"),
)

PLC_REGISTER_LAYOUT = {
    "status": RegisterBlockDefinition(address=0, count=12),
    "live_record": RegisterBlockDefinition(address=100, count=34),
    "history_base": 300,
    "history_record_words": 34,
    "history_capacity": 300,
    "command_registers": {
        "circuit_select": 1000,
        "start_request": 1001,
        "stop_request": 1002,
        "abort_request": 1003,
        "test_phase": 1004,
        "test_active": 1005,
        "time_sync_request": 1010,
        "time_sync_unix_high": 1011,
        "time_sync_unix_low": 1012,
    },
}


def tag_by_field(field_name: str) -> TagDefinition:
    for tag in TAG_DEFINITIONS:
        if tag.field_name == field_name:
            return tag
    raise KeyError(field_name)


def parameter_definitions() -> dict[str, dict[str, str]]:
    return {str(tag.tag_id): {"label": tag.label, "unit": tag.unit} for tag in TAG_DEFINITIONS}


def validity_tag_map() -> dict[str, int]:
    return {str(tag.tag_id): tag.validity_bit for tag in TAG_DEFINITIONS if tag.validity_bit is not None}


def parameter_codes_for_scope(scope: str) -> set[str]:
    return {str(tag.tag_id) for tag in TAG_DEFINITIONS if tag.circuit_scope == scope}


def chart_groups() -> list[dict[str, object]]:
    groups: list[dict[str, object]] = []
    for group in CHART_GROUP_DEFINITIONS:
        datasets = [
            {
                "key": str(tag.tag_id),
                "label": tag.label,
                "color": tag.chart_color,
            }
            for tag in TAG_DEFINITIONS
            if tag.chart_group == group.slug
        ]
        groups.append({"chart_id": group.chart_id, "title": group.title, "datasets": datasets})
    return groups
