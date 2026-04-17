from __future__ import annotations

from django.contrib import messages
from django.db.models.deletion import ProtectedError
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.products.forms import ProductModelForm
from apps.products.models import ProductModel


class ProductModelListView(ListView):
    model = ProductModel
    template_name = "products/list.html"
    context_object_name = "products"


class ProductModelCreateView(CreateView):
    model = ProductModel
    form_class = ProductModelForm
    template_name = "products/form.html"
    success_url = reverse_lazy("products:list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["language"] = self.request.session.get("ui_language", "tr")
        return kwargs


class ProductModelUpdateView(UpdateView):
    model = ProductModel
    form_class = ProductModelForm
    template_name = "products/form.html"
    success_url = reverse_lazy("products:list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["language"] = self.request.session.get("ui_language", "tr")
        return kwargs


class ProductModelDeleteView(DeleteView):
    model = ProductModel
    template_name = "products/confirm_delete.html"
    success_url = reverse_lazy("products:list")

    def form_valid(self, form):
        try:
            messages.success(self.request, f"{self.object.model_name} modeli silindi.")
            return super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                "Bu modele bagli recipe veya test kayitlari oldugu icin silinemedi.",
            )
            return HttpResponseRedirect(self.success_url)
