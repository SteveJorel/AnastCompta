import hashlib
import hmac
import re
import secrets
import sqlite3
import time

ITERATIONS = 200_000
MIN_PASSWORD_LENGTH = 6
MAX_ATTEMPTS = 5
LOCK_SECONDS = 30
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sans 0/O/1/I pour éviter les confusions


class AuthError(Exception):
    """Erreur d'authentification ou de validation, message affichable à l'utilisateur."""


def _new_salt() -> str:
    return secrets.token_hex(16)


def _hash(secret: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", secret.encode("utf-8"), bytes.fromhex(salt_hex), ITERATIONS
    ).hex()


def _normalize_code(code: str) -> str:
    return re.sub(r"[\s-]", "", code).upper()


def _make_code_hash(code: str) -> str:
    salt = _new_salt()
    return f"{salt}${_hash(_normalize_code(code), salt)}"


def _check_code(code: str, stored: str | None) -> bool:
    if not stored or "$" not in stored:
        return False
    salt, expected = stored.split("$", 1)
    return hmac.compare_digest(_hash(_normalize_code(code), salt), expected)


def generate_recovery_code() -> str:
    groups = ["".join(secrets.choice(_ALPHABET) for _ in range(4)) for _ in range(3)]
    return "-".join(groups)


def validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AuthError(f"Le mot de passe doit contenir au moins {MIN_PASSWORD_LENGTH} caractères.")


def user_exists(conn: sqlite3.Connection) -> bool:
    return conn.execute("SELECT 1 FROM utilisateur WHERE id = 1").fetchone() is not None


def get_user(conn: sqlite3.Connection):
    return conn.execute("SELECT * FROM utilisateur WHERE id = 1").fetchone()


def create_user(conn: sqlite3.Connection, nom_complet: str, nom_utilisateur: str, password: str) -> str:
    """Crée le compte unique et retourne le code de récupération (affiché une seule fois)."""
    if user_exists(conn):
        raise AuthError("Un compte existe déjà.")
    nom_complet, nom_utilisateur = nom_complet.strip(), nom_utilisateur.strip()
    if not nom_complet or not nom_utilisateur:
        raise AuthError("Le nom du responsable et le nom d'utilisateur sont obligatoires.")
    validate_password(password)
    salt = _new_salt()
    code = generate_recovery_code()
    conn.execute(
        "INSERT INTO utilisateur (id, nom_complet, nom_utilisateur, mot_de_passe_hash, sel, "
        "code_recuperation_hash) VALUES (1, ?, ?, ?, ?, ?)",
        (nom_complet, nom_utilisateur, _hash(password, salt), salt, _make_code_hash(code)),
    )
    conn.commit()
    return code


def authenticate(conn: sqlite3.Connection, nom_utilisateur: str, password: str) -> bool:
    user = get_user(conn)
    if user is None:
        return False
    hash_ok = hmac.compare_digest(_hash(password, user["sel"]), user["mot_de_passe_hash"])
    name_ok = user["nom_utilisateur"].casefold() == nom_utilisateur.strip().casefold()
    return hash_ok and name_ok


def change_password(conn: sqlite3.Connection, old_password: str, new_password: str) -> None:
    user = get_user(conn)
    if user is None or not hmac.compare_digest(
        _hash(old_password, user["sel"]), user["mot_de_passe_hash"]
    ):
        raise AuthError("L'ancien mot de passe est incorrect.")
    validate_password(new_password)
    salt = _new_salt()
    conn.execute(
        "UPDATE utilisateur SET mot_de_passe_hash = ?, sel = ? WHERE id = 1",
        (_hash(new_password, salt), salt),
    )
    conn.commit()


def reset_password_with_code(conn: sqlite3.Connection, code: str, new_password: str) -> str:
    """Réinitialise le mot de passe avec le code de récupération. Retourne un NOUVEAU code."""
    user = get_user(conn)
    if user is None or not _check_code(code, user["code_recuperation_hash"]):
        raise AuthError("Code de récupération incorrect.")
    validate_password(new_password)
    salt = _new_salt()
    new_code = generate_recovery_code()
    conn.execute(
        "UPDATE utilisateur SET mot_de_passe_hash = ?, sel = ?, code_recuperation_hash = ? WHERE id = 1",
        (_hash(new_password, salt), salt, _make_code_hash(new_code)),
    )
    conn.commit()
    return new_code

def force_reset_password(conn: sqlite3.Connection, new_password: str) -> str:
    """Réinitialisation par le développeur, sans ancien mot de passe ni code. Retourne un NOUVEAU code."""
    if get_user(conn) is None:
        raise AuthError("Aucun compte à réinitialiser.")
    validate_password(new_password)
    salt = _new_salt()
    code = generate_recovery_code()
    conn.execute(
        "UPDATE utilisateur SET mot_de_passe_hash = ?, sel = ?, code_recuperation_hash = ? WHERE id = 1",
        (_hash(new_password, salt), salt, _make_code_hash(code)),
    )
    conn.commit()
    return code

class LoginThrottle:
    """Blocage de 30 s après 5 échecs de connexion consécutifs."""

    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._failures = 0
        self._locked_until = 0.0

    def remaining(self) -> int:
        left = self._locked_until - self._clock()
        return int(left) + 1 if left > 0 else 0

    def register_failure(self) -> None:
        self._failures += 1
        if self._failures >= MAX_ATTEMPTS:
            self._failures = 0
            self._locked_until = self._clock() + LOCK_SECONDS

    def reset(self) -> None:
        self._failures = 0
        self._locked_until = 0.0