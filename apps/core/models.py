from __future__ import annotations

from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SingletonModel(models.Model):
    singleton_key = models.PositiveSmallIntegerField(default=1, unique=True, editable=False)

    class Meta:
        abstract = True

    @classmethod
    def load(cls) -> "SingletonModel":
        instance, _ = cls.objects.get_or_create(singleton_key=1)
        return instance


class PlcSchemaConfig(SingletonModel, TimeStampedModel):
    plc_host = models.CharField(max_length=255, default="127.0.0.1")
    plc_port = models.PositiveIntegerField(default=502)
    modbus_unit_id = models.PositiveIntegerField(default=1)
    status_address = models.PositiveIntegerField(default=0)
    status_count = models.PositiveIntegerField(default=12)
    live_record_address = models.PositiveIntegerField(default=100)
    live_record_count = models.PositiveIntegerField(default=34)
    history_base_address = models.PositiveIntegerField(default=300)
    history_record_words = models.PositiveIntegerField(default=34)
    history_capacity = models.PositiveIntegerField(default=300)
    cmd_circuit_select = models.PositiveIntegerField(default=1000)
    cmd_start_request = models.PositiveIntegerField(default=1001)
    cmd_stop_request = models.PositiveIntegerField(default=1002)
    cmd_abort_request = models.PositiveIntegerField(default=1003)
    cmd_test_phase = models.PositiveIntegerField(default=1004)
    cmd_test_active = models.PositiveIntegerField(default=1005)
    cmd_time_sync_request = models.PositiveIntegerField(default=1010)
    cmd_time_sync_unix_high = models.PositiveIntegerField(default=1011)
    cmd_time_sync_unix_low = models.PositiveIntegerField(default=1012)

    class Meta:
        verbose_name = "PLC Schema Config"
        verbose_name_plural = "PLC Schema Config"


class TagConfig(TimeStampedModel):
    class CircuitScope(models.TextChoices):
        SHARED = "shared", "Shared"
        CIRCUIT_1 = "circuit1", "Circuit 1"
        CIRCUIT_2 = "circuit2", "Circuit 2"

    class RegisterType(models.TextChoices):
        HOLDING = "holding", "Holding Register"
        INPUT = "input", "Input Register"

    class SourceBlock(models.TextChoices):
        LIVE = "live", "Live Record"
        HISTORY = "history", "History Record"
        STATUS = "status", "Status Block"

    class DataType(models.TextChoices):
        INT16 = "int16", "INT16"
        UINT16 = "uint16", "UINT16"
        INT32 = "int32", "INT32"
        UINT32 = "uint32", "UINT32"
        FLOAT32 = "float32", "FLOAT32"

    class WordOrder(models.TextChoices):
        HIGH_LOW = "high_low", "High Word / Low Word"
        LOW_HIGH = "low_high", "Low Word / High Word"

    class ScaleMode(models.TextChoices):
        NONE = "none", "No Scale"
        X10 = "x10", "x10"
        X100 = "x100", "x100"
        X1000 = "x1000", "x1000"

    class SimulationWave(models.TextChoices):
        FAST = "fast", "Fast"
        SLOW = "slow", "Slow"

    tag_id = models.PositiveIntegerField(unique=True)
    label = models.CharField(max_length=255)
    label_en = models.CharField(max_length=255, blank=True, default="")
    unit = models.CharField(max_length=32)
    scale = models.CharField(max_length=20, choices=ScaleMode.choices, default=ScaleMode.X10)
    register_type = models.CharField(max_length=20, choices=RegisterType.choices, default=RegisterType.HOLDING)
    source_block = models.CharField(max_length=20, choices=SourceBlock.choices, default=SourceBlock.LIVE)
    data_type = models.CharField(max_length=20, choices=DataType.choices, default=DataType.INT16)
    word_order = models.CharField(max_length=20, choices=WordOrder.choices, default=WordOrder.HIGH_LOW)
    modbus_address = models.PositiveIntegerField(default=0)
    register_offset = models.PositiveIntegerField()
    circuit_scope = models.CharField(max_length=20, choices=CircuitScope.choices, default=CircuitScope.SHARED)
    chart_group = models.CharField(max_length=64, default="temperature")
    chart_group_title = models.CharField(max_length=255, blank=True, default="")
    chart_group_title_en = models.CharField(max_length=255, blank=True, default="")
    chart_color = models.CharField(max_length=16, default="#2563eb")
    validity_bit = models.PositiveSmallIntegerField(blank=True, null=True)
    simulation_enabled = models.BooleanField(default=True)
    simulation_base = models.IntegerField(default=0)
    simulation_amplitude = models.IntegerField(default=0)
    simulation_wave = models.CharField(max_length=10, choices=SimulationWave.choices, default=SimulationWave.SLOW)
    is_active = models.BooleanField(default=True)
    include_in_limits = models.BooleanField(default=True)
    include_in_reports = models.BooleanField(default=True)

    class Meta:
        ordering = ("source_block", "modbus_address", "register_offset", "tag_id")

    def __str__(self) -> str:
        return f"{self.tag_id} / {self.label}"

    @property
    def modbus_reference(self) -> str:
        prefix = "4" if self.register_type == self.RegisterType.HOLDING else "3"
        return f"{prefix}{int(self.modbus_address):05d}"
