"""AlgoRadar Codeforces Adapter.

Fetches and parses contests from the official Codeforces API:
https://codeforces.com/api/contest.list
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

from algoradar.adapters.base import BaseAdapter
from algoradar.models import CODEFORCES, Contest, ContestStatus


logger = logging.getLogger("algoradar.adapters.codeforces")


class CodeforcesAdapter(BaseAdapter):
    """Adapter for Codeforces contest list."""

    API_URL = "https://codeforces.com/api/contest.list?gym=false"

    def __init__(self, timeout: int = 12) -> None:
        super().__init__(platform=CODEFORCES, timeout=timeout)

    def fetch_contests(self, include_finished: bool = False) -> List[Contest]:
        """Fetch and parse contests from Codeforces.

        Args:
            include_finished: Whether to include finished contests.

        Returns:
            List of Contest objects.
        """
        response = self.safe_request(self.API_URL)
        if not response or not isinstance(response, dict):
            logger.warning("[Codeforces] Failed to fetch or invalid JSON response.")
            return []

        if response.get("status") != "OK":
            logger.warning("[Codeforces] API returned status != OK: %s", response.get("comment"))
            return []

        results = response.get("result", [])
        contests: List[Contest] = []
        now = datetime.now(timezone.utc)

        for item in results:
            try:
                contest = self._parse_contest_item(item, now)
                if contest is None:
                    continue

                if not include_finished and contest.status == ContestStatus.FINISHED:
                    continue

                contests.append(contest)
            except Exception as e:
                logger.debug("[Codeforces] Error parsing contest item %s: %s", item.get("id"), e)
                continue

        # Sort chronologically by start_time
        contests.sort(key=lambda c: c.start_time)
        return contests

    def _parse_contest_item(
        self, item: dict[str, Any], now: datetime
    ) -> Optional[Contest]:
        """Parse a single contest dict from Codeforces API."""
        contest_id = item.get("id")
        name = item.get("name")
        duration_seconds = int(item.get("durationSeconds", 0))
        start_seconds = item.get("startTimeSeconds")

        if not contest_id or not name:
            return None

        # Some contests on CF don't have startTimeSeconds set yet (tentative)
        if start_seconds is None or start_seconds <= 0:
            rel_sec = item.get("relativeTimeSeconds")
            if rel_sec is not None and rel_sec < 0:
                start_time = now + timedelta(seconds=abs(rel_sec))
            else:
                return None
        else:
            start_time = datetime.fromtimestamp(start_seconds, tz=timezone.utc)

        end_time = start_time + timedelta(seconds=duration_seconds)

        phase = str(item.get("phase", "")).upper()
        if phase == "BEFORE":
            status = ContestStatus.UPCOMING
        elif phase in ("CODING", "PENDING_SYSTEM_TEST", "SYSTEM_TEST"):
            status = ContestStatus.RUNNING
        elif phase == "FINISHED":
            status = ContestStatus.FINISHED
        else:
            status = self.compute_status(start_time, end_time, now)

        url = f"https://codeforces.com/contest/{contest_id}"

        return Contest(
            id=f"codeforces_{contest_id}",
            platform=self.platform,
            name=name.strip(),
            url=url,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration_seconds,
            status=status,
            description=f"Type: {item.get('type', 'CF')} | Phase: {phase}",
            raw_data=item,
        )
