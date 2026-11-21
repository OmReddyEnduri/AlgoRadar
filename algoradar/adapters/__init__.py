"""AlgoRadar Adapters Package & Registry.

Exposes platform adapters and registry lookup for Codeforces, LeetCode, AtCoder,
CodeChef, HackerRank, and Multi-Platform Aggregation.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Type

from algoradar.adapters.aggregator import Aggregator
from algoradar.adapters.atcoder import AtCoderAdapter
from algoradar.adapters.base import BaseAdapter
from algoradar.adapters.codechef import CodeChefAdapter
from algoradar.adapters.codeforces import CodeforcesAdapter
from algoradar.adapters.hackerrank import HackerRankAdapter
from algoradar.adapters.leetcode import LeetCodeAdapter


ADAPTER_REGISTRY: Dict[str, Type[BaseAdapter]] = {
    "codeforces": CodeforcesAdapter,
    "cf": CodeforcesAdapter,
    "leetcode": LeetCodeAdapter,
    "lc": LeetCodeAdapter,
    "atcoder": AtCoderAdapter,
    "ac": AtCoderAdapter,
    "codechef": CodeChefAdapter,
    "cc": CodeChefAdapter,
    "hackerrank": HackerRankAdapter,
    "hr": HackerRankAdapter,
}


def register_adapter(identifier: str, adapter_cls: Type[BaseAdapter]) -> None:
    """Register or override an adapter class in the registry."""
    key = str(identifier).strip().lower()
    ADAPTER_REGISTRY[key] = adapter_cls


def get_adapter(platform_id: str, timeout: int = 12) -> Optional[BaseAdapter]:
    """Retrieve an initialized adapter instance for the specified platform."""
    key = str(platform_id).strip().lower()
    cls = ADAPTER_REGISTRY.get(key)
    if cls is not None:
        return cls(timeout=timeout)
    return None


def get_all_adapters(timeout: int = 12) -> List[BaseAdapter]:
    """Return initialized instances of all unique registered platform adapters."""
    unique_classes = set(ADAPTER_REGISTRY.values())
    return [cls(timeout=timeout) for cls in unique_classes]


def list_supported_platforms() -> List[str]:
    """Return a list of canonical supported platform IDs."""
    return ["codeforces", "leetcode", "atcoder", "codechef", "hackerrank"]


__all__ = [
    "BaseAdapter",
    "CodeforcesAdapter",
    "LeetCodeAdapter",
    "AtCoderAdapter",
    "CodeChefAdapter",
    "HackerRankAdapter",
    "Aggregator",
    "ADAPTER_REGISTRY",
    "register_adapter",
    "get_adapter",
    "get_all_adapters",
    "list_supported_platforms",
]
