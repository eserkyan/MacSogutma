from __future__ import annotations

from django.urls import path

from apps.recipes.views import RecipeCreateView, RecipeDeleteView, RecipeListView, RecipeUpdateView

app_name = "recipes"

urlpatterns = [
    path("", RecipeListView.as_view(), name="list"),
    path("new/", RecipeCreateView.as_view(), name="create"),
    path("<int:pk>/edit/", RecipeUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", RecipeDeleteView.as_view(), name="delete"),
]
