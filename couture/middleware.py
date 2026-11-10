from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse

from comptes.acces import ACCUEIL, module_pour_chemin, modules_pour
from comptes.context_processors import profil_de


class AccesMiddleware:
    """Contrôle d'accès : connexion obligatoire, puis accès aux seuls modules du profil.

    - pas de session -> page de connexion ;
    - module non autorisé pour le profil -> redirection vers la page d'accueil du profil ;
    - utilisateur sans profil -> accès refusé.
    Exemptés : connexion, fichiers statiques, administration Django (contrôle propre).
    """

    EXEMPTES = ('/static/', '/admin/')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        chemin = request.path
        if chemin.startswith(self.EXEMPTES) or chemin == reverse('couture:connexion'):
            return self.get_response(request)

        if not request.user.is_authenticated:
            return redirect(f"{reverse('couture:connexion')}?suivant={request.get_full_path()}")

        profil = profil_de(request)
        if profil not in ACCUEIL:
            return HttpResponseForbidden('Aucun profil ne vous a encore été attribué. Contactez l’administrateur.')

        module = module_pour_chemin(chemin)
        if module is not None and module not in modules_pour(profil):
            return redirect(reverse(ACCUEIL[profil]))
        return self.get_response(request)
