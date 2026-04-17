from __future__ import annotations

from django import forms

from apps.core.forms_translation import apply_bootstrap_form_style, apply_form_labels
from apps.products.models import ProductModel


class ProductModelForm(forms.ModelForm):
    LABELS = {
        "model_code": "products.code",
        "model_name": "products.name",
        "product_type": "products.type",
        "description": "form.description",
        "is_active": "form.is_active",
    }

    class Meta:
        model = ProductModel
        fields = ["model_code", "model_name", "product_type", "description", "is_active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args: object, language: str = "tr", **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        apply_form_labels(self, language, self.LABELS)
        apply_bootstrap_form_style(self)
