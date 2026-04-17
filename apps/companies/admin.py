from __future__ import annotations

from django.contrib import admin

from apps.companies.models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "contact_name", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("code", "name")
