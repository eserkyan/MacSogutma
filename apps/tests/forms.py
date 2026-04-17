from __future__ import annotations

from django import forms

from apps.companies.models import Company
from apps.core.constants import CircuitSelect
from apps.core.forms_translation import apply_bootstrap_form_style, apply_form_labels
from apps.products.models import ProductModel
from apps.recipes.models import Recipe


class TestStartForm(forms.Form):
    company = forms.ModelChoiceField(queryset=Company.objects.filter(is_active=True))
    product_model = forms.ModelChoiceField(queryset=ProductModel.objects.filter(is_active=True))
    recipe = forms.ModelChoiceField(queryset=Recipe.objects.filter(is_active=True))
    circuit = forms.ChoiceField(choices=CircuitSelect.choices())
    operator_name = forms.CharField(max_length=255)
    notes = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)

    LABELS = {
        "company": "tests.company",
        "product_model": "products.name",
        "recipe": "tests.recipe",
        "circuit": "form.circuit",
        "operator_name": "form.operator_name",
        "notes": "form.notes",
    }

    def __init__(self, *args: object, language: str = "tr", **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        apply_form_labels(self, language, self.LABELS)
        apply_bootstrap_form_style(self)


class AbortTestForm(forms.Form):
    reason = forms.CharField(
        max_length=1000,
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": "Abort nedeni opsiyoneldir.",
            }
        ),
    )

    def __init__(self, *args: object, language: str = "tr", **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        apply_form_labels(self, language, {"reason": "form.abort_reason"})
        apply_bootstrap_form_style(self)
        if language == "en":
            self.fields["reason"].widget.attrs["placeholder"] = "Abort reason is optional."
