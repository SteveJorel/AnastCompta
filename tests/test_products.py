import os
import tempfile
import unittest

from app.db.schema import init_db
from app.services import product_service as ps


class TestProducts(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.conn = init_db(self.path)
        units = {u["libelle"]: u["id"] for u in ps.list_units(self.conn)}
        self.piece, self.kg = units["pièce"], units["kg"]

    def tearDown(self):
        self.conn.close()
        os.remove(self.path)

    def nouveau(self, nom="Huile", stock=10, seuil=None):
        return ps.create_product(self.conn, nom, self.piece, stock, 100, 150, seuil)

    def test_creation_et_mouvement_initial(self):
        pid = self.nouveau()
        self.assertEqual(ps.get_product(self.conn, pid)["quantite_stock"], 10)
        n = self.conn.execute(
            "SELECT COUNT(*) FROM mouvement_stock WHERE produit_id = ? AND type = 'INITIAL'", (pid,)
        ).fetchone()[0]
        self.assertEqual(n, 1)

    def test_marge_et_benefice_previsionnel(self):
        self.assertEqual(ps.margin(100, 150), (50, 50.0))
        self.assertEqual(ps.margin(0, 150), (150, None))
        pid = self.nouveau()
        self.assertEqual(ps.forecast_profit(ps.get_product(self.conn, pid)), 500)

    def test_nom_unique(self):
        self.nouveau()
        with self.assertRaises(ps.ProductError):
            self.nouveau()

    def test_quantite_decimale(self):
        with self.assertRaises(ps.ProductError):
            ps.create_product(self.conn, "Bidon", self.piece, 2.5, 100, 150)
        pid = ps.create_product(self.conn, "Riz", self.kg, 2.5, 400, 500)
        self.assertEqual(ps.get_product(self.conn, pid)["quantite_stock"], 2.5)

    def test_reapprovisionnement(self):
        pid = self.nouveau()
        ps.restock(self.conn, pid, 5, 120)
        p = ps.get_product(self.conn, pid)
        self.assertEqual((p["quantite_stock"], p["prix_achat"]), (15, 120))

    def test_perte_et_ajustement(self):
        pid = self.nouveau()
        ps.declare_loss(self.conn, pid, 3)
        self.assertEqual(ps.get_product(self.conn, pid)["quantite_stock"], 7)
        with self.assertRaises(ps.ProductError):
            ps.declare_loss(self.conn, pid, 100)
        ps.adjust_stock(self.conn, pid, 12)
        self.assertEqual(ps.get_product(self.conn, pid)["quantite_stock"], 12)
        diff = self.conn.execute("SELECT quantite FROM mouvement_stock WHERE type = 'AJUSTEMENT'").fetchone()[0]
        self.assertEqual(diff, 5)

    def test_stock_bas(self):
        self.nouveau("Sucre", stock=4, seuil=5)
        self.nouveau("Sel", stock=50, seuil=5)
        self.assertEqual([p["nom"] for p in ps.low_stock(self.conn)], ["Sucre"])

    def test_desactivation(self):
        pid = self.nouveau()
        ps.set_active(self.conn, pid, False)
        self.assertEqual(len(ps.list_products(self.conn)), 0)
        self.assertEqual(len(ps.list_products(self.conn, include_inactive=True)), 1)


if __name__ == "__main__":
    unittest.main()