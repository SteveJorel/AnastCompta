import sqlite3
from pathlib import Path

from app.config import get_db_path


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Ouvre une connexion SQLite avec les clés étrangères activées."""
    conn = sqlite3.connect(str(db_path or get_db_path()))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn