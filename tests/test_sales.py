import os
import tempfile
import unittest
from datetime import date, timedelta

from app.db.schema import init_db
from app.services import product_service as ps
from app.services import sales_service as ss
from app.utils.format import today_iso


class TestSales(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.conn = init_db(self.path)
        piece = {u["libelle"]: u["id"] for u in ps.list_units(self.conn)}["pièce"]
        self.pid = ps.create_product(self.conn, "Huile", piece, 10, 100, 150)
        self.today = today_iso()

    def tearDown(self):
        self.conn.close()
        os.remove(self.path)

    def stock(self):
        return ps.get_product(self.conn, self.pid)["quantite_stock"]

    def test_calcul_cloture(self):
        ss.save_closure(self.conn, self.today, {self.pid: 4}, 850)
        c = ss.get_closure(self.conn, self.today)
        self.assertEqual((c["total_theorique"], c["total_cout_achat"], c["total_benefice"]), (900, 600, 300))
        self.assertEqual(c["ecart_caisse"], -50)
        self.assertEqual(self.stock(), 4)
        mvt = self.conn.execute("SELECT quantite FROM mouvement_stock WHERE type = 'SORTIE_VENTE'").fetchone()[0]
        self.assertEqual(mvt, -6)

    def test_produit_non_compte_est_non_vendu(self):
        ss.save_closure(self.conn, self.today, {})
        self.assertEqual(self.stock(), 10)
        self.assertEqual(ss.get_closure(self.conn, self.today)["total_theorique"], 0)

    def test_restant_superieur_refuse(self):
        with self.assertRaises(ss.SalesError):
            ss.save_closure(self.conn, self.today, {self.pid: 11})

    def test_date_future_refusee(self):
        demain = (date.today() + timedelta(days=1)).isoformat()
        with self.assertRaises(ss.SalesError):
            ss.save_closure(self.conn, demain, {self.pid: 4})

    def test_modification_derniere_cloture(self):
        ss.save_closure(self.conn, self.today, {self.pid: 4})
        ss.save_closure(self.conn, self.today, {self.pid: 3})
        self.assertEqual(self.stock(), 3)
        self.assertEqual(ss.get_closure(self.conn, self.today)["total_theorique"], 1050)
        rows = self.conn.execute("SELECT quantite FROM mouvement_stock WHERE type = 'SORTIE_VENTE'").fetchall()
        self.assertEqual([r[0] for r in rows], [-7])

    def test_cloture_ancienne_refusee(self):
        ss.save_closure(self.conn, self.today, {self.pid: 4})
        hier = (date.today() - timedelta(days=1)).isoformat()
        with self.assertRaises(ss.SalesError):
            ss.save_closure(self.conn, hier, {self.pid: 3})


if __name__ == "__main__":
    unittest.main()