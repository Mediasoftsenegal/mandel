"""Nouvelle facture en 4 étapes, comme le PHP (admin/panier + admin/facture/fact.php).

1. choix du client        2. choix des articles        3. panier        4. confirmation

Le panier est conservé en session (équivalent de $_SESSION['panier'] en PHP).
Les prix viennent du catalogue, comme en PHP.
"""

from datetime import date, datetime

from django.contrib import messages
from django.db import router, transaction
from django.db.models import Max, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import ConfirmationFactureForm
from .models import Client, DetailFacture, Facture, Mesure, Produit
from .views import _filtres_get, _paginer, _societe

CLE_BROUILLON = 'facture_brouillon'


# ---------------------------------------------------------------- Session
def _brouillon(request):
    return request.session.get(CLE_BROUILLON)


def _sauver_brouillon(request, brouillon):
    request.session[CLE_BROUILLON] = brouillon
    request.session.modified = True


def _etape_client_requise(request):
    """(brouillon, client) si l'étape 1 est faite, sinon None."""
    brouillon = _brouillon(request)
    if not brouillon or not brouillon.get('client'):
        return None
    client = Client.objects.filter(pk=brouillon['client'], id_societe=_societe()).first()
    return (brouillon, client) if client else None


def _lignes_brouillon(brouillon):
    """Lignes du panier : produit, quantité et total (prix du catalogue)."""
    produits = Produit.objects.in_bulk([int(k) for k in brouillon['lignes']])
    lignes = []
    for cle, qte in brouillon['lignes'].items():
        produit = produits.get(int(cle))
        if produit is not None:
            lignes.append({'produit': produit, 'qte': qte, 'total': (produit.pu or 0) * qte})
    return lignes


# ---------------------------------------------------------------- Étape 1 : client
def facture_creer(request):
    societe = _societe()
    if request.method == 'POST':
        client = get_object_or_404(Client, pk=request.POST.get('client'), id_societe=societe, etat=1)
        _sauver_brouillon(request, {'client': client.pk, 'lignes': {}})
        return redirect(reverse('couture:facture_articles'))

    q = request.GET.get('q', '').strip()
    clients = Client.objects.filter(id_societe=societe, etat=1)
    if q:
        clients = clients.filter(Q(prenom_nom__icontains=q) | Q(telephone__icontains=q))
    clients = clients.order_by('prenom_nom')
    return render(request, 'couture/facture_etape_client.html', {
        'page_obj': _paginer(request, clients),
        'filtres': _filtres_get(request, 'q'),
        'q': q, 'etape': 1, 'en_cours': _brouillon(request), 'page': 'factures',
    })


# ---------------------------------------------------------------- Étape 2 : articles
def facture_articles(request):
    contexte = _etape_client_requise(request)
    if contexte is None:
        return redirect(reverse('couture:facture_creer'))
    brouillon, client = contexte

    q = request.GET.get('q', '').strip()
    produits = Produit.objects.select_related('modele').order_by('des', 'codep')
    if q:
        produits = produits.filter(des__icontains=q)
    page = _paginer(request, produits)
    for produit in page.object_list:
        produit.dans_panier = brouillon['lignes'].get(str(produit.pk), 0)
    return render(request, 'couture/facture_etape_articles.html', {
        'page_obj': page,
        'filtres': _filtres_get(request, 'q'),
        'q': q, 'client': client,
        'panier': brouillon['lignes'],
        'nb_articles': sum(brouillon['lignes'].values()),
        'etape': 2, 'page': 'factures',
    })


@require_POST
def facture_ajouter(request, pk):
    contexte = _etape_client_requise(request)
    if contexte is None:
        return redirect(reverse('couture:facture_creer'))
    brouillon, _ = contexte
    get_object_or_404(Produit, pk=pk)
    cle = str(pk)
    brouillon['lignes'][cle] = brouillon['lignes'].get(cle, 0) + 1
    _sauver_brouillon(request, brouillon)
    return redirect(reverse('couture:facture_articles'))


# ---------------------------------------------------------------- Étape 3 : panier
def facture_panier(request):
    contexte = _etape_client_requise(request)
    if contexte is None:
        return redirect(reverse('couture:facture_creer'))
    brouillon, client = contexte

    if request.method == 'POST':
        for cle in list(brouillon['lignes']):
            saisie = request.POST.get(f'qte_{cle}', '').strip()
            if saisie.isdigit():
                quantite = int(saisie)
                if quantite <= 0:
                    del brouillon['lignes'][cle]
                else:
                    brouillon['lignes'][cle] = quantite
        _sauver_brouillon(request, brouillon)
        return redirect(reverse('couture:facture_panier'))

    lignes = _lignes_brouillon(brouillon)
    return render(request, 'couture/facture_etape_panier.html', {
        'client': client, 'lignes': lignes,
        'total': sum(l['total'] for l in lignes),
        'nb_articles': sum(brouillon['lignes'].values()),
        'etape': 3, 'page': 'factures',
    })


@require_POST
def facture_supprimer_ligne(request, pk):
    contexte = _etape_client_requise(request)
    if contexte is None:
        return redirect(reverse('couture:facture_creer'))
    brouillon, _ = contexte
    brouillon['lignes'].pop(str(pk), None)
    _sauver_brouillon(request, brouillon)
    return redirect(reverse('couture:facture_panier'))


@require_POST
def facture_annuler(request):
    request.session.pop(CLE_BROUILLON, None)
    messages.success(request, 'Facture en cours annulée.')
    return redirect(reverse('couture:facture_liste'))


# ---------------------------------------------------------------- Étape 4 : confirmation
def _mesures_du_client(client):
    from .pdf import FICHE_MESURES
    mesure = Mesure.objects.filter(client=client, id_societe=_societe()).order_by('-id_mesure').first()
    if mesure is None:
        return None
    return [(libelle, getattr(mesure, champ)) for libelle, champ in FICHE_MESURES
            if getattr(mesure, champ) is not None]


def facture_confirmation(request):
    contexte = _etape_client_requise(request)
    if contexte is None:
        return redirect(reverse('couture:facture_creer'))
    brouillon, client = contexte
    lignes = _lignes_brouillon(brouillon)
    if not lignes:
        messages.error(request, 'Le panier est vide : ajoutez au moins un article.')
        return redirect(reverse('couture:facture_articles'))

    societe = _societe()
    dernier = Facture.objects.filter(id_societe=societe).aggregate(m=Max('numero_facture'))['m'] or 0
    form = ConfirmationFactureForm(request.POST or None, initial={
        'numero_facture': dernier + 1,
        'date_facture': date.today(),
        'date_echeance': date.today(),
        'montpaye': 0,
    })
    if request.method == 'POST' and form.is_valid():
        erreur = creer_facture(
            client=client,
            numero=form.cleaned_data['numero_facture'],
            date_facture=form.cleaned_data['date_facture'],
            date_echeance=form.cleaned_data['date_echeance'],
            paye=form.cleaned_data['montpaye'] or 0,
            lignes=[(l['produit'], l['qte']) for l in lignes],
            societe=societe,
        )
        if erreur is None:
            request.session.pop(CLE_BROUILLON, None)
            messages.success(request, 'Facture enregistrée.')
            return redirect(reverse('couture:facture_detail', args=[form.cleaned_data['numero_facture']]))
        messages.error(request, erreur)

    return render(request, 'couture/facture_etape_confirmation.html', {
        'form': form, 'client': client, 'lignes': lignes,
        'total': sum(l['total'] for l in lignes),
        'mesures': _mesures_du_client(client),
        'etape': 4, 'page': 'factures',
    })


def creer_facture(client, numero, date_facture, date_echeance, paye, lignes, societe):
    """Enregistre la facture et son détail au format PHP. Renvoie un message d'erreur, ou None."""
    if Facture.objects.filter(numero_facture=numero, id_societe=societe).exists():
        return f'Le numéro de facture {numero} existe déjà.'
    total = sum((p.pu or 0) * q for p, q in lignes)
    if paye > total:
        return "L'acompte ne peut pas dépasser le total de la facture."
    noms = ','.join(p.des for p, _ in lignes)
    if len(noms) > 250:
        return 'Trop d’articles sur une seule facture (le détail est limité à 250 caractères).'

    heure = datetime.now().time().replace(microsecond=0)
    from scores.models import incrementer as incrementer_score
    with transaction.atomic(using=router.db_for_write(Facture)):
        facture = Facture.objects.create(
            client=client,
            date_facture=date_facture,
            heure_facture=heure,
            date_echeance=date_echeance,
            id_societe=societe,
            numero_facture=numero,
            montant_facture=str(total),
            montpaye=paye,
            etat_facture=1 if total - paye == 0 else 0,
        )
        DetailFacture.objects.create(
            facture=facture,
            client=client,
            article=noms,
            prix_unitaire=','.join(str(p.pu or 0) for p, _ in lignes),
            nombre=','.join(str(q) for _, q in lignes),
            montant=total,
            id_societe=societe,
            id_article=','.join(str(p.pk) for p, _ in lignes),
        )
        # Chaque article ajouté au panier = un choix de modèle : +1 par exemplaire, dans la même transaction.
        for produit, qte in lignes:
            if produit.modele_id:
                incrementer_score(produit.modele_id, societe=societe, pas=qte)
    return None
