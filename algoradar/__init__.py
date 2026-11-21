"""AlgoRadar - Terminal Competitive Programming Contest Radar & Calendar Workstation.

A high-performance workstation for tracking, aggregating, and syncing competitive
programming contests from Codeforces, LeetCode, AtCoder, CodeChef, HackerRank, and more.
"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "AlgoRadar Team"

from algoradar.adapters import (
    Aggregator,
    BaseAdapter,
    get_adapter,
    get_all_adapters,
    list_supported_platforms,
)
from algoradar.calendar_sync import build_vevent, export_ics, generate_ics
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
from algoradar.storage import DEFAULT_DB_PATH, Storage


def main(argv=None) -> int:
    """CLI workstation entrypoint."""
    from algoradar.cli import main as _main

    return _main(argv)


__all__ = [
    "__version__",
    "__author__",
    "main",
    # Domain Models
    "Contest",
    "Platform",
    "ContestStatus",
    "get_platform",
    "CODEFORCES",
    "LEETCODE",
    "ATCODER",
    "CODECHEF",
    "HACKERRANK",
    # Storage
    "Storage",
    "DEFAULT_DB_PATH",
    # Adapters & Aggregation
    "BaseAdapter",
    "Aggregator",
    "get_adapter",
    "get_all_adapters",
    "list_supported_platforms",
    # Calendar Sync & Export
    "generate_ics",
    "export_ics",
    "build_vevent",
]
