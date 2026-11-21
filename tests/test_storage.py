"""Tests for AlgoRadar SQLite Storage Layer."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import tempfile
import unittest

from algoradar.models import (
    ATCODER,
    CODECHEF,
    CODEFORCES,
    LEETCODE,
    Contest,
    ContestStatus,
)
from algoradar.storage import Storage


class TestStorage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_algoradar.db"
        self.storage = Storage(db_path=self.db_path)
        self.now = datetime.now(timezone.utc)

    def tearDown(self):
        self.storage.close()
        self.temp_dir.cleanup()

    def test_wal_mode_enabled(self):
        conn = self.storage._get_connection()
        cursor = conn.execute("PRAGMA journal_mode;")
        mode = cursor.fetchone()[0]
        self.assertEqual(mode.lower(), "wal")

    def test_save_and_retrieve_upcoming(self):
        c1 = Contest(
            id="cf_101",
            platform=CODEFORCES,
            name="CF Round 101",
            url="https://codeforces.com/contest/101",
            start_time=self.now + timedelta(hours=5),
            end_time=self.now + timedelta(hours=7),
            duration_seconds=7200,
            status=ContestStatus.UPCOMING,
        )
        c2 = Contest(
            id="lc_201",
            platform=LEETCODE,
            name="LC Weekly 201",
            url="https://leetcode.com/contest/201",
            start_time=self.now + timedelta(hours=2),
            end_time=self.now + timedelta(hours=3, minutes=30),
            duration_seconds=5400,
            status=ContestStatus.UPCOMING,
        )

        saved = self.storage.save_contests([c1, c2])
        self.assertEqual(saved, 2)

        upcoming = self.storage.get_upcoming()
        self.assertEqual(len(upcoming), 2)
        # Should be ordered by start_time ASC (c2 then c1)
        self.assertEqual(upcoming[0].id, "lc_201")
        self.assertEqual(upcoming[1].id, "cf_101")

    def test_get_running_and_history(self):
        c_running = Contest(
            id="ac_301",
            platform=ATCODER,
            name="ABC 301",
            url="https://atcoder.jp/contests/301",
            start_time=self.now - timedelta(minutes=30),
            end_time=self.now + timedelta(minutes=70),
            duration_seconds=6000,
            status=ContestStatus.RUNNING,
        )
        c_past = Contest(
            id="cc_401",
            platform=CODECHEF,
            name="Starters 401",
            url="https://codechef.com/401",
            start_time=self.now - timedelta(days=2),
            end_time=self.now - timedelta(days=2, hours=-2),
            duration_seconds=7200,
            status=ContestStatus.FINISHED,
        )

        self.storage.save_contests([c_running, c_past])

        running = self.storage.get_running()
        self.assertEqual(len(running), 1)
        self.assertEqual(running[0].id, "ac_301")

        history = self.storage.get_history(limit=10)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].id, "cc_401")

    def test_get_by_platform(self):
        c_cf = Contest("cf_1", CODEFORCES, "CF 1", "url", self.now + timedelta(hours=1), self.now + timedelta(hours=3), 7200)
        c_lc = Contest("lc_1", LEETCODE, "LC 1", "url", self.now + timedelta(hours=1), self.now + timedelta(hours=3), 5400)
        self.storage.save_contests([c_cf, c_lc])

        by_id = self.storage.get_by_platform("codeforces")
        self.assertEqual(len(by_id), 1)
        self.assertEqual(by_id[0].id, "cf_1")

        by_code = self.storage.get_by_platform("LC")
        self.assertEqual(len(by_code), 1)
        self.assertEqual(by_code[0].id, "lc_1")

    def test_toggle_favorite_and_preservation_on_save(self):
        c = Contest("cf_fav", CODEFORCES, "CF Fav", "url", self.now + timedelta(hours=1), self.now + timedelta(hours=3), 7200)
        self.storage.save_contests([c])

        # Initially not favorite
        cont = self.storage.get_contest("cf_fav")
        self.assertIsNotNone(cont)
        self.assertFalse(cont.is_favorite)

        # Toggle to True
        is_fav = self.storage.toggle_favorite("cf_fav")
        self.assertTrue(is_fav)

        favorites = self.storage.get_favorites()
        self.assertEqual(len(favorites), 1)
        self.assertEqual(favorites[0].id, "cf_fav")

        # Crucial test: re-saving contest with is_favorite=False MUST NOT overwrite stored is_favorite=True!
        c_updated = Contest("cf_fav", CODEFORCES, "CF Fav Updated Name", "url", self.now + timedelta(hours=1), self.now + timedelta(hours=3), 7200, is_favorite=False)
        self.storage.save_contests([c_updated])

        refetched = self.storage.get_contest("cf_fav")
        self.assertTrue(refetched.is_favorite)
        self.assertEqual(refetched.name, "CF Fav Updated Name")

        # Toggle back to False
        is_fav_back = self.storage.toggle_favorite("cf_fav")
        self.assertFalse(is_fav_back)

    def test_delete_and_clear_all(self):
        c1 = Contest("c1", CODEFORCES, "C1", "url", self.now, self.now, 3600)
        c2 = Contest("c2", LEETCODE, "C2", "url", self.now, self.now, 3600)
        self.storage.save_contests([c1, c2])

        self.assertTrue(self.storage.delete_contest("c1"))
        self.assertFalse(self.storage.delete_contest("non_existent"))

        self.assertEqual(len(self.storage.get_upcoming()), 1)

        cleared = self.storage.clear_all()
        self.assertEqual(cleared, 1)
        self.assertEqual(len(self.storage.get_upcoming()), 0)

    def test_context_manager(self):
        with Storage(db_path=self.db_path) as s:
            s.save_contests([Contest("c3", CODEFORCES, "C3", "u", self.now, self.now, 3600)])
            self.assertIsNotNone(s.get_contest("c3"))


if __name__ == "__main__":
    unittest.main()
