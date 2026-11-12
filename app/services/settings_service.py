class SettingsError(Exception):
    pass


def get(conn, key, default=""):
    row = conn.execute("SELECT valeur FROM parametre WHERE cle = ?", (key,)).fetchone()
    return row["valeur"] if row else default


def set_value(conn, key, value):
    conn.execute(
        "INSERT INTO parametre (cle, valeur) VALUES (?, ?) "
        "ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur",
        (key, value),
    )
    conn.commit()


def save_shop(conn, nom, devise):
    devise = devise.strip()
    if not devise:
        raise SettingsError("La devise est obligatoire (ex. FCFA).")
    if len(devise) > 10:
        raise SettingsError("La devise est trop longue (10 caractères maximum).")
    set_value(conn, "nom_boutique", nom.strip())
    set_value(conn, "devise", devise)