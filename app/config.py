import os
import sys
from pathlib import Path

APP_NAME = "AnastCompta"


def get_data_dir() -> Path:
    """Dossier des données utilisateur : %APPDATA%\\AnastCompta (jamais le dossier temporaire du .exe)."""
    base = os.environ.get("APPDATA") or str(Path.home())
    path = Path(base) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_db_path() -> Path:
    override = os.environ.get("ANASTCOMPTA_DB")  # pour les tests sur une base de démonstration
    return Path(override) if override else get_data_dir() / "anastcompta.db"


def resource_path(relative: str) -> Path:
    """Chemin d'une ressource embarquée (fonctionne en développement et dans le .exe)."""
    base = getattr(sys, "_MEIPASS", None)
    root = Path(base) if base else Path(__file__).resolve().parent.parent
    return root / relative