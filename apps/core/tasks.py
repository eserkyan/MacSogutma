from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.plc.models import PlcEventLog


@shared_task
def cleanup_old_events_task(days: int = 14) -> int:
    threshold = timezone.now() - timedelta(days=days)
    deleted, _ = PlcEventLog.objects.filter(created_at__lt=threshold).delete()
    return deleted
