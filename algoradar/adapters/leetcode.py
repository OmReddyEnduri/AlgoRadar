"""AlgoRadar LeetCode Adapter.

Fetches upcoming and active contests from LeetCode GraphQL API with Kontests fallback.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

from algoradar.adapters.base import BaseAdapter
from algoradar.models import Contest, ContestStatus, LEETCODE


logger = logging.getLogger("algoradar.adapters.leetcode")


class LeetCodeAdapter(BaseAdapter):
    """Adapter for LeetCode contests via GraphQL with fallback."""

    GRAPHQL_URL = "https://leetcode.com/graphql"
    KONTESTS_URL = "https://kontests.net/api/v1/leet_code"

    GRAPHQL_QUERY = """
    query getContests {
      topTwoContests {
        title
        titleSlug
        startTime
        duration
        originStartTime
        isVirtual
      }
      allContests {
        title
        titleSlug
        startTime
        duration
        originStartTime
        isVirtual
      }
    }
    """

    def __init__(self, timeout: int = 12) -> None:
        super().__init__(platform=LEETCODE, timeout=timeout)

    def fetch_contests(self, include_finished: bool = False) -> List[Contest]:
        """Fetch LeetCode contests trying GraphQL then Kontests fallback."""
        # 1. Try GraphQL API
        contests = self._fetch_from_graphql(include_finished)
        if contests:
            return contests

        # 2. Try Kontests fallback
        contests = self._fetch_from_kontests(include_finished)
        return contests

    def _fetch_from_graphql(self, include_finished: bool) -> List[Contest]:
        """Fetch contests using LeetCode's official GraphQL endpoint."""
        payload = {"query": self.GRAPHQL_QUERY, "variables": {}}
        headers = {
            "Content-Type": "application/json",
            "Referer": "https://leetcode.com/contest/",
            "Origin": "https://leetcode.com",
        }

        response = self.safe_request(
            self.GRAPHQL_URL,
            method="POST",
            json_data=payload,
            headers=headers,
        )

        if not isinstance(response, dict) or "data" not in response:
            return []

        data = response["data"]
        raw_contests: list[dict[str, Any]] = []

        # topTwoContests contains the most immediate upcoming contests
        top_two = data.get("topTwoContests") or []
        if isinstance(top_two, list):
            raw_contests.extend(top_two)

        # allContests contains recent and upcoming
        all_c = data.get("allContests") or []
        if isinstance(all_c, list):
            for item in all_c:
                if not any(item.get("titleSlug") == x.get("titleSlug") for x in raw_contests):
                    raw_contests.append(item)

        contests: List[Contest] = []
        now = datetime.now(timezone.utc)

        for item in raw_contests:
            try:
                if item.get("isVirtual", False):
                    continue

                slug = item.get("titleSlug")
                title = item.get("title")
                start_sec = item.get("startTime")
                duration_sec = int(item.get("duration", 5400))

                if not slug or not title or not start_sec:
                    continue

                start_time = datetime.fromtimestamp(start_sec, tz=timezone.utc)
                end_time = start_time + timedelta(seconds=duration_sec)

                status = self.compute_status(start_time, end_time, now)
                if not include_finished and status == ContestStatus.FINISHED:
                    continue

                contests.append(
                    Contest(
                        id=f"leetcode_{slug}",
                        platform=self.platform,
                        name=title.strip(),
                        url=f"https://leetcode.com/contest/{slug}",
                        start_time=start_time,
                        end_time=end_time,
                        duration_seconds=duration_sec,
                        status=status,
                        raw_data=item,
                    )
                )
            except Exception as e:
                logger.debug("[LeetCode] Error parsing GraphQL contest item: %s", e)
                continue

        contests.sort(key=lambda c: c.start_time)
        return contests

    def _fetch_from_kontests(self, include_finished: bool) -> List[Contest]:
        """Fetch LeetCode contests from Kontests fallback."""
        data = self.safe_request(self.KONTESTS_URL)
        if not isinstance(data, list):
            return []

        contests: List[Contest] = []
        now = datetime.now(timezone.utc)

        for item in data:
            try:
                name = item.get("name")
                url = item.get("url", "")
                start_str = item.get("start_time")
                end_str = item.get("end_time")
                duration_sec = int(float(item.get("duration", 5400)))

                if not name or not start_str or not end_str:
                    continue

                start_time = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                end_time = datetime.fromisoformat(end_str.replace("Z", "+00:00"))

                slug_match = re.search(r"/contest/([a-zA-Z0-9_\-]+)", url)
                slug = slug_match.group(1) if slug_match else re.sub(r"\W+", "-", name.lower()).strip("-")

                status = self.compute_status(start_time, end_time, now)
                if not include_finished and status == ContestStatus.FINISHED:
                    continue

                contests.append(
                    Contest(
                        id=f"leetcode_{slug}",
                        platform=self.platform,
                        name=name.strip(),
                        url=url if url.startswith("http") else f"https://leetcode.com/contest/{slug}",
                        start_time=start_time,
                        end_time=end_time,
                        duration_seconds=duration_sec,
                        status=status,
                        raw_data=item,
                    )
                )
            except Exception as e:
                logger.debug("[LeetCode] Error parsing Kontests fallback item: %s", e)
                continue

        contests.sort(key=lambda c: c.start_time)
        return contests
