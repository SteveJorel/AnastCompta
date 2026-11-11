import sqlite3
from pathlib import Path

from app.db.connection import get_connection

MIGRATION_1 = """
CREATE TABLE utilisateur (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    nom_complet TEXT NOT NULL,
    nom_utilisateur TEXT NOT NULL UNIQUE,
    mot_de_passe_hash TEXT NOT NULL,
    sel TEXT NOT NULL,
    code_recuperation_hash TEXT,
    cree_le TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE unite (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    libelle TEXT NOT NULL UNIQUE,
    decimales_autorisees INTEGER NOT NULL DEFAULT 0 CHECK (decimales_autorisees IN (0,1))
);

CREATE TABLE produit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL UNIQUE,
    unite_id INTEGER NOT NULL REFERENCES unite(id),
    quantite_stock REAL NOT NULL DEFAULT 0 CHECK (quantite_stock >= 0),
    prix_achat INTEGER NOT NULL CHECK (prix_achat >= 0),
    prix_vente INTEGER NOT NULL CHECK (prix_vente >= 0),
    seuil_alerte REAL,
    actif INTEGER NOT NULL DEFAULT 1,
    cree_le TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    modifie_le TEXT
);

CREATE TABLE cloture_journee (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date_cloture TEXT NOT NULL UNIQUE,
    total_theorique INTEGER NOT NULL DEFAULT 0,
    total_cout_achat INTEGER NOT NULL DEFAULT 0,
    total_benefice INTEGER NOT NULL DEFAULT 0,
    montant_encaisse INTEGER,
    ecart_caisse INTEGER,
    commentaire TEXT,
    cree_le TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    modifie_le TEXT
);

CREATE TABLE ligne_vente (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cloture_id INTEGER NOT NULL REFERENCES cloture_journee(id) ON DELETE CASCADE,
    produit_id INTEGER NOT NULL REFERENCES produit(id),
    stock_ouverture REAL NOT NULL,
    stock_cloture REAL NOT NULL,
    quantite_vendue REAL NOT NULL CHECK (quantite_vendue >= 0),
    prix_achat_unit INTEGER NOT NULL,
    prix_vente_unit INTEGER NOT NULL,
    montant_theorique INTEGER NOT NULL,
    benefice INTEGER NOT NULL,
    UNIQUE (cloture_id, produit_id)
);

CREATE TABLE mouvement_stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    produit_id INTEGER NOT NULL REFERENCES produit(id),
    date_mvt TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('INITIAL','ENTREE','SORTIE_VENTE','AJUSTEMENT','PERTE')),
    quantite REAL NOT NULL,
    stock_apres REAL NOT NULL,
    cloture_id INTEGER REFERENCES cloture_journee(id) ON DELETE SET NULL,
    note TEXT,
    cree_le TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE categorie_recette (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    libelle TEXT NOT NULL,
    actif INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE recette_annexe (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    categorie_id INTEGER NOT NULL REFERENCES categorie_recette(id),
    date_recette TEXT NOT NULL,
    montant INTEGER NOT NULL CHECK (montant > 0),
    note TEXT,
    cree_le TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    modifie_le TEXT
);

CREATE TABLE parametre (
    cle TEXT PRIMARY KEY,
    valeur TEXT NOT NULL
);

CREATE TABLE journal_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date_heure TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    action TEXT NOT NULL,
    entite TEXT NOT NULL,
    entite_id INTEGER,
    detail TEXT
);

CREATE INDEX idx_recette_date ON recette_annexe(date_recette);
CREATE INDEX idx_mvt_produit ON mouvement_stock(produit_id, date_mvt);
CREATE INDEX idx_vente_cloture ON ligne_vente(cloture_id);

INSERT INTO categorie_recette (code, libelle) VALUES
    ('MACHINE', 'Machine à écraser'),
    ('BOIS', 'Bois de chauffage');

INSERT INTO unite (libelle, decimales_autorisees) VALUES
    ('pièce', 0), ('litre', 1), ('kg', 1);

INSERT INTO parametre (cle, valeur) VALUES
    ('nom_boutique', ''), ('devise', 'FCFA');
"""

# Ajouter ici MIGRATION_2, etc. pour les futures évolutions.
MIGRATIONS = [MIGRATION_1]


def init_db(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Crée ou met à jour la base, puis retourne une connexion prête à l'emploi."""
    conn = get_connection(db_path)
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    for number, script in enumerate(MIGRATIONS, start=1):
        if number > version:
            conn.executescript(script)
            conn.execute(f"PRAGMA user_version = {number}")
            conn.commit()
    return conn