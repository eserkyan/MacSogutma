from __future__ import annotations

from django.contrib import admin

from apps.core.models import PlcSchemaConfig, TagConfig


@admin.register(PlcSchemaConfig)
class PlcSchemaConfigAdmin(admin.ModelAdmin):
    list_display = (
        "status_address",
        "live_record_address",
        "history_base_address",
        "cmd_circuit_select",
        "cmd_test_phase",
    )

    def has_add_permission(self, request):
        return not PlcSchemaConfig.objects.exists()


@admin.register(TagConfig)
class TagConfigAdmin(admin.ModelAdmin):
    list_display = (
        "tag_id",
        "label",
        "register_offset",
        "scale",
        "circuit_scope",
        "chart_group",
        "validity_bit",
        "simulation_enabled",
        "is_active",
    )
    list_filter = ("circuit_scope", "chart_group", "simulation_enabled", "is_active", "include_in_limits", "include_in_reports")
    search_fields = ("label", "label_en", "chart_group")
    ordering = ("source_block", "modbus_address", "register_offset", "tag_id")
