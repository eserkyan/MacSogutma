from __future__ import annotations

from django.db import models

from apps.companies.models import Company
from apps.core.constants import CircuitSelect, EvaluationPhase, TestPhase, TestStatus
from apps.core.models import TimeStampedModel
from apps.core.services.tag_registry import TagRegistryService
from apps.products.models import ProductModel
from apps.recipes.models import Recipe


class ActiveTestQuerySet(models.QuerySet["TestRecord"]):
    def active(self) -> "ActiveTestQuerySet":
        return self.filter(status__in=TestRecord.active_statuses())


class TestRecord(TimeStampedModel):
    test_no = models.CharField(max_length=50, unique=True)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="tests")
    product_model = models.ForeignKey(ProductModel, on_delete=models.PROTECT, related_name="tests")
    recipe = models.ForeignKey(Recipe, on_delete=models.PROTECT, related_name="tests")
    operator_name = models.CharField(max_length=255)
    selected_circuit = models.PositiveSmallIntegerField(choices=CircuitSelect.choices())
    status = models.CharField(max_length=32, choices=TestStatus.choices(), default=TestStatus.DRAFT)
    started_at = models.DateTimeField(blank=True, null=True)
    stable_started_at = models.DateTimeField(blank=True, null=True)
    stop_started_at = models.DateTimeField(blank=True, null=True)
    ended_at = models.DateTimeField(blank=True, null=True)
    recipe_name_snapshot = models.CharField(max_length=255)
    recipe_code_snapshot = models.CharField(max_length=64)
    recipe_revision_snapshot = models.CharField(max_length=32)
    start_duration_sec_snapshot = models.PositiveIntegerField()
    stable_duration_sec_snapshot = models.PositiveIntegerField()
    stop_duration_sec_snapshot = models.PositiveIntegerField()
    phase_context_sec_snapshot = models.PositiveIntegerField(default=5)
    prestart_samples_json = models.JSONField(default=list, blank=True)
    limits_snapshot_json = models.JSONField(default=dict)
    result_passed = models.BooleanField(blank=True, null=True)
    abort_reason = models.CharField(max_length=255, blank=True, null=True)
    fail_reason_summary = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    pdf_file_path = models.CharField(max_length=500, blank=True, null=True)
    pdf_generated_at = models.DateTimeField(blank=True, null=True)
    excel_file_path = models.CharField(max_length=500, blank=True, null=True)
    excel_generated_at = models.DateTimeField(blank=True, null=True)

    objects = ActiveTestQuerySet.as_manager()

    class Meta:
        ordering = ("-created_at",)

    @classmethod
    def active_statuses(cls) -> tuple[str, ...]:
        return (TestStatus.START_REQUESTED, TestStatus.RUNNING)

    @classmethod
    def active(cls) -> ActiveTestQuerySet:
        return cls.objects.active()

    @property
    def current_phase(self) -> TestPhase:
        if self.ended_at and self.status in {TestStatus.COMPLETED_PASS, TestStatus.COMPLETED_FAIL}:
            return TestPhase.STOP
        if self.stop_started_at:
            return TestPhase.STOP
        if self.stable_started_at:
            return TestPhase.STABLE
        if self.started_at:
            return TestPhase.START
        return TestPhase.IDLE

    def __str__(self) -> str:
        return self.test_no


class TestSampleManager(models.Manager["TestSample"]):
    def create_from_parsed(self, test_record: TestRecord, parsed: object) -> "TestSample":
        data = {
            "test_record": test_record,
            "sequence_no": parsed.sequence_no,
            "timestamp_unix": parsed.timestamp_unix,
            "test_phase": parsed.test_phase,
            "status_word": parsed.status_word,
            "validity_word1": parsed.validity_word1,
            "validity_word2": parsed.validity_word2,
            "dynamic_values": dict(parsed.values),
        }
        return self.create(**data)


class TestSample(TimeStampedModel):
    test_record = models.ForeignKey(TestRecord, on_delete=models.CASCADE, related_name="samples")
    sequence_no = models.PositiveIntegerField()
    timestamp_unix = models.BigIntegerField()
    test_phase = models.PositiveSmallIntegerField(choices=TestPhase.choices())
    status_word = models.PositiveIntegerField()
    validity_word1 = models.PositiveIntegerField()
    validity_word2 = models.PositiveIntegerField(blank=True, null=True)
    dynamic_values = models.JSONField(default=dict, blank=True)

    objects = TestSampleManager()

    class Meta:
        ordering = ("timestamp_unix", "sequence_no")
        unique_together = ("test_record", "sequence_no")

    def get_value(self, code: str | int) -> object:
        payload = self.dynamic_values or {}
        lookup_key = str(code)
        if lookup_key in payload:
            return payload.get(lookup_key)
        for tag in TagRegistryService().get_tags():
            if str(tag["tag_id"]) == lookup_key:
                legacy_code = str(tag.get("legacy_code") or "")
                if legacy_code and legacy_code in payload:
                    return payload.get(legacy_code)
        return None


class TestEvaluationResult(TimeStampedModel):
    test_record = models.ForeignKey(TestRecord, on_delete=models.CASCADE, related_name="evaluation_results")
    parameter_code = models.CharField(max_length=100)
    parameter_name = models.CharField(max_length=255)
    phase_used = models.CharField(max_length=20, choices=EvaluationPhase.choices(), default=EvaluationPhase.STABLE)
    avg_value = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)
    min_enabled = models.BooleanField(default=False)
    min_limit = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)
    max_enabled = models.BooleanField(default=False)
    max_limit = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)
    passed = models.BooleanField(blank=True, null=True, default=None)
    message = models.TextField(blank=True)

    class Meta:
        ordering = ("parameter_code",)
