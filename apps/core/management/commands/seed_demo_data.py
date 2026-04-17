from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.companies.models import Company
from apps.products.models import ProductModel
from apps.recipes.models import Recipe
from apps.recipes.services.phase_limits import empty_limit


class Command(BaseCommand):
    help = "Seed demo data for the HVAC test system."

    def handle(self, *args: object, **options: object) -> None:
        company, _ = Company.objects.get_or_create(code="DEMO", defaults={"name": "Demo Company"})
        model, _ = ProductModel.objects.get_or_create(
            model_code="HX-100",
            defaults={"model_name": "HX 100", "product_type": "Cooling Unit"},
        )
        Recipe.objects.get_or_create(
            recipe_code="RCP-DEMO",
            defaults={
                "product_model": model,
                "recipe_name": "Demo Recipe",
                "revision_no": "1.0",
                "start_duration_sec": 30,
                "stable_duration_sec": 60,
                "stop_duration_sec": 20,
                "limits_json": {
                    "105": {
                        "start": empty_limit(),
                        "stable": {"min_enabled": True, "min_value": 20, "max_enabled": True, "max_value": 28},
                        "stop": empty_limit(),
                    },
                    "112": {
                        "start": empty_limit(),
                        "stable": {"min_enabled": False, "min_value": None, "max_enabled": True, "max_value": 12},
                        "stop": empty_limit(),
                    },
                },
            },
        )
        self.stdout.write(self.style.SUCCESS(f"Seed completed for {company} / {model}"))
