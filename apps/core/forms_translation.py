from __future__ import annotations

from django import forms

from apps.core.ui_translations import get_text


def apply_form_labels(form: forms.BaseForm, language: str, labels: dict[str, str]) -> None:
    for field_name, translation_key in labels.items():
        if field_name in form.fields:
            form.fields[field_name].label = get_text(translation_key, language)


def apply_bootstrap_form_style(form: forms.BaseForm) -> None:
    for field in form.fields.values():
        widget = field.widget
        classes = widget.attrs.get("class", "").split()
        if isinstance(widget, forms.CheckboxInput):
            base_class = "form-check-input"
        elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
            base_class = "form-select"
        else:
            base_class = "form-control"
        if base_class not in classes:
            classes.append(base_class)
        widget.attrs["class"] = " ".join(filter(None, classes))
