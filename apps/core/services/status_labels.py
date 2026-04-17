from __future__ import annotations

from apps.core.constants import TestStatus


def get_test_status_label(status: str | TestStatus | None, language: str = "tr") -> str:
    if status is None:
        return "-"
    value = str(status)
    translations = {
        TestStatus.DRAFT.value: {"tr": "Taslak", "en": "Draft"},
        TestStatus.START_REQUESTED.value: {"tr": "Baslatiliyor", "en": "Starting"},
        TestStatus.RUNNING.value: {"tr": "Devam Ediyor", "en": "Running"},
        TestStatus.COMPLETED_PASS.value: {"tr": "Gecti", "en": "Passed"},
        TestStatus.COMPLETED_FAIL.value: {"tr": "Kaldi", "en": "Failed"},
        TestStatus.ABORTED.value: {"tr": "Iptal Edildi", "en": "Aborted"},
        TestStatus.FAILED_TO_START.value: {"tr": "Kaldi", "en": "Failed to Start"},
    }
    localized = translations.get(value)
    if localized:
        return localized.get(language, localized["tr"])
    return value.replace("_", " ").title()
