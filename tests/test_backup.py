import os
import tempfile
import unittest
from pathlib import Path

from app.db.schema import init_db
from app.services import backup_service as bs
from app.services import product_service as ps
from app.services import settings_service as st


class TestBackup(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.conn = init_db(self.path)
        self.piece = {u["libelle"]: u["id"] for u in ps.list_units(self.conn)}["pièce"]

    def tearDown(self):
        self.conn.close()
        os.remove(self.path)
        self.tmp.cleanup()

    def test_sauvegarde_et_restauration(self):
        ps.create_product(self.conn, "A", self.piece, 5, 100, 150)
        backup = bs.create_backup(self.conn, self.tmp.name)
        self.assertTrue(backup.exists())
        ps.create_product(self.conn, "B", self.piece, 1, 100, 150)
        bs.restore_backup(self.conn, backup, safety_dir=self.tmp.name)
        self.assertEqual([p["nom"] for p in ps.list_products(self.conn)], ["A"])
        self.assertTrue(list(Path(self.tmp.name).glob("avant_restauration_*.db")))

    def test_fichier_invalide(self):
        bad = Path(self.tmp.name) / "faux.db"
        bad.write_text("ceci n'est pas une base de données", encoding="utf-8")
        with self.assertRaises(bs.BackupError):
            bs.restore_backup(self.conn, bad, safety_dir=self.tmp.name)

    def test_fichier_inexistant(self):
        with self.assertRaises(bs.BackupError):
            bs.restore_backup(self.conn, Path(self.tmp.name) / "absent.db", safety_dir=self.tmp.name)

    def test_parametres(self):
        self.assertEqual(st.get(self.conn, "devise"), "FCFA")
        st.save_shop(self.conn, " Ma Boutique ", "XAF")
        self.assertEqual((st.get(self.conn, "nom_boutique"), st.get(self.conn, "devise")), ("Ma Boutique", "XAF"))
        with self.assertRaises(st.SettingsError):
            st.save_shop(self.conn, "X", "  ")


if __name__ == "__main__":
    unittest.main()