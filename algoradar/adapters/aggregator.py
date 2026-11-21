"""AlgoRadar Multi-Platform Aggregator.

Provides concurrent fetching across all supported CP platforms, deduplication,
cross-platform sorting, and universal fallback integration.
"""

from __future__ import annotations

import concurrent.futures
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Type

from algoradar.adapters.atcoder import AtCoderAdapter
from algoradar.adapters.base import BaseAdapter
from algoradar.adapters.codechef import CodeChefAdapter
from algoradar.adapters.codeforces import CodeforcesAdapter
from algoradar.adapters.hackerrank import HackerRankAdapter
from algoradar.adapters.leetcode import LeetCodeAdapter
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


logger = logging.getLogger("algoradar.adapters.aggregator")


DEFAULT_ADAPTER_CLASSES: list[Type[BaseAdapter]] = [
    CodeforcesAdapter,
    LeetCodeAdapter,
    AtCoderAdapter,
    CodeChefAdapter,
    HackerRankAdapter,
]


class Aggregator:
    """Multi-platform aggregator with concurrent fetching and fallback handling."""

    KONTESTS_ALL_URL = "https://kontests.net/api/v1/all"

    def __init__(
        self,
        adapters: Optional[List[BaseAdapter]] = None,
        max_workers: int = 5,
        timeout: int = 15,
    ) -> None:
        """Initialize aggregator with list of adapters or standard defaults."""
        self.adapters: List[BaseAdapter] = (
            adapters if adapters is not None else [cls() for cls in DEFAULT_ADAPTER_CLASSES]
        )
        self.max_workers = max_workers
        self.timeout = timeout
        self.last_results: Dict[str, List[Contest]] = {}
        self.last_errors: Dict[str, str] = {}

    def get_adapter_by_platform(self, platform_id: str) -> Optional[BaseAdapter]:
        """Find registered adapter by platform ID or short code."""
        plat_clean = platform_id.strip().lower()
        for adapter in self.adapters:
            if (
                adapter.platform.id.lower() == plat_clean
                or adapter.platform.short_code.lower() == plat_clean
            ):
                return adapter
        return None

    def fetch_all(
        self,
        platform_ids: Optional[List[str]] = None,
        include_finished: bool = False,
    ) -> List[Contest]:
        """Concurrently fetch contests from all or specified platforms.

        Args:
            platform_ids: Optional list of platform IDs to filter (e.g. ['codeforces', 'leetcode']).
            include_finished: Whether to include finished contests.

        Returns:
            Deduplicated list of Contest objects sorted chronologically by start_time.
        """
        active_adapters: List[BaseAdapter] = []
        if platform_ids:
            normalized_ids = {p.strip().lower() for p in platform_ids}
            for adapter in self.adapters:
                if (
                    adapter.platform.id.lower() in normalized_ids
                    or adapter.platform.short_code.lower() in normalized_ids
                ):
                    active_adapters.append(adapter)
        else:
            active_adapters = list(self.adapters)

        if not active_adapters:
            return []

        all_contests: List[Contest] = []
        failed_platforms: Set[str] = set()

        def _run_adapter(adapter: BaseAdapter) -> tuple[str, List[Contest], Optional[str]]:
            try:
                results = adapter.fetch_contests(include_finished=include_finished)
                return adapter.platform.id, results, None
            except Exception as exc:
                logger.error("[Aggregator] %s failed: %s", adapter.platform.name, exc)
                return adapter.platform.id, [], str(exc)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_adapter = {
                executor.submit(_run_adapter, ad): ad for ad in active_adapters
            }
            for future in concurrent.futures.as_completed(future_to_adapter, timeout=self.timeout):
                ad = future_to_adapter[future]
                try:
                    pid, res, err = future.result()
                    self.last_results[pid] = res
                    if err:
                        self.last_errors[pid] = err
                        failed_platforms.add(pid)
                    elif not res:
                        failed_platforms.add(pid)
                    else:
                        all_contests.extend(res)
                except Exception as exc:
                    self.last_errors[ad.platform.id] = str(exc)
                    failed_platforms.add(ad.platform.id)

        # If any requested platforms produced 0 contests, attempt universal fallback
        if failed_platforms:
            fallback_contests = self._fetch_universal_fallback(
                target_platforms=failed_platforms,
                include_finished=include_finished,
            )
            all_contests.extend(fallback_contests)

        # Deduplicate and sort
        deduped = self._deduplicate_contests(all_contests)
        deduped.sort(key=lambda c: c.start_time)
        return deduped

    def fetch_platform(
        self, platform_id: str, include_finished: bool = False
    ) -> List[Contest]:
        """Fetch contests for a single platform."""
        results = self.fetch_all(platform_ids=[platform_id], include_finished=include_finished)
        return results

    def _fetch_universal_fallback(
        self, target_platforms: Set[str], include_finished: bool = False
    ) -> List[Contest]:
        """Query multi-platform Kontests API for platforms that failed to resolve."""
        logger.info("[Aggregator] Attempting universal fallback for: %s", target_platforms)
        # Use first adapter's safe_request helper
        helper = self.adapters[0] if self.adapters else BaseAdapter(platform=CODEFORCES)
        data = helper.safe_request(self.KONTESTS_ALL_URL)
        if not isinstance(data, list):
            return []

        site_to_platform: dict[str, Platform] = {
            "codeforces": CODEFORCES,
            "codeforces::gym": CODEFORCES,
            "leet_code": LEETCODE,
            "leetcode": LEETCODE,
            "at_coder": ATCODER,
            "atcoder": ATCODER,
            "code_chef": CODECHEF,
            "codechef": CODECHEF,
            "hacker_rank": HACKERRANK,
            "hackerrank": HACKERRANK,
        }

        contests: List[Contest] = []
        now = datetime.now(timezone.utc)

        for item in data:
            try:
                site = str(item.get("site", "")).lower().replace(" ", "_")
                plat = site_to_platform.get(site)
                if not plat or plat.id not in target_platforms:
                    continue

                name = item.get("name")
                url = item.get("url", "")
                start_str = item.get("start_time")
                end_str = item.get("end_time")
                duration_sec = int(float(item.get("duration", 7200)))

                if not name or not start_str or not end_str:
                    continue

                start_time = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                end_time = datetime.fromisoformat(end_str.replace("Z", "+00:00"))

                clean_name = re.sub(r"\W+", "_", name.lower()).strip("_")
                cid = f"{plat.id}_{clean_name}"

                status = helper.compute_status(start_time, end_time, now)
                if not include_finished and status == ContestStatus.FINISHED:
                    continue

                contests.append(
                    Contest(
                        id=cid,
                        platform=plat,
                        name=name.strip(),
                        url=url,
                        start_time=start_time,
                        end_time=end_time,
                        duration_seconds=duration_sec,
                        status=status,
                        raw_data=item,
                    )
                )
            except Exception as e:
                logger.debug("[Aggregator] Fallback parse item error: %s", e)
                continue

        return contests

    def _deduplicate_contests(self, contests: List[Contest]) -> List[Contest]:
        """Deduplicate contests across multiple sources by ID or normalized name."""
        seen_ids: Set[str] = set()
        seen_signatures: Set[str] = set()
        unique_contests: List[Contest] = []

        for c in contests:
            if c.id in seen_ids:
                continue

            # Create a signature: (platform.id, simplified name, start_time_epoch_hours)
            norm_name = re.sub(r"[^a-z0-9]", "", c.name.lower())
            start_hour = int(c.start_time.timestamp() // 3600)
            signature = f"{c.platform.id}_{norm_name}_{start_hour}"

            if signature in seen_signatures:
                continue

            seen_ids.add(c.id)
            seen_signatures.add(signature)
            unique_contests.append(c)

        return unique_contests
