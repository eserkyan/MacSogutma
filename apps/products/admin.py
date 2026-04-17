from __future__ import annotations

from django.contrib import admin

from apps.products.models import ProductModel


@admin.register(ProductModel)
class ProductModelAdmin(admin.ModelAdmin):
    list_display = ("model_code", "model_name", "product_type", "is_active", "updated_at")
    list_filter = ("product_type", "is_active")
    search_fields = ("model_code", "model_name")
