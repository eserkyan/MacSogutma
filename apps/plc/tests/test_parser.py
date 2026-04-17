from __future__ import annotations

from django.test import SimpleTestCase

from apps.plc.services.parser import PlcParserService


class PlcParserServiceTests(SimpleTestCase):
    def test_parse_record_decodes_scaled_values(self) -> None:
        registers = [0, 1, 0, 10, 2, 1, 0b11, 0] + [100] * 26
        parsed = PlcParserService.parse_record(registers)
        self.assertEqual(parsed.sequence_no, 1)
        self.assertEqual(parsed.timestamp_unix, 10)
        self.assertEqual(parsed.values["101"], 10.0)
