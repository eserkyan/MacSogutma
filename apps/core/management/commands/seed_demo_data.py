from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.companies.models import Company
from apps.core.constants import CircuitSelect, PlcEventType, TestPhase, TestStatus
from apps.plc.models import PlcEventLog
from apps.products.models import ProductModel
from apps.recipes.models import Recipe
from apps.recipes.services.phase_limits import empty_limit
from apps.tests.models import TestRecord, TestSample
from apps.tests.services.evaluation import TestEvaluationService


@dataclass(frozen=True, slots=True)
class DemoTestDefinition:
    test_no: str
    company_code: str
    model_code: str
    recipe_code: str
    circuit: int
    operator_name: str
    status: str
    offset_days: int
    notes: str
    abort_reason: str | None = None
    fail_reason_summary: str | None = None
    sample_profile: str = "pass"


class Command(BaseCommand):
    help = "Seed rich demo data for the HVAC test system."

    def handle(self, *args: object, **options: object) -> None:
        companies = self._seed_companies()
        models = self._seed_models()
        recipes = self._seed_recipes(models)
        created_tests = self._seed_test_records(companies, models, recipes)
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo seed completed. Companies={len(companies)}, Models={len(models)}, "
                f"Recipes={len(recipes)}, Tests={created_tests}"
            )
        )

    def _seed_companies(self) -> dict[str, Company]:
        payloads = [
            {
                "code": "DEMO",
                "name": "Demo Sogutma",
                "address": "Istanbul Tuzla Organize Sanayi",
                "contact_name": "Eser Kiyan",
                "contact_phone": "+90 555 000 00 01",
            },
            {
                "code": "ARKTK",
                "name": "Arktik Iklimlendirme",
                "address": "Kocaeli Gebze",
                "contact_name": "Murat Yildiz",
                "contact_phone": "+90 555 000 00 02",
            },
            {
                "code": "POLAR",
                "name": "Polar HVAC Teknoloji",
                "address": "Bursa Nilufer",
                "contact_name": "Zeynep Kaya",
                "contact_phone": "+90 555 000 00 03",
            },
        ]
        companies: dict[str, Company] = {}
        for item in payloads:
            company, _ = Company.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name": item["name"],
                    "address": item["address"],
                    "contact_name": item["contact_name"],
                    "contact_phone": item["contact_phone"],
                    "is_active": True,
                },
            )
            companies[item["code"]] = company
        return companies

    def _seed_models(self) -> dict[str, ProductModel]:
        payloads = [
            {"model_code": "HX-100", "model_name": "HX 100", "product_type": "Cooling Unit", "description": "Tek devreli demo cihaz."},
            {"model_code": "HX-200", "model_name": "HX 200", "product_type": "Cooling Unit", "description": "Cift devreli rooftop test modeli."},
            {"model_code": "RT-350", "model_name": "RT 350", "product_type": "Rooftop", "description": "Yuksek kapasiteli rooftop cihaz."},
            {"model_code": "CH-90", "model_name": "CH 90", "product_type": "Chiller", "description": "Kompakt chiller test modeli."},
        ]
        models: dict[str, ProductModel] = {}
        for item in payloads:
            model, _ = ProductModel.objects.update_or_create(
                model_code=item["model_code"],
                defaults={
                    "model_name": item["model_name"],
                    "product_type": item["product_type"],
                    "description": item["description"],
                    "is_active": True,
                },
            )
            models[item["model_code"]] = model
        return models

    def _seed_recipes(self, models: dict[str, ProductModel]) -> dict[str, Recipe]:
        recipe_payloads = [
            {
                "recipe_code": "RCP-HX100-STD",
                "product_model": models["HX-100"],
                "recipe_name": "HX100 Standart Test",
                "revision_no": "1.0",
                "description": "Tek devreli standart sogutma testi.",
                "start_duration_sec": 20,
                "stable_duration_sec": 45,
                "stop_duration_sec": 20,
                "phase_context_sec": 5,
                "limits_json": self._single_circuit_limits(max_current=12.5, max_discharge=84.0),
            },
            {
                "recipe_code": "RCP-HX100-HOT",
                "product_model": models["HX-100"],
                "recipe_name": "HX100 Sicak Ortam Testi",
                "revision_no": "1.2",
                "description": "Yuksek ortam sicakligi icin daraltilmis limitler.",
                "start_duration_sec": 25,
                "stable_duration_sec": 55,
                "stop_duration_sec": 25,
                "phase_context_sec": 5,
                "limits_json": self._single_circuit_limits(max_current=11.8, max_discharge=80.0),
            },
            {
                "recipe_code": "RCP-HX200-DUAL",
                "product_model": models["HX-200"],
                "recipe_name": "HX200 Cift Devre Testi",
                "revision_no": "2.0",
                "description": "Iki devre birlikte calisan rooftop tarzi test.",
                "start_duration_sec": 30,
                "stable_duration_sec": 70,
                "stop_duration_sec": 30,
                "phase_context_sec": 5,
                "limits_json": self._dual_circuit_limits(),
            },
            {
                "recipe_code": "RCP-RT350-LONG",
                "product_model": models["RT-350"],
                "recipe_name": "RT350 Uzun Sureli Test",
                "revision_no": "3.0",
                "description": "Uzun sureli stabilite ve yuk testi.",
                "start_duration_sec": 35,
                "stable_duration_sec": 90,
                "stop_duration_sec": 35,
                "phase_context_sec": 5,
                "limits_json": self._dual_circuit_limits(comp1_max=16.0, comp2_max=16.0, air_flow_min=2.2),
            },
            {
                "recipe_code": "RCP-CH90-WATER",
                "product_model": models["CH-90"],
                "recipe_name": "CH90 Su Devresi Testi",
                "revision_no": "1.0",
                "description": "Kondenser su giris-cikis sicaklik takibi bulunan test.",
                "start_duration_sec": 20,
                "stable_duration_sec": 50,
                "stop_duration_sec": 25,
                "phase_context_sec": 5,
                "limits_json": self._water_loop_limits(),
            },
        ]

        recipes: dict[str, Recipe] = {}
        for item in recipe_payloads:
            recipe, _ = Recipe.objects.update_or_create(
                recipe_code=item["recipe_code"],
                defaults={
                    "product_model": item["product_model"],
                    "recipe_name": item["recipe_name"],
                    "description": item["description"],
                    "revision_no": item["revision_no"],
                    "is_active": True,
                    "start_duration_sec": item["start_duration_sec"],
                    "stable_duration_sec": item["stable_duration_sec"],
                    "stop_duration_sec": item["stop_duration_sec"],
                    "phase_context_sec": item["phase_context_sec"],
                    "limits_json": item["limits_json"],
                },
            )
            recipes[item["recipe_code"]] = recipe
        return recipes

    def _seed_test_records(
        self,
        companies: dict[str, Company],
        models: dict[str, ProductModel],
        recipes: dict[str, Recipe],
    ) -> int:
        now = timezone.now()
        definitions = [
            DemoTestDefinition(
                test_no="T-20260417-100001",
                company_code="DEMO",
                model_code="HX-100",
                recipe_code="RCP-HX100-STD",
                circuit=int(CircuitSelect.CIRCUIT_1),
                operator_name="Demo Operator",
                status=TestStatus.COMPLETED_PASS,
                offset_days=4,
                notes="Basarili demo test kaydi. Stable fazinda tum ortalamalar limit icinde.",
                sample_profile="pass_single",
            ),
            DemoTestDefinition(
                test_no="T-20260417-100002",
                company_code="ARKTK",
                model_code="HX-100",
                recipe_code="RCP-HX100-HOT",
                circuit=int(CircuitSelect.CIRCUIT_1),
                operator_name="Murat Yildiz",
                status=TestStatus.COMPLETED_FAIL,
                offset_days=3,
                notes="Fail senaryosu. Stable fazinda kompresor akimi ve discharge line sicakligi limiti asiyor.",
                fail_reason_summary="Stable fazinda limit asimi olustu.",
                sample_profile="fail_single",
            ),
            DemoTestDefinition(
                test_no="T-20260417-100003",
                company_code="POLAR",
                model_code="HX-200",
                recipe_code="RCP-HX200-DUAL",
                circuit=int(CircuitSelect.BOTH),
                operator_name="Zeynep Kaya",
                status=TestStatus.ABORTED,
                offset_days=2,
                notes="PLC fault nedeniyle operator ekranda warning gorebilsin diye abort edilmis kayit.",
                abort_reason="PLC fault algilandi, test guvenli sekilde abort edildi.",
                sample_profile="abort_dual",
            ),
            DemoTestDefinition(
                test_no="T-20260417-100004",
                company_code="DEMO",
                model_code="CH-90",
                recipe_code="RCP-CH90-WATER",
                circuit=int(CircuitSelect.CIRCUIT_2),
                operator_name="Demo Operator",
                status=TestStatus.FAILED_TO_START,
                offset_days=1,
                notes="Baslama hatasi senaryosu. Start request verildi ancak PlcRunning gelmedi.",
                abort_reason="Baslatma sonrasi 3 saniye icinde PlcRunning geri bildirimi alinmadi.",
                sample_profile="failed_to_start",
            ),
            DemoTestDefinition(
                test_no="T-20260417-100005",
                company_code="ARKTK",
                model_code="RT-350",
                recipe_code="RCP-RT350-LONG",
                circuit=int(CircuitSelect.BOTH),
                operator_name="Deniz Karaca",
                status=TestStatus.COMPLETED_PASS,
                offset_days=6,
                notes="Cift devreli uzun sureli basarili test. Grafik ve rapor ekranlari icin dolu veri seti.",
                sample_profile="pass_dual",
            ),
            DemoTestDefinition(
                test_no="T-20260417-100006",
                company_code="POLAR",
                model_code="CH-90",
                recipe_code="RCP-CH90-WATER",
                circuit=int(CircuitSelect.CIRCUIT_2),
                operator_name="Selin Acar",
                status=TestStatus.COMPLETED_FAIL,
                offset_days=5,
                notes="Su devresi sicaklik limiti ve akim limiti asimi bulunan fail ornegi.",
                fail_reason_summary="Stable fazinda birden fazla limit asimi olustu.",
                sample_profile="fail_water",
            ),
        ]

        created = 0
        evaluator = TestEvaluationService()

        for item in definitions:
            recipe = recipes[item.recipe_code]
            started_at = now - timedelta(days=item.offset_days, minutes=12)
            stable_started_at = started_at + timedelta(seconds=recipe.start_duration_sec)
            stop_started_at = stable_started_at + timedelta(seconds=recipe.stable_duration_sec)
            ended_at = stop_started_at + timedelta(seconds=recipe.stop_duration_sec)

            record, _ = TestRecord.objects.update_or_create(
                test_no=item.test_no,
                defaults={
                    "company": companies[item.company_code],
                    "product_model": models[item.model_code],
                    "recipe": recipe,
                    "operator_name": item.operator_name,
                    "selected_circuit": item.circuit,
                    "status": item.status,
                    "started_at": started_at,
                    "stable_started_at": stable_started_at if item.status != TestStatus.FAILED_TO_START else None,
                    "stop_started_at": stop_started_at if item.status in {TestStatus.COMPLETED_PASS, TestStatus.COMPLETED_FAIL, TestStatus.ABORTED} else None,
                    "ended_at": ended_at if item.status != TestStatus.RUNNING else None,
                    "recipe_name_snapshot": recipe.recipe_name,
                    "recipe_code_snapshot": recipe.recipe_code,
                    "recipe_revision_snapshot": recipe.revision_no,
                    "start_duration_sec_snapshot": recipe.start_duration_sec,
                    "stable_duration_sec_snapshot": recipe.stable_duration_sec,
                    "stop_duration_sec_snapshot": recipe.stop_duration_sec,
                    "phase_context_sec_snapshot": recipe.phase_context_sec,
                    "limits_snapshot_json": recipe.limits_json,
                    "notes": item.notes,
                    "abort_reason": item.abort_reason,
                    "fail_reason_summary": item.fail_reason_summary,
                    "result_passed": True if item.status == TestStatus.COMPLETED_PASS else False if item.status in {TestStatus.COMPLETED_FAIL, TestStatus.ABORTED, TestStatus.FAILED_TO_START} else None,
                },
            )
            created += 1

            record.samples.all().delete()
            record.evaluation_results.all().delete()
            record.plc_events.all().delete()
            record.prestart_samples_json = self._build_prestart_samples(item.sample_profile)
            record.save(update_fields=["prestart_samples_json", "updated_at"])

            if item.sample_profile == "pass_single":
                self._create_pass_samples(record)
                evaluator.evaluate(record)
                self._create_info_event(record, "DEMO_PASS_COMPLETED", "Demo pass testi olusturuldu.")
            elif item.sample_profile == "fail_single":
                self._create_fail_samples(record)
                evaluator.evaluate(record)
                self._create_fault_event(record, "DEMO_LIMIT_FAIL", "Stable fazinda limit asimi goruldu.")
            elif item.sample_profile == "abort_dual":
                self._create_abort_samples(record)
                self._create_fault_event(record, "PLC_FAULT_ABORT", item.abort_reason or "PLC fault nedeniyle abort.")
            elif item.sample_profile == "failed_to_start":
                self._create_failed_to_start_samples(record)
                self._create_warning_event(record, "FAILED_TO_START", item.abort_reason or "PlcRunning geri bildirimi gelmedi.")
                record.result_passed = False
                record.save(update_fields=["result_passed", "updated_at"])
            elif item.sample_profile == "pass_dual":
                self._create_dual_pass_samples(record)
                evaluator.evaluate(record)
                self._create_info_event(record, "DEMO_DUAL_PASS", "Cift devreli pass demo testi olusturuldu.")
            elif item.sample_profile == "fail_water":
                self._create_water_fail_samples(record)
                evaluator.evaluate(record)
                self._create_fault_event(record, "DEMO_WATER_FAIL", "Su devresi ve akim limitleri asildi.")

        return created

    def _create_pass_samples(self, record: TestRecord) -> None:
        samples = [
            (1, TestPhase.START, 0, self._base_values(c1_hp=23.4, c1_lp=6.1, c1_discharge=59.0, c1_suction=13.2, comp1_current=9.6)),
            (2, TestPhase.START, 7, self._base_values(c1_hp=24.0, c1_lp=6.4, c1_discharge=62.0, c1_suction=13.5, comp1_current=10.4)),
            (3, TestPhase.START, 14, self._base_values(c1_hp=24.6, c1_lp=6.6, c1_discharge=66.0, c1_suction=13.8, comp1_current=10.9)),
            (4, TestPhase.STABLE, 24, self._base_values(c1_hp=25.4, c1_lp=6.8, c1_discharge=72.0, c1_suction=14.2, comp1_current=11.2, inlet_humidity=46.5, air_flow=2.6)),
            (5, TestPhase.STABLE, 34, self._base_values(c1_hp=25.5, c1_lp=6.8, c1_discharge=72.8, c1_suction=14.2, comp1_current=11.2, inlet_humidity=46.6, air_flow=2.6)),
            (6, TestPhase.STABLE, 44, self._base_values(c1_hp=25.7, c1_lp=6.9, c1_discharge=74.0, c1_suction=14.0, comp1_current=11.4, inlet_humidity=47.1, air_flow=2.5)),
            (7, TestPhase.STABLE, 54, self._base_values(c1_hp=25.8, c1_lp=7.0, c1_discharge=73.5, c1_suction=14.1, comp1_current=11.3, inlet_humidity=46.8, air_flow=2.6)),
            (8, TestPhase.STOP, 70, self._base_values(c1_hp=24.1, c1_lp=6.5, c1_discharge=67.0, c1_suction=13.7, comp1_current=8.8)),
            (9, TestPhase.STOP, 78, self._base_values(c1_hp=22.0, c1_lp=6.1, c1_discharge=58.0, c1_suction=13.0, comp1_current=6.3)),
            (10, TestPhase.STOP, 84, self._base_values(c1_hp=20.8, c1_lp=5.8, c1_discharge=50.0, c1_suction=12.6, comp1_current=2.2)),
        ]
        self._create_samples(record, samples)

    def _create_fail_samples(self, record: TestRecord) -> None:
        samples = [
            (1, TestPhase.START, 0, self._base_values(c1_hp=23.2, c1_lp=6.2, c1_discharge=64.0, c1_suction=13.0, comp1_current=11.4)),
            (2, TestPhase.START, 8, self._base_values(c1_hp=23.5, c1_lp=6.3, c1_discharge=68.0, c1_suction=13.2, comp1_current=11.8)),
            (3, TestPhase.START, 16, self._base_values(c1_hp=24.1, c1_lp=6.4, c1_discharge=74.0, c1_suction=13.5, comp1_current=12.3)),
            (4, TestPhase.STABLE, 26, self._base_values(c1_hp=25.2, c1_lp=6.7, c1_discharge=82.0, c1_suction=14.3, comp1_current=12.9, inlet_humidity=49.0, air_flow=2.3)),
            (5, TestPhase.STABLE, 36, self._base_values(c1_hp=25.3, c1_lp=6.8, c1_discharge=84.1, c1_suction=14.4, comp1_current=13.0, inlet_humidity=49.1, air_flow=2.2)),
            (6, TestPhase.STABLE, 46, self._base_values(c1_hp=25.4, c1_lp=6.8, c1_discharge=84.5, c1_suction=14.5, comp1_current=13.2, inlet_humidity=49.6, air_flow=2.2)),
            (7, TestPhase.STABLE, 58, self._base_values(c1_hp=25.3, c1_lp=6.8, c1_discharge=83.9, c1_suction=14.4, comp1_current=13.1, inlet_humidity=49.2, air_flow=2.1)),
            (8, TestPhase.STOP, 72, self._base_values(c1_hp=24.0, c1_lp=6.4, c1_discharge=70.0, c1_suction=13.8, comp1_current=8.5)),
            (9, TestPhase.STOP, 86, self._base_values(c1_hp=21.8, c1_lp=6.0, c1_discharge=61.0, c1_suction=13.1, comp1_current=6.1)),
            (10, TestPhase.STOP, 94, self._base_values(c1_hp=20.5, c1_lp=5.8, c1_discharge=52.0, c1_suction=12.8, comp1_current=2.4)),
        ]
        self._create_samples(record, samples)

    def _create_abort_samples(self, record: TestRecord) -> None:
        samples = [
            (1, TestPhase.START, 0, self._base_values(c1_hp=22.8, c1_lp=6.1, c2_hp=22.5, c2_lp=6.0, c1_discharge=62.0, c2_discharge=61.0, c1_current=9.8, c2_current=9.4)),
            (2, TestPhase.START, 10, self._base_values(c1_hp=23.0, c1_lp=6.2, c2_hp=22.8, c2_lp=6.1, c1_discharge=65.0, c2_discharge=64.0, c1_current=10.5, c2_current=9.9)),
            (3, TestPhase.START, 20, self._base_values(c1_hp=24.0, c1_lp=6.4, c2_hp=23.8, c2_lp=6.3, c1_discharge=69.0, c2_discharge=68.0, c1_current=11.0, c2_current=10.7)),
            (4, TestPhase.STABLE, 35, self._base_values(c1_hp=25.1, c1_lp=6.8, c2_hp=25.0, c2_lp=6.9, c1_discharge=75.0, c2_discharge=74.0, c1_current=12.3, c2_current=11.7, inlet_humidity=47.0, outlet_humidity=38.0, water_in=18.0, water_out=24.0)),
            (5, TestPhase.STABLE, 47, self._base_values(c1_hp=25.4, c1_lp=6.9, c2_hp=25.2, c2_lp=6.9, c1_discharge=76.0, c2_discharge=75.0, c1_current=12.7, c2_current=11.9, inlet_humidity=47.2, outlet_humidity=38.1, water_in=18.2, water_out=24.2)),
            (6, TestPhase.ABORTED, 58, self._base_values(c1_hp=24.2, c1_lp=6.4, c2_hp=24.0, c2_lp=6.4, c1_discharge=66.0, c2_discharge=65.0, c1_current=5.0, c2_current=4.6)),
        ]
        self._create_samples(record, samples)

    def _create_failed_to_start_samples(self, record: TestRecord) -> None:
        samples = [
            (1, TestPhase.START, 0, self._base_values(c2_hp=21.8, c2_lp=5.9, c2_discharge=54.0, c2_suction=12.8, c2_current=0.0, air_flow=1.9, water_in=17.5, water_out=22.2)),
            (2, TestPhase.START, 2, self._base_values(c2_hp=21.9, c2_lp=6.0, c2_discharge=55.0, c2_suction=12.9, c2_current=0.0, air_flow=1.9, water_in=17.6, water_out=22.3)),
            (3, TestPhase.START, 4, self._base_values(c2_hp=22.0, c2_lp=6.0, c2_discharge=55.0, c2_suction=12.9, c2_current=0.0, air_flow=1.9, water_in=17.6, water_out=22.4)),
        ]
        self._create_samples(record, samples, phase_running_bits=False)

    def _create_dual_pass_samples(self, record: TestRecord) -> None:
        samples = [
            (1, TestPhase.START, 0, self._base_values(c1_hp=23.1, c1_lp=6.2, c2_hp=22.9, c2_lp=6.1, c1_discharge=60.0, c2_discharge=59.0, c1_current=10.2, c2_current=9.9, air_flow=2.3)),
            (2, TestPhase.START, 10, self._base_values(c1_hp=23.9, c1_lp=6.4, c2_hp=23.6, c2_lp=6.3, c1_discharge=65.0, c2_discharge=64.0, c1_current=11.0, c2_current=10.6, air_flow=2.4)),
            (3, TestPhase.START, 22, self._base_values(c1_hp=24.5, c1_lp=6.5, c2_hp=24.1, c2_lp=6.4, c1_discharge=70.0, c2_discharge=69.0, c1_current=11.5, c2_current=11.0, air_flow=2.4)),
            (4, TestPhase.STABLE, 38, self._base_values(c1_hp=25.4, c1_lp=6.8, c2_hp=25.1, c2_lp=6.8, c1_discharge=76.0, c2_discharge=75.0, c1_current=12.7, c2_current=12.0, inlet_humidity=45.0, outlet_humidity=36.0, air_flow=2.7)),
            (5, TestPhase.STABLE, 56, self._base_values(c1_hp=25.7, c1_lp=6.9, c2_hp=25.4, c2_lp=6.9, c1_discharge=77.0, c2_discharge=76.0, c1_current=12.9, c2_current=12.3, inlet_humidity=45.5, outlet_humidity=36.4, air_flow=2.8)),
            (6, TestPhase.STABLE, 74, self._base_values(c1_hp=25.9, c1_lp=7.0, c2_hp=25.6, c2_lp=7.0, c1_discharge=78.0, c2_discharge=77.0, c1_current=13.1, c2_current=12.5, inlet_humidity=46.0, outlet_humidity=36.9, air_flow=2.8)),
            (7, TestPhase.STOP, 108, self._base_values(c1_hp=24.2, c1_lp=6.5, c2_hp=24.0, c2_lp=6.4, c1_discharge=68.0, c2_discharge=67.0, c1_current=8.2, c2_current=7.9, air_flow=2.2)),
            (8, TestPhase.STOP, 124, self._base_values(c1_hp=22.1, c1_lp=6.0, c2_hp=21.8, c2_lp=5.9, c1_discharge=57.0, c2_discharge=56.0, c1_current=4.0, c2_current=3.8, air_flow=1.8)),
            (9, TestPhase.STOP, 138, self._base_values(c1_hp=20.7, c1_lp=5.6, c2_hp=20.4, c2_lp=5.5, c1_discharge=48.0, c2_discharge=47.0, c1_current=1.6, c2_current=1.5, air_flow=1.2)),
        ]
        self._create_samples(record, samples)

    def _create_water_fail_samples(self, record: TestRecord) -> None:
        samples = [
            (1, TestPhase.START, 0, self._base_values(c2_hp=22.2, c2_lp=6.1, c2_discharge=58.0, c2_suction=13.0, c2_current=10.8, air_flow=2.1, water_in=18.0, water_out=24.5)),
            (2, TestPhase.START, 10, self._base_values(c2_hp=23.0, c2_lp=6.2, c2_discharge=63.0, c2_suction=13.2, c2_current=11.5, air_flow=2.2, water_in=18.2, water_out=25.5)),
            (3, TestPhase.STABLE, 24, self._base_values(c2_hp=24.5, c2_lp=6.5, c2_discharge=77.0, c2_suction=14.0, c2_current=12.8, air_flow=2.4, water_in=23.4, water_out=31.5)),
            (4, TestPhase.STABLE, 36, self._base_values(c2_hp=24.8, c2_lp=6.5, c2_discharge=79.0, c2_suction=14.1, c2_current=13.0, air_flow=2.3, water_in=24.1, water_out=32.4)),
            (5, TestPhase.STABLE, 48, self._base_values(c2_hp=25.0, c2_lp=6.6, c2_discharge=80.0, c2_suction=14.2, c2_current=13.1, air_flow=2.2, water_in=24.3, water_out=33.0)),
            (6, TestPhase.STABLE, 60, self._base_values(c2_hp=24.9, c2_lp=6.5, c2_discharge=79.4, c2_suction=14.2, c2_current=13.0, air_flow=2.2, water_in=24.0, water_out=32.8)),
            (7, TestPhase.STOP, 76, self._base_values(c2_hp=23.8, c2_lp=6.3, c2_discharge=69.0, c2_suction=13.6, c2_current=8.0, air_flow=1.9, water_in=21.0, water_out=28.0)),
            (8, TestPhase.STOP, 88, self._base_values(c2_hp=21.7, c2_lp=5.9, c2_discharge=56.0, c2_suction=12.9, c2_current=3.1, air_flow=1.5, water_in=18.8, water_out=24.7)),
        ]
        self._create_samples(record, samples)

    def _create_samples(
        self,
        record: TestRecord,
        samples: list[tuple[int, TestPhase, int, dict[str, float]]],
        *,
        phase_running_bits: bool = True,
    ) -> None:
        started_at = record.started_at or timezone.now()
        for sequence_no, phase, offset_sec, values in samples:
            TestSample.objects.create(
                test_record=record,
                sequence_no=sequence_no,
                timestamp_unix=int((started_at + timedelta(seconds=offset_sec)).timestamp()),
                test_phase=int(phase),
                status_word=self._status_word_for_phase(phase, record.selected_circuit, phase_running_bits=phase_running_bits),
                validity_word1=0xFFFF,
                validity_word2=0x0FFF,
                dynamic_values={key: round(value, 2) for key, value in values.items()},
            )

    @staticmethod
    def _status_word_for_phase(phase: TestPhase, circuit: int, *, phase_running_bits: bool = True) -> int:
        word = 0
        if phase_running_bits and phase in {TestPhase.START, TestPhase.STABLE, TestPhase.STOP}:
            word |= 1 << 0
        if phase == TestPhase.ABORTED:
            word |= 1 << 1
        if (
            phase_running_bits
            and circuit in {int(CircuitSelect.CIRCUIT_1), int(CircuitSelect.BOTH)}
            and phase in {TestPhase.START, TestPhase.STABLE}
        ):
            word |= 1 << 2
        if (
            phase_running_bits
            and circuit in {int(CircuitSelect.CIRCUIT_2), int(CircuitSelect.BOTH)}
            and phase in {TestPhase.START, TestPhase.STABLE}
        ):
            word |= 1 << 3
        return word

    def _build_prestart_samples(self, sample_profile: str) -> list[dict[str, object]]:
        if sample_profile in {"pass_dual", "abort_dual"}:
            presets = [
                (-5, self._base_values(c1_hp=22.1, c1_lp=6.0, c2_hp=21.9, c2_lp=5.9, c1_discharge=54.0, c2_discharge=53.0, c1_current=0.0, c2_current=0.0, air_flow=1.1)),
                (-3, self._base_values(c1_hp=22.2, c1_lp=6.0, c2_hp=22.0, c2_lp=6.0, c1_discharge=55.0, c2_discharge=54.0, c1_current=0.0, c2_current=0.0, air_flow=1.1)),
                (-1, self._base_values(c1_hp=22.3, c1_lp=6.1, c2_hp=22.1, c2_lp=6.0, c1_discharge=56.0, c2_discharge=55.0, c1_current=0.0, c2_current=0.0, air_flow=1.2)),
            ]
        elif sample_profile == "failed_to_start":
            presets = [
                (-5, self._base_values(c2_hp=21.6, c2_lp=5.8, c2_discharge=52.0, c2_suction=12.7, c2_current=0.0, air_flow=1.8, water_in=17.4, water_out=22.0)),
                (-3, self._base_values(c2_hp=21.7, c2_lp=5.9, c2_discharge=53.0, c2_suction=12.7, c2_current=0.0, air_flow=1.8, water_in=17.4, water_out=22.1)),
                (-1, self._base_values(c2_hp=21.8, c2_lp=5.9, c2_discharge=54.0, c2_suction=12.8, c2_current=0.0, air_flow=1.9, water_in=17.5, water_out=22.2)),
            ]
        else:
            presets = [
                (-5, self._base_values(c1_hp=22.4, c1_lp=6.0, c1_discharge=55.0, c1_suction=12.9, comp1_current=0.0, air_flow=1.2)),
                (-3, self._base_values(c1_hp=22.5, c1_lp=6.0, c1_discharge=56.0, c1_suction=13.0, comp1_current=0.0, air_flow=1.2)),
                (-1, self._base_values(c1_hp=22.7, c1_lp=6.1, c1_discharge=57.0, c1_suction=13.0, comp1_current=0.0, air_flow=1.3)),
            ]
        return [
            {
                "seconds": seconds,
                "values": {key: round(value, 2) for key, value in values.items()},
            }
            for seconds, values in presets
        ]

    def _single_circuit_limits(self, max_current: float, max_discharge: float) -> dict[str, dict[str, dict[str, bool | float | None]]]:
        return {
            "101": {"start": empty_limit(), "stable": {"min_enabled": True, "min_value": 22.0, "max_enabled": True, "max_value": 28.0}, "stop": empty_limit()},
            "102": {"start": empty_limit(), "stable": {"min_enabled": True, "min_value": 5.5, "max_enabled": True, "max_value": 8.0}, "stop": empty_limit()},
            "105": {"start": empty_limit(), "stable": {"min_enabled": True, "min_value": 55.0, "max_enabled": True, "max_value": max_discharge}, "stop": empty_limit()},
            "107": {"start": empty_limit(), "stable": {"min_enabled": True, "min_value": 8.0, "max_enabled": True, "max_value": 18.0}, "stop": empty_limit()},
            "110": {"start": empty_limit(), "stable": {"min_enabled": True, "min_value": 2.0, "max_enabled": False, "max_value": None}, "stop": empty_limit()},
            "112": {"start": {"min_enabled": False, "min_value": None, "max_enabled": True, "max_value": max_current + 0.5}, "stable": {"min_enabled": False, "min_value": None, "max_enabled": True, "max_value": max_current}, "stop": empty_limit()},
            "127": {"start": empty_limit(), "stable": {"min_enabled": True, "min_value": 35.0, "max_enabled": True, "max_value": 55.0}, "stop": empty_limit()},
        }

    def _dual_circuit_limits(
        self,
        comp1_max: float = 14.0,
        comp2_max: float = 13.5,
        air_flow_min: float = 2.0,
    ) -> dict[str, dict[str, dict[str, bool | float | None]]]:
        limits = self._single_circuit_limits(max_current=comp1_max, max_discharge=85.0)
        limits.update(
            {
                "103": {"start": empty_limit(), "stable": {"min_enabled": True, "min_value": 22.0, "max_enabled": True, "max_value": 28.5}, "stop": empty_limit()},
                "104": {"start": empty_limit(), "stable": {"min_enabled": True, "min_value": 5.5, "max_enabled": True, "max_value": 8.0}, "stop": empty_limit()},
                "106": {"start": empty_limit(), "stable": {"min_enabled": True, "min_value": 55.0, "max_enabled": True, "max_value": 85.0}, "stop": empty_limit()},
                "108": {"start": empty_limit(), "stable": {"min_enabled": True, "min_value": 8.0, "max_enabled": True, "max_value": 18.0}, "stop": empty_limit()},
                "120": {"start": {"min_enabled": False, "min_value": None, "max_enabled": True, "max_value": comp2_max + 0.5}, "stable": {"min_enabled": False, "min_value": None, "max_enabled": True, "max_value": comp2_max}, "stop": empty_limit()},
                "128": {"start": empty_limit(), "stable": {"min_enabled": True, "min_value": 25.0, "max_enabled": True, "max_value": 45.0}, "stop": empty_limit()},
                "110": {"start": empty_limit(), "stable": {"min_enabled": True, "min_value": air_flow_min, "max_enabled": False, "max_value": None}, "stop": empty_limit()},
            }
        )
        return limits

    def _water_loop_limits(self) -> dict[str, dict[str, dict[str, bool | float | None]]]:
        limits = self._single_circuit_limits(max_current=12.2, max_discharge=82.0)
        limits.update(
            {
                "129": {"start": empty_limit(), "stable": {"min_enabled": True, "min_value": 14.0, "max_enabled": True, "max_value": 22.0}, "stop": empty_limit()},
                "130": {"start": empty_limit(), "stable": {"min_enabled": True, "min_value": 20.0, "max_enabled": True, "max_value": 30.0}, "stop": empty_limit()},
                "131": {"start": empty_limit(), "stable": {"min_enabled": True, "min_value": 22.0, "max_enabled": True, "max_value": 35.0}, "stop": empty_limit()},
                "132": {"start": empty_limit(), "stable": {"min_enabled": True, "min_value": 12.0, "max_enabled": True, "max_value": 24.0}, "stop": empty_limit()},
            }
        )
        return limits

    def _base_values(
        self,
        c1_hp: float = 24.5,
        c1_lp: float = 6.5,
        c2_hp: float = 24.0,
        c2_lp: float = 6.4,
        c1_discharge: float = 70.0,
        c2_discharge: float = 69.0,
        c1_suction: float = 14.0,
        c2_suction: float = 14.0,
        comp1_current: float | None = None,
        comp2_current: float | None = None,
        c1_current: float | None = None,
        c2_current: float | None = None,
        inlet_humidity: float = 46.0,
        outlet_humidity: float = 38.0,
        air_flow: float = 2.5,
        water_in: float = 18.0,
        water_out: float = 24.0,
    ) -> dict[str, float]:
        comp1_current_value = comp1_current if comp1_current is not None else (c1_current if c1_current is not None else 11.0)
        comp2_current_value = comp2_current if comp2_current is not None else (c2_current if c2_current is not None else 10.5)
        return {
            "101": c1_hp,
            "102": c1_lp,
            "103": c2_hp,
            "104": c2_lp,
            "105": c1_discharge,
            "106": c2_discharge,
            "107": c1_suction,
            "108": c2_suction,
            "110": air_flow,
            "111": 230.5,
            "112": comp1_current_value,
            "113": max(0.0, round(comp1_current_value * 3.2, 2)),
            "114": 2.8,
            "115": max(0.0, round(comp1_current_value * 3.4, 2)),
            "116": 0.96,
            "117": 50.0,
            "118": 148.0,
            "119": 229.8,
            "120": comp2_current_value,
            "121": max(0.0, round(comp2_current_value * 3.0, 2)),
            "122": 2.5,
            "123": max(0.0, round(comp2_current_value * 3.2, 2)),
            "124": 0.95,
            "125": 50.0,
            "126": 136.0,
            "127": inlet_humidity,
            "128": outlet_humidity,
            "129": water_in,
            "130": water_out,
            "131": 27.8,
            "132": 18.9,
        }

    @staticmethod
    def _create_info_event(record: TestRecord, event_code: str, message: str) -> None:
        PlcEventLog.objects.create(
            test_record=record,
            event_type=PlcEventType.INFO,
            event_code=event_code,
            message=message,
            details_json={"demo": True},
        )

    @staticmethod
    def _create_warning_event(record: TestRecord, event_code: str, message: str) -> None:
        PlcEventLog.objects.create(
            test_record=record,
            event_type=PlcEventType.WARNING,
            event_code=event_code,
            message=message,
            details_json={"demo": True},
        )

    @staticmethod
    def _create_fault_event(record: TestRecord, event_code: str, message: str) -> None:
        PlcEventLog.objects.create(
            test_record=record,
            event_type=PlcEventType.FAULT,
            event_code=event_code,
            message=message,
            details_json={"demo": True},
        )
