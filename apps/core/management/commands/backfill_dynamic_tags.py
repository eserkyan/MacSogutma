from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

from apps.core.services.tag_registry import TagRegistryService
from apps.tests.models import TestSample


class Command(BaseCommand):
    help = "Normalize TestSample dynamic_values payloads for the current tag registry."

    def handle(self, *args: Any, **options: Any) -> None:
        registry = TagRegistryService()
        registry.ensure_defaults()
        tag_codes = [str(tag["tag_id"]) for tag in registry.get_tags()]
        updated_count = 0

        for sample in TestSample.objects.iterator(chunk_size=500):
            payload = dict(sample.dynamic_values or {})
            changed = False
            for code in tag_codes:
                value = payload.get(code)
                if value is None:
                    continue
                normalized = float(value)
                if normalized != value:
                    payload[code] = normalized
                    changed = True
            if not changed:
                continue
            sample.dynamic_values = payload
            sample.save(update_fields=["dynamic_values", "updated_at"])
            updated_count += 1

        self.stdout.write(self.style.SUCCESS(f"Dynamic tag normalization tamamlandi. Guncellenen sample: {updated_count}"))
