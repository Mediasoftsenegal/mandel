"""Liens WhatsApp (wa.me) pour les relances et l'envoi des factures.

Aucun message n'est envoyé par le serveur : le lien ouvre WhatsApp avec le texte prérempli,
et c'est l'utilisateur qui valide l'envoi.
"""

import re
from urllib.parse import quote

INDICATIF_SENEGAL = '221'


def normaliser_telephone(tel):
    """Renvoie le numéro au format international sans « + » (ex. 221771234567), ou None."""
    if not tel:
        return None
    chiffres = re.sub(r'\D', '', tel)
    if chiffres.startswith('00'):
        chiffres = chiffres[2:]
    if len(chiffres) == 9:  # numéro sénégalais local
        chiffres = INDICATIF_SENEGAL + chiffres
    if len(chiffres) < 8 or len(chiffres) > 15:
        return None
    return chiffres


def lien_whatsapp(tel, texte):
    numero = normaliser_telephone(tel)
    if numero is None:
        return None
    return f'https://wa.me/{numero}?text={quote(texte)}'


def _montant(n):
    return f"{int(n):,}".replace(',', ' ') + ' F'


def _prenom(nom):
    return (nom or '').strip().title()


def texte_relance(nom, reste):
    return (f"Bonjour {_prenom(nom)}, nous vous rappelons un reste à payer de {_montant(reste)} "
            f"sur vos factures chez Mandel Couture. Merci de passer régler. Merci de votre confiance.")


def texte_facture(nom, numero, reste):
    if reste > 0:
        etat = f"Il reste à payer {_montant(reste)}."
    else:
        etat = "Cette facture est soldée. Merci."
    return (f"Bonjour {_prenom(nom)}, veuillez trouver ci-joint votre facture n° {numero} "
            f"de Mandel Couture. {etat}")
