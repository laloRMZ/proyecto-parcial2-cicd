import os
import sqlite3
from contextlib import contextmanager
from typing import Dict, List, Optional

from opentelemetry import trace

tracer = trace.get_tracer("proyecto2.db")


def get_db_path() -> str:
    return os.getenv("DATABASE_PATH", os.path.join(os.getcwd(), "data", "items.db"))


def init_db() -> None:
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


@contextmanager
def get_connection():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def list_items() -> List[Dict]:
    with tracer.start_as_current_span("db.list_items"):
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT id, title, description, status, created_at FROM items ORDER BY id DESC"
            ).fetchall()
            return [dict(row) for row in rows]


def create_item(title: str, description: str, status: str) -> Dict:
    with tracer.start_as_current_span("db.create_item"):
        with get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO items (title, description, status) VALUES (?, ?, ?)",
                (title, description, status),
            )
            conn.commit()
            row = conn.execute(
                "SELECT id, title, description, status, created_at FROM items WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
            return dict(row)


def delete_item(item_id: int) -> bool:
    with tracer.start_as_current_span("db.delete_item"):
        with get_connection() as conn:
            cursor = conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
            conn.commit()
            return cursor.rowcount > 0


def get_item(item_id: int) -> Optional[Dict]:
    with tracer.start_as_current_span("db.get_item"):
        with get_connection() as conn:
            row = conn.execute(
                "SELECT id, title, description, status, created_at FROM items WHERE id = ?",
                (item_id,),
            ).fetchone()
            return dict(row) if row else None
