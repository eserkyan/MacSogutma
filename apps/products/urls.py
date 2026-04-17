from __future__ import annotations

from django.urls import path

from apps.products.views import (
    ProductModelCreateView,
    ProductModelDeleteView,
    ProductModelListView,
    ProductModelUpdateView,
)

app_name = "products"

urlpatterns = [
    path("", ProductModelListView.as_view(), name="list"),
    path("new/", ProductModelCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", ProductModelUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", ProductModelDeleteView.as_view(), name="delete"),
]
