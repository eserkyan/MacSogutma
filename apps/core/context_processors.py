from __future__ import annotations

from django.conf import settings

from apps.plc.models import PlcRuntimeState
from apps.tests.models import TestRecord
from apps.core.ui_translations import LANGUAGE_OPTIONS


def app_context(_: object) -> dict[str, object]:
    request = _
    runtime = PlcRuntimeState.load()
    active_test = (
        TestRecord.objects.filter(status__in=TestRecord.active_statuses())
        .select_related("company", "product_model", "recipe")
        .first()
    )
    language = "tr"
    if hasattr(request, "session"):
        language = request.session.get("ui_language", "tr")
    return {
        "app_name": "HVAC Test System",
        "plc_runtime": runtime,
        "active_test_context": active_test,
        "report_root_path": settings.PLC_CONFIG["report_root_path"],
        "ui_language": language,
        "ui_languages": LANGUAGE_OPTIONS,
    }
