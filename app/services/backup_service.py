import sqlite3
from datetime import datetime
from pathlib import Path

from app.config import get_data_dir, get_db_path
from app.db.schema import MIGRATIONS, migrate

REQUIRED_TABLES = {
    "utilisateur", "unite", "produit", "cloture_journee", "ligne_vente",
    "mouvement_stock", "categorie_recette", "recette_annexe", "parametre", "journal_audit",
}
AUTO_PREFIX = "auto_"


class BackupError(Exception):
    pass


def backup_dir() -> Path:
    path = get_data_dir() / "sauvegardes"
    path.mkdir(parents=True, exist_ok=True)
    return path


def create_backup(conn, dest_dir=None, prefix="anastcompta_") -> Path:
    """Copie cohérente de la base (API de sauvegarde SQLite) dans un fichier daté."""
    folder = Path(dest_dir) if dest_dir else backup_dir()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{prefix}{datetime.now():%Y%m%d_%H%M%S}.db"
    target = sqlite3.connect(str(path))
    try:
        conn.backup(target)
    finally:
        target.close()
    return path


def auto_backup(conn, keep=10):
    """Sauvegarde automatique si la base a changé depuis la dernière ; garde les `keep` dernières."""
    existing = sorted(backup_dir().glob(f"{AUTO_PREFIX}*.db"))
    if existing and get_db_path().stat().st_mtime <= existing[-1].stat().st_mtime:
        return None
    path = create_backup(conn, prefix=AUTO_PREFIX)
    for old in sorted(backup_dir().glob(f"{AUTO_PREFIX}*.db"))[:-keep]:
        old.unlink(missing_ok=True)
    return path


def validate_backup(path):
    path = Path(path)
    if not path.is_file():
        raise BackupError("Fichier introuvable.")
    try:
        src = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
        try:
            if src.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise BackupError("Le fichier de sauvegarde est endommagé.")
            tables = {r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            version = src.execute("PRAGMA user_version").fetchone()[0]
        finally:
            src.close()
    except sqlite3.DatabaseError:
        raise BackupError("Ce fichier n'est pas une sauvegarde AnastCompta valide.") from None
    if not REQUIRED_TABLES <= tables:
        raise BackupError("Ce fichier n'est pas une sauvegarde AnastCompta valide.")
    if version > len(MIGRATIONS):
        raise BackupError("Cette sauvegarde provient d'une version plus récente du logiciel.")


def restore_backup(conn, path, safety_dir=None):
    """Remplace les données actuelles par celles de la sauvegarde (copie de sécurité faite avant)."""
    validate_backup(path)
    create_backup(conn, safety_dir, prefix="avant_restauration_")
    src = sqlite3.connect(str(path))
    try:
        src.backup(conn)
    finally:
        src.close()
    migrate(conn)
    conn.execute("PRAGMA foreign_keys = ON")