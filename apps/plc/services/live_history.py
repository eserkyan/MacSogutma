from __future__ import annotations

from collections import deque
from typing import Any

from django.core.cache import cache

HISTORY_CACHE_KEY = "plc_live_history_v1"
MAX_HISTORY_LENGTH = 30


def get_live_history() -> list[dict[str, Any]]:
    history = cache.get(HISTORY_CACHE_KEY, [])
    return history if isinstance(history, list) else []


def append_live_history(record: dict[str, Any]) -> list[dict[str, Any]]:
    history = deque(get_live_history(), maxlen=MAX_HISTORY_LENGTH)
    history.append(record)
    serialized = list(history)
    cache.set(HISTORY_CACHE_KEY, serialized, timeout=None)
    return serialized
