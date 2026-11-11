def log_audit(conn, action, entite, entite_id=None, detail=None):
    """Ajoute une ligne au journal d'audit (le commit est fait par l'appelant)."""
    conn.execute(
        "INSERT INTO journal_audit (action, entite, entite_id, detail) VALUES (?, ?, ?, ?)",
        (action, entite, entite_id, detail),
    )