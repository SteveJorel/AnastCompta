import calendar
import csv
from datetime import date, timedelta
from html import escape

from app.utils.format import fmt_money, fmt_qty, iso_to_fr

MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
          "septembre", "octobre", "novembre", "décembre"]
ADJECTIVES = {"jour": "journalier", "semaine": "hebdomadaire", "mois": "mensuel"}


def _d(iso):
    return date.fromisoformat(iso)


def period_bounds(kind, date_iso):
    """Bornes (début, fin) de la période contenant la date. Semaine = lundi au dimanche."""
    d = _d(date_iso)
    if kind == "jour":
        return d.isoformat(), d.isoformat()
    if kind == "semaine":
        start = d - timedelta(days=d.weekday())
        return start.isoformat(), (start + timedelta(days=6)).isoformat()
    if kind == "mois":
        last = calendar.monthrange(d.year, d.month)[1]
        return d.replace(day=1).isoformat(), d.replace(day=last).isoformat()
    raise ValueError(f"Période inconnue : {kind}")


def shift_period(kind, date_iso, direction):
    """Décale la date de référence d'une période (direction = -1 ou +1)."""
    d = _d(date_iso)
    if kind == "jour":
        return (d + timedelta(days=direction)).isoformat()
    if kind == "semaine":
        return (d + timedelta(days=7 * direction)).isoformat()
    month = d.month - 1 + direction
    year, month = d.year + month // 12, month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day).isoformat()


def period_label(kind, start, end):
    if kind == "jour":
        return iso_to_fr(start)
    if kind == "semaine":
        return f"du {iso_to_fr(start)} au {iso_to_fr(end)}"
    d = _d(start)
    return f"{MONTHS[d.month - 1]} {d.year}"


def report_title(kind, start, end, shop=""):
    prefix = f"{shop} — " if shop else ""
    return f"{prefix}Bilan {ADJECTIVES[kind]} : {period_label(kind, start, end)}"


def variation_pct(current, previous):
    return None if previous <= 0 else (current - previous) / previous * 100


def summary(conn, start, end):
    row = conn.execute(
        "SELECT COALESCE(SUM(total_theorique), 0) AS ca, COALESCE(SUM(total_cout_achat), 0) AS cout, "
        "COALESCE(SUM(total_benefice), 0) AS benef, COALESCE(SUM(montant_encaisse), 0) AS encaisse, "
        "COALESCE(SUM(ecart_caisse), 0) AS ecart, COUNT(*) AS nb "
        "FROM cloture_journee WHERE date_cloture BETWEEN ? AND ?", (start, end),
    ).fetchone()
    annexes = conn.execute(
        "SELECT c.code, c.libelle, COALESCE(SUM(r.montant), 0) AS total FROM categorie_recette c "
        "LEFT JOIN recette_annexe r ON r.categorie_id = c.id AND r.date_recette BETWEEN ? AND ? "
        "WHERE c.actif = 1 OR r.id IS NOT NULL GROUP BY c.id ORDER BY c.id", (start, end),
    ).fetchall()
    annexes_list = [(a["code"], a["libelle"], a["total"]) for a in annexes]
    total_annexes = sum(a[2] for a in annexes_list)
    return {
        "start": start, "end": end,
        "boutique": row["ca"], "cout_achat": row["cout"], "benefice_boutique": row["benef"],
        "encaisse": row["encaisse"], "ecart": row["ecart"], "nb_clotures": row["nb"],
        "annexes": annexes_list, "total_annexes": total_annexes,
        "ca_global": row["ca"] + total_annexes,
        "benefice_total": row["benef"] + total_annexes,
    }


def daily_breakdown(conn, start, end):
    """Une ligne par jour de la période (même les jours sans activité)."""
    closures = {r["date_cloture"]: r for r in conn.execute(
        "SELECT date_cloture, total_theorique, total_benefice FROM cloture_journee "
        "WHERE date_cloture BETWEEN ? AND ?", (start, end))}
    annexes = {}
    for r in conn.execute(
        "SELECT r.date_recette AS d, c.code AS code, SUM(r.montant) AS total FROM recette_annexe r "
        "JOIN categorie_recette c ON c.id = r.categorie_id WHERE r.date_recette BETWEEN ? AND ? "
        "GROUP BY r.date_recette, c.code", (start, end)):
        annexes.setdefault(r["d"], {})[r["code"]] = r["total"]
    rows, day, last = [], _d(start), _d(end)
    while day <= last:
        iso = day.isoformat()
        closure = closures.get(iso)
        boutique = closure["total_theorique"] if closure else 0
        benefice_boutique = closure["total_benefice"] if closure else 0
        ann = annexes.get(iso, {})
        rows.append({
            "date": iso, "boutique": boutique, "annexes": ann,
            "total": boutique + sum(ann.values()),
            "benefice": benefice_boutique + sum(ann.values()),
        })
        day += timedelta(days=1)
    return rows


def top_products(conn, start, end, limit=15):
    return conn.execute(
        "SELECT p.nom, u.libelle AS unite, SUM(l.quantite_vendue) AS quantite, "
        "SUM(l.montant_theorique) AS montant, SUM(l.benefice) AS benefice "
        "FROM ligne_vente l JOIN cloture_journee c ON c.id = l.cloture_id "
        "JOIN produit p ON p.id = l.produit_id JOIN unite u ON u.id = p.unite_id "
        "WHERE c.date_cloture BETWEEN ? AND ? GROUP BY p.id HAVING SUM(l.quantite_vendue) > 0 "
        "ORDER BY benefice DESC LIMIT ?", (start, end, limit),
    ).fetchall()


def report_sections(conn, start, end):
    """Contenu du bilan : liste de (titre, en-têtes, lignes), utilisée pour le CSV et l'impression."""
    s = summary(conn, start, end)
    cats = [(code, libelle) for code, libelle, _ in s["annexes"]]
    synthese = [["Ventes boutique (théorique)", s["boutique"]]]
    synthese += [[libelle, total] for _, libelle, total in s["annexes"]]
    synthese += [
        ["Chiffre d'affaires global", s["ca_global"]],
        ["Coût d'achat des marchandises vendues", s["cout_achat"]],
        ["Bénéfice boutique", s["benefice_boutique"]],
        ["Bénéfice total", s["benefice_total"]],
        ["Montant encaissé (boutique)", s["encaisse"]],
        ["Écart de caisse cumulé", s["ecart"]],
    ]
    header = ["Date", "Boutique"] + [libelle for _, libelle in cats] + ["Total", "Bénéfice"]
    detail = [
        [iso_to_fr(r["date"]), r["boutique"]] + [r["annexes"].get(code, 0) for code, _ in cats]
        + [r["total"], r["benefice"]]
        for r in daily_breakdown(conn, start, end)
    ]
    produits = [
        [p["nom"], p["unite"], fmt_qty(p["quantite"]), p["montant"], p["benefice"]]
        for p in top_products(conn, start, end, 100)
    ]
    return [
        ("Synthèse", ["Indicateur", "Montant"], synthese),
        ("Détail par jour", header, detail),
        ("Produits vendus", ["Produit", "Unité", "Quantité vendue", "Montant", "Bénéfice"], produits),
    ]


def write_csv(path, title, sections):
    """CSV compatible Excel (séparateur ; et encodage UTF-8 avec BOM)."""
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow([title])
        writer.writerow([])
        for name, header, rows in sections:
            writer.writerow([name])
            writer.writerow(header)
            writer.writerows(rows)
            writer.writerow([])


_STYLE = ("body{font-family:'Segoe UI',Arial,sans-serif;margin:30px;color:#222}"
          "table{border-collapse:collapse;margin-bottom:28px}"
          "th,td{border:1px solid #999;padding:5px 12px;text-align:right}"
          "th:first-child,td:first-child{text-align:left}th{background:#eee}")


def _cell(value):
    return fmt_money(value) if isinstance(value, int) else escape(str(value))


def build_html(title, sections):
    """Page HTML imprimable (à ouvrir dans le navigateur, puis Ctrl+P)."""
    parts = [
        "<!DOCTYPE html><html lang='fr'><head><meta charset='utf-8'>",
        f"<title>{escape(title)}</title><style>{_STYLE}</style></head><body>",
        f"<h1>{escape(title)}</h1>",
    ]
    for name, header, rows in sections:
        parts.append(f"<h2>{escape(name)}</h2><table><tr>")
        parts.append("".join(f"<th>{escape(h)}</th>" for h in header) + "</tr>")
        for row in rows:
            parts.append("<tr>" + "".join(f"<td>{_cell(c)}</td>" for c in row) + "</tr>")
        parts.append("</table>")
    parts.append("</body></html>")
    return "".join(parts)