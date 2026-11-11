import sqlite3

from app.services.audit import log_audit
from app.services.product_service import ProductError, add_movement, check_quantity
from app.utils.format import money_round, today_iso


class SalesError(Exception):
    pass


def get_closure(conn, date_iso):
    return conn.execute("SELECT * FROM cloture_journee WHERE date_cloture = ?", (date_iso,)).fetchone()


def get_closure_by_id(conn, closure_id):
    return conn.execute("SELECT * FROM cloture_journee WHERE id = ?", (closure_id,)).fetchone()


def latest_closure_date(conn):
    return conn.execute("SELECT MAX(date_cloture) FROM cloture_journee").fetchone()[0]


def list_closures(conn, start=None, end=None, limit=120):
    sql, params = "SELECT * FROM cloture_journee WHERE 1 = 1", []
    if start:
        sql += " AND date_cloture >= ?"
        params.append(start)
    if end:
        sql += " AND date_cloture <= ?"
        params.append(end)
    return conn.execute(sql + " ORDER BY date_cloture DESC LIMIT ?", (*params, limit)).fetchall()


def get_closure_lines(conn, closure_id):
    return conn.execute(
        "SELECT l.*, p.nom, u.libelle AS unite FROM ligne_vente l "
        "JOIN produit p ON p.id = l.produit_id JOIN unite u ON u.id = p.unite_id "
        "WHERE l.cloture_id = ? ORDER BY p.nom COLLATE NOCASE",
        (closure_id,),
    ).fetchall()


def compute_line(ouverture, restant, prix_achat, prix_vente):
    """Retourne (quantité vendue, montant théorique, coût d'achat, bénéfice)."""
    vendu = round(ouverture - restant, 6)
    montant = money_round(vendu * prix_vente)
    cout = money_round(vendu * prix_achat)
    return vendu, montant, cout, montant - cout


def build_sheet(conn, date_iso):
    """Feuille de clôture : une ligne (dict) par produit actif, ou déjà présent dans la clôture."""
    closure = get_closure(conn, date_iso)
    existing = {}
    if closure:
        existing = {l["produit_id"]: l for l in conn.execute(
            "SELECT * FROM ligne_vente WHERE cloture_id = ?", (closure["id"],))}
    products = conn.execute(
        "SELECT p.*, u.libelle AS unite, u.decimales_autorisees AS decimales "
        "FROM produit p JOIN unite u ON u.id = p.unite_id ORDER BY p.nom COLLATE NOCASE"
    ).fetchall()
    sheet = []
    for p in products:
        line = existing.get(p["id"])
        if not (p["actif"] or line):
            continue
        sheet.append({
            "produit_id": p["id"], "nom": p["nom"], "unite": p["unite"], "decimales": p["decimales"],
            "ouverture": line["stock_ouverture"] if line else p["quantite_stock"],
            "restant": line["stock_cloture"] if line else None,
            "prix_achat": line["prix_achat_unit"] if line else p["prix_achat"],
            "prix_vente": line["prix_vente_unit"] if line else p["prix_vente"],
        })
    return sheet


def save_closure(conn, date_iso, restants, montant_encaisse=None, commentaire=""):
    """Crée ou modifie (si c'est la dernière) la clôture d'une date.
    restants : {produit_id: quantité restante}. Un produit absent = non vendu."""
    if date_iso > today_iso():
        raise SalesError("La date ne peut pas être dans le futur.")
    latest = latest_closure_date(conn)
    if latest and date_iso < latest:
        raise SalesError("Une clôture plus récente existe déjà : seule la dernière clôture peut être modifiée.")
    if montant_encaisse is not None and montant_encaisse < 0:
        raise SalesError("Le montant encaissé ne peut pas être négatif.")

    closure = get_closure(conn, date_iso)
    computed = []
    for line in build_sheet(conn, date_iso):
        restant = restants.get(line["produit_id"], line["ouverture"])
        try:
            check_quantity(line["decimales"], restant, f"La quantité restante de « {line['nom']} »")
        except ProductError as exc:
            raise SalesError(str(exc)) from None
        if restant > line["ouverture"]:
            raise SalesError(
                f"« {line['nom']} » : la quantité restante dépasse le stock d'ouverture ({line['ouverture']:g})."
            )
        computed.append((line, restant, *compute_line(line["ouverture"], restant, line["prix_achat"], line["prix_vente"])))

    total = sum(c[3] for c in computed)
    cout = sum(c[4] for c in computed)
    benefice = sum(c[5] for c in computed)
    ecart = None if montant_encaisse is None else montant_encaisse - total
    comment = commentaire.strip() or None

    try:
        if closure:
            cid = closure["id"]
            for old in conn.execute("SELECT * FROM ligne_vente WHERE cloture_id = ?", (cid,)).fetchall():
                conn.execute(
                    "UPDATE produit SET quantite_stock = ROUND(quantite_stock + ?, 6) WHERE id = ?",
                    (old["quantite_vendue"], old["produit_id"]),
                )
            conn.execute("DELETE FROM ligne_vente WHERE cloture_id = ?", (cid,))
            conn.execute("DELETE FROM mouvement_stock WHERE cloture_id = ? AND type = 'SORTIE_VENTE'", (cid,))
            conn.execute(
                "UPDATE cloture_journee SET total_theorique = ?, total_cout_achat = ?, total_benefice = ?, "
                "montant_encaisse = ?, ecart_caisse = ?, commentaire = ?, "
                "modifie_le = datetime('now','localtime') WHERE id = ?",
                (total, cout, benefice, montant_encaisse, ecart, comment, cid),
            )
        else:
            cur = conn.execute(
                "INSERT INTO cloture_journee (date_cloture, total_theorique, total_cout_achat, total_benefice, "
                "montant_encaisse, ecart_caisse, commentaire) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (date_iso, total, cout, benefice, montant_encaisse, ecart, comment),
            )
            cid = cur.lastrowid

        for line, restant, vendu, montant, cout_l, benef_l in computed:
            pid = line["produit_id"]
            conn.execute(
                "INSERT INTO ligne_vente (cloture_id, produit_id, stock_ouverture, stock_cloture, quantite_vendue, "
                "prix_achat_unit, prix_vente_unit, montant_theorique, benefice) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (cid, pid, line["ouverture"], restant, vendu, line["prix_achat"], line["prix_vente"], montant, benef_l),
            )
            if vendu > 0:
                conn.execute(
                    "UPDATE produit SET quantite_stock = ROUND(quantite_stock - ?, 6), "
                    "modifie_le = datetime('now','localtime') WHERE id = ?",
                    (vendu, pid),
                )
                new_stock = conn.execute("SELECT quantite_stock FROM produit WHERE id = ?", (pid,)).fetchone()[0]
                add_movement(conn, pid, date_iso, "SORTIE_VENTE", -vendu, new_stock, cid)
        log_audit(conn, "CLOTURE_MODIFIEE" if closure else "CLOTURE_CREEE", "cloture_journee", cid,
                  f"{date_iso} : {total}")
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        raise SalesError("Enregistrement impossible : le stock actuel est insuffisant pour cette modification.") from None
    except Exception:
        conn.rollback()
        raise
    return cid