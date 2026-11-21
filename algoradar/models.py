"""AlgoRadar Data Models.

Defines the core domain entities for competitive programming platforms and contests,
including serialization, human-friendly duration and countdown formatters, and status
management.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class ContestStatus(str, Enum):
    """Contest status lifecycle states."""

    UPCOMING = "UPCOMING"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Platform:
    """Represents a competitive programming platform."""

    id: str
    name: str
    short_code: str
    icon: str
    url: str

    def to_dict(self) -> dict[str, str]:
        """Convert platform instance to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "short_code": self.short_code,
            "icon": self.icon,
            "url": self.url,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Platform:
        """Create platform instance from dictionary."""
        return cls(
            id=str(data.get("id", "")).lower(),
            name=str(data.get("name", "")),
            short_code=str(data.get("short_code", "")),
            icon=str(data.get("icon", "⚡")),
            url=str(data.get("url", "")),
        )


# Predefined platform definitions
CODEFORCES = Platform(
    id="codeforces",
    name="Codeforces",
    short_code="CF",
    icon="⚡",
    url="https://codeforces.com",
)

LEETCODE = Platform(
    id="leetcode",
    name="LeetCode",
    short_code="LC",
    icon="🔶",
    url="https://leetcode.com",
)

ATCODER = Platform(
    id="atcoder",
    name="AtCoder",
    short_code="AC",
    icon="🔴",
    url="https://atcoder.jp",
)

CODECHEF = Platform(
    id="codechef",
    name="CodeChef",
    short_code="CC",
    icon="🧑‍🍳",
    url="https://www.codechef.com",
)

HACKERRANK = Platform(
    id="hackerrank",
    name="HackerRank",
    short_code="HR",
    icon="🟩",
    url="https://www.hackerrank.com",
)

PLATFORMS_MAP: dict[str, Platform] = {
    "codeforces": CODEFORCES,
    "cf": CODEFORCES,
    "leetcode": LEETCODE,
    "lc": LEETCODE,
    "atcoder": ATCODER,
    "ac": ATCODER,
    "codechef": CODECHEF,
    "cc": CODECHEF,
    "hackerrank": HACKERRANK,
    "hr": HACKERRANK,
}


def get_platform(identifier: str) -> Optional[Platform]:
    """Retrieve standard Platform object by id or short_code."""
    key = str(identifier).strip().lower()
    return PLATFORMS_MAP.get(key)


def _ensure_utc(dt: datetime) -> datetime:
    """Ensure datetime object is timezone-aware UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass
class Contest:
    """Represents a competitive programming contest."""

    id: str
    platform: Platform
    name: str
    url: str
    start_time: datetime
    end_time: datetime
    duration_seconds: int
    status: ContestStatus | str = ContestStatus.UPCOMING
    is_favorite: bool = False
    description: str = ""
    raw_data: Optional[dict[str, Any]] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Normalize platform, times and status."""
        if isinstance(self.platform, dict):
            self.platform = Platform.from_dict(self.platform)
        elif isinstance(self.platform, str):
            resolved = get_platform(self.platform)
            if resolved:
                self.platform = resolved
            else:
                self.platform = Platform(
                    id=self.platform.lower(),
                    name=self.platform.title(),
                    short_code=self.platform[:2].upper(),
                    icon="⚡",
                    url="",
                )

        if isinstance(self.start_time, str):
            self.start_time = datetime.fromisoformat(self.start_time)
        self.start_time = _ensure_utc(self.start_time)

        if isinstance(self.end_time, str):
            self.end_time = datetime.fromisoformat(self.end_time)
        self.end_time = _ensure_utc(self.end_time)

        if isinstance(self.status, str):
            status_upper = self.status.upper()
            if status_upper in ContestStatus._value2member_map_:
                self.status = ContestStatus(status_upper)

        if self.duration_seconds <= 0 and self.end_time > self.start_time:
            self.duration_seconds = int((self.end_time - self.start_time).total_seconds())

    def update_status(self, now: Optional[datetime] = None) -> ContestStatus:
        """Update and return the contest status based on current time."""
        current_now = _ensure_utc(now) if now else datetime.now(timezone.utc)
        if current_now < self.start_time:
            self.status = ContestStatus.UPCOMING
        elif self.start_time <= current_now <= self.end_time:
            self.status = ContestStatus.RUNNING
        else:
            self.status = ContestStatus.FINISHED
        return self.status

    def starts_in_str(self, now: Optional[datetime] = None) -> str:
        """Return a human-readable string indicating when the contest starts.

        Examples:
            - 'in 2d 5h'
            - 'in 3h 15m'
            - 'in 42m'
            - 'in < 1m'
            - 'Running (ends in 1h 20m)'
            - 'Ended'
        """
        current_now = _ensure_utc(now) if now else datetime.now(timezone.utc)

        if current_now > self.end_time or self.status == ContestStatus.FINISHED:
            return "Ended"

        if self.start_time <= current_now <= self.end_time or self.status == ContestStatus.RUNNING:
            remaining_seconds = int((self.end_time - current_now).total_seconds())
            if remaining_seconds <= 60:
                return "Running (ending soon)"
            hours = remaining_seconds // 3600
            mins = (remaining_seconds % 3600) // 60
            if hours > 0:
                return f"Running (ends in {hours}h {mins:02d}m)"
            return f"Running (ends in {mins}m)"

        # Contest is in the future
        diff = int((self.start_time - current_now).total_seconds())
        if diff <= 0:
            return "Starting now"
        if diff < 60:
            return "in < 1m"

        days = diff // 86400
        hours = (diff % 86400) // 3600
        minutes = (diff % 3600) // 60

        parts: list[str] = []
        if days > 0:
            parts.append(f"{days}d")
            if hours > 0:
                parts.append(f"{hours}h")
        elif hours > 0:
            parts.append(f"{hours}h")
            if minutes > 0:
                parts.append(f"{minutes:02d}m" if minutes < 10 else f"{minutes}m")
        else:
            parts.append(f"{minutes}m")

        return f"in {' '.join(parts)}"

    def duration_str(self) -> str:
        """Return a formatted string representing the contest duration.

        Examples:
            - '2h' (for 7200s)
            - '2h 30m' (for 9000s)
            - '1d' (for 86400s)
            - '1d 4h' (for 100800s)
            - '45m' (for 2700s)
        """
        secs = self.duration_seconds
        if secs <= 0:
            return "0m"

        days = secs // 86400
        hours = (secs % 86400) // 3600
        minutes = (secs % 3600) // 60
        remaining_secs = secs % 60

        parts: list[str] = []
        if days > 0:
            parts.append(f"{days}d")
            if hours > 0:
                parts.append(f"{hours}h")
        elif hours > 0:
            parts.append(f"{hours}h")
            if minutes > 0:
                parts.append(f"{minutes}m")
        elif minutes > 0:
            parts.append(f"{minutes}m")
            if remaining_secs > 0:
                parts.append(f"{remaining_secs}s")
        else:
            parts.append(f"{remaining_secs}s")

        return " ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """Serialize contest to dictionary."""
        return {
            "id": self.id,
            "platform": self.platform.to_dict(),
            "name": self.name,
            "url": self.url,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": self.duration_seconds,
            "status": str(self.status),
            "is_favorite": self.is_favorite,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Contest:
        """Instantiate contest from dictionary."""
        plat_data = data.get("platform")
        if isinstance(plat_data, dict):
            platform = Platform.from_dict(plat_data)
        elif isinstance(plat_data, str):
            platform = get_platform(plat_data) or Platform(
                id=plat_data.lower(),
                name=plat_data.title(),
                short_code=plat_data[:2].upper(),
                icon="⚡",
                url="",
            )
        else:
            platform = CODEFORCES

        start_time_val = data.get("start_time")
        if isinstance(start_time_val, (int, float)):
            start_time = datetime.fromtimestamp(start_time_val, tz=timezone.utc)
        elif isinstance(start_time_val, str):
            start_time = datetime.fromisoformat(start_time_val)
        else:
            start_time = datetime.now(timezone.utc)

        end_time_val = data.get("end_time")
        if isinstance(end_time_val, (int, float)):
            end_time = datetime.fromtimestamp(end_time_val, tz=timezone.utc)
        elif isinstance(end_time_val, str):
            end_time = datetime.fromisoformat(end_time_val)
        else:
            end_time = start_time

        duration_sec = int(data.get("duration_seconds", 0))
        if duration_sec <= 0 and end_time > start_time:
            duration_sec = int((end_time - start_time).total_seconds())

        status_raw = data.get("status", "UPCOMING")
        if isinstance(status_raw, ContestStatus):
            status = status_raw
        else:
            status_str = str(status_raw).upper()
            status = ContestStatus(status_str) if status_str in ContestStatus._value2member_map_ else ContestStatus.UPCOMING

        return cls(
            id=str(data.get("id", "")),
            platform=platform,
            name=str(data.get("name", "")),
            url=str(data.get("url", "")),
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration_sec,
            status=status,
            is_favorite=bool(data.get("is_favorite", False)),
            description=str(data.get("description", "")),
            raw_data=data.get("raw_data"),
        )
