from __future__ import annotations

import time
from dataclasses import asdict
from typing import Any

from django.db.utils import OperationalError, ProgrammingError

from apps.core.models import PlcSchemaConfig, TagConfig
from apps.core.tag_schema import CHART_GROUP_DEFINITIONS, PLC_REGISTER_LAYOUT, TAG_DEFINITIONS
from apps.core.ui_translations import get_text


class TagRegistryService:
    _cache: dict[str, tuple[float, object]] = {}
    ttl_seconds = 5.0
    LEGACY_DISABLED_TAG_IDS: set[int] = {109}

    def get_tags(self) -> list[dict[str, Any]]:
        cached = self._get_cached("tags")
        if cached is not None:
            return cached
        tags = self._load_tags()
        self._cache["tags"] = (time.monotonic(), tags)
        return tags

    def get_parameter_definitions(self, include_limits_only: bool = False, language: str = "tr") -> dict[str, dict[str, str]]:
        return {
            tag["code"]: {"label": self._display_label(tag, language), "unit": tag["unit"]}
            for tag in self.get_tags()
            if tag["is_active"] and (not include_limits_only or tag["include_in_limits"])
        }

    def get_validity_tag_map(self) -> dict[str, int]:
        return {
            tag["code"]: int(tag["validity_bit"])
            for tag in self.get_tags()
            if tag["is_active"] and tag["validity_bit"] is not None
        }

    def get_parameter_codes_for_scope(self, scope: str) -> set[str]:
        return {
            tag["code"]
            for tag in self.get_tags()
            if tag["is_active"] and tag["circuit_scope"] == scope
        }

    def get_chart_groups(self, language: str = "tr") -> list[dict[str, object]]:
        groups: dict[str, dict[str, object]] = {}
        default_titles = {item.slug: item.title for item in CHART_GROUP_DEFINITIONS}
        default_chart_ids = {item.slug: item.chart_id for item in CHART_GROUP_DEFINITIONS}
        for tag in self.get_tags():
            if not tag["is_active"]:
                continue
            group_slug = tag["chart_group"]
            group = groups.setdefault(
                group_slug,
                {
                    "chart_id": default_chart_ids.get(group_slug, f"{group_slug}Chart"),
                    "title": self._resolve_chart_group_title(
                        group_slug,
                        str(tag.get("chart_group_title_en") if language == "en" else tag.get("chart_group_title") or ""),
                        language=language,
                    )
                    or default_titles.get(group_slug, group_slug.title()),
                    "datasets": [],
                },
            )
            group["datasets"].append(
                {
                    "key": tag["code"],
                    "label": self._display_label(tag, language),
                    "color": tag["chart_color"],
                }
            )
        return list(groups.values())

    def get_register_layout(self) -> dict[str, object]:
        cached = self._get_cached("layout")
        if cached is not None:
            return cached
        layout = self._load_layout()
        self._cache["layout"] = (time.monotonic(), layout)
        return layout

    def get_layout_instance(self) -> PlcSchemaConfig:
        try:
            return PlcSchemaConfig.load()
        except (OperationalError, ProgrammingError):
            return PlcSchemaConfig()

    def ensure_defaults(self) -> None:
        try:
            PlcSchemaConfig.load()
            existing_by_tag_id = {int(item.tag_id): item for item in TagConfig.objects.all()}
            create_items = []
            for tag in TAG_DEFINITIONS:
                existing = existing_by_tag_id.get(int(tag.tag_id))
                if existing:
                    changed_fields: list[str] = []
                    defaults = {
                        "tag_id": tag.tag_id,
                        "label": tag.label,
                        "label_en": tag.label_en,
                        "register_type": tag.register_type,
                        "source_block": tag.source_block,
                        "data_type": tag.data_type,
                        "word_order": tag.word_order,
                        "modbus_address": tag.modbus_address,
                        "register_offset": tag.register_offset,
                        "scale": tag.scale,
                        "unit": tag.unit,
                        "circuit_scope": tag.circuit_scope,
                        "chart_group": tag.chart_group,
                        "chart_color": tag.chart_color,
                        "validity_bit": tag.validity_bit,
                        "simulation_enabled": tag.simulation_enabled,
                        "simulation_base": tag.simulation_base,
                        "simulation_amplitude": tag.simulation_amplitude,
                        "simulation_wave": tag.simulation_wave,
                        "is_active": self._default_is_active(tag.tag_id),
                        "include_in_limits": self._default_include_in_limits(tag.tag_id),
                        "include_in_reports": self._default_include_in_reports(tag.tag_id),
                    }
                    for field_name, default_value in defaults.items():
                        current_value = getattr(existing, field_name, None)
                        if current_value in {None, ""} or current_value != default_value:
                            setattr(existing, field_name, default_value)
                            changed_fields.append(field_name)
                    expected_chart_group_title = self._chart_group_title(tag.chart_group, language="tr")
                    expected_chart_group_title_en = self._chart_group_title(tag.chart_group, language="en")
                    if existing.chart_group_title != expected_chart_group_title:
                        existing.chart_group_title = self._chart_group_title(tag.chart_group, language="tr")
                        changed_fields.append("chart_group_title")
                    if existing.chart_group_title_en != expected_chart_group_title_en:
                        existing.chart_group_title_en = self._chart_group_title(tag.chart_group, language="en")
                        changed_fields.append("chart_group_title_en")
                    if changed_fields:
                        existing.save(update_fields=[*changed_fields, "updated_at"])
                    continue
                create_items.append(
                    TagConfig(
                        tag_id=tag.tag_id,
                        label=tag.label,
                        label_en=tag.label_en,
                        unit=tag.unit,
                        scale=tag.scale,
                        register_type=tag.register_type,
                        source_block=tag.source_block,
                        data_type=tag.data_type,
                        word_order=tag.word_order,
                        modbus_address=tag.modbus_address,
                        register_offset=tag.register_offset,
                        circuit_scope=tag.circuit_scope,
                        chart_group=tag.chart_group,
                        chart_group_title=self._chart_group_title(tag.chart_group, language="tr"),
                        chart_group_title_en=self._chart_group_title(tag.chart_group, language="en"),
                        chart_color=tag.chart_color,
                        validity_bit=tag.validity_bit,
                        simulation_enabled=tag.simulation_enabled,
                        simulation_base=tag.simulation_base,
                        simulation_amplitude=tag.simulation_amplitude,
                        simulation_wave=tag.simulation_wave,
                        is_active=self._default_is_active(tag.tag_id),
                        include_in_limits=self._default_include_in_limits(tag.tag_id),
                        include_in_reports=self._default_include_in_reports(tag.tag_id),
                    )
                )
            if create_items:
                TagConfig.objects.bulk_create(create_items)
            self.clear_cache()
        except (OperationalError, ProgrammingError):
            return

    @classmethod
    def clear_cache(cls) -> None:
        cls._cache.clear()

    def _load_tags(self) -> list[dict[str, Any]]:
        default_map = {
            str(tag.tag_id): {
                "code": str(tag.tag_id),
                "legacy_code": tag.field_name,
                "tag_id": tag.tag_id,
                "label": tag.label,
                "label_en": tag.label_en,
                "unit": tag.unit,
                "scale": tag.scale,
                "register_type": tag.register_type,
                "source_block": tag.source_block,
                "data_type": tag.data_type,
                "word_order": tag.word_order,
                "modbus_address": tag.modbus_address,
                "register_offset": tag.register_offset,
                "circuit_scope": tag.circuit_scope,
                "chart_group": tag.chart_group,
                "chart_group_title": self._chart_group_title(tag.chart_group, language="tr"),
                "chart_group_title_en": self._chart_group_title(tag.chart_group, language="en"),
                "chart_color": tag.chart_color,
                "validity_bit": tag.validity_bit,
                "simulation_enabled": tag.simulation_enabled,
                "simulation_base": tag.simulation_base,
                "simulation_amplitude": tag.simulation_amplitude,
                "simulation_wave": tag.simulation_wave,
                "is_active": True,
                "include_in_limits": True,
                "include_in_reports": True,
            }
            for tag in TAG_DEFINITIONS
        }
        try:
            db_tags = list(TagConfig.objects.all())
        except (OperationalError, ProgrammingError):
            return list(default_map.values())

        if not db_tags:
            return list(default_map.values())

        merged: dict[str, dict[str, Any]] = dict(default_map)
        for tag in db_tags:
            merged[str(tag.tag_id)] = {
                "code": str(tag.tag_id),
                "legacy_code": next(
                    (item.field_name for item in TAG_DEFINITIONS if int(item.tag_id) == int(tag.tag_id)),
                    str(tag.tag_id),
                ),
                "tag_id": tag.tag_id,
                "label": tag.label,
                "label_en": tag.label_en,
                "unit": tag.unit,
                "scale": tag.scale,
                "register_type": tag.register_type,
                "source_block": tag.source_block,
                "data_type": tag.data_type,
                "word_order": tag.word_order,
                "modbus_address": tag.modbus_address,
                "register_offset": tag.register_offset,
                "circuit_scope": tag.circuit_scope,
                "chart_group": tag.chart_group,
                "chart_group_title": tag.chart_group_title or self._chart_group_title(tag.chart_group, language="tr"),
                "chart_group_title_en": tag.chart_group_title_en or self._chart_group_title(tag.chart_group, language="en"),
                "chart_color": tag.chart_color,
                "validity_bit": tag.validity_bit,
                "simulation_enabled": tag.simulation_enabled,
                "simulation_base": tag.simulation_base,
                "simulation_amplitude": tag.simulation_amplitude,
                "simulation_wave": tag.simulation_wave,
                "is_active": tag.is_active,
                "include_in_limits": tag.include_in_limits,
                "include_in_reports": tag.include_in_reports,
            }
        return sorted(
            merged.values(),
            key=lambda item: (item["source_block"], item["modbus_address"], item["register_offset"], item["tag_id"]),
        )

    def _load_layout(self) -> dict[str, object]:
        default = {
            "status_address": PLC_REGISTER_LAYOUT["status"].address,
            "status_count": PLC_REGISTER_LAYOUT["status"].count,
            "live_record_address": PLC_REGISTER_LAYOUT["live_record"].address,
            "live_record_count": PLC_REGISTER_LAYOUT["live_record"].count,
            "history_base_address": PLC_REGISTER_LAYOUT["history_base"],
            "history_record_words": PLC_REGISTER_LAYOUT["history_record_words"],
            "history_capacity": PLC_REGISTER_LAYOUT["history_capacity"],
            "cmd_circuit_select": PLC_REGISTER_LAYOUT["command_registers"]["circuit_select"],
            "cmd_start_request": PLC_REGISTER_LAYOUT["command_registers"]["start_request"],
            "cmd_stop_request": PLC_REGISTER_LAYOUT["command_registers"]["stop_request"],
            "cmd_abort_request": PLC_REGISTER_LAYOUT["command_registers"]["abort_request"],
            "cmd_test_phase": PLC_REGISTER_LAYOUT["command_registers"]["test_phase"],
            "cmd_test_active": PLC_REGISTER_LAYOUT["command_registers"]["test_active"],
            "cmd_time_sync_request": PLC_REGISTER_LAYOUT["command_registers"]["time_sync_request"],
            "cmd_time_sync_unix_high": PLC_REGISTER_LAYOUT["command_registers"]["time_sync_unix_high"],
            "cmd_time_sync_unix_low": PLC_REGISTER_LAYOUT["command_registers"]["time_sync_unix_low"],
        }
        try:
            config = PlcSchemaConfig.load()
        except (OperationalError, ProgrammingError):
            return default
        result = default | {
            "status_address": config.status_address,
            "status_count": config.status_count,
            "live_record_address": config.live_record_address,
            "live_record_count": config.live_record_count,
            "history_base_address": config.history_base_address,
            "history_record_words": config.history_record_words,
            "history_capacity": config.history_capacity,
            "cmd_circuit_select": config.cmd_circuit_select,
            "cmd_start_request": config.cmd_start_request,
            "cmd_stop_request": config.cmd_stop_request,
            "cmd_abort_request": config.cmd_abort_request,
            "cmd_test_phase": config.cmd_test_phase,
            "cmd_test_active": config.cmd_test_active,
            "cmd_time_sync_request": config.cmd_time_sync_request,
            "cmd_time_sync_unix_high": config.cmd_time_sync_unix_high,
            "cmd_time_sync_unix_low": config.cmd_time_sync_unix_low,
        }
        return result

    def _get_cached(self, key: str) -> object | None:
        cached = self._cache.get(key)
        if not cached:
            return None
        ts, value = cached
        if time.monotonic() - ts > self.ttl_seconds:
            return None
        return value

    @staticmethod
    def _chart_group_title(group_slug: str, language: str = "tr") -> str:
        translation_map = {
            "pressure": "charts.pressure_group",
            "process_temperature": "charts.process_temperature_group",
            "air_humidity": "charts.air_humidity_group",
            "air_flow": "charts.air_flow_group",
            "water_temperature": "charts.water_temperature_group",
            "air_temperature": "charts.air_temperature_group",
            "comp1_electrical": "charts.comp1_group",
            "comp2_electrical": "charts.comp2_group",
        }
        translation_key = translation_map.get(group_slug)
        if translation_key:
            return get_text(translation_key, language)
        for group in CHART_GROUP_DEFINITIONS:
            if group.slug == group_slug:
                return group.title
        return group_slug.title()

    def _resolve_chart_group_title(self, group_slug: str, raw_title: str, language: str = "tr") -> str:
        localized_default = self._chart_group_title(group_slug, language=language)
        if not raw_title:
            return localized_default
        known_default_titles = {group.title for group in CHART_GROUP_DEFINITIONS}
        known_default_titles.update(self._chart_group_title(group.slug, language="tr") for group in CHART_GROUP_DEFINITIONS)
        known_default_titles.update(self._chart_group_title(group.slug, language="en") for group in CHART_GROUP_DEFINITIONS)
        if raw_title in known_default_titles:
            return localized_default
        return raw_title

    @staticmethod
    def _display_label(tag: dict[str, Any], language: str) -> str:
        if language == "en" and tag.get("label_en"):
            return str(tag["label_en"])
        return str(tag["label"])

    def _default_is_active(self, tag_id: int) -> bool:
        return int(tag_id) not in self.LEGACY_DISABLED_TAG_IDS

    def _default_include_in_limits(self, tag_id: int) -> bool:
        return self._default_is_active(tag_id)

    def _default_include_in_reports(self, tag_id: int) -> bool:
        return self._default_is_active(tag_id)
