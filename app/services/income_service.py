from app.services.audit import log_audit
from app.utils.format import today_iso


class IncomeError(Exception):
    pass


def list_categories(conn):
    return conn.execute("SELECT * FROM categorie_recette WHERE actif = 1 ORDER BY id").fetchall()


def _check(montant, date_iso):
    if montant <= 0:
        raise IncomeError("Le montant doit être supérieur à 0.")
    if date_iso > today_iso():
        raise IncomeError("La date ne peut pas être dans le futur.")


def get_income(conn, income_id):
    row = conn.execute("SELECT * FROM recette_annexe WHERE id = ?", (income_id,)).fetchone()
    if row is None:
        raise IncomeError("Recette introuvable.")
    return row


def add_income(conn, categorie_id, date_iso, montant, note=""):
    _check(montant, date_iso)
    cur = conn.execute(
        "INSERT INTO recette_annexe (categorie_id, date_recette, montant, note) VALUES (?, ?, ?, ?)",
        (categorie_id, date_iso, montant, note.strip() or None),
    )
    log_audit(conn, "CREATION", "recette_annexe", cur.lastrowid, f"{date_iso} : {montant}")
    conn.commit()
    return cur.lastrowid


def update_income(conn, income_id, categorie_id, date_iso, montant, note=""):
    old = get_income(conn, income_id)
    _check(montant, date_iso)
    conn.execute(
        "UPDATE recette_annexe SET categorie_id = ?, date_recette = ?, montant = ?, note = ?, "
        "modifie_le = datetime('now','localtime') WHERE id = ?",
        (categorie_id, date_iso, montant, note.strip() or None, income_id),
    )
    log_audit(conn, "MODIFICATION", "recette_annexe", income_id,
              f"{old['date_recette']} : {old['montant']} -> {date_iso} : {montant}")
    conn.commit()


def delete_income(conn, income_id):
    old = get_income(conn, income_id)
    conn.execute("DELETE FROM recette_annexe WHERE id = ?", (income_id,))
    log_audit(conn, "SUPPRESSION", "recette_annexe", income_id, f"{old['date_recette']} : {old['montant']}")
    conn.commit()


def _filters(categorie_id, start, end):
    clauses, params = [], []
    if categorie_id is not None:
        clauses.append("r.categorie_id = ?")
        params.append(categorie_id)
    if start:
        clauses.append("r.date_recette >= ?")
        params.append(start)
    if end:
        clauses.append("r.date_recette <= ?")
        params.append(end)
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


def list_incomes(conn, categorie_id=None, start=None, end=None):
    where, params = _filters(categorie_id, start, end)
    return conn.execute(
        "SELECT r.*, c.libelle AS activite, c.code FROM recette_annexe r "
        "JOIN categorie_recette c ON c.id = r.categorie_id" + where +
        " ORDER BY r.date_recette DESC, r.id DESC", params,
    ).fetchall()


def total(conn, categorie_id=None, start=None, end=None):
    where, params = _filters(categorie_id, start, end)
    return conn.execute("SELECT COALESCE(SUM(r.montant), 0) FROM recette_annexe r" + where, params).fetchone()[0]


def totals_by_category(conn, start, end):
    """{'MACHINE': total, 'BOIS': total, ...} sur la période (bornes incluses)."""
    rows = conn.execute(
        "SELECT c.code, COALESCE(SUM(r.montant), 0) AS total FROM categorie_recette c "
        "LEFT JOIN recette_annexe r ON r.categorie_id = c.id AND r.date_recette BETWEEN ? AND ? "
        "GROUP BY c.id", (start, end),
    ).fetchall()
    return {r["code"]: r["total"] for r in rows}