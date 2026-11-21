"""AlgoRadar iCalendar (.ics) Generator & Synchronizer.

Converts Contest domain models into standard RFC 5545 compliant iCalendar (.ics) format.
Enables seamless one-click import and subscription across Google Calendar, Apple Calendar,
Microsoft Outlook, and mobile calendar applications.
Includes UTC-normalized timestamps, platform metadata, direct URLs, and 15-minute start alarms.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Union

from algoradar.models import Contest, ContestStatus

logger = logging.getLogger("algoradar.calendar_sync")

DEFAULT_PRODID = "-//AlgoRadar//Competitive Programming Contest Radar//EN"
DEFAULT_CALENDAR_NAME = "AlgoRadar CP Contests"
DEFAULT_CALENDAR_DESC = "Competitive Programming Contests tracked by AlgoRadar"
DEFAULT_ALARM_MINUTES = 15


def format_utc_timestamp(dt: datetime) -> str:
    """Format datetime object into RFC 5545 UTC timestamp (YYYYMMDDTHHMMSSZ).

    Args:
        dt: Datetime object (naive will be assumed UTC).

    Returns:
        String formatted timestamp ending in 'Z'.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def escape_ics_text(text: str) -> str:
    """Escape text for iCalendar property values according to RFC 5545 section 3.3.11.

    Escapes:
        - Backslashes: \\ -> \\\\
        - Semicolons: ; -> \\;
        - Commas: , -> \\,
        - Newlines: \\n or \\r\\n -> \\n
    """
    if not text:
        return ""
    # Normalize line breaks
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Escape backslash first to avoid double-escaping
    text = text.replace("\\", "\\\\")
    # Escape delimiter characters
    text = text.replace(";", "\\;").replace(",", "\\,")
    # Escape newlines as literal \n
    text = text.replace("\n", "\\n")
    return text


def fold_line(line: str, limit: int = 75) -> str:
    """Fold lines exceeding limit (RFC 5545 recommends max 75 octets per line).

    Lines are folded by inserting CRLF followed by a single whitespace character.
    """
    if len(line.encode("utf-8")) <= limit:
        return line

    parts: list[str] = []
    current = ""
    for char in line:
        candidate = current + char
        if len(candidate.encode("utf-8")) > limit:
            parts.append(current)
            current = " " + char
        else:
            current = candidate
    if current:
        parts.append(current)

    return "\r\n".join(parts)


def build_vevent(
    contest: Contest,
    alarm_minutes: int = DEFAULT_ALARM_MINUTES,
    dtstamp: Optional[datetime] = None,
) -> str:
    """Generate a single RFC 5545 VEVENT string for a contest.

    Args:
        contest: Contest object.
        alarm_minutes: Minutes before contest to set the display alarm (default 15).
        dtstamp: Optional generation timestamp. Defaults to current UTC time.

    Returns:
        Formatted VEVENT component string.
    """
    now = dtstamp or datetime.now(timezone.utc)
    stamp_str = format_utc_timestamp(now)
    start_str = format_utc_timestamp(contest.start_time)
    end_str = format_utc_timestamp(contest.end_time)

    # Sanitize UID to be safe alphanumeric + hyphen + period
    safe_id = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", str(contest.id))
    safe_plat = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", str(contest.platform.id))
    uid = f"{safe_plat}_{safe_id}@algoradar.net"

    # Clean summary and description
    plat_icon = contest.platform.icon
    plat_code = contest.platform.short_code
    plat_name = contest.platform.name
    summary_raw = f"{plat_icon} [{plat_code}] {contest.name}"
    summary = escape_ics_text(summary_raw)

    description_parts = [
        f"Contest: {contest.name}",
        f"Platform: {plat_name} ({plat_code})",
        f"URL: {contest.url}",
        f"Duration: {contest.duration_str()}",
        f"Status: {contest.status}",
    ]
    if contest.description:
        description_parts.append(f"\nDetails:\n{contest.description}")
    description = escape_ics_text("\n".join(description_parts))

    location = escape_ics_text(f"{plat_name} ({contest.url})")
    url = contest.url.strip()

    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{stamp_str}",
        f"DTSTART:{start_str}",
        f"DTEND:{end_str}",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:{description}",
        f"URL:{url}",
        f"LOCATION:{location}",
        "STATUS:CONFIRMED",
        "TRANSP:OPAQUE",
        "SEQUENCE:0",
    ]

    # Add 15-minute pre-contest alarm reminder
    if alarm_minutes > 0:
        alarm_desc = escape_ics_text(
            f"Reminder: {contest.name} on {plat_name} starts in {alarm_minutes} minutes!"
        )
        lines.extend(
            [
                "BEGIN:VALARM",
                "ACTION:DISPLAY",
                f"DESCRIPTION:{alarm_desc}",
                f"TRIGGER:-PT{int(alarm_minutes)}M",
                "END:VALARM",
            ]
        )

    lines.append("END:VEVENT")

    folded_lines = [fold_line(line) for line in lines]
    return "\r\n".join(folded_lines)


def generate_ics(
    contests: Iterable[Contest],
    calendar_name: str = DEFAULT_CALENDAR_NAME,
    calendar_desc: str = DEFAULT_CALENDAR_DESC,
    prodid: str = DEFAULT_PRODID,
    alarm_minutes: int = DEFAULT_ALARM_MINUTES,
    dtstamp: Optional[datetime] = None,
) -> str:
    """Generate complete iCalendar (.ics) string for a collection of contests.

    Args:
        contests: Iterable of Contest objects.
        calendar_name: X-WR-CALNAME property value.
        calendar_desc: X-WR-CALDESC property value.
        prodid: PRODID identifier string.
        alarm_minutes: Pre-contest alarm trigger time in minutes.
        dtstamp: Optional timestamp for event generation.

    Returns:
        Complete RFC 5545 iCalendar string with CRLF line endings.
    """
    contest_list = list(contests)
    # Sort chronologically by start_time
    contest_list.sort(key=lambda c: c.start_time)

    header_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{prodid}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_ics_text(calendar_name)}",
        f"X-WR-CALDESC:{escape_ics_text(calendar_desc)}",
        "X-WR-TIMEZONE:UTC",
    ]

    body_vevents = [
        build_vevent(c, alarm_minutes=alarm_minutes, dtstamp=dtstamp)
        for c in contest_list
    ]

    footer_lines = ["END:VCALENDAR"]

    all_parts = [
        "\r\n".join(fold_line(line) for line in header_lines)
    ]
    if body_vevents:
        all_parts.extend(body_vevents)
    all_parts.append("\r\n".join(footer_lines))

    # Join with CRLF and ensure trailing CRLF
    ics_content = "\r\n".join(all_parts) + "\r\n"
    return ics_content


def export_ics(
    contests: Iterable[Contest],
    output_path: Union[str, Path] = "contests.ics",
    calendar_name: str = DEFAULT_CALENDAR_NAME,
    calendar_desc: str = DEFAULT_CALENDAR_DESC,
    alarm_minutes: int = DEFAULT_ALARM_MINUTES,
) -> Path:
    """Export contests to an iCalendar (.ics) file on disk.

    Args:
        contests: Iterable of Contest objects.
        output_path: Destination file path (defaults to 'contests.ics').
        calendar_name: Name of the calendar.
        calendar_desc: Description of the calendar.
        alarm_minutes: Alarm trigger minutes before contest start.

    Returns:
        Path object pointing to the written file.
    """
    path = Path(output_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    content = generate_ics(
        contests=contests,
        calendar_name=calendar_name,
        calendar_desc=calendar_desc,
        alarm_minutes=alarm_minutes,
    )

    # Write in UTF-8 bytes to preserve precise CRLF formatting and emoji icons
    with open(path, "wb") as f:
        f.write(content.encode("utf-8"))

    logger.info("Exported %d contests to %s", len(list(contests)), path)
    return path


# Aliases for convenience
export_to_ics = export_ics
