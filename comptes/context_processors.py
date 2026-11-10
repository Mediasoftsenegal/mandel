from .acces import MODULES_LIBELLES, modules_pour


def acces(request):
    """Modules visibles dans le menu, selon le profil de l'utilisateur connecté."""
    profil = profil_de(request)
    autorises = modules_pour(profil)
    return {
        'modules_autorises': autorises,
        'modules_libelles': {m: MODULES_LIBELLES[m] for m in autorises},
        'profil_libelle': _libelle(profil),
    }


def profil_de(request):
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return None
    try:
        return user.profilcompte.profil
    except Exception:
        return None


def _libelle(profil):
    from .acces import PROFIL_LIBELLES
    return PROFIL_LIBELLES.get(profil, '')
