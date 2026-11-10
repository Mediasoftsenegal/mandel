"""Profils et accès aux modules, d'après l'application PHP.

1 admin      -> admin/          (tout)
2 client     -> client/         (clients et mesures)
3 caisse     -> caisse/         (acomptes et encaissements)
4 comptable  -> comptable/      (synthèse, factures en lecture)
5 marquage   -> marquage/       (suivi de fabrication)
"""

PROFIL_LIBELLES = {
    1: 'Administrateur',
    2: 'Client',
    3: 'Caisse',
    4: 'Comptable',
    5: 'Marquage',
}

# Page d'accueil de chaque profil (nom de l'URL).
ACCUEIL = {
    1: 'couture:dashboard',
    2: 'couture:client_liste',
    3: 'couture:caisse',
    4: 'couture:comptabilite',
    5: 'couture:marquage',
}

MODULES_LIBELLES = {
    'dashboard': 'Tableau de bord',
    'clients': 'Clients',
    'mesures': 'Mesures',
    'articles': 'Articles',
    'modeles': 'Modèles',
    'factures': 'Facturation',
    'caisse': 'Acomptes',
    'comptabilite': 'Indicateur',
    'marquage': 'Marquage',
    'parametres': 'Paramètres',
}

ACCES = {
    1: set(MODULES_LIBELLES),
    2: {'clients', 'mesures'},
    3: {'caisse', 'factures'},
    4: {'comptabilite', 'factures'},
    5: {'marquage'},
}

# Préfixe d'URL -> module. Le tableau de bord correspond exactement à '/'.
PREFIXES = [
    ('/clients/', 'clients'),
    ('/mesures/', 'mesures'),
    ('/articles/', 'articles'),
    ('/modeles/', 'modeles'),
    ('/factures/', 'factures'),
    ('/caisse/', 'caisse'),
    ('/comptabilite/', 'comptabilite'),
    ('/marquage/', 'marquage'),
    ('/parametres/', 'parametres'),
]


def modules_pour(profil):
    return ACCES.get(profil, set())


def module_pour_chemin(chemin):
    if chemin == '/':
        return 'dashboard'
    for prefixe, module in PREFIXES:
        if chemin.startswith(prefixe):
            return module
    return None
