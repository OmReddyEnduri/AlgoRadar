"""AlgoRadar SQLite Storage Layer.

Provides local SQLite persistence for contests, platform metadata, and user favorites.
Configures WAL (Write-Ahead Logging) mode for concurrent high-performance terminal read/writes.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, Union

from algoradar.models import Contest, ContestStatus, Platform, get_platform


DEFAULT_DB_DIR = Path.home() / ".algoradar"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "algoradar.db"


class Storage:
    """SQLite Storage engine with WAL mode and conflict-safe upserting."""

    def __init__(self, db_path: Optional[Union[str, Path]] = None) -> None:
        """Initialize storage engine and ensure database schema exists.

        Args:
            db_path: Custom database file path. Defaults to ~/.algoradar/algoradar.db.
        """
        if db_path is None:
            self.db_path = DEFAULT_DB_PATH
        else:
            self.db_path = Path(db_path)

        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create or return an active SQLite connection configured for WAL mode."""
        if self._conn is None:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
                check_same_thread=False,
                isolation_level=None,  # Autocommit mode; transactions managed explicitly
            )
            conn.row_factory = sqlite3.Row
            # Enable WAL mode and performance optimizations
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            self._conn = conn
        return self._conn

    def _init_db(self) -> None:
        """Create tables and indexes if they do not exist."""
        conn = self._get_connection()
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS contests (
                    id TEXT PRIMARY KEY,
                    platform_id TEXT NOT NULL,
                    platform_name TEXT NOT NULL,
                    platform_code TEXT NOT NULL,
                    platform_icon TEXT NOT NULL,
                    platform_url TEXT NOT NULL,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    duration_seconds INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    is_favorite INTEGER NOT NULL DEFAULT 0,
                    description TEXT DEFAULT '',
                    updated_at TEXT NOT NULL
                );
                """
            )
            # Create indexes for fast filtering and sorting
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_contests_platform ON contests(platform_id);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_contests_code ON contests(platform_code);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_contests_status ON contests(status);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_contests_start_time ON contests(start_time);"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_contests_is_favorite ON contests(is_favorite);"
            )

    def _row_to_contest(self, row: sqlite3.Row) -> Contest:
        """Convert a database row into a Contest instance."""
        plat = Platform(
            id=row["platform_id"],
            name=row["platform_name"],
            short_code=row["platform_code"],
            icon=row["platform_icon"],
            url=row["platform_url"],
        )
        return Contest(
            id=row["id"],
            platform=plat,
            name=row["name"],
            url=row["url"],
            start_time=datetime.fromisoformat(row["start_time"]),
            end_time=datetime.fromisoformat(row["end_time"]),
            duration_seconds=row["duration_seconds"],
            status=ContestStatus(row["status"]) if row["status"] in ContestStatus._value2member_map_ else ContestStatus.UPCOMING,
            is_favorite=bool(row["is_favorite"]),
            description=row["description"] or "",
        )

    def save_contests(self, contests: List[Contest]) -> int:
        """Insert or update contests in SQLite.

        Preserves existing `is_favorite` flag if contest is already stored.

        Args:
            contests: List of Contest objects to persist.

        Returns:
            Number of contests saved/updated.
        """
        if not contests:
            return 0

        now_iso = datetime.now(timezone.utc).isoformat()
        conn = self._get_connection()

        query = """
        INSERT INTO contests (
            id, platform_id, platform_name, platform_code, platform_icon, platform_url,
            name, url, start_time, end_time, duration_seconds, status,
            is_favorite, description, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            platform_id = excluded.platform_id,
            platform_name = excluded.platform_name,
            platform_code = excluded.platform_code,
            platform_icon = excluded.platform_icon,
            platform_url = excluded.platform_url,
            name = excluded.name,
            url = excluded.url,
            start_time = excluded.start_time,
            end_time = excluded.end_time,
            duration_seconds = excluded.duration_seconds,
            status = excluded.status,
            is_favorite = CASE WHEN contests.is_favorite = 1 THEN 1 ELSE excluded.is_favorite END,
            description = excluded.description,
            updated_at = excluded.updated_at;
        """

        records = [
            (
                c.id,
                c.platform.id,
                c.platform.name,
                c.platform.short_code,
                c.platform.icon,
                c.platform.url,
                c.name,
                c.url,
                c.start_time.isoformat(),
                c.end_time.isoformat(),
                c.duration_seconds,
                str(c.status),
                1 if c.is_favorite else 0,
                c.description,
                now_iso,
            )
            for c in contests
        ]

        with conn:
            conn.executemany(query, records)

        return len(records)

    def get_upcoming(self, limit: Optional[int] = None) -> List[Contest]:
        """Fetch all upcoming contests ordered by start_time ascending.

        Includes contests with status='UPCOMING' or whose start_time is in the future.
        """
        conn = self._get_connection()
        now_iso = datetime.now(timezone.utc).isoformat()

        sql = """
            SELECT * FROM contests
            WHERE status = 'UPCOMING' OR start_time > ?
            ORDER BY start_time ASC
        """
        if limit and limit > 0:
            sql += f" LIMIT {int(limit)}"

        cursor = conn.execute(sql, (now_iso,))
        rows = cursor.fetchall()
        return [self._row_to_contest(r) for r in rows]

    def get_running(self) -> List[Contest]:
        """Fetch all currently running contests ordered by end_time ascending."""
        conn = self._get_connection()
        now_iso = datetime.now(timezone.utc).isoformat()

        cursor = conn.execute(
            """
            SELECT * FROM contests
            WHERE status = 'RUNNING'
               OR (start_time <= ? AND end_time >= ?)
            ORDER BY end_time ASC
            """,
            (now_iso, now_iso),
        )
        rows = cursor.fetchall()
        return [self._row_to_contest(r) for r in rows]

    def get_history(self, limit: int = 50) -> List[Contest]:
        """Fetch recently finished contests ordered by end_time descending."""
        conn = self._get_connection()
        now_iso = datetime.now(timezone.utc).isoformat()

        cursor = conn.execute(
            """
            SELECT * FROM contests
            WHERE status = 'FINISHED'
               OR end_time < ?
            ORDER BY end_time DESC
            LIMIT ?
            """,
            (now_iso, limit),
        )
        rows = cursor.fetchall()
        return [self._row_to_contest(r) for r in rows]

    def get_by_platform(self, plat: str) -> List[Contest]:
        """Fetch contests for a specific platform by id or short_code (case-insensitive)."""
        conn = self._get_connection()
        clean = plat.strip().lower()

        cursor = conn.execute(
            """
            SELECT * FROM contests
            WHERE LOWER(platform_id) = ? OR LOWER(platform_code) = ?
            ORDER BY start_time ASC
            """,
            (clean, clean),
        )
        rows = cursor.fetchall()
        return [self._row_to_contest(r) for r in rows]

    def get_favorites(self) -> List[Contest]:
        """Fetch all contests bookmarked as favorites."""
        conn = self._get_connection()
        cursor = conn.execute(
            """
            SELECT * FROM contests
            WHERE is_favorite = 1
            ORDER BY start_time ASC
            """
        )
        rows = cursor.fetchall()
        return [self._row_to_contest(r) for r in rows]

    def get_contest(self, contest_id: str) -> Optional[Contest]:
        """Retrieve a specific contest by its unique id."""
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM contests WHERE id = ? LIMIT 1",
            (contest_id,),
        )
        row = cursor.fetchone()
        if row:
            return self._row_to_contest(row)
        return None

    def toggle_favorite(self, contest_id: str) -> bool:
        """Toggle the favorite status of a contest.

        Args:
            contest_id: Unique contest identifier.

        Returns:
            The new boolean favorite state. Returns False if contest not found.
        """
        conn = self._get_connection()
        with conn:
            cursor = conn.execute(
                """
                UPDATE contests
                SET is_favorite = CASE WHEN is_favorite = 1 THEN 0 ELSE 1 END
                WHERE id = ?
                RETURNING is_favorite;
                """,
                (contest_id,),
            )
            row = cursor.fetchone()
            if row is not None:
                return bool(row["is_favorite"])

        # Fallback for older sqlite without RETURNING
        cursor = conn.execute(
            "SELECT is_favorite FROM contests WHERE id = ?",
            (contest_id,),
        )
        row = cursor.fetchone()
        if row:
            new_val = 0 if row["is_favorite"] else 1
            with conn:
                conn.execute(
                    "UPDATE contests SET is_favorite = ? WHERE id = ?",
                    (new_val, contest_id),
                )
            return bool(new_val)

        return False

    def delete_contest(self, contest_id: str) -> bool:
        """Delete a contest by id."""
        conn = self._get_connection()
        with conn:
            cursor = conn.execute("DELETE FROM contests WHERE id = ?", (contest_id,))
            return cursor.rowcount > 0

    def clear_all(self) -> int:
        """Delete all contest records."""
        conn = self._get_connection()
        with conn:
            cursor = conn.execute("DELETE FROM contests;")
            return cursor.rowcount

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def __enter__(self) -> Storage:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
