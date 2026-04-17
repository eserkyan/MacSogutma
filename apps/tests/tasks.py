from __future__ import annotations

from celery import shared_task

from apps.tests.services.test_runner import TestRunnerService


@shared_task
def supervise_active_test_task() -> str | None:
    result = TestRunnerService().supervise_active_test()
    return result.test_no if result else None
