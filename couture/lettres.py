"""Montant en lettres (français), pour le pied de facture."""

UNITES = ['zéro', 'un', 'deux', 'trois', 'quatre', 'cinq', 'six', 'sept', 'huit', 'neuf', 'dix',
          'onze', 'douze', 'treize', 'quatorze', 'quinze', 'seize', 'dix-sept', 'dix-huit', 'dix-neuf']
DIZAINES = {2: 'vingt', 3: 'trente', 4: 'quarante', 5: 'cinquante', 6: 'soixante'}


def _moins_de_cent(n):
    if n < 20:
        return UNITES[n]
    if n < 70:
        d, u = divmod(n, 10)
        dz = DIZAINES[d]
        if u == 0:
            return dz
        return f'{dz}-et-{UNITES[u]}' if u == 1 else f'{dz}-{UNITES[u]}'
    if n < 80:  # soixante-dix … soixante-dix-neuf
        return 'soixante-' + _moins_de_cent(n - 60)
    if n < 100:  # quatre-vingts … quatre-vingt-dix-neuf
        if n == 80:
            return 'quatre-vingts'
        return 'quatre-vingt-' + _moins_de_cent(n - 80)
    return ''


def _moins_de_mille(n):
    c, r = divmod(n, 100)
    parties = []
    if c:
        if c == 1:
            parties.append('cent')
        else:
            parties.append(f'{UNITES[c]} cent' + ('s' if r == 0 else ''))
    if r:
        parties.append(_moins_de_cent(r))
    return ' '.join(parties)


def montant_en_lettres(n):
    n = int(n)
    if n == 0:
        return 'zéro'
    if n < 0:
        return 'moins ' + montant_en_lettres(-n)
    parties = []
    millions, reste = divmod(n, 1_000_000)
    milliers, reste = divmod(reste, 1000)
    if millions:
        parties.append(('un million' if millions == 1 else f'{_moins_de_mille(millions)} millions'))
    if milliers:
        parties.append('mille' if milliers == 1 else f'{_moins_de_mille(milliers)} mille')
    if reste:
        parties.append(_moins_de_mille(reste))
    return ' '.join(p for p in parties if p)
