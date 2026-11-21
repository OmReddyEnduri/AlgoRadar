"""Tests for AlgoRadar Data Models."""

from datetime import datetime, timedelta, timezone
import unittest

from algoradar.models import (
    ATCODER,
    CODECHEF,
    CODEFORCES,
    HACKERRANK,
    LEETCODE,
    Contest,
    ContestStatus,
    Platform,
    get_platform,
)


class TestPlatform(unittest.TestCase):
    def test_platform_attributes(self):
        self.assertEqual(CODEFORCES.id, "codeforces")
        self.assertEqual(CODEFORCES.short_code, "CF")
        self.assertEqual(CODEFORCES.name, "Codeforces")
        self.assertEqual(CODEFORCES.icon, "⚡")
        self.assertEqual(CODEFORCES.url, "https://codeforces.com")

    def test_platform_dict_roundtrip(self):
        d = LEETCODE.to_dict()
        self.assertEqual(d["id"], "leetcode")
        self.assertEqual(d["name"], "LeetCode")
        self.assertEqual(d["short_code"], "LC")

        restored = Platform.from_dict(d)
        self.assertEqual(restored, LEETCODE)

    def test_get_platform_lookup(self):
        self.assertEqual(get_platform("codeforces"), CODEFORCES)
        self.assertEqual(get_platform("CF"), CODEFORCES)
        self.assertEqual(get_platform("leetcode"), LEETCODE)
        self.assertEqual(get_platform("LC"), LEETCODE)
        self.assertEqual(get_platform("atcoder"), ATCODER)
        self.assertEqual(get_platform("AC"), ATCODER)
        self.assertEqual(get_platform("codechef"), CODECHEF)
        self.assertEqual(get_platform("CC"), CODECHEF)
        self.assertEqual(get_platform("hackerrank"), HACKERRANK)
        self.assertEqual(get_platform("HR"), HACKERRANK)
        self.assertIsNone(get_platform("unknown_platform"))


class TestContest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 4, 15, 12, 0, 0, tzinfo=timezone.utc)

    def test_contest_creation_and_normalization(self):
        # Platform as string
        c = Contest(
            id="cf_123",
            platform="codeforces",
            name="Round 123",
            url="https://codeforces.com/contest/123",
            start_time=self.now + timedelta(hours=2),
            end_time=self.now + timedelta(hours=4),
            duration_seconds=0,  # Should auto-compute
            status="UPCOMING",
        )
        self.assertEqual(c.platform, CODEFORCES)
        self.assertEqual(c.duration_seconds, 7200)
        self.assertEqual(c.status, ContestStatus.UPCOMING)

    def test_contest_starts_in_str(self):
        # 1. Starts in 2 days and 3 hours
        c_future = Contest(
            id="c1",
            platform=CODEFORCES,
            name="Future Round",
            url="https://example.com",
            start_time=self.now + timedelta(days=2, hours=3, minutes=10),
            end_time=self.now + timedelta(days=2, hours=5, minutes=10),
            duration_seconds=7200,
        )
        self.assertEqual(c_future.starts_in_str(now=self.now), "in 2d 3h")

        # 2. Starts in 3 hours 15 mins
        c_today = Contest(
            id="c2",
            platform=LEETCODE,
            name="Weekly Contest",
            url="https://example.com",
            start_time=self.now + timedelta(hours=3, minutes=15),
            end_time=self.now + timedelta(hours=4, minutes=45),
            duration_seconds=5400,
        )
        self.assertEqual(c_today.starts_in_str(now=self.now), "in 3h 15m")

        # 3. Starts in 42 mins
        c_soon = Contest(
            id="c3",
            platform=ATCODER,
            name="Beginner Contest",
            url="https://example.com",
            start_time=self.now + timedelta(minutes=42),
            end_time=self.now + timedelta(minutes=142),
            duration_seconds=6000,
        )
        self.assertEqual(c_soon.starts_in_str(now=self.now), "in 42m")

        # 4. Starts in 30 seconds (< 1m)
        c_imminent = Contest(
            id="c4",
            platform=CODECHEF,
            name="Starters",
            url="https://example.com",
            start_time=self.now + timedelta(seconds=30),
            end_time=self.now + timedelta(hours=2),
            duration_seconds=7200,
        )
        self.assertEqual(c_imminent.starts_in_str(now=self.now), "in < 1m")

        # 5. Currently running
        c_running = Contest(
            id="c5",
            platform=HACKERRANK,
            name="HackFest",
            url="https://example.com",
            start_time=self.now - timedelta(minutes=30),
            end_time=self.now + timedelta(hours=1, minutes=30),
            duration_seconds=7200,
        )
        self.assertEqual(c_running.starts_in_str(now=self.now), "Running (ends in 1h 30m)")

        # 6. Finished
        c_ended = Contest(
            id="c6",
            platform=CODEFORCES,
            name="Past Round",
            url="https://example.com",
            start_time=self.now - timedelta(hours=5),
            end_time=self.now - timedelta(hours=3),
            duration_seconds=7200,
            status=ContestStatus.FINISHED,
        )
        self.assertEqual(c_ended.starts_in_str(now=self.now), "Ended")

    def test_duration_str(self):
        c1 = Contest("1", CODEFORCES, "T", "U", self.now, self.now, 7200)
        self.assertEqual(c1.duration_str(), "2h")

        c2 = Contest("2", CODEFORCES, "T", "U", self.now, self.now, 9000)
        self.assertEqual(c2.duration_str(), "2h 30m")

        c3 = Contest("3", CODEFORCES, "T", "U", self.now, self.now, 86400)
        self.assertEqual(c3.duration_str(), "1d")

        c4 = Contest("4", CODEFORCES, "T", "U", self.now, self.now, 100800)
        self.assertEqual(c4.duration_str(), "1d 4h")

        c5 = Contest("5", CODEFORCES, "T", "U", self.now, self.now, 2700)
        self.assertEqual(c5.duration_str(), "45m")

        c6 = Contest("6", CODEFORCES, "T", "U", self.now, self.now, 45)
        self.assertEqual(c6.duration_str(), "45s")

    def test_dict_serialization_roundtrip(self):
        c = Contest(
            id="cf_1900",
            platform=CODEFORCES,
            name="Codeforces Round 1900",
            url="https://codeforces.com/contest/1900",
            start_time=self.now + timedelta(hours=1),
            end_time=self.now + timedelta(hours=3),
            duration_seconds=7200,
            status=ContestStatus.UPCOMING,
            is_favorite=True,
            description="Div 2 round",
        )

        d = c.to_dict()
        self.assertEqual(d["id"], "cf_1900")
        self.assertEqual(d["is_favorite"], True)
        self.assertEqual(d["platform"]["id"], "codeforces")

        restored = Contest.from_dict(d)
        self.assertEqual(restored.id, c.id)
        self.assertEqual(restored.platform, c.platform)
        self.assertEqual(restored.name, c.name)
        self.assertEqual(restored.url, c.url)
        self.assertEqual(restored.start_time, c.start_time)
        self.assertEqual(restored.end_time, c.end_time)
        self.assertEqual(restored.duration_seconds, c.duration_seconds)
        self.assertEqual(restored.status, c.status)
        self.assertEqual(restored.is_favorite, True)
        self.assertEqual(restored.description, "Div 2 round")

    def test_update_status(self):
        c = Contest(
            id="test",
            platform=LEETCODE,
            name="Contest",
            url="",
            start_time=self.now + timedelta(hours=1),
            end_time=self.now + timedelta(hours=2),
            duration_seconds=3600,
        )
        self.assertEqual(c.update_status(self.now), ContestStatus.UPCOMING)
        self.assertEqual(c.update_status(self.now + timedelta(hours=1, minutes=10)), ContestStatus.RUNNING)
        self.assertEqual(c.update_status(self.now + timedelta(hours=3)), ContestStatus.FINISHED)


if __name__ == "__main__":
    unittest.main()
