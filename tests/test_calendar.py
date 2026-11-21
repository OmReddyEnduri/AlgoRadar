"""Unit tests for AlgoRadar iCalendar (.ics) Generator and Synchronizer."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from algoradar.calendar_sync import (
    DEFAULT_ALARM_MINUTES,
    DEFAULT_CALENDAR_DESC,
    DEFAULT_CALENDAR_NAME,
    DEFAULT_PRODID,
    build_vevent,
    escape_ics_text,
    export_ics,
    fold_line,
    format_utc_timestamp,
    generate_ics,
)
from algoradar.models import (
    ATCODER,
    CODECHEF,
    CODEFORCES,
    HACKERRANK,
    LEETCODE,
    Contest,
    ContestStatus,
)


class TestCalendarSync(unittest.TestCase):
    """Test RFC 5545 compliance, timestamp formatting, escaping, line folding, and exports."""

    def setUp(self):
        self.base_time = datetime(2026, 11, 21, 14, 30, 0, tzinfo=timezone.utc)
        self.contest1 = Contest(
            id="cf_2000",
            platform=CODEFORCES,
            name="Codeforces Round 1000 (Div. 1 + Div. 2)",
            url="https://codeforces.com/contest/2000",
            start_time=self.base_time,
            end_time=self.base_time + timedelta(hours=2),
            duration_seconds=7200,
            status=ContestStatus.UPCOMING,
            description="Official rated round; 6 problems.",
        )
        self.contest2 = Contest(
            id="lc_410",
            platform=LEETCODE,
            name="Weekly Contest 410",
            url="https://leetcode.com/contest/weekly-contest-410",
            start_time=self.base_time + timedelta(days=1),
            end_time=self.base_time + timedelta(days=1, minutes=90),
            duration_seconds=5400,
            status=ContestStatus.UPCOMING,
            description="LeetCode rating contest; 4 algorithm problems.",
        )

    def test_format_utc_timestamp(self):
        """Test timestamp formatting to RFC 5545 UTC (YYYYMMDDTHHMMSSZ)."""
        # UTC aware
        dt_utc = datetime(2026, 11, 21, 14, 30, 45, tzinfo=timezone.utc)
        self.assertEqual(format_utc_timestamp(dt_utc), "20261121T143045Z")

        # Naive datetime (should assume UTC)
        dt_naive = datetime(2026, 5, 1, 9, 0, 0)
        self.assertEqual(format_utc_timestamp(dt_naive), "20260501T090000Z")

        # Non-UTC timezone (e.g. IST UTC+05:30)
        ist = timezone(timedelta(hours=5, minutes=30))
        dt_ist = datetime(2026, 11, 21, 20, 0, 0, tzinfo=ist)
        # 20:00:00 IST is 14:30:00 UTC
        self.assertEqual(format_utc_timestamp(dt_ist), "20261121T143000Z")

    def test_escape_ics_text(self):
        """Test RFC 5545 escaping for backslashes, semicolons, commas, and newlines."""
        self.assertEqual(escape_ics_text(""), "")
        self.assertEqual(escape_ics_text("Hello World"), "Hello World")
        self.assertEqual(escape_ics_text("C:\\Program Files"), "C:\\\\Program Files")
        self.assertEqual(escape_ics_text("Param 1; Param 2"), "Param 1\\; Param 2")
        self.assertEqual(escape_ics_text("Item 1, Item 2"), "Item 1\\, Item 2")
        self.assertEqual(escape_ics_text("Line 1\nLine 2"), "Line 1\\nLine 2")
        self.assertEqual(escape_ics_text("Line 1\r\nLine 2"), "Line 1\\nLine 2")

        # Combined special characters
        complex_text = "Important: Check, Read; Follow\\Notice\nNext Line"
        expected = "Important: Check\\, Read\\; Follow\\\\Notice\\nNext Line"
        self.assertEqual(escape_ics_text(complex_text), expected)

    def test_fold_line(self):
        """Test RFC 5545 line folding at 75-octet boundary."""
        # Under limit
        short_line = "SUMMARY:Short Summary"
        self.assertEqual(fold_line(short_line), short_line)

        # Long line (over 75 bytes)
        long_line = "DESCRIPTION:" + "A" * 100
        folded = fold_line(long_line, limit=75)
        lines = folded.split("\r\n")
        self.assertGreater(len(lines), 1)
        self.assertLessEqual(len(lines[0].encode("utf-8")), 75)
        # Folded line continuation must start with a space
        for continuation in lines[1:]:
            self.assertTrue(continuation.startswith(" "))

    def test_build_vevent_structure_and_fields(self):
        """Test build_vevent component generation and fields."""
        fixed_dtstamp = datetime(2026, 11, 21, 10, 0, 0, tzinfo=timezone.utc)
        vevent_str = build_vevent(self.contest1, alarm_minutes=15, dtstamp=fixed_dtstamp)

        self.assertTrue(vevent_str.startswith("BEGIN:VEVENT"))
        self.assertTrue(vevent_str.endswith("END:VEVENT"))

        # Verify UID
        self.assertIn("UID:codeforces_cf_2000@algoradar.net", vevent_str)
        # Verify DTSTAMP, DTSTART, DTEND
        self.assertIn("DTSTAMP:20261121T100000Z", vevent_str)
        self.assertIn("DTSTART:20261121T143000Z", vevent_str)
        self.assertIn("DTEND:20261121T163000Z", vevent_str)

        # Verify Summary and Details
        self.assertIn("[CF]", vevent_str)
        self.assertIn("Codeforces Round 1000", vevent_str)
        self.assertIn("URL:https://codeforces.com/contest/2000", vevent_str)
        self.assertIn("STATUS:CONFIRMED", vevent_str)
        self.assertIn("TRANSP:OPAQUE", vevent_str)

        # Verify Alarm
        self.assertIn("BEGIN:VALARM", vevent_str)
        self.assertIn("TRIGGER:-PT15M", vevent_str)
        self.assertIn("ACTION:DISPLAY", vevent_str)
        self.assertIn("END:VALARM", vevent_str)

    def test_build_vevent_custom_alarm_and_disabled_alarm(self):
        """Test build_vevent with custom alarm timing or disabled alarm."""
        # Custom 30-minute alarm
        v30 = build_vevent(self.contest1, alarm_minutes=30)
        self.assertIn("TRIGGER:-PT30M", v30)

        # Disabled alarm (alarm_minutes = 0)
        v0 = build_vevent(self.contest1, alarm_minutes=0)
        self.assertNotIn("BEGIN:VALARM", v0)
        self.assertNotIn("TRIGGER:", v0)

    def test_generate_ics_complete_calendar(self):
        """Test generate_ics produces compliant VCALENDAR container and order."""
        fixed_dtstamp = datetime(2026, 11, 21, 10, 0, 0, tzinfo=timezone.utc)
        # Pass contests in reverse chronological order
        ics = generate_ics(
            [self.contest2, self.contest1],
            calendar_name="My CP Radar",
            calendar_desc="Custom Description",
            alarm_minutes=15,
            dtstamp=fixed_dtstamp,
        )

        # Verify header & properties
        self.assertTrue(ics.startswith("BEGIN:VCALENDAR\r\n"))
        self.assertTrue(ics.endswith("END:VCALENDAR\r\n"))
        self.assertIn("VERSION:2.0\r\n", ics)
        self.assertIn(f"PRODID:{DEFAULT_PRODID}\r\n", ics)
        self.assertIn("CALSCALE:GREGORIAN\r\n", ics)
        self.assertIn("METHOD:PUBLISH\r\n", ics)
        self.assertIn("X-WR-CALNAME:My CP Radar\r\n", ics)
        self.assertIn("X-WR-CALDESC:Custom Description\r\n", ics)
        self.assertIn("X-WR-TIMEZONE:UTC\r\n", ics)

        # Verify chronological order (contest1 before contest2)
        idx_cf = ics.find("UID:codeforces_cf_2000@algoradar.net")
        idx_lc = ics.find("UID:leetcode_lc_410@algoradar.net")
        self.assertNotEqual(idx_cf, -1)
        self.assertNotEqual(idx_lc, -1)
        self.assertLess(idx_cf, idx_lc)

        # Verify number of events
        self.assertEqual(ics.count("BEGIN:VEVENT"), 2)
        self.assertEqual(ics.count("END:VEVENT"), 2)

    def test_generate_ics_empty_contests(self):
        """Test generate_ics with empty contest list generates valid container."""
        ics = generate_ics([])
        self.assertTrue(ics.startswith("BEGIN:VCALENDAR\r\n"))
        self.assertTrue(ics.endswith("END:VCALENDAR\r\n"))
        self.assertEqual(ics.count("BEGIN:VEVENT"), 0)

    def test_export_ics_to_file(self):
        """Test exporting calendar to a physical file and verifying UTF-8 encoding."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "subfolder" / "radar_export.ics"
            returned_path = export_ics(
                [self.contest1],
                output_path=out_file,
                calendar_name="Exported CP Radar",
            )

            self.assertEqual(returned_path, out_file)
            self.assertTrue(out_file.exists())
            self.assertGreater(out_file.stat().st_size, 0)

            # Read back content and verify CRLF line endings and content
            raw_bytes = out_file.read_bytes()
            text = raw_bytes.decode("utf-8")
            self.assertIn("\r\n", text)
            self.assertIn("BEGIN:VCALENDAR", text)
            self.assertIn("Codeforces Round 1000", text)
            self.assertIn("END:VCALENDAR", text)


if __name__ == "__main__":
    unittest.main()
