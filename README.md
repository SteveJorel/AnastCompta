# AnastCompta

Application de bureau locale de gestion de boutique (stock, ventes par clôture de journée, recettes annexes, bilans), développée en Python avec Tkinter et SQLite et compilée en un seul .exe Windows autonome.

## Fonctionnalités

- Compte unique protégé par mot de passe (PBKDF2), code de récupération, blocage après 5 échecs
- Produits : unités de mesure, stock, prix d'achat et de vente, marges, bénéfice prévisionnel, réapprovisionnement, pertes, ajustements
- Clôture de journée : saisie de la quantité vendue ou restante, montant théorique, écart de caisse
- Recettes annexes : machine à écraser, bois de chauffage
- Bilans par jour, semaine et mois avec graphique, export CSV et impression
- Sauvegarde automatique et manuelle, restauration

## Technologies

Python 3.12 ou plus récent, Tkinter, SQLite (module standard), PyInstaller pour l'exécutable. Aucune dépendance externe à l'exécution.

## Lancer en développement

```
python -m venv venv
venv\Scripts\activate
python main.py
```

## Tests

```
python -m unittest discover -s tests -t . -v
```

## Données de démonstration

```
python -m tools.seed_demo
$env:ANASTCOMPTA_DB = "$PWD\demo.db"
python main.py
```

Connexion : `demo` / `demo123`.

## Compiler l'exécutable

```
pip install -r requirements-dev.txt
python -m tools.make_icon
pyinstaller --noconfirm --clean --onefile --windowed --name AnastCompta --icon assets\app.ico --add-data "assets\app.ico;assets" main.py
```

Résultat : `dist\AnastCompta.exe`.

## Données de l'utilisateur

Base, sauvegardes et journal sont dans `%APPDATA%\AnastCompta`.

## Structure

- `app/` : configuration, base de données, services métier, interface, utilitaires
- `tools/` : génération de l'icône et des données de démonstration
- `tests/` : tests automatiques
- `main.py` : point d'entrée

## Auteur

Steve Jorel