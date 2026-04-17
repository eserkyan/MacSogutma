from __future__ import annotations

from celery import shared_task

from apps.reports.services.excel_builder import ExcelBuilderService
from apps.reports.services.pdf_builder import PdfBuilderService
from apps.tests.models import TestRecord


@shared_task
def generate_pdf_task(test_record_id: int, language: str = "tr") -> str:
    return PdfBuilderService().build(TestRecord.objects.get(pk=test_record_id), language=language)


@shared_task
def generate_excel_task(test_record_id: int, language: str = "tr") -> str:
    return ExcelBuilderService().build(TestRecord.objects.get(pk=test_record_id), language=language)
