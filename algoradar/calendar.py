"""AlgoRadar Calendar module alias (re-exports calendar_sync)."""

from algoradar.calendar_sync import (
    DEFAULT_ALARM_MINUTES,
    DEFAULT_CALENDAR_DESC,
    DEFAULT_CALENDAR_NAME,
    DEFAULT_PRODID,
    build_vevent,
    escape_ics_text,
    export_ics,
    export_to_ics,
    fold_line,
    format_utc_timestamp,
    generate_ics,
)

__all__ = [
    "DEFAULT_PRODID",
    "DEFAULT_CALENDAR_NAME",
    "DEFAULT_CALENDAR_DESC",
    "DEFAULT_ALARM_MINUTES",
    "format_utc_timestamp",
    "escape_ics_text",
    "fold_line",
    "build_vevent",
    "generate_ics",
    "export_ics",
    "export_to_ics",
]
