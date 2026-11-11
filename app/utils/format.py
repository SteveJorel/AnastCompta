import math
from datetime import date, datetime


def money_round(value: float) -> int:
    if value >= 0:
        return int(value + 0.5 + 1e-9)
    return -int(-value + 0.5 + 1e-9)


def fmt_money(value) -> str:
    return f"{int(value):,}".replace(",", " ")


def fmt_qty(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _to_float(text: str, message: str) -> float:
    cleaned = text.strip().replace("\u00a0", "").replace(" ", "").replace(",", ".")
    try:
        value = float(cleaned)
    except ValueError:
        raise ValueError(message) from None
    if not math.isfinite(value):
        raise ValueError(message)
    return value


def parse_amount(text: str) -> int:
    """Montant entier positif ou nul (ex. '12 500' -> 12500)."""
    value = _to_float(text, "Montant invalide.")
    if value < 0 or value != int(value):
        raise ValueError("Le montant doit être un nombre entier positif.")
    return int(value)


def parse_quantity(text: str) -> float:
    value = _to_float(text, "Quantité invalide.")
    if value < 0:
        raise ValueError("La quantité ne peut pas être négative.")
    return value


def today_iso() -> str:
    return date.today().isoformat()


def iso_to_fr(iso: str) -> str:
    return datetime.strptime(iso, "%Y-%m-%d").strftime("%d/%m/%Y")


def fr_to_iso(text: str) -> str:
    try:
        return datetime.strptime(text.strip(), "%d/%m/%Y").date().isoformat()
    except ValueError:
        raise ValueError("Date invalide (format attendu : JJ/MM/AAAA).") from None