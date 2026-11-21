"""Tests for AlgoRadar Command-Line Interface."""

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from algoradar.cli import build_parser, main
from algoradar.models import CODEFORCES, LEETCODE, Contest, ContestStatus
from algoradar.storage import Storage


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.parser = build_parser()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_algoradar.db"
        self.storage = Storage(db_path=self.db_path)

        # Seed sample contest
        now = datetime.now(timezone.utc)
        self.contest1 = Contest(
            id="cf_sample",
            platform=CODEFORCES,
            name="Codeforces Sample Round",
            url="https://codeforces.com/contest/1000",
            start_time=now + timedelta(hours=5),
            end_time=now + timedelta(hours=7),
            duration_seconds=7200,
        )
        self.storage.save_contests([self.contest1])

    def tearDown(self):
        self.storage.close()
        self.temp_dir.cleanup()

    def test_parser_subcommands(self):
        # Test command parsing
        args_list = self.parser.parse_args(["list", "--platform", "CF", "--limit", "5"])
        self.assertEqual(args_list.command, "list")
        self.assertEqual(args_list.platform, "CF")
        self.assertEqual(args_list.limit, 5)

        args_now = self.parser.parse_args(["now"])
        self.assertEqual(args_now.command, "now")

        args_sync = self.parser.parse_args(["sync", "--timeout", "10"])
        self.assertEqual(args_sync.command, "sync")
        self.assertEqual(args_sync.timeout, 10)

        args_export = self.parser.parse_args(["export", "--format", "ics", "--output", "test.ics"])
        self.assertEqual(args_export.command, "export")
        self.assertEqual(args_export.format, "ics")
        self.assertEqual(args_export.output, "test.ics")

        args_platforms = self.parser.parse_args(["platforms"])
        self.assertEqual(args_platforms.command, "platforms")

        args_stats = self.parser.parse_args(["stats"])
        self.assertEqual(args_stats.command, "stats")

    def test_cli_platforms_command(self):
        exit_code = main(["platforms"])
        self.assertEqual(exit_code, 0)

    @patch("algoradar.cli.Storage")
    def test_cli_stats_command(self, mock_storage_cls):
        mock_storage_cls.return_value = self.storage
        exit_code = main(["stats"])
        self.assertEqual(exit_code, 0)

    @patch("algoradar.cli.Storage")
    def test_cli_list_command(self, mock_storage_cls):
        mock_storage_cls.return_value = self.storage
        exit_code = main(["list", "--limit", "5"])
        self.assertEqual(exit_code, 0)

    @patch("algoradar.cli.Storage")
    def test_cli_now_command(self, mock_storage_cls):
        mock_storage_cls.return_value = self.storage
        exit_code = main(["now"])
        self.assertEqual(exit_code, 0)

    @patch("algoradar.cli.Storage")
    def test_cli_export_command(self, mock_storage_cls):
        mock_storage_cls.return_value = self.storage
        out_ics = Path(self.temp_dir.name) / "out.ics"
        exit_code = main(["export", "--output", str(out_ics)])
        self.assertEqual(exit_code, 0)
        self.assertTrue(out_ics.exists())


if __name__ == "__main__":
    unittest.main()
