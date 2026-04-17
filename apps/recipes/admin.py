from __future__ import annotations

from django.contrib import admin

from apps.recipes.models import Recipe


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("recipe_code", "recipe_name", "product_model", "revision_no", "is_active", "updated_at")
    list_filter = ("is_active", "product_model__product_type")
    search_fields = ("recipe_code", "recipe_name", "product_model__model_code")
