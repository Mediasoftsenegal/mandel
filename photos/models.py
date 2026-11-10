import io

from django.core.files.base import ContentFile
from django.db import models
from django.db.models import Count, F
from PIL import Image

NOMBRE_PHOTOS_PAR_MODELE = 5    # un modèle a 5 photos exactement, ou aucune
NOMBRE_MAX_MODELES = 15         # seuls 15 modèles peuvent avoir des photos
TAILLE_MAX_UPLOAD = 2 * 1024 * 1024
COTE_MAX = 800
QUALITE_JPEG = 80


class PhotoModele(models.Model):
    """Une des 5 photos d'un modèle. `position` = 1 à 5. `score` = votes d'évaluation."""
    modele_id = models.IntegerField(help_text='Identifiant du modèle (codemod)')
    position = models.PositiveSmallIntegerField()
    image = models.ImageField(upload_to='modeles/')
    score = models.IntegerField(default=0)
    societe = models.IntegerField(default=1)

    class Meta:
        verbose_name = 'photo de modèle'
        unique_together = [('modele_id', 'position')]
        ordering = ['modele_id', 'position']

    def __str__(self):
        return f'Modèle {self.modele_id} · photo {self.position}'


class GalerieInvalide(Exception):
    pass


def photos_du_modele(modele_id):
    return list(PhotoModele.objects.filter(modele_id=modele_id).order_by('position'))


def nombre_modeles_avec_galerie(societe=1):
    """Modèles qui ont leur galerie complète (5 photos)."""
    return (PhotoModele.objects.filter(societe=societe).values('modele_id')
            .annotate(n=Count('id')).filter(n=NOMBRE_PHOTOS_PAR_MODELE).count())


def _image_reduite(fichier):
    if fichier.size > TAILLE_MAX_UPLOAD:
        raise GalerieInvalide('Photo trop lourde (2 Mo maximum).')
    try:
        image = Image.open(fichier).convert('RGB')
    except Exception:
        raise GalerieInvalide('Le fichier n’est pas une image valide.')
    image.thumbnail((COTE_MAX, COTE_MAX))
    tampon = io.BytesIO()
    image.save(tampon, format='JPEG', quality=QUALITE_JPEG, optimize=True)
    return tampon.getvalue()


def appliquer_galerie(modele_id, fichiers, a_supprimer, societe=1):
    """Met à jour la galerie d'un modèle.

    fichiers : {position: fichier téléversé} ; a_supprimer : ensemble de positions.
    Le résultat doit compter 0 ou 5 photos. Lève GalerieInvalide sinon.
    """
    existantes = {p.position: p for p in photos_du_modele(modele_id)}
    finale = {}
    for pos in range(1, NOMBRE_PHOTOS_PAR_MODELE + 1):
        if pos in a_supprimer and pos not in fichiers:
            continue
        if pos in existantes or pos in fichiers:
            finale[pos] = True
    if len(finale) not in (0, NOMBRE_PHOTOS_PAR_MODELE):
        raise GalerieInvalide(
            f'Un modèle a {NOMBRE_PHOTOS_PAR_MODELE} photos exactement, ou aucune. '
            f'Il en reste {len(finale)} après cette modification.')

    deja_complet = len(existantes) == NOMBRE_PHOTOS_PAR_MODELE
    if len(finale) == NOMBRE_PHOTOS_PAR_MODELE and not deja_complet:
        if nombre_modeles_avec_galerie(societe) >= NOMBRE_MAX_MODELES:
            raise GalerieInvalide(f'Limite atteinte : {NOMBRE_MAX_MODELES} modèles ont déjà leurs photos.')

    # Préparation des images avant toute écriture.
    nouvelles = {pos: _image_reduite(f) for pos, f in fichiers.items()}

    for pos in range(1, NOMBRE_PHOTOS_PAR_MODELE + 1):
        existante = existantes.get(pos)
        if pos in nouvelles:
            if existante is None:
                existante = PhotoModele(modele_id=modele_id, position=pos, societe=societe)
            else:
                existante.image.delete(save=False)
            existante.image.save(f'modele-{modele_id}-{pos}.jpg', ContentFile(nouvelles[pos]), save=False)
            existante.save()
        elif pos in a_supprimer and existante is not None:
            existante.image.delete(save=False)
            existante.delete()
        # si pos n'est ni téléversée ni supprimée, on garde ce qui existe
    if len(finale) == 0:
        for p in photos_du_modele(modele_id):
            p.image.delete(save=False)
            p.delete()


def voter(photo_pk):
    PhotoModele.objects.filter(pk=photo_pk).update(score=F('score') + 1)
