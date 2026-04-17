from __future__ import annotations

from django.contrib import admin

from apps.tests.models import TestEvaluationResult, TestRecord, TestSample


class TestSampleInline(admin.TabularInline):
    model = TestSample
    extra = 0
    fields = ("sequence_no", "timestamp_unix", "test_phase")
    readonly_fields = fields


class TestEvaluationInline(admin.TabularInline):
    model = TestEvaluationResult
    extra = 0
    fields = ("parameter_code", "avg_value", "passed", "message")
    readonly_fields = fields


@admin.register(TestRecord)
class TestRecordAdmin(admin.ModelAdmin):
    list_display = ("test_no", "company", "product_model", "selected_circuit", "status", "created_at")
    list_filter = ("status", "selected_circuit")
    search_fields = ("test_no", "operator_name", "company__name")
    inlines = [TestEvaluationInline, TestSampleInline]


@admin.register(TestSample)
class TestSampleAdmin(admin.ModelAdmin):
    list_display = ("test_record", "sequence_no", "test_phase", "timestamp_unix")
    list_filter = ("test_phase",)


@admin.register(TestEvaluationResult)
class TestEvaluationResultAdmin(admin.ModelAdmin):
    list_display = ("test_record", "parameter_code", "avg_value", "passed")
