import os
from pathlib import Path

APP_NAME = "AnastCompta"
VERSION = "0.2.0"


def get_data_dir() -> Path:
    """Dossier des données utilisateur : %APPDATA%\\AnastCompta (jamais le dossier temporaire du .exe)."""
    base = os.environ.get("APPDATA") or str(Path.home())
    path = Path(base) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_db_path() -> Path:
    return get_data_dir() / "anastcompta.db"