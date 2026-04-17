from __future__ import annotations

from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def ui_datetime(value, language: str = "tr") -> str:
    if not value:
        return "-"
    localized = timezone.localtime(value) if hasattr(value, "astimezone") else value
    if language == "en":
        return localized.strftime("%Y-%m-%d %H:%M:%S")
    return localized.strftime("%d.%m.%Y %H:%M:%S")


@register.filter
def ui_datetime_short(value, language: str = "tr") -> str:
    if not value:
        return "-"
    localized = timezone.localtime(value) if hasattr(value, "astimezone") else value
    if language == "en":
        return localized.strftime("%Y-%m-%d %H:%M")
    return localized.strftime("%d.%m.%Y %H:%M")
