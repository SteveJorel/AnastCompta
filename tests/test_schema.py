import os
import sqlite3
import tempfile
import unittest

from app.db.schema import init_db, MIGRATIONS

TABLES = {
    "utilisateur", "unite", "produit", "cloture_journee", "ligne_vente",
    "mouvement_stock", "categorie_recette", "recette_annexe", "parametre", "journal_audit",
}


class TestSchema(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

    def tearDown(self):
        os.remove(self.path)

    def test_creation_tables_et_version(self):
        conn = init_db(self.path)
        noms = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue(TABLES.issubset(noms))
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], len(MIGRATIONS))
        conn.close()

    def test_init_idempotent(self):
        init_db(self.path).close()
        conn = init_db(self.path)  # second appel : ne doit rien casser ni dupliquer
        n = conn.execute("SELECT COUNT(*) FROM categorie_recette").fetchone()[0]
        self.assertEqual(n, 2)
        conn.close()

    def test_cles_etrangeres_actives(self):
        conn = init_db(self.path)
        self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO produit (nom, unite_id, prix_achat, prix_vente) VALUES ('X', 999, 1, 2)"
            )
        conn.close()

    def test_compte_unique(self):
        conn = init_db(self.path)
        sql = ("INSERT INTO utilisateur (id, nom_complet, nom_utilisateur, mot_de_passe_hash, sel) "
               "VALUES (?, 'A', ?, 'h', 's')")
        conn.execute(sql, (1, "a"))
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute(sql, (2, "b"))
        conn.close()


if __name__ == "__main__":
    unittest.main()