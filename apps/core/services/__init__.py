from __future__ import annotations

from datetime import timedelta

from django.utils import timezone


def now_plus(seconds: int) -> timezone.datetime:
    return timezone.now() + timedelta(seconds=seconds)

