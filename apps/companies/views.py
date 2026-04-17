from __future__ import annotations

from django.contrib import messages
from django.db.models.deletion import ProtectedError
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.companies.forms import CompanyForm
from apps.companies.models import Company


class CompanyListView(ListView):
    model = Company
    template_name = "companies/list.html"
    context_object_name = "companies"


class CompanyCreateView(CreateView):
    model = Company
    form_class = CompanyForm
    template_name = "companies/form.html"
    success_url = reverse_lazy("companies:list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["language"] = self.request.session.get("ui_language", "tr")
        return kwargs


class CompanyUpdateView(UpdateView):
    model = Company
    form_class = CompanyForm
    template_name = "companies/form.html"
    success_url = reverse_lazy("companies:list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["language"] = self.request.session.get("ui_language", "tr")
        return kwargs


class CompanyDeleteView(DeleteView):
    model = Company
    template_name = "companies/confirm_delete.html"
    success_url = reverse_lazy("companies:list")

    def form_valid(self, form):
        try:
            messages.success(self.request, f"{self.object.name} firmasi silindi.")
            return super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                "Bu firmaya bagli test kayitlari oldugu icin silinemedi.",
            )
            return HttpResponseRedirect(self.success_url)
