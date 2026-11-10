from datetime import date, datetime, timedelta

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import router, transaction
from django.db.models import DecimalField, Max, Min, Q, Sum
from django.db.models.functions import Cast
from django.http import Http404, HttpResponse
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import (
    ArticleForm, ClientForm, ConnexionForm, FactureForm, MesureFemmeForm,
    MesureHommeForm, ModeleForm, PaiementForm,
)
from .pdf import facture_pdf
from .whatsapp import lien_whatsapp, texte_facture, texte_relance
from .models import (
    Client, DetailFacture, Facture, Mesure, Modele, Produit, Profil, Tarification, UtilisateurLegacy, _vers_nombre,
)

PAR_PAGE = 35
MONTANT = DecimalField(max_digits=14, decimal_places=2)


def _societe():
    return settings.SOCIETE_ID


def _paginer(request, qs):
    return Paginator(qs, PAR_PAGE).get_page(request.GET.get('page'))


def _filtres_get(request, *cles):
    """Paramètres de filtre non vides, repris dans les liens de pagination."""
    return {k: request.GET.get(k, '').strip() for k in cles if request.GET.get(k, '').strip()}


# ================================================================ Tableau de bord
def tableau_de_bord(request):
    from .periodes import CLES, MOIS, PERIODES, plage

    aujourdhui = date.today()
    periode = request.GET.get('periode', 'mois')
    if periode not in CLES:
        periode = 'mois'
    debut, fin, libelle_periode = plage(periode, aujourdhui)
    societe = _societe()

    # --- Indicateurs de la période (date de la facture / de l'acompte)
    lignes_periode = Facture.objects.filter(id_societe=societe, date_facture__range=(debut, fin)).annotate(
        montant_num=Cast('montant_facture', MONTANT))
    agr = lignes_periode.aggregate(total=Sum('montant_num'), paye=Sum('montpaye'))
    total = agr['total'] or 0
    paye = agr['paye'] or 0
    nb_factures = lignes_periode.filter(montant_num__gt=0).count()
    taux = round(paye * 100 / total) if total else 0
    panier_moyen = round(total / nb_factures) if nb_factures else 0

    # --- Situation globale (à la date du jour)
    groupes = _groupes_factures(societe, etat='impayees')
    reste_global = sum(g['reste'] for g in groupes)
    en_retard = [g for g in groupes if g['echeance'] and g['echeance'] < aujourdhui]
    echeances_proches = [g for g in groupes if g['echeance'] and aujourdhui <= g['echeance'] <= aujourdhui + timedelta(days=7)]

    # --- Clients à relancer : reste à payer le plus élevé
    encours = {}
    for g in groupes:
        if g['client'] is not None:
            encours[g['client'].pk] = encours.get(g['client'].pk, 0) + g['reste']
    top_clients = sorted(encours.items(), key=lambda kv: kv[1], reverse=True)[:5]
    clients = Client.objects.in_bulk([pk for pk, _ in top_clients])
    top_clients = [{
        'client': clients[pk], 'reste': r,
        'lien': lien_whatsapp(clients[pk].telephone, texte_relance(clients[pk].prenom_nom, r)),
    } for pk, r in top_clients if pk in clients]

    # --- Articles les plus vendus sur la période
    ventes = {}
    for d in DetailFacture.objects.filter(facture__date_facture__range=(debut, fin), id_societe=societe):
        noms = d.article.split(',')
        prix = d.prix_unitaire.split(',')
        qtes = d.nombre.split(',')
        for i, nom in enumerate(noms):
            q = _vers_nombre(qtes[i]) if i < len(qtes) else 0
            p = _vers_nombre(prix[i]) if i < len(prix) else 0
            v = ventes.setdefault(nom.strip(), {'article': nom.strip(), 'qte': 0, 'montant': 0})
            v['qte'] += q
            v['montant'] += p * q
    top_articles = sorted(ventes.values(), key=lambda v: v['montant'], reverse=True)[:5]

    # --- Graphe comparatif : facturé et encaissé par mois, année en cours
    annee = aujourdhui.year
    facture_mois = [0] * 12
    paye_mois = [0] * 12
    par_mois = (Facture.objects.filter(id_societe=societe, date_facture__year=annee)
                .annotate(montant_num=Cast('montant_facture', MONTANT))
                .values('date_facture__month')
                .annotate(f=Sum('montant_num'), p=Sum('montpaye')))
    for r in par_mois:
        i = r['date_facture__month'] - 1
        facture_mois[i] = int(r['f'] or 0)
        paye_mois[i] = int(r['p'] or 0)
    graphe = {'labels': [m[:3].capitalize() for m in MOIS], 'facture': facture_mois,
              'paiements': paye_mois, 'annee': annee}

    return render(request, 'couture/dashboard.html', {
        'periodes': PERIODES, 'periode': periode, 'libelle_periode': libelle_periode,
        'nb_factures': nb_factures, 'total_facture': total, 'total_paye': paye,
        'taux_encaissement': taux, 'panier_moyen': panier_moyen,
        'reste_global': reste_global,
        'nb_retard': len(en_retard), 'montant_retard': sum(g['reste'] for g in en_retard),
        'nb_echeances': len(echeances_proches),
        'nb_clients': Client.objects.filter(id_societe=societe, etat=1).count(),
        'top_clients': top_clients, 'top_articles': top_articles,
        'graphe': graphe,
        'dernieres_factures': lignes_periode_recentes(societe),
        'page': 'dashboard',
    })


def lignes_periode_recentes(societe):
    return Facture.objects.filter(id_societe=societe).select_related('client').order_by('-date_facture', '-id_facture')[:8]


# ================================================================ Clients
def client_liste(request):
    nom = request.GET.get('nom', '').strip()
    telephone = request.GET.get('telephone', '').strip()
    etat = request.GET.get('etat', '')

    clients = Client.objects.filter(id_societe=_societe())
    if nom:
        clients = clients.filter(prenom_nom__icontains=nom)
    if telephone:
        clients = clients.filter(telephone__icontains=telephone)
    if etat in ('0', '1'):
        clients = clients.filter(etat=int(etat))
    clients = clients.order_by('prenom_nom', 'id_client')

    return render(request, 'couture/client_liste.html', {
        'page_obj': _paginer(request, clients),
        'filtres': _filtres_get(request, 'nom', 'telephone', 'etat'),
        'nom': nom, 'telephone': telephone, 'etat': etat, 'page': 'clients',
    })


def client_creer(request):
    form = ClientForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        client = form.save(commit=False)
        client.id_societe = _societe()
        client.etat = 1
        client.save()
        messages.success(request, 'Client enregistré. Saisissez maintenant les mesures.')
        return redirect(reverse('couture:mesure_creer', args=[client.pk]))
    return render(request, 'couture/client_form.html', {
        'form': form, 'titre': 'Nouveau client', 'page': 'clients',
    })


def client_modifier(request, pk):
    client = get_object_or_404(Client, pk=pk, id_societe=_societe())
    form = ClientForm(request.POST or None, instance=client)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Client modifié.')
        return redirect(reverse('couture:client_detail', args=[client.pk]))
    return render(request, 'couture/client_form.html', {
        'form': form, 'titre': 'Modifier le client', 'client': client, 'page': 'clients',
    })


def client_detail(request, pk):
    client = get_object_or_404(Client, pk=pk, id_societe=_societe())
    mesures = Mesure.objects.filter(client=client, id_societe=_societe()).order_by('-id_mesure')
    factures = _groupes_factures(_societe(), client=client)
    return render(request, 'couture/client_detail.html', {
        'client': client, 'mesures': mesures, 'factures': factures, 'page': 'clients',
    })


@require_POST
def client_basculer_etat(request, pk):
    """Active ou désactive un client. Aucune suppression."""
    client = get_object_or_404(Client, pk=pk, id_societe=_societe())
    client.etat = 0 if client.etat == 1 else 1
    client.save(update_fields=['etat'])
    messages.success(request, 'Client activé.' if client.etat == 1 else 'Client désactivé.')
    return redirect(reverse('couture:client_detail', args=[client.pk]))


# ================================================================ Mesures
def _formulaire_mesure(client):
    """Formulaire selon le genre du client, ou (None, None) si le genre n'est pas renseigné."""
    if client.genre == 'Homme':
        return MesureHommeForm, 'Mesures — homme'
    if client.genre == 'Femme':
        return MesureFemmeForm, 'Mesures — femme'
    return None, None


def mesure_creer(request, pk):
    client = get_object_or_404(Client, pk=pk, id_societe=_societe())
    form_classe, titre = _formulaire_mesure(client)
    if form_classe is None:
        messages.error(request, "Genre non renseigné : modifiez la fiche client avant de saisir les mesures.")
        return redirect(reverse('couture:client_detail', args=[client.pk]))

    form = form_classe(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        mesure = form.save(commit=False)
        mesure.client = client
        mesure.id_societe = _societe()
        mesure.genre = client.genre
        mesure.telephone = client.telephone
        mesure.save()
        messages.success(request, 'Mesures enregistrées.')
        return redirect(reverse('couture:client_detail', args=[client.pk]))
    return render(request, 'couture/mesure_form.html', {
        'form': form, 'client': client, 'titre': titre, 'page': 'clients',
    })


def mesure_modifier(request, pk, mesure_pk):
    client = get_object_or_404(Client, pk=pk, id_societe=_societe())
    mesure = get_object_or_404(Mesure, pk=mesure_pk, client=client, id_societe=_societe())
    form_classe, titre = _formulaire_mesure(client)
    if form_classe is None:
        messages.error(request, "Genre non renseigné : modifiez la fiche client avant de modifier les mesures.")
        return redirect(reverse('couture:client_detail', args=[client.pk]))

    form = form_classe(request.POST or None, instance=mesure)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Mesures modifiées.')
        return redirect(reverse('couture:client_detail', args=[client.pk]))
    return render(request, 'couture/mesure_form.html', {
        'form': form, 'client': client, 'titre': f'{titre} (n° {mesure.pk})', 'page': 'clients',
    })


# ================================================================ Articles (table produit)
def article_liste(request):
    des = request.GET.get('des', '').strip()
    catp = request.GET.get('catp', '')
    genre = request.GET.get('genre', '')

    articles = Produit.objects.select_related('modele').order_by('des', 'codep')
    if des:
        articles = articles.filter(des__icontains=des)
    if catp in ('PAP', 'TISSU'):
        articles = articles.filter(catp=catp)
    if genre in ('Homme', 'Femme'):
        articles = articles.filter(genre=genre)

    return render(request, 'couture/article_liste.html', {
        'page_obj': _paginer(request, articles),
        'filtres': _filtres_get(request, 'des', 'catp', 'genre'),
        'des': des, 'catp': catp, 'genre': genre, 'page': 'articles',
    })


def article_creer(request):
    form = ArticleForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Article enregistré.')
        return redirect(reverse('couture:article_liste'))
    return render(request, 'couture/article_form.html', {
        'form': form, 'titre': 'Nouvel article', 'page': 'articles',
    })


def article_modifier(request, pk):
    article = get_object_or_404(Produit, pk=pk)
    form = ArticleForm(request.POST or None, instance=article)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Article modifié.')
        return redirect(reverse('couture:article_liste'))
    return render(request, 'couture/article_form.html', {
        'form': form, 'titre': 'Modifier l’article', 'page': 'articles',
    })


# ================================================================ Modèles, galerie de photos, évaluation
def modele_liste(request):
    from scores.models import ScoreModele
    from photos.models import PhotoModele, NOMBRE_PHOTOS_PAR_MODELE, NOMBRE_MAX_MODELES, nombre_modeles_avec_galerie
    libelle = request.GET.get('libelle', '').strip()
    modeles = Modele.objects.order_by('libmod')
    if libelle:
        modeles = modeles.filter(libmod__icontains=libelle)
    scores = dict(ScoreModele.objects.values_list('modele_id', 'score'))
    galeries = {}
    for ph in PhotoModele.objects.all():  # ordonné par modèle puis position
        galeries.setdefault(ph.modele_id, []).append(ph)
    lignes = []
    for m in modeles:
        photos = galeries.get(m.pk, [])
        vedette = max(photos, key=lambda p: p.score) if photos else None
        lignes.append({'modele': m, 'score': scores.get(m.pk, 0), 'nb_photos': len(photos),
                       'vedette': vedette})
    tri = request.GET.get('tri', '')
    if tri == 'score':
        lignes.sort(key=lambda l: (-l['score'], l['modele'].libmod))
    return render(request, 'couture/modele_liste.html', {
        'page_obj': _paginer(request, lignes),
        'filtres': _filtres_get(request, 'libelle', 'tri'),
        'libelle': libelle, 'tri': tri, 'page': 'modeles',
        'nb_galeries': nombre_modeles_avec_galerie(_societe()),
        'max_galeries': NOMBRE_MAX_MODELES,
        'par_galerie': NOMBRE_PHOTOS_PAR_MODELE,
    })


def modele_creer(request):
    form = ModeleForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        modele = form.save()
        messages.success(request, 'Modèle enregistré. Vous pouvez maintenant ajouter ses photos.')
        return redirect(reverse('couture:modele_modifier', args=[modele.pk]))
    return render(request, 'couture/modele_form.html', {
        'form': form, 'titre': 'Nouveau modèle', 'page': 'modeles',
    })


def modele_modifier(request, pk):
    from scores.models import ScoreModele
    modele = get_object_or_404(Modele, pk=pk)
    form = ModeleForm(request.POST or None, instance=modele)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Modèle modifié.')
        return redirect(reverse('couture:modele_liste'))
    from photos.models import photos_du_modele, NOMBRE_PHOTOS_PAR_MODELE
    score = ScoreModele.objects.filter(modele_id=modele.pk).values_list('score', flat=True).first() or 0
    # Aperçu en lecture seule : aucune action ici ne modifie le score des photos.
    apercu = {p.position: p for p in photos_du_modele(modele.pk)}
    emplacements = [{'position': i, 'photo': apercu.get(i)} for i in range(1, NOMBRE_PHOTOS_PAR_MODELE + 1)]
    return render(request, 'couture/modele_form.html', {
        'form': form, 'titre': 'Modifier le modèle', 'page': 'modeles', 'modele': modele, 'score': score,
        'apercu': emplacements,
    })


def modele_galerie(request, pk):
    """Galerie du modèle : exactement 5 photos (ou aucune), chacune évaluable."""
    from photos.models import (GalerieInvalide, NOMBRE_PHOTOS_PAR_MODELE, appliquer_galerie,
                               nombre_modeles_avec_galerie, NOMBRE_MAX_MODELES, photos_du_modele)
    modele = get_object_or_404(Modele, pk=pk)
    if request.method == 'POST':
        fichiers = {}
        for pos in range(1, NOMBRE_PHOTOS_PAR_MODELE + 1):
            f = request.FILES.get(f'photo_{pos}')
            if f:
                fichiers[pos] = f
        a_supprimer = {pos for pos in range(1, NOMBRE_PHOTOS_PAR_MODELE + 1)
                       if request.POST.get(f'supprimer_{pos}')}
        try:
            with transaction.atomic(using='default'):
                appliquer_galerie(modele.pk, fichiers, a_supprimer, societe=_societe())
            messages.success(request, 'Galerie enregistrée.')
            return redirect(reverse('couture:modele_galerie', args=[modele.pk]))
        except GalerieInvalide as erreur:
            messages.error(request, str(erreur))

    photos = {p.position: p for p in photos_du_modele(modele.pk)}
    emplacements = [{'position': pos, 'photo': photos.get(pos)} for pos in range(1, NOMBRE_PHOTOS_PAR_MODELE + 1)]
    return render(request, 'couture/modele_galerie.html', {
        'modele': modele, 'emplacements': emplacements, 'par_galerie': NOMBRE_PHOTOS_PAR_MODELE,
        'nb_galeries': nombre_modeles_avec_galerie(_societe()), 'max_galeries': NOMBRE_MAX_MODELES,
        'page': 'modeles',
    })


@require_POST
def photo_voter(request, pk):
    """Évaluation : +1 au score de la photo."""
    from photos.models import PhotoModele, voter
    photo = get_object_or_404(PhotoModele, pk=pk)
    voter(photo.pk)
    messages.success(request, f'Vote enregistré pour la photo {photo.position} du modèle {photo.modele_id}.')
    suivant = request.POST.get('suivant', '')
    if suivant and url_has_allowed_host_and_scheme(suivant, allowed_hosts={request.get_host()}):
        return redirect(suivant)
    return redirect(reverse('couture:modele_galerie', args=[photo.modele_id]))


def photos_evaluation(request):
    """Classement des photos de modèles par score."""
    from photos.models import PhotoModele
    photos = list(PhotoModele.objects.order_by('-score', 'modele_id', 'position'))
    noms = Modele.objects.in_bulk({p.modele_id for p in photos})
    lignes = [{'photo': p, 'modele': noms.get(p.modele_id)} for p in photos]
    return render(request, 'couture/photos_evaluation.html', {
        'page_obj': _paginer(request, lignes), 'filtres': {}, 'page': 'modeles',
    })


# ================================================================ Factures
def _groupes_factures(societe, client=None, recherche=None, etat=None):
    """Une ligne par numéro de facture : total, payé, reste. Les acomptes sont regroupés."""
    qs = Facture.objects.filter(id_societe=societe)
    if client is not None:
        qs = qs.filter(client=client)
    if recherche:
        qs = qs.filter(Q(numero_facture__icontains=recherche) | Q(client__prenom_nom__icontains=recherche))
    groupes = (
        qs.values('numero_facture')
        .annotate(
            total=Sum(Cast('montant_facture', MONTANT)),
            paye=Sum('montpaye'),
            date_min=Min('date_facture'),
            echeance=Max('date_echeance'),
            cli=Max('client_id'),
        )
        .order_by('-numero_facture')
    )
    clients = Client.objects.in_bulk({g['cli'] for g in groupes})
    resultat = []
    for g in groupes:
        total = g['total'] or 0
        paye = g['paye'] or 0
        reste = total - paye
        solde = reste <= 0
        if etat == 'soldees' and not solde:
            continue
        if etat == 'impayees' and solde:
            continue
        resultat.append({
            'numero': g['numero_facture'],
            'client': clients.get(g['cli']),
            'date': g['date_min'],
            'echeance': g['echeance'],
            'total': total,
            'paye': paye,
            'reste': reste,
            'solde': solde,
        })
    return resultat


def facture_liste(request):
    recherche = request.GET.get('q', '').strip()
    etat = request.GET.get('etat', '')
    echeance = request.GET.get('echeance', '').strip()
    groupes = _groupes_factures(_societe(), recherche=recherche, etat=etat)
    if echeance:
        try:
            limite = date.fromisoformat(echeance)
            groupes = [g for g in groupes if g['echeance'] is not None and g['echeance'] <= limite]
        except ValueError:
            pass
    return render(request, 'couture/facture_liste.html', {
        'page_obj': Paginator(groupes, PAR_PAGE).get_page(request.GET.get('page')),
        'filtres': _filtres_get(request, 'q', 'etat', 'echeance'),
        'recherche': recherche, 'etat': etat, 'echeance': echeance, 'page': 'factures',
    })


def _lignes_facture(societe, numero):
    """Lignes d'articles d'une facture. Le PHP stocke les listes séparées par des virgules."""
    lignes = []
    for d in DetailFacture.objects.filter(facture__numero_facture=numero, id_societe=societe):
        noms = d.article.split(',')
        prix = d.prix_unitaire.split(',')
        qtes = d.nombre.split(',')
        for i, nom in enumerate(noms):
            p = _vers_nombre(prix[i]) if i < len(prix) else 0
            q = _vers_nombre(qtes[i]) if i < len(qtes) else 0
            lignes.append({'article': nom, 'prix': p, 'qte': q, 'total': p * q})
    return lignes


def facture_detail(request, numero):
    tranches = list(
        Facture.objects.filter(numero_facture=numero, id_societe=_societe())
        .select_related('client').order_by('id_facture')
    )
    if not tranches:
        raise Http404('Facture introuvable')
    total = sum(f.montant for f in tranches)
    paye = sum((f.montpaye or 0) for f in tranches)
    reste = total - paye
    return render(request, 'couture/facture_detail.html', {
        'numero': numero,
        'client': tranches[0].client,
        'echeance': tranches[0].date_echeance,
        'tranches': tranches,
        'lignes': _lignes_facture(_societe(), numero),
        'total': total, 'paye': paye, 'reste': reste, 'solde': reste <= 0,
        'lien_whatsapp_facture': lien_whatsapp(
            tranches[0].client.telephone,
            texte_facture(tranches[0].client.prenom_nom, numero, reste)),
        'telephone_client': tranches[0].client.telephone,
        'whatsapp_donnees': {
            'telephone_valide': lien_whatsapp(tranches[0].client.telephone, '') is not None,
            'lien': lien_whatsapp(tranches[0].client.telephone, texte_facture(tranches[0].client.prenom_nom, numero, reste)),
            'texte': texte_facture(tranches[0].client.prenom_nom, numero, reste),
            'titre': f'Facture {numero}',
            'nom_fichier': f'facture-{numero}.pdf',
            'pdf_url': reverse('couture:facture_imprimer', args=[numero]),
        },
        'page': 'factures',
    })


def facture_encaisser(request, numero):
    """Ajoute un acompte (tranche) à une facture, comme ajout_ac.php."""
    societe = _societe()
    groupe = next((g for g in _groupes_factures(societe) if g['numero'] == numero), None)
    if groupe is None:
        raise Http404('Facture introuvable')

    form = PaiementForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        montant = form.cleaned_data['montant']
        if montant > groupe['reste']:
            messages.error(request, f"Le montant dépasse le reste à payer ({groupe['reste']}).")
        else:
            premiere = Facture.objects.filter(numero_facture=numero, id_societe=societe).order_by('id_facture').first()
            now = datetime.now()
            with transaction.atomic(using=router.db_for_write(Facture)):
                Facture.objects.create(
                    client=premiere.client,
                    date_facture=now.date(),
                    heure_facture=now.time().replace(microsecond=0),
                    date_echeance=premiere.date_echeance,
                    id_societe=societe,
                    numero_facture=numero,
                    montant_facture='0',
                    montpaye=montant,
                    etat_facture=0,
                )
                solde = groupe['reste'] - montant <= 0
                Facture.objects.filter(numero_facture=numero, id_societe=societe).update(
                    etat_facture=1 if solde else 0)
            messages.success(request, 'Paiement enregistré.')
            return redirect(reverse('couture:facture_detail', args=[numero]))

    return render(request, 'couture/facture_paiement.html', {
        'form': form, 'numero': numero, 'groupe': groupe, 'page': 'factures',
    })


def facture_imprimer(request, numero):
    """Facture au format PDF (affichage dans le navigateur ou téléchargement)."""
    impression = request.GET.get('impression') == '1'
    contenu = facture_pdf(numero, _societe(), avec_mesures=impression)
    if contenu is None:
        raise Http404('Facture introuvable')
    reponse = HttpResponse(contenu, content_type='application/pdf')
    reponse['Content-Disposition'] = f'inline; filename="facture-{numero}.pdf"'
    return reponse


# ================================================================ Connexion
def _accueil(request):
    from comptes.acces import ACCUEIL
    from comptes.context_processors import profil_de
    return redirect(reverse(ACCUEIL.get(profil_de(request), 'couture:connexion')))


def _premiere_connexion(identifiant, password):
    """Crée le compte Django à partir de la table `user` existante, une seule fois.

    Le mot de passe est lu en lecture seule dans la table PHP, puis enregistré haché
    dans la base Django. La table `user` n'est jamais modifiée.
    """
    from django.contrib.auth import get_user_model
    from comptes.models import ProfilCompte

    if get_user_model().objects.filter(username=identifiant).exists():
        return None  # compte déjà créé : seul le mot de passe Django fait foi
    legacy = UtilisateurLegacy.objects.filter(login=identifiant, password=password).first()
    if legacy is None:
        return None
    with transaction.atomic():
        utilisateur = get_user_model()(username=identifiant)
        utilisateur.set_password(password)
        utilisateur.save()
        ProfilCompte.objects.create(
            user=utilisateur,
            legacy_id=legacy.pk,
            profil=legacy.profil_id,
            id_societe=legacy.id_societe,
        )
    return utilisateur


def connexion(request):
    if request.user.is_authenticated and request.method == 'GET':
        return _accueil(request)

    form = ConnexionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login_saisi = form.cleaned_data['login']
        mot_de_passe = form.cleaned_data['password']
        utilisateur = authenticate(request, username=login_saisi, password=mot_de_passe)
        if utilisateur is None:
            utilisateur = _premiere_connexion(login_saisi, mot_de_passe)
        if utilisateur is None:
            form.add_error(None, "Nom d'utilisateur ou mot de passe incorrect.")
        else:
            login(request, utilisateur)
            suivant = request.POST.get('suivant') or request.GET.get('suivant') or ''
            if suivant and url_has_allowed_host_and_scheme(suivant, allowed_hosts={request.get_host()}):
                return redirect(suivant)
            return _accueil(request)

    return render(request, 'couture/login.html', {
        'form': form,
        'suivant': request.GET.get('suivant', ''),
    })


@require_POST
def deconnexion(request):
    logout(request)
    return redirect(reverse('couture:connexion'))


# ================================================================ Caisse, comptabilité, marquage
def caisse(request):
    """Caisse : factures non soldées et encaissement d'un acompte (acompte.php, ajout_ac.php)."""
    recherche = request.GET.get('q', '').strip()
    groupes = _groupes_factures(_societe(), recherche=recherche, etat='impayees')
    return render(request, 'couture/caisse.html', {
        'page_obj': Paginator(groupes, PAR_PAGE).get_page(request.GET.get('page')),
        'filtres': _filtres_get(request, 'q'),
        'recherche': recherche, 'page': 'caisse',
    })


def comptabilite(request):
    """Synthèse comptable (compta.php, finance.php)."""
    factures = Facture.objects.filter(id_societe=_societe())
    agr = factures.annotate(montant_num=Cast('montant_facture', MONTANT)).aggregate(
        total=Sum('montant_num'), paye=Sum('montpaye'))
    total = agr['total'] or 0
    paye = agr['paye'] or 0
    return render(request, 'couture/comptabilite.html', {
        'total_facture': total,
        'total_paye': paye,
        'reste_a_payer': total - paye,
        'nb_factures': factures.values('numero_facture').distinct().count(),
        'nb_impayees': len([g for g in _groupes_factures(_societe()) if not g['solde']]),
        'page': 'comptabilite',
    })


MARQUAGE_SECTIONS = {
    'tailleur': 'Tailleurs',
    'tarif': 'Tarifs',
    'marquage': 'Marquage',
    'honoraires': 'Honoraires',
}


def marquage(request, section=None):
    """Marquage (tailleurs, tarifs, broderie, couture, boutons, honoraires) : pas encore migré."""
    return render(request, 'couture/marquage.html', {
        'page': 'marquage',
        'section': section,
        'section_titre': MARQUAGE_SECTIONS.get(section, 'Marquage'),
        'sections': MARQUAGE_SECTIONS,
    })


# ================================================================ Mesures (liste)
def mesure_liste(request):
    nom = request.GET.get('nom', '').strip()
    mesures = Mesure.objects.filter(id_societe=_societe()).select_related('client').order_by('-id_mesure')
    if nom:
        mesures = mesures.filter(client__prenom_nom__icontains=nom)
    return render(request, 'couture/mesure_liste.html', {
        'page_obj': _paginer(request, mesures),
        'filtres': _filtres_get(request, 'nom'),
        'nom': nom, 'page': 'mesures',
    })


# ================================================================ Facturation : état de suivi
def facture_suivi(request):
    """État de suivi : toutes les factures, classées par échéance, en retard en évidence."""
    etat = request.GET.get('etat', '')
    from .periodes import MOIS
    aujourdhui = date.today()
    groupes = _groupes_factures(_societe(), etat=etat)
    for g in groupes:
        g['en_retard'] = (not g['solde']) and g['echeance'] is not None and g['echeance'] < aujourdhui
        reference = g['echeance'] or g['date'] or aujourdhui
        g['annee'] = reference.year
        g['mois'] = f"{MOIS[reference.month - 1].capitalize()} {reference.year}"
        g['cle_mois'] = (reference.year, reference.month)
    annees = sorted({g['annee'] for g in groupes}, reverse=True)
    # Par défaut : année en cours ; « toutes » affiche toutes les années groupées.
    annee = request.GET.get('annee', str(aujourdhui.year))
    if annee != 'toutes':
        try:
            annee = int(annee)
        except ValueError:
            annee = aujourdhui.year
        groupes = [g for g in groupes if g['annee'] == annee]
    groupes.sort(key=lambda g: (-g['annee'], g['cle_mois'][1], g['echeance'] is None, g['echeance'] or date.max, g['numero']))
    return render(request, 'couture/facture_suivi.html', {
        'page_obj': Paginator(groupes, PAR_PAGE).get_page(request.GET.get('page')),
        'filtres': _filtres_get(request, 'etat', 'annee'),
        'etat': etat, 'annee': annee, 'annees': annees, 'annee_courante': aujourdhui.year,
        'page': 'factures_suivi',
    })


# ================================================================ Paramètres (lecture seule)
def profils_liste(request):
    comptes = {}
    for u in UtilisateurLegacy.objects.values('profil_id'):
        comptes[u['profil_id']] = comptes.get(u['profil_id'], 0) + 1
    profils = [{'profil': p, 'nb_comptes': comptes.get(p.pk, 0)} for p in Profil.objects.order_by('id_profil')]
    return render(request, 'couture/profils_liste.html', {'profils': profils, 'page': 'parametres', 'onglet': 'profils'})


def utilisateurs_liste(request):
    from comptes.models import ProfilCompte
    from comptes.acces import PROFIL_LIBELLES
    comptes = ProfilCompte.objects.select_related('user').order_by('user__username')
    lignes = [{'compte': c, 'profil_libelle': PROFIL_LIBELLES.get(c.profil, 'Sans profil')} for c in comptes]
    return render(request, 'couture/utilisateurs_liste.html', {
        'page_obj': _paginer(request, lignes), 'filtres': {}, 'page': 'parametres', 'onglet': 'utilisateurs',
    })
