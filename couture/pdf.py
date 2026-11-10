"""Facture PDF, reprise de admin/facture/details.php (FPDF) avec ReportLab.

Page 1 : en-tête, client, tableau des articles, fiche de mesures, total, acomptes, reste, conditions.
"""

from io import BytesIO
from pathlib import Path

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .lettres import montant_en_lettres
from .models import DetailFacture, Facture, Mesure, _vers_nombre

LOGO = Path(settings.BASE_DIR) / 'static' / 'img' / 'logo0.png'

CONDITIONS = [
    'NB : Le délai de livraison est de 3 mois à compter de cette date.',
    'Passé ces 3 mois, nous ne sommes plus responsables des habits qui nous sont confiés.',
    "En cas de perte du reçu, se présenter avec une pièce d'identité portant le même nom que celui inscrit",
    'sur la souche. Merci.',
]

# Champs de la fiche de mesures : (libellé, colonne)
FICHE_MESURES = [
    ('Longueur', 'longueur'), ('Épaule (E)', 'epaule'), ('Manche (M)', 'manche'), ('Cou (C)', 'cou'),
    ('Poitrine (P)', 'poitrine'), ('Ceinture (CT)', 'ceinture'), ('Tour de fesses (LP)', 'tourfess'),
    ('Cuisse', 'cuisse'), ('Bas', 'bas'), ('Longueur pantalon', 'longueurpantalon'),
    ('Longueur grand boubou', 'longueurgrandboubou'), ('Tour de manche', 'tourmanche'),
    ('Thiaya', 'thiaya'),
]


def _montant(n):
    return f'{int(n):,}'.replace(',', ' ')


def _lignes(facture_numero, societe):
    lignes = []
    for d in DetailFacture.objects.filter(facture__numero_facture=facture_numero, id_societe=societe):
        noms = d.article.split(',')
        prix = d.prix_unitaire.split(',')
        qtes = d.nombre.split(',')
        for i, nom in enumerate(noms):
            p = _vers_nombre(prix[i]) if i < len(prix) else 0
            q = _vers_nombre(qtes[i]) if i < len(qtes) else 0
            lignes.append((nom, p, q, p * q))
    return lignes


def facture_pdf(numero, societe, avec_mesures=False):
    """Renvoie le PDF (bytes) de la facture `numero`, ou None si elle n'existe pas."""
    tranches = list(Facture.objects.filter(numero_facture=numero, id_societe=societe)
                    .select_related('client').order_by('id_facture'))
    if not tranches:
        return None

    client = tranches[0].client
    total = sum(f.montant for f in tranches)
    paye = sum((f.montpaye or 0) for f in tranches)
    reste = total - paye
    lignes = _lignes(numero, societe)
    date_cmd = min(f.date_facture for f in tranches)

    styles = getSampleStyleSheet()
    gras = styles['Normal'].clone('gras', fontName='Helvetica-Bold', fontSize=9, leading=12)
    normal = styles['Normal'].clone('norm', fontSize=9, leading=12)
    titre = styles['Title'].clone('titre', fontName='Helvetica-Bold', fontSize=18, leading=22,
                                  alignment=2, spaceAfter=4)
    petit = styles['Normal'].clone('petit', fontSize=8, leading=10)

    entete = [
        [Image(str(LOGO), width=60 * mm, height=22 * mm) if LOGO.exists() else Paragraph('MANDEL', gras),
         Paragraph(f'FACTURE N° {numero}', titre)],
        [Paragraph(f'Date commande : {date_cmd:%d/%m/%Y}', normal),
         Paragraph(f"Date livraison : {tranches[0].date_echeance:%d/%m/%Y}", normal)],
        [Paragraph(f'Prénom et nom : {client.prenom_nom or ""}', gras),
         Paragraph(f'Contact client : {client.telephone or ""}', normal)],
    ]
    t_entete = Table(entete, colWidths=[90 * mm, 90 * mm])
    t_entete.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))

    donnees = [['DÉSIGNATION', 'P. UNITAIRE', 'QUANTITÉ', 'PRIX TOTAL']]
    for nom, pu, qte, tot in lignes:
        donnees.append([nom, _montant(pu), str(qte), _montant(tot)])
    qte_total = sum(q for _, _, q, _ in lignes)
    donnees.append(['TOTAL', '', str(qte_total), _montant(total)])
    t_articles = Table(donnees, colWidths=[85 * mm, 35 * mm, 25 * mm, 35 * mm], repeatRows=1)
    t_articles.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 9),
        ('FONT', (0, 1), (-1, -1), 'Helvetica', 9),
        ('FONT', (0, -1), (-1, -1), 'Helvetica-Bold', 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E0F2F1')),
    ]))

    pied = [
        [Paragraph(f'{montant_en_lettres(total).upper()} FRANCS CFA', gras), ''],
        [Paragraph(f'Avance : {_montant(paye)}', normal), Paragraph(f'Reste : {_montant(reste)}', normal)],
    ]
    if reste <= 0:
        pied.append([Paragraph(f'Soldée le : {date_cmd:%d/%m/%Y}', gras), ''])
    t_pied = Table(pied, colWidths=[110 * mm, 70 * mm])
    t_pied.setStyle(TableStyle([('SPAN', (0, 0), (1, 0))]))

    conditions = [Paragraph(c, petit) for c in CONDITIONS]

    # Mesures du client juste sous le tableau des articles, puis totaux et conditions.
    elements = [t_entete, Spacer(1, 6 * mm), t_articles]
    if avec_mesures:
        elements += _bloc_mesures(client, societe, styles)
    elements += [Spacer(1, 6 * mm), t_pied, Spacer(1, 6 * mm)]
    elements += conditions

    tampon = BytesIO()
    doc = SimpleDocTemplate(tampon, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=12 * mm, bottomMargin=12 * mm,
                            title=f'Facture {numero}', author='Mandel')
    doc.build(elements)
    return tampon.getvalue()


def _bloc_mesures(client, societe, styles):
    mesure = Mesure.objects.filter(client=client, id_societe=societe).order_by('-id_mesure').first()
    if mesure is None:
        return []
    cellules = []
    ligne = []
    for libelle, champ in FICHE_MESURES:
        valeur = getattr(mesure, champ)
        ligne.append(f'{libelle} : {valeur if valeur is not None else ""}')
        if len(ligne) == 3:
            cellules.append(ligne)
            ligne = []
    if ligne:
        ligne += [''] * (3 - len(ligne))
        cellules.append(ligne)
    style = styles['Normal'].clone('m', fontSize=8, leading=10)
    tableau = Table([[Paragraph(c, style) for c in row] for row in cellules],
                    colWidths=[60 * mm, 60 * mm, 60 * mm])
    tableau.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
                                 ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    return [Spacer(1, 4 * mm), Paragraph('<b>Mesures du client</b>', style), Spacer(1, 2 * mm), tableau]
