import os
import tempfile
import unittest
from datetime import date, timedelta

from app.services import product_service as ps
from app.services import report_service as rs
from tools.seed_demo import build_demo


class TestScenario(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.conn = build_demo(os.path.join(cls.tmp.name, "demo.db"))

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        cls.tmp.cleanup()

    def test_stock_coherent(self):
        self.assertEqual(ps.check_stock_integrity(self.conn), [])
        negatifs = self.conn.execute("SELECT COUNT(*) FROM produit WHERE quantite_stock < 0").fetchone()[0]
        self.assertEqual(negatifs, 0)
        clotures = self.conn.execute("SELECT COUNT(*) FROM cloture_journee").fetchone()[0]
        self.assertEqual(clotures, 30)

    def test_bilans_coherents(self):
        end = date.today().isoformat()
        start = (date.today() - timedelta(days=30)).isoformat()
        total = rs.summary(self.conn, start, end)
        days = rs.daily_breakdown(self.conn, start, end)
        self.assertEqual(total["ca_global"], sum(d["total"] for d in days))
        self.assertEqual(total["benefice_total"], sum(d["benefice"] for d in days))
        self.assertEqual(total["ca_global"], sum(rs.summary(self.conn, d["date"], d["date"])["ca_global"] for d in days))
        self.assertGreater(total["ca_global"], 0)

    def test_totaux_alignes_sur_les_lignes_de_vente(self):
        end = date.today().isoformat()
        start = (date.today() - timedelta(days=30)).isoformat()
        total = rs.summary(self.conn, start, end)
        montant, benefice = self.conn.execute(
            "SELECT SUM(montant_theorique), SUM(benefice) FROM ligne_vente").fetchone()
        self.assertEqual(total["boutique"], montant)
        self.assertEqual(total["benefice_boutique"], benefice)
        self.assertEqual(total["ecart"], total["encaisse"] - total["boutique"])


if __name__ == "__main__":
    unittest.main()