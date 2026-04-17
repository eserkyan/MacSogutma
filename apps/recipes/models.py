from __future__ import annotations

from django.db import models

from apps.core.models import TimeStampedModel
from apps.products.models import ProductModel


class Recipe(TimeStampedModel):
    product_model = models.ForeignKey(ProductModel, on_delete=models.PROTECT, related_name="recipes")
    recipe_name = models.CharField(max_length=255)
    recipe_code = models.CharField(max_length=64, unique=True)
    description = models.TextField(blank=True, null=True)
    revision_no = models.CharField(max_length=32)
    is_active = models.BooleanField(default=True)
    start_duration_sec = models.PositiveIntegerField()
    stable_duration_sec = models.PositiveIntegerField()
    stop_duration_sec = models.PositiveIntegerField()
    phase_context_sec = models.PositiveIntegerField(default=5)
    limits_json = models.JSONField(default=dict)

    class Meta:
        ordering = ["recipe_code", "-updated_at"]

    @property
    def product_type(self) -> str:
        return self.product_model.product_type

    def __str__(self) -> str:
        return f"{self.recipe_code} / {self.recipe_name}"
