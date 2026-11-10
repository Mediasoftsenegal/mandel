from django.db import models


class Depense(models.Model):
    """Sortie de caisse (dépense) du livre de caisse. Stockée dans la base Django."""
    date_depense = models.DateField()
    nom = models.CharField(max_length=250)
    objet = models.CharField(max_length=250)
    montant = models.PositiveIntegerField()
    societe = models.IntegerField(default=1)
    saisie_par = models.CharField(max_length=150, blank=True)

    class Meta:
        verbose_name = 'dépense'
        ordering = ['id']

    def __str__(self):
        return f'{self.nom} - {self.objet}'
