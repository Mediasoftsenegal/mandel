"""Périodes du tableau de bord. Chaque période est la période en cours, à la date de référence."""

import calendar
from datetime import date, timedelta

PERIODES = [
    ('jour', 'Jour'),
    ('semaine', 'Semaine'),
    ('quinzaine', 'Quinzaine'),
    ('mois', 'Mois'),
    ('trimestre', 'Trimestre'),
    ('semestre', 'Semestriel'),
    ('annee', 'Annuel'),
]
CLES = {c for c, _ in PERIODES}
MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août',
        'septembre', 'octobre', 'novembre', 'décembre']


def plage(periode, ref):
    """Renvoie (début, fin, libellé) pour la période demandée, contenant la date `ref`."""
    dernier = lambda y, m: calendar.monthrange(y, m)[1]
    if periode == 'jour':
        return ref, ref, f'le {ref:%d/%m/%Y}'
    if periode == 'semaine':
        debut = ref - timedelta(days=ref.weekday())
        return debut, debut + timedelta(days=6), f'semaine du {debut:%d/%m} au {debut + timedelta(days=6):%d/%m/%Y}'
    if periode == 'quinzaine':
        if ref.day <= 15:
            return date(ref.year, ref.month, 1), date(ref.year, ref.month, 15), f'1re quinzaine de {MOIS[ref.month - 1]} {ref.year}'
        return date(ref.year, ref.month, 16), date(ref.year, ref.month, dernier(ref.year, ref.month)), f'2e quinzaine de {MOIS[ref.month - 1]} {ref.year}'
    if periode == 'mois':
        return date(ref.year, ref.month, 1), date(ref.year, ref.month, dernier(ref.year, ref.month)), f'{MOIS[ref.month - 1]} {ref.year}'
    if periode == 'trimestre':
        m0 = 3 * ((ref.month - 1) // 3) + 1
        m1 = m0 + 2
        return date(ref.year, m0, 1), date(ref.year, m1, dernier(ref.year, m1)), f'T{(m0 - 1) // 3 + 1} {ref.year}'
    if periode == 'semestre':
        m0, m1 = (1, 6) if ref.month <= 6 else (7, 12)
        return date(ref.year, m0, 1), date(ref.year, m1, dernier(ref.year, m1)), f'S{1 if m0 == 1 else 2} {ref.year}'
    return date(ref.year, 1, 1), date(ref.year, 12, 31), f'année {ref.year}'
