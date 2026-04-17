from __future__ import annotations

from decimal import Decimal

from django import forms

from apps.core.forms_translation import apply_bootstrap_form_style, apply_form_labels
from apps.core.services.tag_registry import TagRegistryService
from apps.recipes.models import Recipe
from apps.recipes.services.phase_limits import PHASE_SLUGS, normalize_limit_config


def _limit_field_name(parameter_code: str, phase_slug: str, suffix: str) -> str:
    return f"{parameter_code}__{phase_slug}__{suffix}"


class RecipeForm(forms.ModelForm):
    LABELS = {
        "product_model": "recipes.model",
        "recipe_name": "recipes.name",
        "recipe_code": "recipes.code",
        "description": "form.description",
        "revision_no": "recipes.rev",
        "is_active": "form.is_active",
        "start_duration_sec": "form.start_duration",
        "stable_duration_sec": "form.stable_duration",
        "stop_duration_sec": "form.stop_duration",
        "phase_context_sec": "form.phase_context_duration",
    }

    class Meta:
        model = Recipe
        fields = [
            "product_model",
            "recipe_name",
            "recipe_code",
            "description",
            "revision_no",
            "is_active",
            "start_duration_sec",
            "stable_duration_sec",
            "stop_duration_sec",
            "phase_context_sec",
        ]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args: object, language: str = "tr", **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.language = language
        self.parameter_definitions = TagRegistryService().get_parameter_definitions(include_limits_only=True)
        self._build_limit_fields()
        apply_form_labels(self, language, self.LABELS)
        apply_bootstrap_form_style(self)
        self._configure_limit_widgets()

    def _build_limit_fields(self) -> None:
        saved_limits = self.instance.limits_json if self.instance.pk else {}
        for parameter_code in self.parameter_definitions:
            phase_limits = normalize_limit_config(saved_limits.get(parameter_code, {}))
            for phase_slug in PHASE_SLUGS:
                limit = phase_limits.get(phase_slug, {})
                self.fields[_limit_field_name(parameter_code, phase_slug, "min_enabled")] = forms.BooleanField(
                    required=False,
                    initial=bool(limit.get("min_enabled")),
                )
                self.fields[_limit_field_name(parameter_code, phase_slug, "min_value")] = forms.DecimalField(
                    required=False,
                    decimal_places=3,
                    max_digits=12,
                    initial=limit.get("min_value"),
                )
                self.fields[_limit_field_name(parameter_code, phase_slug, "max_enabled")] = forms.BooleanField(
                    required=False,
                    initial=bool(limit.get("max_enabled")),
                )
                self.fields[_limit_field_name(parameter_code, phase_slug, "max_value")] = forms.DecimalField(
                    required=False,
                    decimal_places=3,
                    max_digits=12,
                    initial=limit.get("max_value"),
                )

    def _configure_limit_widgets(self) -> None:
        for parameter_code in self.parameter_definitions:
            for phase_slug in PHASE_SLUGS:
                min_enabled = self.fields[_limit_field_name(parameter_code, phase_slug, "min_enabled")]
                min_value = self.fields[_limit_field_name(parameter_code, phase_slug, "min_value")]
                max_enabled = self.fields[_limit_field_name(parameter_code, phase_slug, "max_enabled")]
                max_value = self.fields[_limit_field_name(parameter_code, phase_slug, "max_value")]

                min_enabled.widget.attrs.update(
                    {
                        "class": "form-check-input limit-toggle",
                        "data-target": _limit_field_name(parameter_code, phase_slug, "min_value"),
                    }
                )
                max_enabled.widget.attrs.update(
                    {
                        "class": "form-check-input limit-toggle",
                        "data-target": _limit_field_name(parameter_code, phase_slug, "max_value"),
                    }
                )

                min_value.widget.attrs.update(
                    {
                        "class": "form-control form-control-sm limit-input",
                        "step": "0.001",
                        "placeholder": "0.000",
                        "id": _limit_field_name(parameter_code, phase_slug, "min_value"),
                    }
                )
                max_value.widget.attrs.update(
                    {
                        "class": "form-control form-control-sm limit-input",
                        "step": "0.001",
                        "placeholder": "0.000",
                        "id": _limit_field_name(parameter_code, phase_slug, "max_value"),
                    }
                )

                if not min_enabled.initial:
                    min_value.widget.attrs["disabled"] = "disabled"
                if not max_enabled.initial:
                    max_value.widget.attrs["disabled"] = "disabled"

    def clean(self) -> dict[str, object]:
        cleaned_data = super().clean()
        limits_json: dict[str, dict[str, dict[str, bool | float | None]]] = {}

        for parameter_code in self.parameter_definitions:
            limits_json[parameter_code] = {}
            for phase_slug in PHASE_SLUGS:
                min_enabled = bool(cleaned_data.get(_limit_field_name(parameter_code, phase_slug, "min_enabled")))
                max_enabled = bool(cleaned_data.get(_limit_field_name(parameter_code, phase_slug, "max_enabled")))
                min_value = cleaned_data.get(_limit_field_name(parameter_code, phase_slug, "min_value"))
                max_value = cleaned_data.get(_limit_field_name(parameter_code, phase_slug, "max_value"))

                if min_enabled and min_value is None:
                    self.add_error(
                        _limit_field_name(parameter_code, phase_slug, "min_value"),
                        "Minimum limit aktifken bir deger girilmelidir."
                        if self.language == "tr"
                        else "Enter a value when minimum limit is enabled.",
                    )
                if max_enabled and max_value is None:
                    self.add_error(
                        _limit_field_name(parameter_code, phase_slug, "max_value"),
                        "Maximum limit aktifken bir deger girilmelidir."
                        if self.language == "tr"
                        else "Enter a value when maximum limit is enabled.",
                    )
                if min_enabled and max_enabled and min_value is not None and max_value is not None and min_value > max_value:
                    self.add_error(
                        _limit_field_name(parameter_code, phase_slug, "max_value"),
                        "Maksimum limit minimum degerden kucuk olamaz."
                        if self.language == "tr"
                        else "Maximum limit cannot be smaller than minimum value.",
                    )

                limits_json[parameter_code][phase_slug] = {
                    "min_enabled": min_enabled,
                    "min_value": self._normalize_decimal(min_value),
                    "max_enabled": max_enabled,
                    "max_value": self._normalize_decimal(max_value),
                }

        cleaned_data["limits_json"] = limits_json
        return cleaned_data

    def save(self, commit: bool = True) -> Recipe:
        self.instance.limits_json = self.cleaned_data["limits_json"]
        return super().save(commit=commit)

    def general_fields(self) -> list[forms.BoundField]:
        field_names = list(self.Meta.fields)
        return [self[name] for name in field_names]

    def limit_rows(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for parameter_code, item in self.parameter_definitions.items():
            rows.append(
                {
                    "code": parameter_code,
                    "label": item["label"],
                    "unit": item["unit"],
                    "phases": {
                        phase_slug: {
                            "min_enabled": self[_limit_field_name(parameter_code, phase_slug, "min_enabled")],
                            "min_value": self[_limit_field_name(parameter_code, phase_slug, "min_value")],
                            "max_enabled": self[_limit_field_name(parameter_code, phase_slug, "max_enabled")],
                            "max_value": self[_limit_field_name(parameter_code, phase_slug, "max_value")],
                        }
                        for phase_slug in PHASE_SLUGS
                    },
                }
            )
        return rows

    @staticmethod
    def _normalize_decimal(value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)
