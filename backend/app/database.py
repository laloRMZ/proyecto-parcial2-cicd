import hashlib
import hmac
import os
import secrets
import sqlite3
from contextlib import contextmanager
from typing import Dict, List, Optional

from opentelemetry import trace

tracer = trace.get_tracer("proyecto2.db")


def get_db_path() -> str:
    return os.getenv("DATABASE_PATH", os.path.join(os.getcwd(), "data", "app.db"))


def hash_password(password: str, salt: Optional[str] = None) -> str:
    salt_val = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_val.encode("utf-8"), 100_000).hex()
    return f"{salt_val}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    if "$" not in stored_hash:
        return False
    salt_val, expected_digest = stored_hash.split("$", 1)
    actual_digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_val.encode("utf-8"), 100_000).hex()
    return hmac.compare_digest(actual_digest, expected_digest)


@contextmanager
def get_connection():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                password_hash TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        default_user = os.getenv("DEFAULT_ADMIN_USER", "admin")
        default_pass = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
        existing = conn.execute("SELECT id FROM users WHERE username = ?", (default_user,)).fetchone()
        if not existing:
            conn.execute(
                """
                INSERT INTO users (username, email, full_name, role, password_hash, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (default_user, "admin@proyecto2.local", "Administrador", "admin", hash_password(default_pass)),
            )
        conn.commit()


def _serialize_user(row: sqlite3.Row) -> Dict:
    return {
        "id": row["id"],
        "username": row["username"],
        "email": row["email"],
        "full_name": row["full_name"],
        "role": row["role"],
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
    }


def authenticate_user(username: str, password: str) -> Optional[Dict]:
    with tracer.start_as_current_span("db.authenticate_user"):
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ? AND is_active = 1",
                (username,),
            ).fetchone()
            if not row or not verify_password(password, row["password_hash"]):
                return None
            return _serialize_user(row)


def list_users() -> List[Dict]:
    with tracer.start_as_current_span("db.list_users"):
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT id, username, email, full_name, role, is_active, created_at FROM users ORDER BY id DESC"
            ).fetchall()
            return [_serialize_user(row) for row in rows]


def get_user_by_id(user_id: int) -> Optional[Dict]:
    with tracer.start_as_current_span("db.get_user_by_id"):
        with get_connection() as conn:
            row = conn.execute(
                "SELECT id, username, email, full_name, role, is_active, created_at FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            return _serialize_user(row) if row else None


def create_user(username: str, email: str, full_name: str, role: str, password: str) -> Dict:
    with tracer.start_as_current_span("db.create_user"):
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (username, email, full_name, role, password_hash, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (username, email, full_name, role, hash_password(password)),
            )
            conn.commit()
            row = conn.execute(
                "SELECT id, username, email, full_name, role, is_active, created_at FROM users WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
            return _serialize_user(row)


def update_user(
    user_id: int,
    email: Optional[str] = None,
    full_name: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    password: Optional[str] = None,
) -> Optional[Dict]:
    with tracer.start_as_current_span("db.update_user"):
        with get_connection() as conn:
            current = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            if not current:
                return None

            new_email = email if email is not None else current["email"]
            new_full_name = full_name if full_name is not None else current["full_name"]
            new_role = role if role is not None else current["role"]
            new_active = int(is_active) if is_active is not None else current["is_active"]
            new_hash = hash_password(password) if password else current["password_hash"]

            conn.execute(
                """
                UPDATE users
                SET email = ?, full_name = ?, role = ?, is_active = ?, password_hash = ?
                WHERE id = ?
                """,
                (new_email, new_full_name, new_role, new_active, new_hash, user_id),
            )
            conn.commit()
            row = conn.execute(
                "SELECT id, username, email, full_name, role, is_active, created_at FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            return _serialize_user(row)


def delete_user(user_id: int) -> bool:
    with tracer.start_as_current_span("db.delete_user"):
        with get_connection() as conn:
            cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            return cursor.rowcount > 0
