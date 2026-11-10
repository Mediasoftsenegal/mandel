from django.db import models
from django.db.models import F


class ScoreModele(models.Model):
    """Nombre de fois qu'un modèle a été choisi par les clients (+1 à chaque choix).

    Stocké dans la base Django, pas dans la table `modele` de l'application PHP.
    """
    modele_id = models.IntegerField(unique=True, help_text='Identifiant du modèle (codemod)')
    societe = models.IntegerField(default=1)
    score = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'score de modèle'

    def __str__(self):
        return f'Modèle {self.modele_id} : {self.score}'


def incrementer(modele_id, societe=1, pas=1):
    """Ajoute `pas` au score du modèle (crée la ligne si besoin)."""
    obj, _ = ScoreModele.objects.get_or_create(modele_id=modele_id, defaults={'societe': societe})
    ScoreModele.objects.filter(pk=obj.pk).update(score=F('score') + pas)
