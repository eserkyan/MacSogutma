from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from apps.companies.models import Company
from apps.core.constants import CircuitSelect, TestPhase, TestStatus
from apps.products.models import ProductModel
from apps.recipes.models import Recipe
from apps.recipes.services.phase_limits import empty_limit
from apps.tests.models import TestRecord, TestSample
from apps.tests.services.evaluation import TestEvaluationService


class TestEvaluationServiceTests(TestCase):
    def test_stable_avg_drives_pass_fail(self) -> None:
        company = Company.objects.create(name="Company", code="CMP")
        product = ProductModel.objects.create(model_code="M1", model_name="Model", product_type="Type")
        recipe = Recipe.objects.create(
            product_model=product,
            recipe_name="Recipe",
            recipe_code="R1",
            revision_no="1",
            start_duration_sec=1,
            stable_duration_sec=1,
            stop_duration_sec=1,
            limits_json={
                "105": {
                    "start": empty_limit(),
                    "stable": {"min_enabled": True, "min_value": 20, "max_enabled": True, "max_value": 30},
                    "stop": empty_limit(),
                }
            },
        )
        record = TestRecord.objects.create(
            test_no="T-1",
            company=company,
            product_model=product,
            recipe=recipe,
            operator_name="Op",
            selected_circuit=CircuitSelect.CIRCUIT_1,
            status=TestStatus.RUNNING,
            recipe_name_snapshot=recipe.recipe_name,
            recipe_code_snapshot=recipe.recipe_code,
            recipe_revision_snapshot=recipe.revision_no,
            start_duration_sec_snapshot=1,
            stable_duration_sec_snapshot=1,
            stop_duration_sec_snapshot=1,
            limits_snapshot_json={
                "105": {
                    "start": empty_limit(),
                    "stable": {"min_enabled": True, "min_value": 20, "max_enabled": True, "max_value": 30},
                    "stop": empty_limit(),
                }
            },
        )
        TestSample.objects.create(
            test_record=record,
            sequence_no=1,
            timestamp_unix=1,
            test_phase=TestPhase.STABLE,
            status_word=0,
            validity_word1=1 << 4,
            dynamic_values={"105": float(Decimal("25.0"))},
        )
        summary = TestEvaluationService().evaluate(record)
        record.refresh_from_db()
        self.assertTrue(summary.passed)
        self.assertEqual(record.status, TestStatus.COMPLETED_PASS)

    def test_start_phase_limit_can_fail_test(self) -> None:
        company = Company.objects.create(name="Company", code="CMP2")
        product = ProductModel.objects.create(model_code="M2", model_name="Model 2", product_type="Type")
        recipe = Recipe.objects.create(
            product_model=product,
            recipe_name="Recipe 2",
            recipe_code="R2",
            revision_no="1",
            start_duration_sec=1,
            stable_duration_sec=1,
            stop_duration_sec=1,
            limits_json={
                "105": {
                    "start": {"min_enabled": True, "min_value": 20, "max_enabled": True, "max_value": 30},
                    "stable": empty_limit(),
                    "stop": empty_limit(),
                }
            },
        )
        record = TestRecord.objects.create(
            test_no="T-2",
            company=company,
            product_model=product,
            recipe=recipe,
            operator_name="Op",
            selected_circuit=CircuitSelect.CIRCUIT_1,
            status=TestStatus.RUNNING,
            recipe_name_snapshot=recipe.recipe_name,
            recipe_code_snapshot=recipe.recipe_code,
            recipe_revision_snapshot=recipe.revision_no,
            start_duration_sec_snapshot=1,
            stable_duration_sec_snapshot=1,
            stop_duration_sec_snapshot=1,
            limits_snapshot_json={
                "105": {
                    "start": {"min_enabled": True, "min_value": 20, "max_enabled": True, "max_value": 30},
                    "stable": empty_limit(),
                    "stop": empty_limit(),
                }
            },
        )
        TestSample.objects.create(
            test_record=record,
            sequence_no=1,
            timestamp_unix=1,
            test_phase=TestPhase.START,
            status_word=0,
            validity_word1=1 << 4,
            dynamic_values={"105": float(Decimal("31.0"))},
        )
        summary = TestEvaluationService().evaluate(record)
        record.refresh_from_db()
        self.assertFalse(summary.passed)
        self.assertEqual(record.status, TestStatus.COMPLETED_FAIL)

    def test_invalid_samples_do_not_fail_test(self) -> None:
        company = Company.objects.create(name="Company", code="CMP3")
        product = ProductModel.objects.create(model_code="M3", model_name="Model 3", product_type="Type")
        recipe = Recipe.objects.create(
            product_model=product,
            recipe_name="Recipe 3",
            recipe_code="R3",
            revision_no="1",
            start_duration_sec=1,
            stable_duration_sec=1,
            stop_duration_sec=1,
            limits_json={
                "105": {
                    "start": empty_limit(),
                    "stable": {"min_enabled": True, "min_value": 20, "max_enabled": True, "max_value": 30},
                    "stop": empty_limit(),
                }
            },
        )
        record = TestRecord.objects.create(
            test_no="T-3",
            company=company,
            product_model=product,
            recipe=recipe,
            operator_name="Op",
            selected_circuit=CircuitSelect.CIRCUIT_1,
            status=TestStatus.RUNNING,
            recipe_name_snapshot=recipe.recipe_name,
            recipe_code_snapshot=recipe.recipe_code,
            recipe_revision_snapshot=recipe.revision_no,
            start_duration_sec_snapshot=1,
            stable_duration_sec_snapshot=1,
            stop_duration_sec_snapshot=1,
            limits_snapshot_json={
                "105": {
                    "start": empty_limit(),
                    "stable": {"min_enabled": True, "min_value": 20, "max_enabled": True, "max_value": 30},
                    "stop": empty_limit(),
                }
            },
        )
        TestSample.objects.create(
            test_record=record,
            sequence_no=1,
            timestamp_unix=1,
            test_phase=TestPhase.STABLE,
            status_word=0,
            validity_word1=0,
            dynamic_values={"105": float(Decimal("35.0"))},
        )
        summary = TestEvaluationService().evaluate(record)
        record.refresh_from_db()
        result = record.evaluation_results.get(parameter_code="105", phase_used="STABLE")
        self.assertTrue(summary.passed)
        self.assertEqual(record.status, TestStatus.COMPLETED_PASS)
        self.assertIsNone(result.passed)
