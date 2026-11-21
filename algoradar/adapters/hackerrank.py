"""AlgoRadar HackerRank Adapter.

Fetches contests from HackerRank API with Kontests fallback.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

from algoradar.adapters.base import BaseAdapter
from algoradar.models import Contest, ContestStatus, HACKERRANK


logger = logging.getLogger("algoradar.adapters.hackerrank")


class HackerRankAdapter(BaseAdapter):
    """Adapter for HackerRank contests."""

    API_URL = "https://www.hackerrank.com/rest/contests/upcoming?limit=20"
    KONTESTS_URL = "https://kontests.net/api/v1/hacker_rank"

    def __init__(self, timeout: int = 12) -> None:
        super().__init__(platform=HACKERRANK, timeout=timeout)

    def fetch_contests(self, include_finished: bool = False) -> List[Contest]:
        """Fetch HackerRank contests."""
        # 1. Try official API
        contests = self._fetch_from_official_api(include_finished)
        if contests:
            return contests

        # 2. Try Kontests fallback
        contests = self._fetch_from_kontests(include_finished)
        return contests

    def _fetch_from_official_api(self, include_finished: bool) -> List[Contest]:
        """Fetch from HackerRank REST endpoint."""
        headers = {
            "Accept": "application/json",
        }
        data = self.safe_request(self.API_URL, headers=headers)
        if not isinstance(data, dict):
            return []

        models = data.get("models")
        if not isinstance(models, list):
            return []

        contests: List[Contest] = []
        now = datetime.now(timezone.utc)

        for item in models:
            try:
                slug = item.get("slug")
                name = item.get("name")
                start_sec = item.get("epoch_starttime")
                end_sec = item.get("epoch_endtime")

                if not slug or not name or not start_sec:
                    continue

                start_time = datetime.fromtimestamp(start_sec, tz=timezone.utc)
                if end_sec:
                    end_time = datetime.fromtimestamp(end_sec, tz=timezone.utc)
                else:
                    end_time = start_time + timedelta(hours=2)

                duration_sec = int((end_time - start_time).total_seconds())
                status = self.compute_status(start_time, end_time, now)

                if not include_finished and status == ContestStatus.FINISHED:
                    continue

                contests.append(
                    Contest(
                        id=f"hackerrank_{slug}",
                        platform=self.platform,
                        name=name.strip(),
                        url=f"https://www.hackerrank.com/contests/{slug}",
                        start_time=start_time,
                        end_time=end_time,
                        duration_seconds=duration_sec,
                        status=status,
                        description=str(item.get("description", "")),
                        raw_data=item,
                    )
                )
            except Exception as e:
                logger.debug("[HackerRank] Error parsing item: %s", e)
                continue

        contests.sort(key=lambda c: c.start_time)
        return contests

    def _fetch_from_kontests(self, include_finished: bool) -> List[Contest]:
        """Fetch HackerRank contests from Kontests fallback."""
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
                duration_sec = int(float(item.get("duration", 7200)))

                if not name or not start_str or not end_str:
                    continue

                start_time = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                end_time = datetime.fromisoformat(end_str.replace("Z", "+00:00"))

                slug_match = re.search(r"/contests/([a-zA-Z0-9_\-]+)", url)
                slug = slug_match.group(1) if slug_match else re.sub(r"\W+", "_", name.lower())

                status = self.compute_status(start_time, end_time, now)
                if not include_finished and status == ContestStatus.FINISHED:
                    continue

                contests.append(
                    Contest(
                        id=f"hackerrank_{slug}",
                        platform=self.platform,
                        name=name.strip(),
                        url=url if url.startswith("http") else f"https://www.hackerrank.com/contests/{slug}",
                        start_time=start_time,
                        end_time=end_time,
                        duration_seconds=duration_sec,
                        status=status,
                        raw_data=item,
                    )
                )
            except Exception as e:
                logger.debug("[HackerRank] Error parsing Kontests item: %s", e)
                continue

        contests.sort(key=lambda c: c.start_time)
        return contests
