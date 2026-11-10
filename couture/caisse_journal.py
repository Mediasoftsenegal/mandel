"""Caisse du jour et livre de caisse (reprise de sbroderie_django : caisse/journal).

- Caisse du jour : factures créées à la date choisie, avec montant et encaissement.
- Livre de caisse : entrées (encaissements du jour) et sorties (dépenses), total de caisse.

Les dépenses sont stockées dans la base Django (application `depenses`) : la base
de production `mediapla_mandel` n'est pas modifiée.
"""

from datetime import date

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from depenses.models import Depense

from .models import Facture
from .views import _societe


def _jour_demande(request):
    brut = request.POST.get('jour') or request.GET.get('jour') or ''
    try:
        return date.fromisoformat(brut)
    except ValueError:
        return date.today()


def _entier(valeur):
    try:
        return int(float(str(valeur).replace(' ', '').replace(',', '.')))
    except (TypeError, ValueError):
        return 0


def caisse_jour(request):
    """Caisse du jour : factures de la journée, avec total facturé et encaissé."""
    jour = _jour_demande(request)
    lignes = list(Facture.objects.filter(id_societe=_societe(), date_facture=jour)
                  .order_by('heure_facture', 'id_facture'))
    total_facture = sum(f.montant for f in lignes)
    total_paye = sum((f.montpaye or 0) for f in lignes)
    return render(request, 'couture/caisse_jour.html', {
        'jour': jour,
        'lignes': lignes,
        'total_facture': total_facture,
        'total_paye': total_paye,
        'page': 'caisse',
    })


def livre_caisse(request):
    """Livre de caisse : entrées encaissées, sorties (dépenses) et total de caisse."""
    jour = _jour_demande(request)
    societe = _societe()
    entrees = list(Facture.objects.filter(id_societe=societe, date_facture=jour, montpaye__gt=0)
                   .select_related('client').order_by('heure_facture', 'id_facture'))
    total_entrees = sum((e.montpaye or 0) for e in entrees)
    sorties = list(Depense.objects.filter(societe=societe, date_depense=jour).order_by('id'))
    total_sorties = sum(s.montant for s in sorties)
    return render(request, 'couture/livre_caisse.html', {
        'jour': jour,
        'entrees': entrees,
        'sorties': sorties,
        'total_entrees': total_entrees,
        'total_sorties': total_sorties,
        'total_caisse': total_entrees - total_sorties,
        'page': 'caisse',
    })


@require_POST
def depense_ajouter(request):
    jour = _jour_demande(request)
    nom = ' '.join(request.POST.get('nom', '').split())
    objet = ' '.join(request.POST.get('objet', '').split())
    montant = _entier(request.POST.get('montant'))
    if nom and objet and montant > 0:
        Depense.objects.create(
            date_depense=jour, nom=nom[:250], objet=objet[:250], montant=montant,
            societe=_societe(),
            saisie_par=request.user.username if request.user.is_authenticated else '',
        )
        messages.success(request, 'Dépense enregistrée.')
    else:
        messages.error(request, 'Renseignez le bénéficiaire, l’objet et un montant supérieur à 0.')
    return redirect(f"{reverse('couture:livre_caisse')}?jour={jour.isoformat()}")


@require_POST
def depense_supprimer(request, pk):
    depense = get_object_or_404(Depense, pk=pk, societe=_societe())
    jour = depense.date_depense
    depense.delete()
    messages.success(request, 'Dépense supprimée.')
    return redirect(f"{reverse('couture:livre_caisse')}?jour={jour.isoformat()}")
