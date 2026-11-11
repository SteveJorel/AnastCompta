import os
import tempfile
import unittest
from datetime import date, timedelta

from app.db.schema import init_db
from app.services import income_service as inc
from app.utils.format import today_iso


class TestIncome(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.conn = init_db(self.path)
        cats = {c["code"]: c["id"] for c in inc.list_categories(self.conn)}
        self.machine, self.bois = cats["MACHINE"], cats["BOIS"]
        self.today = today_iso()

    def tearDown(self):
        self.conn.close()
        os.remove(self.path)

    def test_ajout_et_totaux(self):
        inc.add_income(self.conn, self.machine, self.today, 5000)
        inc.add_income(self.conn, self.bois, self.today, 2000, "fagots")
        inc.add_income(self.conn, self.machine, self.today, 3000)
        self.assertEqual(inc.totals_by_category(self.conn, self.today, self.today), {"MACHINE": 8000, "BOIS": 2000})
        self.assertEqual(inc.total(self.conn), 10000)

    def test_montant_invalide(self):
        with self.assertRaises(inc.IncomeError):
            inc.add_income(self.conn, self.machine, self.today, 0)

    def test_date_future(self):
        demain = (date.today() + timedelta(days=1)).isoformat()
        with self.assertRaises(inc.IncomeError):
            inc.add_income(self.conn, self.bois, demain, 1000)

    def test_modification_et_suppression(self):
        rid = inc.add_income(self.conn, self.machine, self.today, 5000)
        inc.update_income(self.conn, rid, self.bois, self.today, 6000, "corrigé")
        row = inc.get_income(self.conn, rid)
        self.assertEqual((row["categorie_id"], row["montant"]), (self.bois, 6000))
        inc.delete_income(self.conn, rid)
        self.assertEqual(inc.total(self.conn), 0)

    def test_filtre_par_categorie(self):
        inc.add_income(self.conn, self.machine, self.today, 5000)
        inc.add_income(self.conn, self.bois, self.today, 2000)
        rows = inc.list_incomes(self.conn, self.bois)
        self.assertEqual([r["montant"] for r in rows], [2000])


if __name__ == "__main__":
    unittest.main()