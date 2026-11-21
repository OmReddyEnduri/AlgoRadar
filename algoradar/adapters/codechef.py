"""AlgoRadar CodeChef Adapter.

Fetches contests from CodeChef official API with Kontests fallback.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

from algoradar.adapters.base import BaseAdapter
from algoradar.models import CODECHEF, Contest, ContestStatus


logger = logging.getLogger("algoradar.adapters.codechef")


class CodeChefAdapter(BaseAdapter):
    """Adapter for CodeChef contests."""

    API_URL = "https://www.codechef.com/api/list/contests/all?sort_by=START&sorting_order=asc&offset=0&mode=all"
    KONTESTS_URL = "https://kontests.net/api/v1/code_chef"

    def __init__(self, timeout: int = 12) -> None:
        super().__init__(platform=CODECHEF, timeout=timeout)

    def fetch_contests(self, include_finished: bool = False) -> List[Contest]:
        """Fetch CodeChef contests using official API with fallback."""
        # 1. Try official API
        contests = self._fetch_from_official_api(include_finished)
        if contests:
            return contests

        # 2. Try Kontests fallback
        contests = self._fetch_from_kontests(include_finished)
        return contests

    def _parse_codechef_date(self, date_iso: Optional[str], date_str: Optional[str]) -> Optional[datetime]:
        """Parse CodeChef datetime which may be ISO or formatted string in IST."""
        if date_iso:
            try:
                # Handle ISO string with offset e.g. '2026-04-10T20:00:00+05:30'
                clean_iso = date_iso.replace("Z", "+00:00")
                dt = datetime.fromisoformat(clean_iso)
                return dt.astimezone(timezone.utc)
            except Exception:
                pass

        if date_str:
            # CodeChef often returns '10 Apr 2026  20:00:00' in IST (UTC+5:30)
            clean_str = re.sub(r"\s+", " ", date_str).strip()
            for fmt in ("%d %b %Y %H:%M:%S", "%d %B %Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                try:
                    parsed = datetime.strptime(clean_str, fmt)
                    # CodeChef server time is IST (UTC+5:30)
                    ist = timezone(timedelta(hours=5, minutes=30))
                    return parsed.replace(tzinfo=ist).astimezone(timezone.utc)
                except ValueError:
                    continue

        return None

    def _fetch_from_official_api(self, include_finished: bool) -> List[Contest]:
        """Fetch from official CodeChef contests API."""
        headers = {
            "Accept": "application/json",
            "Referer": "https://www.codechef.com/contests",
        }
        data = self.safe_request(self.API_URL, headers=headers)
        if not isinstance(data, dict):
            return []

        status_val = data.get("status")
        if status_val not in ("success", "OK", True):
            return []

        contests: List[Contest] = []
        now = datetime.now(timezone.utc)

        # Process future and present contests
        categories = [
            ("future_contests", ContestStatus.UPCOMING),
            ("present_contests", ContestStatus.RUNNING),
        ]
        if include_finished:
            categories.append(("past_contests", ContestStatus.FINISHED))

        for cat_key, default_status in categories:
            items = data.get(cat_key, [])
            if not isinstance(items, list):
                continue

            for item in items:
                try:
                    code = item.get("contest_code")
                    name = item.get("contest_name")
                    if not code or not name:
                        continue

                    start_time = self._parse_codechef_date(
                        item.get("contest_start_date_iso"),
                        item.get("contest_start_date"),
                    )
                    end_time = self._parse_codechef_date(
                        item.get("contest_end_date_iso"),
                        item.get("contest_end_date"),
                    )

                    if not start_time:
                        continue

                    # Duration parsing: CodeChef often gives minutes in string (e.g. "120")
                    duration_sec = 0
                    dur_val = item.get("contest_duration")
                    if dur_val is not None:
                        try:
                            # If value is numeric, check if minutes or seconds
                            val_num = int(float(str(dur_val).strip()))
                            # If end_time is available, use end_time - start_time
                            if end_time and end_time > start_time:
                                duration_sec = int((end_time - start_time).total_seconds())
                            else:
                                duration_sec = val_num * 60  # assume minutes
                        except Exception:
                            pass

                    if end_time is None and duration_sec > 0:
                        end_time = start_time + timedelta(seconds=duration_sec)
                    elif end_time is None:
                        end_time = start_time + timedelta(hours=2)
                        duration_sec = 7200

                    if duration_sec <= 0:
                        duration_sec = int((end_time - start_time).total_seconds())

                    status = self.compute_status(start_time, end_time, now)

                    contests.append(
                        Contest(
                            id=f"codechef_{code.lower()}",
                            platform=self.platform,
                            name=name.strip(),
                            url=f"https://www.codechef.com/{code}",
                            start_time=start_time,
                            end_time=end_time,
                            duration_seconds=duration_sec,
                            status=status,
                            raw_data=item,
                        )
                    )
                except Exception as e:
                    logger.debug("[CodeChef] Error parsing item: %s", e)
                    continue

        contests.sort(key=lambda c: c.start_time)
        return contests

    def _fetch_from_kontests(self, include_finished: bool) -> List[Contest]:
        """Fetch CodeChef contests from Kontests fallback."""
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

                code_match = re.search(r"codechef\.com/([a-zA-Z0-9_\-]+)", url)
                code = code_match.group(1) if code_match else re.sub(r"\W+", "_", name.lower())

                status = self.compute_status(start_time, end_time, now)
                if not include_finished and status == ContestStatus.FINISHED:
                    continue

                contests.append(
                    Contest(
                        id=f"codechef_{code.lower()}",
                        platform=self.platform,
                        name=name.strip(),
                        url=url if url.startswith("http") else f"https://www.codechef.com/{code}",
                        start_time=start_time,
                        end_time=end_time,
                        duration_seconds=duration_sec,
                        status=status,
                        raw_data=item,
                    )
                )
            except Exception as e:
                logger.debug("[CodeChef] Error parsing Kontests item: %s", e)
                continue

        contests.sort(key=lambda c: c.start_time)
        return contests
