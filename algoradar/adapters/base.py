"""AlgoRadar Base Adapter.

Provides abstract BaseAdapter with resilient HTTP request handling, custom User-Agents,
automatic gzip decompression, timeout management, and retry backoff.
"""

from __future__ import annotations

import abc
import gzip
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from algoradar.models import Contest, ContestStatus, Platform


logger = logging.getLogger("algoradar.adapters")


class BaseAdapter(abc.ABC):
    """Abstract base class for all competitive programming platform adapters."""

    def __init__(
        self,
        platform: Platform,
        timeout: int = 12,
        user_agent: Optional[str] = None,
        retries: int = 2,
    ) -> None:
        """Initialize adapter.

        Args:
            platform: Platform metadata instance.
            timeout: HTTP request timeout in seconds.
            user_agent: Custom HTTP User-Agent header string.
            retries: Number of retry attempts on network error.
        """
        self.platform = platform
        self.timeout = timeout
        self.retries = retries
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36 AlgoRadar/1.0"
        )

    @property
    def platform_id(self) -> str:
        """Convenience property for platform ID."""
        return self.platform.id

    @property
    def name(self) -> str:
        """Adapter name."""
        return self.platform.name

    def safe_request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        json_data: Optional[Any] = None,
        timeout: Optional[int] = None,
        parse_json: bool = True,
    ) -> Optional[Union[Dict[str, Any], List[Any], str]]:
        """Perform a safe, fault-tolerant HTTP request.

        Handles timeouts, retries, headers, compression, and JSON decoding.
        Never throws unhandled network exceptions; returns None on failure.

        Args:
            url: Target URL.
            method: HTTP method (GET, POST, etc.).
            headers: Optional dictionary of HTTP headers.
            data: Raw or form data.
            json_data: Python object to serialize as JSON payload.
            timeout: Custom timeout in seconds (overrides default).
            parse_json: If True and response looks like JSON, returns parsed object.

        Returns:
            Parsed JSON (dict/list), raw text string, or None if request failed.
        """
        req_headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/html, application/xhtml+xml, */*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.9",
        }
        if headers:
            req_headers.update(headers)

        payload_bytes: Optional[bytes] = None
        if json_data is not None:
            payload_bytes = json.dumps(json_data).encode("utf-8")
            req_headers["Content-Type"] = "application/json; charset=utf-8"
        elif data is not None:
            if isinstance(data, dict):
                payload_bytes = urllib.parse.urlencode(data).encode("utf-8")
                req_headers["Content-Type"] = "application/x-www-form-urlencoded"
            elif isinstance(data, str):
                payload_bytes = data.encode("utf-8")
            elif isinstance(data, bytes):
                payload_bytes = data

        req_timeout = timeout or self.timeout
        attempts = max(1, self.retries + 1)

        for attempt in range(1, attempts + 1):
            try:
                request = urllib.request.Request(
                    url=url,
                    data=payload_bytes,
                    headers=req_headers,
                    method=method.upper(),
                )

                with urllib.request.urlopen(request, timeout=req_timeout) as response:
                    raw_content = response.read()
                    content_encoding = response.headers.get("Content-Encoding", "").lower()

                    # Handle gzip / deflate decompression
                    if "gzip" in content_encoding:
                        try:
                            raw_content = gzip.decompress(raw_content)
                        except Exception:
                            pass
                    elif "deflate" in content_encoding:
                        try:
                            raw_content = zlib.decompress(raw_content)
                        except Exception:
                            pass

                    # Decode text
                    text = raw_content.decode("utf-8", errors="replace")

                    if parse_json:
                        stripped = text.strip()
                        if (stripped.startswith("{") and stripped.endswith("}")) or (
                            stripped.startswith("[") and stripped.endswith("]")
                        ):
                            try:
                                return json.loads(stripped)
                            except json.JSONDecodeError:
                                pass

                    return text

            except urllib.error.HTTPError as http_err:
                logger.warning(
                    "[%s] HTTP %d on %s (attempt %d/%d): %s",
                    self.platform.name,
                    http_err.code,
                    url,
                    attempt,
                    attempts,
                    http_err.reason,
                )
                if http_err.code in (401, 403, 404):
                    # Do not retry client auth/not-found errors
                    break
            except urllib.error.URLError as url_err:
                logger.warning(
                    "[%s] Network URLError on %s (attempt %d/%d): %s",
                    self.platform.name,
                    url,
                    attempt,
                    attempts,
                    url_err.reason,
                )
            except (TimeoutError, OSError) as os_err:
                logger.warning(
                    "[%s] Timeout/Socket error on %s (attempt %d/%d): %s",
                    self.platform.name,
                    url,
                    attempt,
                    attempts,
                    os_err,
                )
            except Exception as exc:
                logger.error(
                    "[%s] Unexpected error on %s (attempt %d/%d): %s",
                    self.platform.name,
                    url,
                    attempt,
                    attempts,
                    exc,
                )

            if attempt < attempts:
                time.sleep(0.5 * attempt)

        return None

    @abc.abstractmethod
    def fetch_contests(self) -> List[Contest]:
        """Fetch, parse, and return list of contests from this platform.

        Must not raise unhandled exceptions; return empty list on failure.
        """
        raise NotImplementedError

    def compute_status(
        self, start_time: datetime, end_time: datetime, now: Optional[datetime] = None
    ) -> ContestStatus:
        """Helper to compute contest status relative to current time."""
        current_now = now or datetime.now(timezone.utc)
        if current_now < start_time:
            return ContestStatus.UPCOMING
        elif start_time <= current_now <= end_time:
            return ContestStatus.RUNNING
        return ContestStatus.FINISHED
