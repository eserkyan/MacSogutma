from __future__ import annotations

from django import template

from apps.core.services.status_labels import get_test_status_label

register = template.Library()


@register.filter
def test_status_label(status: object, language: str = "tr") -> str:
    return get_test_status_label(str(status) if status is not None else None, language)
