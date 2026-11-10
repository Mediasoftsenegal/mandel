from django.conf import settings
from django.db import models


class ProfilCompte(models.Model):
    """Profil métier d'un compte. Le mot de passe est géré par `django.contrib.auth` (haché).

    `legacy_id` relie le compte à la ligne de la table `user` de l'application PHP,
    utile pour la première connexion et pour la traçabilité pendant la transition.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profilcompte')
    legacy_id = models.IntegerField(unique=True, null=True, blank=True)
    profil = models.IntegerField(null=True, blank=True, help_text='1 admin, 2 client, 3 caisse, 4 comptable, 5 marquage')
    id_societe = models.IntegerField(default=1)

    class Meta:
        verbose_name = 'profil de compte'

    def __str__(self):
        return f'{self.user.username} ({self.get_profil_display()})'

    def get_profil_display(self):
        from .acces import PROFIL_LIBELLES
        return PROFIL_LIBELLES.get(self.profil, 'Sans profil')
