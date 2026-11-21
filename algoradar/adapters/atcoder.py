"""AlgoRadar AtCoder Adapter.

Fetches contests for AtCoder using Kenkoooo API with Kontests and direct HTML parsing fallbacks.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from typing import Any, List, Optional

from algoradar.adapters.base import BaseAdapter
from algoradar.models import ATCODER, Contest, ContestStatus


logger = logging.getLogger("algoradar.adapters.atcoder")


class AtCoderHTMLParser(HTMLParser):
    """HTML parser to extract upcoming contests directly from atcoder.jp/contests/."""

    def __init__(self) -> None:
        super().__init__()
        self.in_target_table = False
        self.current_row: list[str] = []
        self.current_link = ""
        self.current_text = ""
        self.contests_data: list[dict[str, str]] = []
        self._target_table_ids = {"contest-table-upcoming", "contest-table-action"}
        self._table_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        attrs_dict = dict(attrs)
        tag_id = attrs_dict.get("id", "")
        if tag_id in self._target_table_ids:
            self.in_target_table = True
            self._table_depth = 1
        elif self.in_target_table and tag in ("div", "table"):
            self._table_depth += 1

        if self.in_target_table:
            if tag == "tr":
                self.current_row = []
            elif tag == "a":
                href = attrs_dict.get("href", "")
                if "/contests/" in href and not self.current_link:
                    self.current_link = href
            self.current_text = ""

    def handle_endtag(self, tag: str) -> None:
        if self.in_target_table:
            if tag == "td" or tag == "th":
                text = self.current_text.strip()
                if text:
                    self.current_row.append(text)
                self.current_text = ""
            elif tag == "tr" and self.current_row:
                if len(self.current_row) >= 2 and self.current_link:
                    self.contests_data.append(
                        {
                            "time_str": self.current_row[0],
                            "title": self.current_row[1],
                            "link": self.current_link,
                            "duration_str": self.current_row[2] if len(self.current_row) > 2 else "",
                        }
                    )
                self.current_row = []
                self.current_link = ""
            elif tag in ("div", "table"):
                self._table_depth -= 1
                if self._table_depth <= 0:
                    self.in_target_table = False

    def handle_data(self, data: str) -> None:
        if self.in_target_table:
            self.current_text += data


class AtCoderAdapter(BaseAdapter):
    """Adapter for AtCoder contests."""

    KENKOOOO_API_URL = "https://kenkoooo.com/atcoder/resources/contests.json"
    KONTESTS_API_URL = "https://kontests.net/api/v1/at_coder"
    ATCODER_WEB_URL = "https://atcoder.jp/contests/"

    def __init__(self, timeout: int = 12) -> None:
        super().__init__(platform=ATCODER, timeout=timeout)

    def fetch_contests(self, include_finished: bool = False) -> List[Contest]:
        """Fetch AtCoder contests with automatic fallback chain."""
        # 1. Try Kenkoooo API
        contests = self._fetch_from_kenkoooo(include_finished)
        if contests:
            return contests

        # 2. Try Kontests API
        contests = self._fetch_from_kontests(include_finished)
        if contests:
            return contests

        # 3. Direct HTML scraping fallback
        contests = self._fetch_from_html()
        return contests

    def _fetch_from_kenkoooo(self, include_finished: bool) -> List[Contest]:
        """Fetch from Kenkoooo contests JSON endpoint."""
        data = self.safe_request(self.KENKOOOO_API_URL)
        if not isinstance(data, list):
            return []

        contests: List[Contest] = []
        now = datetime.now(timezone.utc)

        for item in data:
            try:
                cid = item.get("id")
                title = item.get("title")
                start_sec = item.get("start_epoch_second")
                duration_sec = item.get("duration_second", 0)

                if not cid or not title or not start_sec:
                    continue

                start_time = datetime.fromtimestamp(start_sec, tz=timezone.utc)
                end_time = start_time + timedelta(seconds=duration_sec)

                status = self.compute_status(start_time, end_time, now)
                if not include_finished and status == ContestStatus.FINISHED:
                    continue

                contests.append(
                    Contest(
                        id=f"atcoder_{cid}",
                        platform=self.platform,
                        name=title.strip(),
                        url=f"https://atcoder.jp/contests/{cid}",
                        start_time=start_time,
                        end_time=end_time,
                        duration_seconds=duration_sec,
                        status=status,
                        description=f"Rated: {item.get('rate_change', 'All')}",
                        raw_data=item,
                    )
                )
            except Exception as e:
                logger.debug("[AtCoder] Kenkoooo parse item error: %s", e)
                continue

        contests.sort(key=lambda c: c.start_time)
        return contests

    def _fetch_from_kontests(self, include_finished: bool) -> List[Contest]:
        """Fetch from Kontests AtCoder endpoint."""
        data = self.safe_request(self.KONTESTS_API_URL)
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
                duration_sec = int(float(item.get("duration", 0)))

                if not name or not start_str or not end_str:
                    continue

                start_time = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                end_time = datetime.fromisoformat(end_str.replace("Z", "+00:00"))

                # Extract contest id from url e.g. https://atcoder.jp/contests/abc350
                cid_match = re.search(r"/contests/([a-zA-Z0-9_\-]+)", url)
                cid = cid_match.group(1) if cid_match else re.sub(r"\W+", "_", name.lower())

                status = self.compute_status(start_time, end_time, now)
                if not include_finished and status == ContestStatus.FINISHED:
                    continue

                contests.append(
                    Contest(
                        id=f"atcoder_{cid}",
                        platform=self.platform,
                        name=name.strip(),
                        url=url if url.startswith("http") else f"https://atcoder.jp/contests/{cid}",
                        start_time=start_time,
                        end_time=end_time,
                        duration_seconds=duration_sec,
                        status=status,
                        raw_data=item,
                    )
                )
            except Exception as e:
                logger.debug("[AtCoder] Kontests parse error: %s", e)
                continue

        contests.sort(key=lambda c: c.start_time)
        return contests

    def _fetch_from_html(self) -> List[Contest]:
        """Scrape upcoming/active contests directly from atcoder.jp/contests/."""
        html_text = self.safe_request(self.ATCODER_WEB_URL, parse_json=False)
        if not isinstance(html_text, str) or not html_text:
            return []

        parser = AtCoderHTMLParser()
        try:
            parser.feed(html_text)
        except Exception as e:
            logger.debug("[AtCoder] HTML parser error: %s", e)
            return []

        contests: List[Contest] = []
        now = datetime.now(timezone.utc)

        for item in parser.contests_data:
            try:
                title = item.get("title", "")
                link = item.get("link", "")
                time_str = item.get("time_str", "")
                duration_str = item.get("duration_str", "")

                cid_match = re.search(r"/contests/([a-zA-Z0-9_\-]+)", link)
                cid = cid_match.group(1) if cid_match else re.sub(r"\W+", "_", title.lower())

                # AtCoder format: '2026-04-20 21:00:00+0900'
                start_time = None
                time_match = re.search(r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)", time_str)
                if time_match:
                    parsed_dt = datetime.strptime(time_match.group(1), "%Y-%m-%d %H:%M:%S" if ":" in time_match.group(1)[14:] else "%Y-%m-%d %H:%M")
                    # AtCoder is JST (UTC+9)
                    start_time = parsed_dt.replace(tzinfo=timezone(timedelta(hours=9))).astimezone(timezone.utc)

                if not start_time:
                    continue

                duration_seconds = 6000
                if duration_str:
                    d_match = re.search(r"(\d+):(\d+)", duration_str)
                    if d_match:
                        duration_seconds = int(d_match.group(1)) * 3600 + int(d_match.group(2)) * 60

                end_time = start_time + timedelta(seconds=duration_seconds)
                status = self.compute_status(start_time, end_time, now)

                full_url = f"https://atcoder.jp{link}" if link.startswith("/") else link

                contests.append(
                    Contest(
                        id=f"atcoder_{cid}",
                        platform=self.platform,
                        name=title,
                        url=full_url,
                        start_time=start_time,
                        end_time=end_time,
                        duration_seconds=duration_seconds,
                        status=status,
                    )
                )
            except Exception as e:
                logger.debug("[AtCoder] HTML row parse error: %s", e)
                continue

        contests.sort(key=lambda c: c.start_time)
        return contests
