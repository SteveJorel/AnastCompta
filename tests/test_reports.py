import csv
import os
import tempfile
import unittest

from app.db.schema import init_db
from app.services import income_service as inc
from app.services import product_service as ps
from app.services import report_service as rs
from app.services import sales_service as ss
from app.utils.format import today_iso


class TestReports(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.conn = init_db(self.path)
        self.today = today_iso()
        piece = {u["libelle"]: u["id"] for u in ps.list_units(self.conn)}["pièce"]
        self.pid = ps.create_product(self.conn, "Huile", piece, 10, 100, 150)
        ss.save_closure(self.conn, self.today, {self.pid: 4}, 850)
        cats = {c["code"]: c["id"] for c in inc.list_categories(self.conn)}
        inc.add_income(self.conn, cats["MACHINE"], self.today, 5000)
        inc.add_income(self.conn, cats["BOIS"], self.today, 2000)

    def tearDown(self):
        self.conn.close()
        os.remove(self.path)

    def test_synthese_jour(self):
        s = rs.summary(self.conn, self.today, self.today)
        self.assertEqual((s["boutique"], s["cout_achat"], s["benefice_boutique"]), (900, 600, 300))
        self.assertEqual((s["ca_global"], s["benefice_total"]), (7900, 7300))
        self.assertEqual((s["encaisse"], s["ecart"], s["nb_clotures"]), (850, -50, 1))
        self.assertEqual({code: total for code, _, total in s["annexes"]}, {"MACHINE": 5000, "BOIS": 2000})

    def test_bornes_de_periode(self):
        self.assertEqual(rs.period_bounds("jour", "2026-11-12"), ("2026-11-12", "2026-11-12"))
        self.assertEqual(rs.period_bounds("semaine", "2026-11-12"), ("2026-11-09", "2026-11-15"))
        self.assertEqual(rs.period_bounds("mois", "2026-02-10"), ("2026-02-01", "2026-02-28"))

    def test_decalage_de_periode(self):
        self.assertEqual(rs.shift_period("mois", "2026-01-15", -1), "2025-12-15")
        self.assertEqual(rs.shift_period("mois", "2026-01-31", 1), "2026-02-28")
        self.assertEqual(rs.shift_period("semaine", "2026-11-12", -1), "2026-11-05")
        self.assertEqual(rs.shift_period("jour", "2026-03-01", -1), "2026-02-28")

    def test_detail_par_jour(self):
        start, end = rs.period_bounds("semaine", self.today)
        rows = rs.daily_breakdown(self.conn, start, end)
        self.assertEqual(len(rows), 7)
        self.assertEqual(sum(r["total"] for r in rows), 7900)
        jour = [r for r in rows if r["date"] == self.today][0]
        self.assertEqual((jour["boutique"], jour["benefice"]), (900, 7300))

    def test_produits_vendus(self):
        rows = rs.top_products(self.conn, self.today, self.today)
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["nom"], rows[0]["quantite"], rows[0]["benefice"]), ("Huile", 6, 300))

    def test_variation(self):
        self.assertEqual(rs.variation_pct(150, 100), 50.0)
        self.assertIsNone(rs.variation_pct(10, 0))

    def test_export_csv_et_html(self):
        sections = rs.report_sections(self.conn, self.today, self.today)
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        try:
            rs.write_csv(path, "Bilan test", sections)
            with open(path, encoding="utf-8-sig", newline="") as f:
                cells = [cell for row in csv.reader(f, delimiter=";") for cell in row]
        finally:
            os.remove(path)
        self.assertIn("Synthèse", cells)
        self.assertIn("Huile", cells)
        html = rs.build_html("Bilan <test>", sections)
        self.assertIn("<table>", html)
        self.assertIn("Huile", html)
        self.assertIn("&lt;test&gt;", html)

    def test_integrite_stock(self):
        self.assertEqual(ps.check_stock_integrity(self.conn), [])
        self.conn.execute("UPDATE produit SET quantite_stock = 99 WHERE id = ?", (self.pid,))
        self.conn.commit()
        self.assertEqual([r["nom"] for r in ps.check_stock_integrity(self.conn)], ["Huile"])


if __name__ == "__main__":
    unittest.main()