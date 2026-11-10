"""Point d'entrée pour cPanel (Setup Python App / Passenger).

Les variables d'environnement (secret, base, hôte) sont lues dans le fichier .env
du dossier de l'application. Les valeurs entre guillemets simples ou doubles sont acceptées.
"""

import os
import sys
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
sys.path.insert(0, str(DOSSIER))

GUILLEMETS = ("'", '"')


def _charger_env(fichier):
    for ligne in fichier.read_text(encoding='utf-8').splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith('#') or '=' not in ligne:
            continue
        cle, valeur = ligne.split('=', 1)
        valeur = valeur.strip()
        if len(valeur) >= 2 and valeur[0] == valeur[-1] and valeur[0] in GUILLEMETS:
            valeur = valeur[1:-1]
        os.environ.setdefault(cle.strip(), valeur)


_env = DOSSIER / '.env'
if _env.exists():
    _charger_env(_env)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mandel.settings')

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
