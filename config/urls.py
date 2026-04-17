from __future__ import annotations

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.dashboard.urls")),
    path("companies/", include("apps.companies.urls")),
    path("products/", include("apps.products.urls")),
    path("recipes/", include("apps.recipes.urls")),
    path("tests/", include("apps.tests.urls")),
    path("settings/", include("apps.core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
