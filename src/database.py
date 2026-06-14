"""
database.py
-----------
Handles all persistent storage using SQLite — a lightweight, zero-configuration
database that's part of Python's standard library. No external DB server needed,
making this project easy to run anywhere.

Schema:
  - rate_history: stores fetched exchange rates over time
  - alerts: stores user-defined rate alert rules
"""

import sqlite3
import json
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Optional


DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "rates.db"


class Database:
    """
    Manages SQLite storage for rate history and price alerts.

    Uses context manager protocol for safe connection handling,
    and WAL mode for better concurrent read performance.
    """

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Access columns by name
        conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent performance
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self):
        """Create tables if they don't exist yet (idempotent)."""
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS rate_history (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    fetched_at  TEXT    NOT NULL,           -- ISO datetime of the fetch
                    rate_date   TEXT    NOT NULL,           -- Date the rate applies to
                    base        TEXT    NOT NULL,           -- e.g. "USD"
                    target      TEXT    NOT NULL,           -- e.g. "EUR"
                    rate        REAL    NOT NULL,           -- e.g. 0.9234
                    UNIQUE(rate_date, base, target)         -- Prevent duplicates
                );

                CREATE TABLE IF NOT EXISTS alerts (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at      TEXT    NOT NULL,
                    base            TEXT    NOT NULL,
                    target          TEXT    NOT NULL,
                    target_rate     REAL    NOT NULL,       -- Rate the user wants to hit
                    direction       TEXT    NOT NULL,       -- 'above' or 'below'
                    triggered       INTEGER NOT NULL DEFAULT 0,  -- 0=pending, 1=triggered
                    triggered_at    TEXT,
                    triggered_rate  REAL
                );

                CREATE INDEX IF NOT EXISTS idx_history_lookup
                    ON rate_history(base, target, rate_date);
            """)

    # ─── Rate History ────────────────────────────────────────────────────────

    def save_rates(self, base: str, rates: dict[str, float], rate_date: str):
        """
        Persist a batch of rates to history.

        Args:
            base: Base currency code
            rates: Dict of {target_currency: rate}
            rate_date: The date the rates are for (YYYY-MM-DD)
        """
        now = datetime.now(timezone.utc).isoformat()
        rows = [
            (now, rate_date, base.upper(), target.upper(), rate)
            for target, rate in rates.items()
        ]
        with self._connect() as conn:
            # INSERT OR IGNORE respects the UNIQUE constraint — no duplicate rates
            conn.executemany(
                """INSERT OR IGNORE INTO rate_history
                   (fetched_at, rate_date, base, target, rate)
                   VALUES (?, ?, ?, ?, ?)""",
                rows,
            )

    def get_rate_history(
        self,
        base: str,
        target: str,
        days: int = 30,
    ) -> list[dict]:
        """
        Retrieve recent rate history for a currency pair.

        Args:
            base: Base currency
            target: Target currency
            days: How many days back to look

        Returns:
            List of dicts with keys: rate_date, rate
        """
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT rate_date, rate
                   FROM rate_history
                   WHERE base = ? AND target = ?
                   ORDER BY rate_date DESC
                   LIMIT ?""",
                (base.upper(), target.upper(), days),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_latest_stored_rate(self, base: str, target: str) -> Optional[dict]:
        """Return the most recently stored rate for a currency pair."""
        with self._connect() as conn:
            row = conn.execute(
                """SELECT rate_date, rate, fetched_at
                   FROM rate_history
                   WHERE base = ? AND target = ?
                   ORDER BY rate_date DESC, fetched_at DESC
                   LIMIT 1""",
                (base.upper(), target.upper()),
            ).fetchone()
        return dict(row) if row else None

    # ─── Alerts ──────────────────────────────────────────────────────────────

    def add_alert(self, base: str, target: str, target_rate: float, direction: str) -> int:
        """
        Create a new rate alert.

        Args:
            base: Base currency
            target: Target currency
            target_rate: Rate threshold
            direction: 'above' (trigger when rate goes above) or 'below'

        Returns:
            The ID of the new alert row.
        """
        if direction not in ("above", "below"):
            raise ValueError(f"direction must be 'above' or 'below', got {direction!r}")

        with self._connect() as conn:
            cursor = conn.execute(
                """INSERT INTO alerts (created_at, base, target, target_rate, direction)
                   VALUES (?, ?, ?, ?, ?)""",
                (datetime.now(timezone.utc).isoformat(), base.upper(), target.upper(), target_rate, direction),
            )
            return cursor.lastrowid

    def get_pending_alerts(self) -> list[dict]:
        """Return all alerts that haven't fired yet."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM alerts WHERE triggered = 0 ORDER BY created_at"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_all_alerts(self) -> list[dict]:
        """Return all alerts including triggered ones."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM alerts ORDER BY triggered, created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def mark_alert_triggered(self, alert_id: int, triggered_rate: float):
        """Mark an alert as fired and record the rate that triggered it."""
        with self._connect() as conn:
            conn.execute(
                """UPDATE alerts
                   SET triggered = 1,
                       triggered_at = ?,
                       triggered_rate = ?
                   WHERE id = ?""",
                (datetime.now(timezone.utc).isoformat(), triggered_rate, alert_id),
            )

    def delete_alert(self, alert_id: int) -> bool:
        """Delete an alert by ID. Returns True if a row was deleted."""
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
            return cursor.rowcount > 0

    def delete_all_triggered_alerts(self) -> int:
        """Clean up triggered alerts. Returns count deleted."""
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM alerts WHERE triggered = 1")
            return cursor.rowcount
