from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .config import settings


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None


def rows_to_dicts(items: list[sqlite3.Row]) -> list[dict]:
    return [dict(item) for item in items]


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    path = Path(settings.db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS business_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            business_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT NOT NULL,
            address TEXT NOT NULL,
            timezone TEXT NOT NULL,
            booking_notice TEXT NOT NULL,
            slot_interval INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL CHECK(duration_minutes > 0),
            price REAL NOT NULL CHECK(price >= 0),
            active INTEGER NOT NULL DEFAULT 1,
            color TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            bio TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS staff_services (
            staff_id INTEGER NOT NULL REFERENCES staff(id) ON DELETE CASCADE,
            service_id INTEGER NOT NULL REFERENCES services(id) ON DELETE CASCADE,
            PRIMARY KEY(staff_id, service_id)
        );

        CREATE TABLE IF NOT EXISTS availability (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id INTEGER NOT NULL REFERENCES staff(id) ON DELETE CASCADE,
            weekday INTEGER NOT NULL CHECK(weekday BETWEEN 0 AND 6),
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS blocked_times (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id INTEGER NOT NULL REFERENCES staff(id) ON DELETE CASCADE,
            block_date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            reason TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            customer_email TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            service_id INTEGER NOT NULL REFERENCES services(id),
            staff_id INTEGER NOT NULL REFERENCES staff(id),
            appointment_date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            status TEXT NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            description TEXT NOT NULL,
            appointment_id INTEGER REFERENCES appointments(id) ON DELETE SET NULL,
            created_at TEXT NOT NULL
        );
        """
    )
