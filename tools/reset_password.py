"""Outil du développeur : réinitialise le mot de passe du compte unique, à la demande du client."""
import getpass
import sqlite3
import sys
from pathlib import Path

from app.config import get_db_path
from app.db.schema import init_db
from app.services import auth_service as auth
from app.services import backup_service


def main() -> int:
    db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else get_db_path()
    print("=== AnastCompta : réinitialisation du mot de passe (outil du développeur) ===")
    print(f"Base de données : {db_path}")
    if not db_path.is_file():
        print("Base introuvable. Vérifiez le chemin.")
        return 1
    print("\nAnastCompta doit être fermé avant de continuer.")
    if input("Le client demande cette réinitialisation. Tapez OUI pour continuer : ").strip().upper() != "OUI":
        print("Annulé.")
        return 0

    conn = None
    try:
        conn = init_db(db_path)
        user = auth.get_user(conn)
        if user is None:
            print("Aucun compte dans cette base.")
            return 1
        print(f"Compte concerné : {user['nom_utilisateur']} ({user['nom_complet']})")
        new_password = getpass.getpass("Nouveau mot de passe (6 caractères minimum) : ")
        if new_password != getpass.getpass("Confirmer le nouveau mot de passe : "):
            print("Les deux mots de passe ne sont pas identiques.")
            return 1
        safety = backup_service.create_backup(conn, db_path.parent / "sauvegardes", prefix="avant_reset_mdp_")
        code = auth.force_reset_password(conn, new_password)
    except (auth.AuthError, sqlite3.Error) as exc:
        print(f"Erreur : {exc}")
        return 1
    finally:
        if conn is not None:
            conn.close()

    print(f"\nSauvegarde de sécurité : {safety}")
    print("Mot de passe réinitialisé.")
    print(f"NOUVEAU code de récupération : {code}")
    print("Faites-le noter sur papier par le client, puis il peut se reconnecter.")
    return 0


if __name__ == "__main__":
    exit_code = main()
    input("\nAppuyez sur Entrée pour fermer cette fenêtre.")
    sys.exit(exit_code)