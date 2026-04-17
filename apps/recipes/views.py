from __future__ import annotations

from django.contrib import messages
from django.db.models.deletion import ProtectedError
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.core.services.tag_registry import TagRegistryService
from apps.recipes.forms import RecipeForm
from apps.recipes.models import Recipe


class RecipeListView(ListView):
    model = Recipe
    template_name = "recipes/list.html"
    context_object_name = "recipes"


class RecipeCreateView(CreateView):
    model = Recipe
    form_class = RecipeForm
    template_name = "recipes/form.html"
    success_url = reverse_lazy("recipes:list")

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        context = super().get_context_data(**kwargs)
        context["parameter_definitions"] = TagRegistryService().get_parameter_definitions(include_limits_only=True)
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["language"] = self.request.session.get("ui_language", "tr")
        return kwargs


class RecipeUpdateView(UpdateView):
    model = Recipe
    form_class = RecipeForm
    template_name = "recipes/form.html"
    success_url = reverse_lazy("recipes:list")

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        context = super().get_context_data(**kwargs)
        context["parameter_definitions"] = TagRegistryService().get_parameter_definitions(include_limits_only=True)
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["language"] = self.request.session.get("ui_language", "tr")
        return kwargs


class RecipeDeleteView(DeleteView):
    model = Recipe
    template_name = "recipes/confirm_delete.html"
    success_url = reverse_lazy("recipes:list")

    def form_valid(self, form):
        try:
            messages.success(self.request, f"{self.object.recipe_name} recipe kaydi silindi.")
            return super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                "Bu recipe kaydina bagli testler oldugu icin silinemedi.",
            )
            return HttpResponseRedirect(self.success_url)
