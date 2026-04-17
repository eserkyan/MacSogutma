from __future__ import annotations

from django.db import models

from apps.core.constants import PlcEventType
from apps.core.models import SingletonModel, TimeStampedModel


class PlcRuntimeState(SingletonModel, TimeStampedModel):
    plc_ready = models.BooleanField(default=False)
    plc_fault = models.BooleanField(default=False)
    buf_write_index = models.PositiveIntegerField(default=0)
    buf_record_count = models.PositiveIntegerField(default=0)
    buf_buffer_size = models.PositiveIntegerField(default=300)
    buf_last_sequence_no = models.PositiveIntegerField(default=0)
    plc_current_unix = models.BigIntegerField(default=0)
    live_record_json = models.JSONField(default=dict, blank=True)
    status_json = models.JSONField(default=dict, blank=True)
    monitoring_active = models.BooleanField(default=False)
    connection_ok = models.BooleanField(default=False)
    stale_data = models.BooleanField(default=False)
    last_seen_at = models.DateTimeField(blank=True, null=True)
    last_history_sync_at = models.DateTimeField(blank=True, null=True)
    last_overrun_at = models.DateTimeField(blank=True, null=True)
    last_time_sync_at = models.DateTimeField(blank=True, null=True)
    last_time_sync_drift_sec = models.IntegerField(default=0)
    communication_loss_since = models.DateTimeField(blank=True, null=True)
    last_error = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        verbose_name = "PLC Runtime State"


class PlcEventLog(TimeStampedModel):
    test_record = models.ForeignKey(
        "tests.TestRecord",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="plc_events",
    )
    event_type = models.CharField(max_length=20, choices=PlcEventType.choices())
    event_code = models.CharField(max_length=100)
    message = models.TextField()
    details_json = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.event_type}::{self.event_code}"
