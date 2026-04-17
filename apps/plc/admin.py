from __future__ import annotations

from django.contrib import admin

from apps.plc.models import PlcEventLog, PlcRuntimeState


@admin.register(PlcRuntimeState)
class PlcRuntimeStateAdmin(admin.ModelAdmin):
    list_display = ("plc_ready", "plc_fault", "connection_ok", "last_seen_at")


@admin.register(PlcEventLog)
class PlcEventLogAdmin(admin.ModelAdmin):
    list_display = ("event_type", "event_code", "test_record", "created_at")
    list_filter = ("event_type", "event_code")
    search_fields = ("message", "event_code")
