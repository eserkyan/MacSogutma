from __future__ import annotations

from django import forms

from apps.core.forms_translation import apply_bootstrap_form_style, apply_form_labels
from apps.companies.models import Company


class CompanyForm(forms.ModelForm):
    LABELS = {
        "name": "companies.name",
        "code": "companies.code",
        "address": "form.address",
        "contact_name": "form.contact_name",
        "contact_phone": "form.contact_phone",
        "is_active": "form.is_active",
    }

    class Meta:
        model = Company
        fields = [
            "name",
            "code",
            "address",
            "contact_name",
            "contact_phone",
            "is_active",
        ]
        widgets = {"address": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args: object, language: str = "tr", **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        apply_form_labels(self, language, self.LABELS)
        apply_bootstrap_form_style(self)
