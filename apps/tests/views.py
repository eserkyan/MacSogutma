from __future__ import annotations

import json
import logging
from pathlib import Path

from django.contrib import messages
from django.db.models import Q
from django.http import FileResponse, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DeleteView, DetailView, FormView, ListView, TemplateView

from apps.core.services.tag_registry import TagRegistryService
from apps.core.ui_translations import get_text
from apps.plc.models import PlcRuntimeState
from apps.recipes.services.phase_limits import has_active_limit, phase_limit
from apps.reports.services.chart_builder import ChartBuilderService
from apps.reports.services.excel_builder import ExcelBuilderService
from apps.reports.services.pdf_builder import PdfBuilderService
from apps.reports.tasks import generate_excel_task, generate_pdf_task
from apps.tests.forms import AbortTestForm, TestStartForm
from apps.tests.models import TestRecord
from apps.tests.services.evaluation import TestEvaluationService
from apps.tests.services.limit_analysis import LimitAnalysisService
from apps.tests.services.test_runner import StartTestInput, TestRunnerService
from apps.core.constants import TestPhase

logger = logging.getLogger(__name__)


class TestStartView(FormView):
    template_name = "tests/start.html"
    form_class = TestStartForm
    success_url = reverse_lazy("tests:active")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["language"] = self.request.session.get("ui_language", "tr")
        return kwargs

    def form_valid(self, form: TestStartForm):
        data = StartTestInput(
            company_id=form.cleaned_data["company"].pk,
            product_model_id=form.cleaned_data["product_model"].pk,
            recipe_id=form.cleaned_data["recipe"].pk,
            circuit=int(form.cleaned_data["circuit"]),
            operator_name=form.cleaned_data["operator_name"],
            notes=form.cleaned_data["notes"],
        )
        record = TestRunnerService().start_test(data)
        messages.success(self.request, f"Test {record.test_no} started.")
        return super().form_valid(form)


class ActiveTestView(TemplateView):
    template_name = "tests/active.html"

    def dispatch(self, request, *args, **kwargs):
        if not TestRecord.active().exists():
            messages.info(request, "Aktif test bulunmuyor. Gecmis testler ekranina yonlendirildiniz.")
            return redirect("tests:history")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        context = super().get_context_data(**kwargs)
        language = self.request.session.get("ui_language", "tr")
        active_test = TestRecord.active().select_related("company", "product_model", "recipe").first()
        chart_data = (
            ChartBuilderService().build_phase_series(active_test, language=language)
            if active_test else {}
        )
        runtime = PlcRuntimeState.load()
        chart_service = ChartBuilderService()
        context["test_record"] = active_test
        context["runtime"] = runtime
        context["abort_form"] = AbortTestForm(language=language)
        context["chart_data"] = chart_data
        context["active_chart_cards"] = chart_service.chart_definitions(
            language=language,
            selected_circuit=int(active_test.selected_circuit) if active_test else None,
        )
        context["live_record_pretty_json"] = json.dumps(runtime.live_record_json or {}, indent=2, ensure_ascii=False)
        context["active_test_meta_json"] = json.dumps(self._build_active_test_meta(active_test))
        live_flags = (runtime.live_record_json or {}).get("status_flags", {})
        context["commanded_circuit_label"] = self._circuit_label(int(active_test.selected_circuit), language) if active_test else "-"
        context["comp1_rng"] = bool(live_flags.get("comp1_rng"))
        context["comp2_rng"] = bool(live_flags.get("comp2_rng"))
        return context

    def post(self, request, *args, **kwargs):
        active_test = TestRecord.active().first()
        if not active_test:
            messages.warning(request, "Active test was not found.")
            return redirect("tests:active")
        language = self.request.session.get("ui_language", "tr")
        form = AbortTestForm(request.POST, language=language)
        if form.is_valid():
            reason = (form.cleaned_data.get("reason") or "").strip()
            if not reason:
                reason = "Operator abort." if language == "en" else "Operator abort etti."
            TestRunnerService().abort_test(active_test, reason)
            messages.error(request, "Active test aborted.")
        return redirect("tests:active")

    def _build_active_test_meta(self, active_test: TestRecord | None) -> dict[str, object]:
        if not active_test:
            return {}
        return {
            "started_at": active_test.started_at.isoformat() if active_test.started_at else None,
            "stable_started_at": active_test.stable_started_at.isoformat() if active_test.stable_started_at else None,
            "stop_started_at": active_test.stop_started_at.isoformat() if active_test.stop_started_at else None,
            "start_duration_sec": active_test.start_duration_sec_snapshot,
            "stable_duration_sec": active_test.stable_duration_sec_snapshot,
            "stop_duration_sec": active_test.stop_duration_sec_snapshot,
            "current_phase": int(active_test.current_phase.value),
            "server_now": timezone.now().isoformat(),
        }

    @staticmethod
    def _circuit_label(value: int, language: str) -> str:
        labels = {
            0: {"tr": "-", "en": "-"},
            1: {"tr": "Devre 1", "en": "Circuit 1"},
            2: {"tr": "Devre 2", "en": "Circuit 2"},
            3: {"tr": "Devre 1 + Devre 2", "en": "Circuit 1 + Circuit 2"},
        }
        return labels.get(int(value), {"tr": str(value), "en": str(value)}).get(language, str(value))


class TestHistoryView(ListView):
    model = TestRecord
    template_name = "tests/history.html"
    context_object_name = "tests"
    paginate_by = 20

    def get_queryset(self):
        queryset = TestRecord.objects.select_related("company", "product_model", "recipe")
        query = self.request.GET.get("q")
        result = self.request.GET.get("result")
        if query:
            queryset = queryset.filter(
                Q(test_no__icontains=query)
                | Q(company__name__icontains=query)
                | Q(product_model__model_name__icontains=query)
                | Q(recipe__recipe_name__icontains=query)
            )
        if result:
            queryset = queryset.filter(status=result)
        return queryset

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        context = super().get_context_data(**kwargs)
        evaluation_service = TestEvaluationService()
        pdf_service = PdfBuilderService()
        excel_service = ExcelBuilderService()
        for item in context["tests"]:
            evaluation_service.reconcile_completed_result(item)
            item.pdf_path_tr = str(pdf_service.target_path_for(item, language="tr"))
            item.pdf_path_en = str(pdf_service.target_path_for(item, language="en"))
            item.excel_path_tr = str(excel_service.target_path_for(item, language="tr"))
            item.excel_path_en = str(excel_service.target_path_for(item, language="en"))
        return context


class TestDetailView(DetailView):
    model = TestRecord
    template_name = "tests/detail.html"
    context_object_name = "test_record"

    def get_queryset(self):
        return TestRecord.objects.select_related("company", "product_model", "recipe").prefetch_related(
            "evaluation_results",
            "samples",
            "plc_events",
        )

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        TestEvaluationService().reconcile_completed_result(self.object)
        self.object.refresh_from_db()
        context = super().get_context_data(**kwargs)
        chart_service = ChartBuilderService()
        language = self.request.session.get("ui_language", "tr")
        registry = TagRegistryService()
        parameter_definitions = registry.get_parameter_definitions(language=language)
        excursions = LimitAnalysisService().analyze(self.object)
        evaluation_service = TestEvaluationService()
        context["chart_data"] = chart_service.build_phase_series(self.object, language=language)
        context["detail_chart_cards"] = chart_service.detail_chart_definitions(
            language=language,
            selected_circuit=int(self.object.selected_circuit),
        )
        parameter_codes = self._parameter_codes_for_test(registry)
        context["limit_excursions"] = [
            {
                "parameter_name": item.parameter_name,
                "phase_name": self._phase_label(item.phase_value, language),
                "elapsed_seconds": item.elapsed_seconds,
                "sample_value": item.sample_value,
                "unit": item.unit,
                "limit_type": item.limit_type,
                "limit_value": item.limit_value,
                "message": self._localize_limit_message(item, language),
            }
            for item in excursions
        ]
        result_map = {result.parameter_code: result for result in self.object.evaluation_results.all()}
        phase_result_map = {(result.parameter_code, str(result.phase_used)): result for result in self.object.evaluation_results.all()}
        context["evaluation_rows"] = []
        for parameter_code in parameter_codes:
            definition = parameter_definitions.get(parameter_code)
            if not definition:
                continue
            result = phase_result_map.get((parameter_code, "STABLE"))
            stats = evaluation_service.stable_stats(self.object, parameter_code)
            raw_limit = self.object.limits_snapshot_json.get(parameter_code, {})
            limit = phase_limit(raw_limit, TestPhase.STABLE)
            has_limit = has_active_limit(raw_limit, TestPhase.STABLE)
            context["evaluation_rows"].append(
                {
                    "parameter_code": parameter_code,
                    "parameter_name": str(definition.get("label", parameter_code)),
                    "unit": str(definition.get("unit", "")),
                    "stats": stats,
                    "avg_value": result.avg_value if result else stats["avg_value"],
                    "min_enabled": result.min_enabled if result else bool(limit.get("min_enabled")),
                    "min_limit": result.min_limit if result else limit.get("min_value"),
                    "max_enabled": result.max_enabled if result else bool(limit.get("max_enabled")),
                    "max_limit": result.max_limit if result else limit.get("max_value"),
                    "passed": result.passed if result else None,
                    "has_limit": has_limit,
                    "display_message": self._build_display_message(result, stats["avg_value"], has_limit, language),
                }
            )
        context["phase_stat_sections"] = [
            {
                "slug": "start",
                "title": get_text("tests.start_stats", language),
                "rows": self._phase_stat_rows(parameter_codes, parameter_definitions, TestPhase.START, phase_result_map, language),
            },
            {
                "slug": "stop",
                "title": get_text("tests.stop_stats", language),
                "rows": self._phase_stat_rows(parameter_codes, parameter_definitions, TestPhase.STOP, phase_result_map, language),
            },
        ]
        pdf_service = PdfBuilderService()
        excel_service = ExcelBuilderService()
        context["pdf_path_tr"] = str(pdf_service.target_path_for(self.object, language="tr"))
        context["pdf_path_en"] = str(pdf_service.target_path_for(self.object, language="en"))
        context["excel_path_tr"] = str(excel_service.target_path_for(self.object, language="tr"))
        context["excel_path_en"] = str(excel_service.target_path_for(self.object, language="en"))
        return context

    @staticmethod
    def _phase_label(phase_value: int, language: str) -> str:
        mapping = {
            0: get_text("tests.phase_idle", language),
            1: get_text("tests.phase_start", language),
            2: get_text("tests.phase_stable", language),
            3: get_text("tests.phase_stop", language),
            4: get_text("tests.phase_manual", language),
            5: get_text("tests.phase_aborted", language),
        }
        return mapping.get(int(phase_value), str(phase_value))

    @staticmethod
    def _format_number(value: object) -> str:
        if value is None or value == "":
            return "-"
        return f"{float(value):.2f}"

    def _localize_evaluation_message(self, result: object, language: str) -> str:
        if result.avg_value is None:
            return get_text("tests.msg_no_valid_stable", language)
        if result.min_enabled and result.min_limit is not None and result.avg_value < result.min_limit:
            return get_text("tests.msg_avg_below", language).format(
                value=self._format_number(result.avg_value),
                limit=self._format_number(result.min_limit),
            )
        if result.max_enabled and result.max_limit is not None and result.avg_value > result.max_limit:
            return get_text("tests.msg_avg_above", language).format(
                value=self._format_number(result.avg_value),
                limit=self._format_number(result.max_limit),
            )
        return get_text("tests.msg_passed", language)

    def _localize_limit_message(self, item: object, language: str) -> str:
        if item.limit_type == "MIN":
            return get_text("tests.msg_limit_below", language).format(
                value=self._format_number(item.sample_value),
                limit=self._format_number(item.limit_value),
            )
        return get_text("tests.msg_limit_above", language).format(
            value=self._format_number(item.sample_value),
            limit=self._format_number(item.limit_value),
        )

    def _build_display_message(
        self,
        result: object | None,
        avg_value: object,
        has_limit: bool,
        language: str,
        phase: TestPhase = TestPhase.STABLE,
    ) -> str:
        if result is not None:
            if result.avg_value is None:
                phase_name = self._phase_label(int(phase), language)
                return get_text("tests.msg_no_valid_phase", language).format(phase=phase_name)
            return self._localize_evaluation_message(result, language)
        if avg_value is None:
            if phase == TestPhase.STABLE:
                return get_text("tests.msg_no_valid_stable", language)
            phase_name = self._phase_label(int(phase), language)
            return get_text("tests.msg_no_valid_phase", language).format(phase=phase_name)
        if not has_limit:
            return get_text("tests.msg_no_limit_defined", language)
        return "-"

    def _parameter_codes_for_test(self, registry: TagRegistryService) -> list[str]:
        from apps.core.constants import CircuitSelect

        circuit = int(self.object.selected_circuit)
        codes = set(registry.get_parameter_codes_for_scope("shared"))
        if circuit in {int(CircuitSelect.CIRCUIT_1), int(CircuitSelect.BOTH)}:
            codes.update(registry.get_parameter_codes_for_scope("circuit1"))
        if circuit in {int(CircuitSelect.CIRCUIT_2), int(CircuitSelect.BOTH)}:
            codes.update(registry.get_parameter_codes_for_scope("circuit2"))
        return sorted(codes)

    def _phase_stat_rows(
        self,
        parameter_codes: list[str],
        parameter_definitions: dict[str, dict[str, str]],
        phase: TestPhase,
        phase_result_map: dict[tuple[str, str], object],
        language: str,
    ) -> list[dict[str, object]]:
        evaluation_service = TestEvaluationService()
        rows: list[dict[str, object]] = []
        evaluation_phase = phase.value
        phase_key = "START" if phase == TestPhase.START else "STOP" if phase == TestPhase.STOP else "STABLE"
        for parameter_code in parameter_codes:
            definition = parameter_definitions.get(parameter_code)
            if not definition:
                continue
            stats = self._phase_stats(self.object, parameter_code, phase, evaluation_service)
            raw_limit = self.object.limits_snapshot_json.get(parameter_code, {})
            limit = phase_limit(raw_limit, evaluation_phase)
            has_limit = has_active_limit(raw_limit, evaluation_phase)
            result = phase_result_map.get((parameter_code, phase_key))
            rows.append(
                {
                    "parameter_code": parameter_code,
                    "parameter_name": str(definition.get("label", parameter_code)),
                    "unit": str(definition.get("unit", "")),
                    "min_enabled": bool(limit.get("min_enabled")),
                    "min_limit": limit.get("min_value"),
                    "max_enabled": bool(limit.get("max_enabled")),
                    "max_limit": limit.get("max_value"),
                    "stats": stats,
                    "avg_value": result.avg_value if result else stats["avg_value"],
                    "passed": result.passed if result else None,
                    "has_limit": has_limit,
                    "display_message": self._build_display_message(result, stats["avg_value"], has_limit, language, phase),
                }
            )
        return rows

    def _phase_stats(
        self,
        test_record: TestRecord,
        parameter_code: str,
        phase: TestPhase,
        evaluation_service: TestEvaluationService,
    ) -> dict[str, object]:
        stats = evaluation_service.phase_stats(test_record, parameter_code, phase)
        values = [value for value in [stats["min_value"], stats["avg_value"], stats["max_value"]] if value is not None]
        if not values:
            return {"min_value": None, "avg_value": None, "max_value": None}
        return {
            "min_value": float(stats["min_value"]) if stats["min_value"] is not None else None,
            "avg_value": float(stats["avg_value"]) if stats["avg_value"] is not None else None,
            "max_value": float(stats["max_value"]) if stats["max_value"] is not None else None,
        }


class TestDeleteView(DeleteView):
    model = TestRecord
    template_name = "tests/confirm_delete.html"
    success_url = reverse_lazy("tests:history")

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.status in TestRecord.active_statuses():
            messages.error(request, "Aktif test kaydi silinemez.")
            return redirect("tests:active")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f"{self.object.test_no} test kaydi silindi.")
        return super().form_valid(form)


class TestReportDownloadView(View):
    def get(self, request: HttpRequest, pk: int, *args, **kwargs) -> HttpResponse:
        test_record = get_object_or_404(TestRecord, pk=pk)
        language = self._resolve_language(request)
        pdf_service = PdfBuilderService()
        report_path = pdf_service.target_path_for(test_record, language=language)
        latest_pdf_asset_mtime = PdfBuilderService.latest_asset_mtime()
        pdf_is_stale_for_assets = (
            test_record.pdf_generated_at is None
            or test_record.pdf_generated_at.timestamp() < latest_pdf_asset_mtime
        )
        should_queue = (
            not test_record.pdf_generated_at
            or not test_record.pdf_file_path
            or not report_path.exists()
            or not report_path.is_file()
            or (test_record.ended_at is not None and test_record.pdf_generated_at < test_record.ended_at)
            or pdf_is_stale_for_assets
        )
        if should_queue:
            try:
                generated_path = pdf_service.build(test_record, language=language)
                report_path = Path(generated_path)
            except Exception:
                logger.exception("PDF report could not be generated immediately", extra={"test_record_id": test_record.pk})
                generate_pdf_task.delay(test_record.pk, language=language)
                if language == "tr":
                    messages.info(request, "PDF raporu olusturma kuyruguna alindi. Birkac saniye sonra tekrar deneyin.")
                else:
                    messages.info(request, "PDF report generation was queued. Please try again in a few seconds.")
                return redirect("tests:detail", pk=test_record.pk)

        try:
            return FileResponse(
                report_path.open("rb"),
                as_attachment=True,
                filename=report_path.name,
            )
        except OSError:
            if language == "tr":
                messages.warning(request, "PDF raporu su anda acilamadi. Lutfen biraz sonra tekrar deneyin.")
            else:
                messages.warning(request, "The PDF report could not be opened right now. Please try again shortly.")
            return redirect("tests:detail", pk=test_record.pk)

    @staticmethod
    def _resolve_language(request: HttpRequest) -> str:
        language = (request.GET.get("lang") or request.session.get("ui_language") or "tr").lower()
        return language if language in {"tr", "en"} else "tr"


class TestExcelDownloadView(View):
    def get(self, request: HttpRequest, pk: int, *args, **kwargs) -> HttpResponse:
        test_record = get_object_or_404(TestRecord, pk=pk)
        language = self._resolve_language(request)
        excel_service = ExcelBuilderService()
        excel_path = excel_service.target_path_for(test_record, language=language)
        should_build = (
            not test_record.excel_generated_at
            or not test_record.excel_file_path
            or not excel_path.exists()
            or not excel_path.is_file()
            or (test_record.ended_at is not None and test_record.excel_generated_at < test_record.ended_at)
        )
        try:
            if should_build:
                generated_path = excel_service.build(test_record, language=language)
                excel_path = Path(generated_path)
        except Exception:
            logger.exception("Excel export could not be generated", extra={"test_record_id": test_record.pk})
            generate_excel_task.delay(test_record.pk, language=language)
            if language == "tr":
                messages.warning(request, "Excel raporu olusturma kuyruguna alindi. Lutfen biraz sonra tekrar deneyin.")
            else:
                messages.warning(request, "Excel report generation was queued. Please try again shortly.")
            return redirect("tests:detail", pk=test_record.pk)
        try:
            return FileResponse(
                excel_path.open("rb"),
                as_attachment=True,
                filename=excel_path.name,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except OSError:
            if language == "tr":
                messages.warning(request, "Excel raporu su anda acilamadi. Lutfen biraz sonra tekrar deneyin.")
            else:
                messages.warning(request, "The Excel report could not be opened right now. Please try again shortly.")
            return redirect("tests:detail", pk=test_record.pk)

    @staticmethod
    def _resolve_language(request: HttpRequest) -> str:
        language = (request.GET.get("lang") or request.session.get("ui_language") or "tr").lower()
        return language if language in {"tr", "en"} else "tr"
