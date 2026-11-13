import os
import re
import tempfile
import unittest

from app.db.schema import init_db
from app.services import auth_service as auth


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class TestAuth(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.conn = init_db(self.path)

    def tearDown(self):
        self.conn.close()
        os.remove(self.path)

    def creer(self):
        return auth.create_user(self.conn, "Jean Test", "jean", "secret1")

    def test_creation_et_format_du_code(self):
        self.assertFalse(auth.user_exists(self.conn))
        code = self.creer()
        self.assertTrue(auth.user_exists(self.conn))
        self.assertRegex(code, r"^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$")

    def test_compte_unique(self):
        self.creer()
        with self.assertRaises(auth.AuthError):
            auth.create_user(self.conn, "Autre", "autre", "secret2")

    def test_mot_de_passe_trop_court(self):
        with self.assertRaises(auth.AuthError):
            auth.create_user(self.conn, "Jean", "jean", "123")

    def test_mot_de_passe_non_stocke_en_clair(self):
        self.creer()
        user = auth.get_user(self.conn)
        self.assertNotIn("secret1", user["mot_de_passe_hash"])
        self.assertTrue(re.fullmatch(r"[0-9a-f]{32}", user["sel"]))

    def test_authentification(self):
        self.creer()
        self.assertTrue(auth.authenticate(self.conn, "jean", "secret1"))
        self.assertTrue(auth.authenticate(self.conn, " JEAN ", "secret1"))
        self.assertFalse(auth.authenticate(self.conn, "jean", "mauvais"))
        self.assertFalse(auth.authenticate(self.conn, "paul", "secret1"))

    def test_changement_mot_de_passe(self):
        self.creer()
        with self.assertRaises(auth.AuthError):
            auth.change_password(self.conn, "faux", "nouveau1")
        auth.change_password(self.conn, "secret1", "nouveau1")
        self.assertFalse(auth.authenticate(self.conn, "jean", "secret1"))
        self.assertTrue(auth.authenticate(self.conn, "jean", "nouveau1"))

    def test_recuperation_par_code(self):
        code = self.creer()
        with self.assertRaises(auth.AuthError):
            auth.reset_password_with_code(self.conn, "AAAA-AAAA-AAAA", "nouveau1")
        nouveau_code = auth.reset_password_with_code(self.conn, code.lower().replace("-", " "), "nouveau1")
        self.assertTrue(auth.authenticate(self.conn, "jean", "nouveau1"))
        with self.assertRaises(auth.AuthError):  # l'ancien code ne marche plus
            auth.reset_password_with_code(self.conn, code, "autre123")
        auth.reset_password_with_code(self.conn, nouveau_code, "autre123")
        self.assertTrue(auth.authenticate(self.conn, "jean", "autre123"))

    def test_blocage_apres_5_echecs(self):
        clock = FakeClock()
        throttle = auth.LoginThrottle(clock)
        for _ in range(4):
            throttle.register_failure()
        self.assertEqual(throttle.remaining(), 0)
        throttle.register_failure()
        self.assertGreater(throttle.remaining(), 0)
        clock.now = 31
        self.assertEqual(throttle.remaining(), 0)

    def test_reinitialisation_par_le_developpeur(self):
        code_initial = self.creer()
        code_apres_reset = auth.force_reset_password(self.conn, "reset123")
        self.assertTrue(auth.authenticate(self.conn, "jean", "reset123"))
        self.assertFalse(auth.authenticate(self.conn, "jean", "secret1"))
        with self.assertRaises(auth.AuthError):  # l'ancien code ne marche plus
            auth.reset_password_with_code(self.conn, code_initial, "autre123")
        auth.reset_password_with_code(self.conn, code_apres_reset, "autre123")
        with self.assertRaises(auth.AuthError):
            auth.force_reset_password(self.conn, "123")

if __name__ == "__main__":
    unittest.main()