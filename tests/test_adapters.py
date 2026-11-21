"""Tests for AlgoRadar Adapters and Multi-Platform Aggregator."""

from datetime import datetime, timedelta, timezone
import json
import unittest
from unittest.mock import MagicMock, patch

from algoradar.adapters import (
    ADAPTER_REGISTRY,
    Aggregator,
    AtCoderAdapter,
    BaseAdapter,
    CodeChefAdapter,
    CodeforcesAdapter,
    HackerRankAdapter,
    LeetCodeAdapter,
    get_adapter,
    get_all_adapters,
    list_supported_platforms,
    register_adapter,
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


class DummyAdapter(BaseAdapter):
    def fetch_contests(self, include_finished: bool = False):
        return []


class TestBaseAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = DummyAdapter(platform=CODEFORCES, timeout=5)

    def test_safe_request_success_json(self):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"status": "OK", "result": []}).encode("utf-8")
        mock_response.headers = {}
        mock_response.__enter__.return_value = mock_response

        with patch("urllib.request.urlopen", return_value=mock_response):
            data = self.adapter.safe_request("https://fake-url.com")
            self.assertIsInstance(data, dict)
            self.assertEqual(data["status"], "OK")

    def test_safe_request_handles_network_error_gracefully(self):
        import urllib.error

        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
            data = self.adapter.safe_request("https://fake-url.com")
            self.assertIsNone(data)

    def test_safe_request_handles_http_error(self):
        import urllib.error

        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError("url", 404, "Not Found", {}, None)):
            data = self.adapter.safe_request("https://fake-url.com")
            self.assertIsNone(data)


class TestCodeforcesAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = CodeforcesAdapter()

    def test_codeforces_parse(self):
        now = datetime.now(timezone.utc)
        start_ts = int((now + timedelta(hours=2)).timestamp())
        mock_data = {
            "status": "OK",
            "result": [
                {
                    "id": 1950,
                    "name": "Codeforces Round 950 (Div. 3)",
                    "type": "CF",
                    "phase": "BEFORE",
                    "durationSeconds": 7200,
                    "startTimeSeconds": start_ts,
                },
                {
                    "id": 1949,
                    "name": "Codeforces Round 949 (Div. 2)",
                    "type": "CF",
                    "phase": "FINISHED",
                    "durationSeconds": 7200,
                    "startTimeSeconds": start_ts - 20000,
                },
            ],
        }

        with patch.object(self.adapter, "safe_request", return_value=mock_data):
            # Without finished
            contests = self.adapter.fetch_contests(include_finished=False)
            self.assertEqual(len(contests), 1)
            self.assertEqual(contests[0].id, "codeforces_1950")
            self.assertEqual(contests[0].status, ContestStatus.UPCOMING)
            self.assertEqual(contests[0].duration_seconds, 7200)

            # With finished
            contests_all = self.adapter.fetch_contests(include_finished=True)
            self.assertEqual(len(contests_all), 2)


class TestAtCoderAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = AtCoderAdapter()

    def test_atcoder_kenkoooo_parse(self):
        now = datetime.now(timezone.utc)
        start_ts = int((now + timedelta(hours=3)).timestamp())
        mock_kenkoooo = [
            {
                "id": "abc360",
                "title": "AtCoder Beginner Contest 360",
                "start_epoch_second": start_ts,
                "duration_second": 6000,
                "rate_change": " ~ 1999",
            }
        ]

        with patch.object(self.adapter, "safe_request", return_value=mock_kenkoooo):
            contests = self.adapter.fetch_contests()
            self.assertEqual(len(contests), 1)
            self.assertEqual(contests[0].id, "atcoder_abc360")
            self.assertEqual(contests[0].name, "AtCoder Beginner Contest 360")
            self.assertEqual(contests[0].duration_seconds, 6000)
            self.assertEqual(contests[0].status, ContestStatus.UPCOMING)

    def test_atcoder_kontests_fallback(self):
        now = datetime.now(timezone.utc)
        start_str = (now + timedelta(hours=4)).isoformat()
        end_str = (now + timedelta(hours=5, minutes=40)).isoformat()

        mock_kontests = [
            {
                "name": "AtCoder Regular Contest 180",
                "url": "https://atcoder.jp/contests/arc180",
                "start_time": start_str,
                "end_time": end_str,
                "duration": "6000.0",
                "site": "AtCoder",
            }
        ]

        # Kenkoooo returns None, Kontests returns data
        def mock_safe_request(url, **kwargs):
            if "kenkoooo" in url:
                return None
            return mock_kontests

        with patch.object(self.adapter, "safe_request", side_effect=mock_safe_request):
            contests = self.adapter.fetch_contests()
            self.assertEqual(len(contests), 1)
            self.assertEqual(contests[0].id, "atcoder_arc180")


class TestLeetCodeAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = LeetCodeAdapter()

    def test_leetcode_graphql_parse(self):
        now = datetime.now(timezone.utc)
        start_ts = int((now + timedelta(hours=6)).timestamp())
        mock_graphql = {
            "data": {
                "topTwoContests": [
                    {
                        "title": "Weekly Contest 405",
                        "titleSlug": "weekly-contest-405",
                        "startTime": start_ts,
                        "duration": 5400,
                        "isVirtual": False,
                    }
                ],
                "allContests": [],
            }
        }

        with patch.object(self.adapter, "safe_request", return_value=mock_graphql):
            contests = self.adapter.fetch_contests()
            self.assertEqual(len(contests), 1)
            self.assertEqual(contests[0].id, "leetcode_weekly-contest-405")
            self.assertEqual(contests[0].duration_seconds, 5400)
            self.assertEqual(contests[0].status, ContestStatus.UPCOMING)


class TestCodeChefAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = CodeChefAdapter()

    def test_codechef_api_parse(self):
        mock_codechef = {
            "status": "success",
            "future_contests": [
                {
                    "contest_code": "START160",
                    "contest_name": "Starters 160",
                    "contest_start_date_iso": "2026-05-01T20:00:00+05:30",
                    "contest_end_date_iso": "2026-05-01T22:00:00+05:30",
                    "contest_duration": "120",
                }
            ],
            "present_contests": [],
        }

        with patch.object(self.adapter, "safe_request", return_value=mock_codechef):
            contests = self.adapter.fetch_contests()
            self.assertEqual(len(contests), 1)
            self.assertEqual(contests[0].id, "codechef_start160")
            self.assertEqual(contests[0].name, "Starters 160")
            self.assertEqual(contests[0].duration_seconds, 7200)


class TestHackerRankAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = HackerRankAdapter()

    def test_hackerrank_api_parse(self):
        now = datetime.now(timezone.utc)
        start_ts = int((now + timedelta(hours=10)).timestamp())
        end_ts = start_ts + 7200
        mock_hr = {
            "models": [
                {
                    "id": 999,
                    "name": "HackerRank CodeFest",
                    "slug": "codefest-2026",
                    "epoch_starttime": start_ts,
                    "epoch_endtime": end_ts,
                    "description": "Annual challenge",
                }
            ]
        }

        with patch.object(self.adapter, "safe_request", return_value=mock_hr):
            contests = self.adapter.fetch_contests()
            self.assertEqual(len(contests), 1)
            self.assertEqual(contests[0].id, "hackerrank_codefest-2026")
            self.assertEqual(contests[0].name, "HackerRank CodeFest")


class TestAggregator(unittest.TestCase):
    def test_aggregator_concurrent_and_dedup(self):
        now = datetime.now(timezone.utc)

        ad1 = MagicMock(spec=BaseAdapter)
        ad1.platform = CODEFORCES
        ad1.fetch_contests.return_value = [
            Contest("cf_1", CODEFORCES, "CF Round 1", "u1", now + timedelta(hours=2), now + timedelta(hours=4), 7200),
        ]

        ad2 = MagicMock(spec=BaseAdapter)
        ad2.platform = LEETCODE
        ad2.fetch_contests.return_value = [
            Contest("lc_1", LEETCODE, "LC Biweekly 1", "u2", now + timedelta(hours=1), now + timedelta(hours=2, minutes=30), 5400),
        ]

        aggregator = Aggregator(adapters=[ad1, ad2])
        all_c = aggregator.fetch_all()

        self.assertEqual(len(all_c), 2)
        # Should be ordered chronologically (lc_1 at +1h then cf_1 at +2h)
        self.assertEqual(all_c[0].id, "lc_1")
        self.assertEqual(all_c[1].id, "cf_1")

    def test_aggregator_universal_fallback(self):
        # When an adapter fails and returns empty
        failing_adapter = MagicMock(spec=BaseAdapter)
        failing_adapter.platform = CODEFORCES
        failing_adapter.fetch_contests.return_value = []

        now = datetime.now(timezone.utc)
        mock_kontests_all = [
            {
                "name": "Codeforces Global Round 25",
                "url": "https://codeforces.com/contest/1951",
                "start_time": (now + timedelta(hours=5)).isoformat(),
                "end_time": (now + timedelta(hours=7)).isoformat(),
                "duration": "7200.0",
                "site": "Codeforces",
            }
        ]

        aggregator = Aggregator(adapters=[failing_adapter])
        with patch.object(aggregator, "_fetch_universal_fallback", return_value=[
            Contest("cf_fb", CODEFORCES, "Codeforces Global Round 25", "u", now + timedelta(hours=5), now + timedelta(hours=7), 7200)
        ]):
            contests = aggregator.fetch_all()
            self.assertEqual(len(contests), 1)
            self.assertEqual(contests[0].name, "Codeforces Global Round 25")


class TestAdapterRegistry(unittest.TestCase):
    def test_registry_lookup(self):
        cf_ad = get_adapter("codeforces")
        self.assertIsInstance(cf_ad, CodeforcesAdapter)

        lc_ad = get_adapter("LC")
        self.assertIsInstance(lc_ad, LeetCodeAdapter)

        ac_ad = get_adapter("atcoder")
        self.assertIsInstance(ac_ad, AtCoderAdapter)

        cc_ad = get_adapter("codechef")
        self.assertIsInstance(cc_ad, CodeChefAdapter)

        hr_ad = get_adapter("hackerrank")
        self.assertIsInstance(hr_ad, HackerRankAdapter)

        none_ad = get_adapter("nonexistent")
        self.assertIsNone(none_ad)

    def test_list_supported_platforms(self):
        plats = list_supported_platforms()
        self.assertIn("codeforces", plats)
        self.assertIn("leetcode", plats)
        self.assertIn("atcoder", plats)
        self.assertIn("codechef", plats)
        self.assertIn("hackerrank", plats)

    def test_get_all_adapters(self):
        adapters = get_all_adapters()
        self.assertGreaterEqual(len(adapters), 5)


if __name__ == "__main__":
    unittest.main()
