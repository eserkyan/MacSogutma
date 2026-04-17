from __future__ import annotations

from django.db import models

from apps.core.models import TimeStampedModel


class ProductModel(TimeStampedModel):
    model_code = models.CharField(max_length=50, unique=True)
    model_name = models.CharField(max_length=255)
    product_type = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("product_type", "model_code")

    def __str__(self) -> str:
        return f"{self.model_code} - {self.model_name}"
