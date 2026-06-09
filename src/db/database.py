"""
Database manager for IAD France property price estimator.

Handles SQLite operations for estimation history and application logs.

Author: [Twoje Imię i Nazwisko]
License: MIT
"""

import sqlite3
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages SQLite database for storing estimation history and logs.

    Creates the database and all required tables automatically
    if they do not exist on first run.

    Args:
        db_path: Path to the SQLite database file.
    """

    DEFAULT_PATH = Path(__file__).parent.parent.parent / "data" / "history.db"

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = Path(db_path) if db_path else self.DEFAULT_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info("DatabaseManager initialized at %s", self.db_path)

    def _get_connection(self) -> sqlite3.Connection:
        """Return a new SQLite connection with row_factory set."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create tables if they do not exist."""
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS estimations (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp       TEXT    NOT NULL,
                    surface_m2      REAL    NOT NULL,
                    bedrooms        INTEGER NOT NULL,
                    dpe_class       TEXT    NOT NULL,
                    image_count     INTEGER NOT NULL,
                    property_type   TEXT    NOT NULL,
                    has_pool        INTEGER NOT NULL DEFAULT 0,
                    has_terrace     INTEGER NOT NULL DEFAULT 0,
                    has_view        INTEGER NOT NULL DEFAULT 0,
                    has_garden      INTEGER NOT NULL DEFAULT 0,
                    has_transport   INTEGER NOT NULL DEFAULT 0,
                    is_quiet        INTEGER NOT NULL DEFAULT 0,
                    has_fireplace   INTEGER NOT NULL DEFAULT 0,
                    needs_work      INTEGER NOT NULL DEFAULT 0,
                    model_used      TEXT    NOT NULL,
                    price_estimate  REAL    NOT NULL,
                    price_low       REAL    NOT NULL,
                    price_high      REAL    NOT NULL,
                    valuation_label TEXT
                );

                CREATE TABLE IF NOT EXISTS logs (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    level     TEXT NOT NULL,
                    action    TEXT NOT NULL,
                    details   TEXT
                );
            """)
        logger.debug("Database tables verified/created.")

    def save_estimation(
        self,
        surface_m2: float,
        bedrooms: int,
        dpe_class: str,
        image_count: int,
        property_type: str,
        amenities: dict,
        model_used: str,
        price_estimate: float,
        price_low: float,
        price_high: float,
        valuation_label: Optional[str] = None,
    ) -> int:
        """
        Persist a price estimation to the database.

        Args:
            surface_m2: Property surface area in m².
            bedrooms: Number of bedrooms.
            dpe_class: Energy class (A–G).
            image_count: Number of listing images.
            property_type: 'apartment', 'house', or 'land'.
            amenities: Dict of boolean amenity flags.
            model_used: 'OLS' or 'RandomForest'.
            price_estimate: Point estimate in EUR.
            price_low: Lower bound of 95% prediction interval.
            price_high: Upper bound of 95% prediction interval.
            valuation_label: 'Okazyjna', 'Przeciętna', or 'Za wysoka'.

        Returns:
            Row ID of the inserted record.
        """
        ts = datetime.now().isoformat(timespec="seconds")
        with self._get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO estimations (
                    timestamp, surface_m2, bedrooms, dpe_class, image_count,
                    property_type, has_pool, has_terrace, has_view, has_garden,
                    has_transport, is_quiet, has_fireplace, needs_work,
                    model_used, price_estimate, price_low, price_high, valuation_label
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    ts, surface_m2, bedrooms, dpe_class, image_count,
                    property_type,
                    int(amenities.get("has_pool", 0)),
                    int(amenities.get("has_terrace", 0)),
                    int(amenities.get("has_view", 0)),
                    int(amenities.get("has_garden", 0)),
                    int(amenities.get("has_transport", 0)),
                    int(amenities.get("is_quiet", 0)),
                    int(amenities.get("has_fireplace", 0)),
                    int(amenities.get("needs_work", 0)),
                    model_used, price_estimate, price_low, price_high,
                    valuation_label,
                ),
            )
            row_id = cur.lastrowid
        self.log_action("ESTIMATION", f"Saved estimation id={row_id}, model={model_used}, price={price_estimate:.0f}")
        return row_id

    def get_history(self, limit: int = 100) -> list[dict]:
        """
        Retrieve recent estimations ordered by newest first.

        Args:
            limit: Maximum number of records to return.

        Returns:
            List of dicts with estimation data.
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM estimations ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def clear_history(self) -> int:
        """
        Delete all estimation records from the database.

        Returns:
            Number of deleted rows.
        """
        with self._get_connection() as conn:
            cur = conn.execute("DELETE FROM estimations")
            deleted = cur.rowcount
        self.log_action("CLEAR_HISTORY", f"Deleted {deleted} estimation records.")
        return deleted

    def log_action(self, action: str, details: str = "", level: str = "INFO") -> None:
        """
        Write an application log entry to the database.

        Args:
            action: Short action identifier (e.g. 'ESTIMATION', 'STARTUP').
            details: Longer description of the event.
            level: Log level string ('INFO', 'WARNING', 'ERROR').
        """
        ts = datetime.now().isoformat(timespec="seconds")
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT INTO logs (timestamp, level, action, details) VALUES (?,?,?,?)",
                    (ts, level, action, details),
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to write log to DB: %s", exc)

    def get_logs(self, limit: int = 200) -> list[dict]:
        """
        Retrieve recent log entries.

        Args:
            limit: Maximum number of records to return.

        Returns:
            List of dicts with log entries.
        """
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM logs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
