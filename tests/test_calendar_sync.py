"""Tests for AlgoRadar iCalendar Generator & Exporter."""

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from algoradar.calendar_sync import (
    DEFAULT_ALARM_MINUTES,
    build_vevent,
    escape_ics_text,
    export_ics,
    fold_line,
    format_utc_timestamp,
    generate_ics,
)
from algoradar.models import CODEFORCES, LEETCODE, Contest, ContestStatus


class TestCalendarSync(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 5, 20, 14, 35, 0, tzinfo=timezone.utc)
        self.end = self.start + timedelta(hours=2)
        self.contest = Contest(
            id="cf_1999",
            platform=CODEFORCES,
            name="Codeforces Round 999 (Div. 2)",
            url="https://codeforces.com/contest/1999",
            start_time=self.start,
            end_time=self.end,
            duration_seconds=7200,
            status=ContestStatus.UPCOMING,
            description="Regular Div. 2 contest with 6 problems; rated for participants < 2100.",
        )

    def test_escape_ics_text(self):
        raw = "Hello, World; this is a test \\ with\nnewline and \r\ncarriage return."
        escaped = escape_ics_text(raw)
        self.assertIn(r"Hello\, World\;", escaped)
        self.assertIn(r"\\ with\nnewline", escaped)
        self.assertNotIn("\r", escaped)

    def test_format_utc_timestamp(self):
        # Timezone aware
        ts = format_utc_timestamp(self.start)
        self.assertEqual(ts, "20260520T143500Z")

        # Naive datetime assumed UTC
        naive = datetime(2026, 12, 31, 23, 59, 59)
        self.assertEqual(format_utc_timestamp(naive), "20261231T235959Z")

    def test_fold_line(self):
        short_line = "SUMMARY:Short text"
        self.assertEqual(fold_line(short_line), short_line)

        long_line = "DESCRIPTION:" + "A" * 150
        folded = fold_line(long_line, limit=75)
        self.assertIn("\r\n ", folded)
        # Verify reconstructed line equals original line
        reconstructed = folded.replace("\r\n ", "")
        self.assertEqual(reconstructed, long_line)

    def test_build_vevent(self):
        dtstamp = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        vevent = build_vevent(self.contest, alarm_minutes=15, dtstamp=dtstamp)

        self.assertIn("BEGIN:VEVENT", vevent)
        self.assertIn("END:VEVENT", vevent)
        self.assertIn("UID:codeforces_cf_1999@algoradar.net", vevent)
        self.assertIn("DTSTART:20260520T143500Z", vevent)
        self.assertIn("DTEND:20260520T163500Z", vevent)
        self.assertIn("URL:https://codeforces.com/contest/1999", vevent)
        self.assertIn("STATUS:CONFIRMED", vevent)

        # Check Alarm
        self.assertIn("BEGIN:VALARM", vevent)
        self.assertIn("TRIGGER:-PT15M", vevent)
        self.assertIn("ACTION:DISPLAY", vevent)
        self.assertIn("END:VALARM", vevent)

    def test_generate_ics(self):
        c2 = Contest(
            id="lc_biweekly_130",
            platform=LEETCODE,
            name="Biweekly Contest 130",
            url="https://leetcode.com/contest/biweekly-contest-130",
            start_time=self.start + timedelta(days=2),
            end_time=self.start + timedelta(days=2, hours=1, minutes=30),
            duration_seconds=5400,
        )

        ics_str = generate_ics([self.contest, c2])

        self.assertTrue(ics_str.startswith("BEGIN:VCALENDAR\r\n"))
        self.assertTrue(ics_str.endswith("END:VCALENDAR\r\n"))
        self.assertIn("VERSION:2.0\r\n", ics_str)
        self.assertIn("X-WR-CALNAME:AlgoRadar CP Contests\r\n", ics_str)
        self.assertEqual(ics_str.count("BEGIN:VEVENT"), 2)
        self.assertEqual(ics_str.count("END:VEVENT"), 2)

    def test_export_ics_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "subfolder" / "radar.ics"
            exported_path = export_ics([self.contest], output_path=out_file)

            self.assertTrue(exported_path.exists())
            self.assertEqual(exported_path, out_file.resolve())

            content = out_file.read_text(encoding="utf-8")
            self.assertIn("BEGIN:VCALENDAR", content)
            self.assertIn("Codeforces Round 999", content)
            self.assertIn("END:VCALENDAR", content)


if __name__ == "__main__":
    unittest.main()
