from __future__ import annotations

import base64
from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils import timezone
from weasyprint import HTML

from apps.reports.services.report_context import ReportContextService
from apps.tests.models import TestRecord


class PdfBuilderService:
    def build(self, test_record: TestRecord, language: str = "tr") -> str:
        target = self._target_path(test_record, language)
        target.parent.mkdir(parents=True, exist_ok=True)
        report_context = ReportContextService().build(test_record, language=language)
        mac_logo_path = self._mac_logo_path()
        kianes_logo_path = self._kianes_logo_path()
        html = render_to_string(
            "reports/pdf_report.html",
            {
                "test_record": test_record,
                "generated_at": timezone.now(),
                "report": report_context,
                "mac_logo_svg": mark_safe(mac_logo_path.read_text(encoding="utf-8")),
                "kianes_logo_uri": self._to_data_uri(kianes_logo_path, "image/png"),
            },
        )
        HTML(string=html, base_url=str(Path(settings.MEDIA_ROOT).parent)).write_pdf(target)
        test_record.pdf_file_path = str(target)
        test_record.pdf_generated_at = timezone.now()
        test_record.save(update_fields=["pdf_file_path", "pdf_generated_at", "updated_at"])
        return str(target)

    def target_path_for(self, test_record: TestRecord, language: str = "tr") -> Path:
        return self._target_path(test_record, language)

    def _target_path(self, test_record: TestRecord, language: str) -> Path:
        stamp = timezone.localtime()
        root = Path(settings.PLC_CONFIG["report_root_path"])
        return (
            root
            / test_record.company.code
            / test_record.product_model.model_code
            / f"{stamp:%Y}"
            / f"{stamp:%m}"
            / f"{test_record.test_no}_{language}.pdf"
        )

    @staticmethod
    def _mac_logo_path() -> Path:
        return Path(settings.BASE_DIR) / "static" / "images" / "mac-logo.svg"

    @staticmethod
    def _kianes_logo_path() -> Path:
        return Path(settings.BASE_DIR) / "static" / "images" / "kianes-logo.png"

    @classmethod
    def latest_asset_mtime(cls) -> float:
        assets = [
            Path(settings.BASE_DIR) / "apps" / "reports" / "templates" / "reports" / "pdf_report.html",
            Path(settings.BASE_DIR) / "apps" / "reports" / "services" / "pdf_builder.py",
            cls._mac_logo_path(),
            cls._kianes_logo_path(),
        ]
        return max(asset.stat().st_mtime for asset in assets if asset.exists())

    @staticmethod
    def _to_data_uri(path: Path, mime_type: str) -> str:
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"
