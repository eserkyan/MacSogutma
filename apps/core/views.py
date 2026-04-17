from __future__ import annotations

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.core.forms import PlcSchemaConfigForm, TagConfigForm
from apps.core.models import TagConfig
from apps.core.services.tag_registry import TagRegistryService
from apps.core.ui_translations import get_text
from apps.plc.models import PlcRuntimeState
from apps.plc.services.time_sync import PlcTimeSyncService


class SettingsView(TemplateView):
    template_name = "core/settings.html"

    def dispatch(self, request: HttpRequest, *args: object, **kwargs: object) -> HttpResponse:
        TagRegistryService().ensure_defaults()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        context = super().get_context_data(**kwargs)
        language = self.request.session.get("ui_language", "tr")
        registry = TagRegistryService()
        plc_form = kwargs.get("plc_form") or PlcSchemaConfigForm(instance=registry.get_layout_instance())
        tag_form = kwargs.get("tag_form") or TagConfigForm()
        context["plc_form"] = plc_form
        context["tag_form"] = tag_form
        context["tags"] = TagConfig.objects.order_by("source_block", "modbus_address", "register_offset", "tag_id")
        context["language"] = language
        context["runtime"] = PlcRuntimeState.load()
        context["server_now"] = timezone.localtime()
        context["utc_now"] = timezone.now()
        return context


class SettingsActionView(View):
    def post(self, request: HttpRequest, *args: object, **kwargs: object) -> HttpResponse:
        TagRegistryService().ensure_defaults()
        action = request.POST.get("action")
        language = request.session.get("ui_language", "tr")

        if action == "save_plc_schema":
            return self._save_plc_schema(request, language)
        if action == "manual_time_sync":
            return self._manual_time_sync(request, language)
        if action == "save_tag":
            return self._save_tag(request, language)
        if action == "delete_tag":
            return self._delete_tag(request, language)

        messages.error(request, get_text("settings.unknown_action", language))
        return redirect("core:settings")

    def _save_plc_schema(self, request: HttpRequest, language: str) -> HttpResponse:
        instance = TagRegistryService().get_layout_instance()
        form = PlcSchemaConfigForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            TagRegistryService.clear_cache()
            messages.success(request, get_text("settings.schema_saved", language))
            return redirect("core:settings")
        return SettingsView.as_view()(request, plc_form=form, tag_form=TagConfigForm())

    def _manual_time_sync(self, request: HttpRequest, language: str) -> HttpResponse:
        result = PlcTimeSyncService().run(force=True)
        if language == "tr":
            messages.success(
                request,
                f"Manuel zaman senkronu gonderildi. Drift: {result.drift_seconds} sn.",
            )
        else:
            messages.success(
                request,
                f"Manual time synchronization was sent. Drift: {result.drift_seconds} sec.",
            )
        return redirect("core:settings")

    def _save_tag(self, request: HttpRequest, language: str) -> HttpResponse:
        config_id = request.POST.get("config_id")
        instance = get_object_or_404(TagConfig, pk=config_id) if config_id else None
        form = TagConfigForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            TagRegistryService.clear_cache()
            messages.success(
                request,
                get_text("settings.tag_updated", language) if instance else get_text("settings.tag_created", language),
            )
            return redirect("core:settings")
        return SettingsView.as_view()(request, plc_form=PlcSchemaConfigForm(instance=TagRegistryService().get_layout_instance()), tag_form=form)

    def _delete_tag(self, request: HttpRequest, language: str) -> HttpResponse:
        tag = get_object_or_404(TagConfig, pk=request.POST.get("tag_id"))
        tag.delete()
        TagRegistryService.clear_cache()
        messages.success(request, get_text("settings.tag_deleted", language))
        return redirect("core:settings")
