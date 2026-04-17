from __future__ import annotations

from django import template

from apps.core.ui_translations import get_text

register = template.Library()


@register.simple_tag(takes_context=True)
def ui_text(context: dict[str, object], key: str) -> str:
    language = str(context.get("ui_language", "tr"))
    return get_text(key, language)


@register.filter
def get_item(mapping: dict[str, object], key: str) -> object:
    if isinstance(mapping, dict):
        return mapping.get(key)
    return None
