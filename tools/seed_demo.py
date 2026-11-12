"""Génère une base de démonstration réaliste (30 jours d'activité) pour la recette."""
import random
from datetime import date, timedelta
from pathlib import Path

from app.db.schema import init_db
from app.services import auth_service as auth
from app.services import income_service as inc
from app.services import product_service as ps
from app.services import sales_service as ss

# (nom, unité, prix d'achat, prix de vente, popularité = ventes maximales par jour)
PRODUCTS = [
    ("Huile de palme", "litre", 1000, 1200, 6), ("Riz", "kg", 450, 550, 10),
    ("Sucre", "kg", 600, 700, 8), ("Sel", "kg", 200, 300, 4),
    ("Farine de blé", "kg", 500, 600, 5), ("Savon de lessive", "pièce", 250, 300, 12),
    ("Allumettes", "pièce", 50, 75, 20), ("Pétrole lampant", "litre", 650, 750, 8),
    ("Lait en poudre", "pièce", 500, 600, 6), ("Tomate concentrée", "pièce", 100, 150, 10),
    ("Spaghetti", "pièce", 300, 400, 8), ("Sardines", "pièce", 400, 500, 7),
    ("Piles", "pièce", 100, 150, 9), ("Bougies", "pièce", 100, 125, 12),
    ("Café", "pièce", 150, 200, 5), ("Thé", "pièce", 100, 150, 5),
    ("Biscuits", "pièce", 100, 150, 10), ("Eau minérale", "pièce", 350, 500, 14),
    ("Jus de fruit", "litre", 700, 900, 4), ("Spirale anti-moustique", "pièce", 150, 200, 6),
]


def build_demo(db_path, days=30, seed=42):
    """Crée la base de démonstration et retourne la connexion. Compte : demo / demo123."""
    rng = random.Random(seed)
    path = Path(db_path)
    if path.exists():
        path.unlink()
    conn = init_db(path)
    auth.create_user(conn, "Démo", "demo", "demo123")
    units = {u["libelle"]: u["id"] for u in ps.list_units(conn)}
    ids = {
        nom: ps.create_product(conn, nom, units[unite], pop * 10, achat, vente, seuil=pop * 2)
        for nom, unite, achat, vente, pop in PRODUCTS
    }
    cats = {c["code"]: c["id"] for c in inc.list_categories(conn)}

    today = date.today()
    for offset in range(days, 0, -1):
        day = (today - timedelta(days=offset)).isoformat()
        restants, total = {}, 0
        for nom, unite, achat, vente, pop in PRODUCTS:
            pid = ids[nom]
            product = ps.get_product(conn, pid)
            if product["quantite_stock"] < pop * 3:
                ps.restock(conn, pid, pop * 10)
                product = ps.get_product(conn, pid)
            stock = product["quantite_stock"]
            vendu = float(rng.randint(0, pop))
            if product["decimales"] and rng.random() < 0.3:
                vendu += 0.5
            vendu = min(vendu, stock)
            restant = round(stock - vendu, 6)
            restants[pid] = restant
            total += ss.compute_line(stock, restant, achat, vente)[1]
        encaisse = max(total - rng.choice([0, 0, 0, 0, 500, 1000, -500]), 0)
        ss.save_closure(conn, day, restants, encaisse)
        if rng.random() < 0.9:
            inc.add_income(conn, cats["MACHINE"], day, rng.randrange(2000, 9000, 500))
        if rng.random() < 0.5:
            inc.add_income(conn, cats["BOIS"], day, rng.randrange(1000, 6000, 500), "fagots")
    return conn


if __name__ == "__main__":
    target = Path("demo.db")
    connection = build_demo(target)
    count = connection.execute("SELECT COUNT(*) FROM cloture_journee").fetchone()[0]
    print(f"Base de démonstration créée : {target.resolve()} ({count} clôtures). Connexion : demo / demo123")
    connection.close()