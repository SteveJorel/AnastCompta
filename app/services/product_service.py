import sqlite3

from app.services.audit import log_audit
from app.utils.format import money_round, today_iso


class ProductError(Exception):
    pass


_SELECT = (
    "SELECT p.*, u.libelle AS unite, u.decimales_autorisees AS decimales "
    "FROM produit p JOIN unite u ON u.id = p.unite_id"
)
_NOW = "datetime('now','localtime')"


def list_units(conn):
    return conn.execute("SELECT * FROM unite ORDER BY libelle").fetchall()


def add_unit(conn, libelle, decimales):
    libelle = libelle.strip()
    if not libelle:
        raise ProductError("Le nom de l'unité est obligatoire.")
    try:
        cur = conn.execute(
            "INSERT INTO unite (libelle, decimales_autorisees) VALUES (?, ?)",
            (libelle, 1 if decimales else 0),
        )
    except sqlite3.IntegrityError:
        raise ProductError("Cette unité existe déjà.") from None
    conn.commit()
    return cur.lastrowid


def check_quantity(unit_decimals, quantity, label="La quantité"):
    if quantity < 0:
        raise ProductError(f"{label} ne peut pas être négative.")
    if not unit_decimals and quantity != int(quantity):
        raise ProductError(f"{label} doit être un nombre entier pour cette unité.")


def list_products(conn, search="", include_inactive=False):
    sql = _SELECT + " WHERE p.nom LIKE ?"
    if not include_inactive:
        sql += " AND p.actif = 1"
    return conn.execute(sql + " ORDER BY p.nom COLLATE NOCASE", (f"%{search.strip()}%",)).fetchall()


def get_product(conn, product_id):
    row = conn.execute(_SELECT + " WHERE p.id = ?", (product_id,)).fetchone()
    if row is None:
        raise ProductError("Produit introuvable.")
    return row


def margin(prix_achat, prix_vente):
    """Marge par unité et taux de marge en % (None si prix d'achat nul)."""
    marge = prix_vente - prix_achat
    taux = marge / prix_achat * 100 if prix_achat > 0 else None
    return marge, taux


def forecast_profit(product):
    return money_round((product["prix_vente"] - product["prix_achat"]) * product["quantite_stock"])


def low_stock(conn):
    return conn.execute(
        _SELECT + " WHERE p.actif = 1 AND p.seuil_alerte IS NOT NULL "
        "AND p.quantite_stock <= p.seuil_alerte ORDER BY p.nom COLLATE NOCASE"
    ).fetchall()


def add_movement(conn, produit_id, date_iso, type_, quantite, stock_apres, cloture_id=None, note=None):
    conn.execute(
        "INSERT INTO mouvement_stock (produit_id, date_mvt, type, quantite, stock_apres, cloture_id, note) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (produit_id, date_iso, type_, quantite, stock_apres, cloture_id, note or None),
    )


def _validate(nom, prix_achat, prix_vente):
    if not nom.strip():
        raise ProductError("Le nom du produit est obligatoire.")
    if prix_achat < 0 or prix_vente < 0:
        raise ProductError("Les prix ne peuvent pas être négatifs.")


def _unit(conn, unite_id):
    unit = conn.execute("SELECT * FROM unite WHERE id = ?", (unite_id,)).fetchone()
    if unit is None:
        raise ProductError("Unité invalide.")
    return unit


def create_product(conn, nom, unite_id, quantite, prix_achat, prix_vente, seuil=None):
    _validate(nom, prix_achat, prix_vente)
    unit = _unit(conn, unite_id)
    check_quantity(unit["decimales_autorisees"], quantite, "Le stock initial")
    try:
        cur = conn.execute(
            "INSERT INTO produit (nom, unite_id, quantite_stock, prix_achat, prix_vente, seuil_alerte) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (nom.strip(), unite_id, quantite, prix_achat, prix_vente, seuil),
        )
    except sqlite3.IntegrityError:
        raise ProductError("Un produit porte déjà ce nom.") from None
    pid = cur.lastrowid
    if quantite > 0:
        add_movement(conn, pid, today_iso(), "INITIAL", quantite, quantite)
    log_audit(conn, "CREATION", "produit", pid, nom.strip())
    conn.commit()
    return pid


def update_product(conn, pid, nom, unite_id, prix_achat, prix_vente, seuil=None):
    product = get_product(conn, pid)
    _validate(nom, prix_achat, prix_vente)
    unit = _unit(conn, unite_id)
    check_quantity(unit["decimales_autorisees"], product["quantite_stock"], "Le stock actuel")
    try:
        conn.execute(
            f"UPDATE produit SET nom = ?, unite_id = ?, prix_achat = ?, prix_vente = ?, "
            f"seuil_alerte = ?, modifie_le = {_NOW} WHERE id = ?",
            (nom.strip(), unite_id, prix_achat, prix_vente, seuil, pid),
        )
    except sqlite3.IntegrityError:
        raise ProductError("Un produit porte déjà ce nom.") from None
    log_audit(conn, "MODIFICATION", "produit", pid, nom.strip())
    conn.commit()


def set_active(conn, pid, actif):
    conn.execute(f"UPDATE produit SET actif = ?, modifie_le = {_NOW} WHERE id = ?", (1 if actif else 0, pid))
    log_audit(conn, "ACTIVATION" if actif else "DESACTIVATION", "produit", pid)
    conn.commit()


def _set_stock(conn, pid, new_stock, prix_achat=None):
    if prix_achat is None:
        conn.execute(f"UPDATE produit SET quantite_stock = ?, modifie_le = {_NOW} WHERE id = ?", (new_stock, pid))
    else:
        conn.execute(
            f"UPDATE produit SET quantite_stock = ?, prix_achat = ?, modifie_le = {_NOW} WHERE id = ?",
            (new_stock, prix_achat, pid),
        )


def restock(conn, pid, quantite, nouveau_prix_achat=None, note=""):
    product = get_product(conn, pid)
    if quantite <= 0:
        raise ProductError("La quantité reçue doit être supérieure à 0.")
    check_quantity(product["decimales"], quantite)
    new_stock = round(product["quantite_stock"] + quantite, 6)
    _set_stock(conn, pid, new_stock, nouveau_prix_achat)
    add_movement(conn, pid, today_iso(), "ENTREE", quantite, new_stock, note=note)
    log_audit(conn, "REAPPROVISIONNEMENT", "produit", pid, f"+{quantite}")
    conn.commit()


def adjust_stock(conn, pid, nouvelle_quantite, note=""):
    product = get_product(conn, pid)
    check_quantity(product["decimales"], nouvelle_quantite, "Le stock")
    diff = round(nouvelle_quantite - product["quantite_stock"], 6)
    if diff == 0:
        return
    _set_stock(conn, pid, nouvelle_quantite)
    add_movement(conn, pid, today_iso(), "AJUSTEMENT", diff, nouvelle_quantite, note=note)
    log_audit(conn, "AJUSTEMENT_STOCK", "produit", pid, f"{diff:+g}")
    conn.commit()


def declare_loss(conn, pid, quantite, note=""):
    product = get_product(conn, pid)
    if quantite <= 0:
        raise ProductError("La quantité perdue doit être supérieure à 0.")
    check_quantity(product["decimales"], quantite)
    if quantite > product["quantite_stock"]:
        raise ProductError("La perte dépasse le stock disponible.")
    new_stock = round(product["quantite_stock"] - quantite, 6)
    _set_stock(conn, pid, new_stock)
    add_movement(conn, pid, today_iso(), "PERTE", -quantite, new_stock, note=note)
    log_audit(conn, "PERTE", "produit", pid, f"-{quantite}")
    conn.commit()