"""Modèles mappés sur la base MySQL existante `mediapla_mandel`.

Source : export structurel `mediapla_mandel.sql` (phpMyAdmin, MariaDB 10.6, MyISAM, latin1).

managed = False : Django ne crée ni ne modifie ces tables.
Attention : plusieurs colonnes de montant sont en `char(255)` (texte). Les calculs
doivent passer par un CAST (voir couture/views.py), jamais par une somme directe.
Toutes les tables portent `id_societe` : toute requête métier doit le filtrer.
"""

from django.db import models


class Modele(models.Model):
    codemod = models.AutoField(primary_key=True)
    libmod = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'modele'
        verbose_name = 'modèle'

    def __str__(self):
        return self.libmod


class Client(models.Model):
    id_client = models.AutoField(primary_key=True)
    prenom_nom = models.CharField(max_length=255, blank=True, null=True)
    genre = models.CharField(max_length=5, blank=True, null=True)
    telephone = models.CharField(max_length=255, blank=True, null=True)
    adresse = models.CharField(max_length=255, blank=True, null=True)
    id_societe = models.IntegerField()
    etat = models.IntegerField(default=1)  # 1 = actif, 0 = désactivé (pas de suppression)

    @property
    def actif(self):
        return self.etat == 1

    class Meta:
        managed = False
        db_table = 'client'
        verbose_name = 'client'

    def __str__(self):
        return self.prenom_nom or f'Client {self.id_client}'


class Facture(models.Model):
    id_facture = models.AutoField(primary_key=True)
    client = models.ForeignKey(Client, models.DO_NOTHING, db_column='id_client', related_name='factures')
    date_facture = models.DateField()
    id_societe = models.IntegerField()
    numero_facture = models.IntegerField()
    montant_facture = models.CharField(max_length=255)  # texte en base : voir CAST
    montpaye = models.IntegerField()
    etat_facture = models.IntegerField(default=0)
    heure_facture = models.TimeField()
    date_echeance = models.DateField()

    class Meta:
        managed = False
        db_table = 'factures'
        verbose_name = 'facture'

    @property
    def montant(self):
        return _vers_nombre(self.montant_facture)

    @property
    def reste(self):
        return self.montant - (self.montpaye or 0)

    def __str__(self):
        return f'Facture {self.numero_facture}'


class DetailFacture(models.Model):
    id_detail = models.AutoField(primary_key=True)
    facture = models.ForeignKey(Facture, models.DO_NOTHING, db_column='id_facture', related_name='details')
    client = models.ForeignKey(Client, models.DO_NOTHING, db_column='id_client')
    article = models.CharField(max_length=250)
    prix_unitaire = models.CharField(max_length=250)  # texte en base
    nombre = models.CharField(max_length=255)         # texte en base
    montant = models.IntegerField()
    id_societe = models.IntegerField()
    id_article = models.CharField(max_length=250)

    class Meta:
        managed = False
        db_table = 'detail_facture'
        verbose_name = 'ligne de facture'


class Produit(models.Model):
    codep = models.AutoField(primary_key=True)
    des = models.CharField(max_length=255)
    pu = models.IntegerField()
    qtstock = models.IntegerField(blank=True, null=True, default=0)
    catp = models.CharField(max_length=8)
    modele = models.ForeignKey(Modele, models.DO_NOTHING, db_column='id_modele')
    genre = models.CharField(max_length=100)
    couleur = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'produit'
        verbose_name = 'produit'

    def __str__(self):
        return self.des


class Tarification(models.Model):
    id_tarif = models.AutoField(primary_key=True)
    modele = models.ForeignKey(Modele, models.DO_NOTHING, db_column='id_modele')
    tarif_simple = models.IntegerField()
    tarif_brodeur = models.IntegerField()
    tarif_bouton = models.IntegerField()
    id_societe = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'tarification'
        verbose_name = 'tarif'


class Mesure(models.Model):
    id_mesure = models.AutoField(primary_key=True)
    genre = models.CharField(max_length=100, blank=True, null=True)
    telephone = models.CharField(max_length=50, blank=True, null=True)
    longueur = models.IntegerField(blank=True, null=True)
    longueurgrandboubou = models.IntegerField(blank=True, null=True)
    epaule = models.IntegerField(blank=True, null=True)
    cou = models.IntegerField(blank=True, null=True)
    manche = models.IntegerField(blank=True, null=True)
    longueurpantalon = models.IntegerField(blank=True, null=True)
    tourfess = models.IntegerField(blank=True, null=True)
    cuisse = models.IntegerField(blank=True, null=True)
    bas = models.IntegerField(blank=True, null=True)
    poitrine = models.IntegerField(blank=True, null=True)
    thiaya = models.IntegerField(blank=True, null=True)
    tourmanche = models.IntegerField(blank=True, null=True)
    ceinture = models.IntegerField(blank=True, null=True)
    id_societe = models.IntegerField(blank=True, null=True)
    client = models.ForeignKey(Client, models.DO_NOTHING, db_column='id_client', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'mesure'
        verbose_name = 'mesure'


class Tailleur(models.Model):
    id_tailleur = models.AutoField(primary_key=True)
    prenom_nom = models.CharField(max_length=255)
    type_tailleur = models.CharField(max_length=255)
    id_societe = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'tailleur'
        verbose_name = 'tailleur'

    def __str__(self):
        return self.prenom_nom


class Marquage(models.Model):
    id_marquage = models.AutoField(primary_key=True)
    id_article = models.IntegerField()
    date_broderie = models.DateField()
    id_brodeur = models.IntegerField()
    date_couture = models.DateField()
    id_couture = models.IntegerField()
    date_bouton = models.DateField()
    id_bouton = models.IntegerField()
    etat = models.IntegerField()
    numero_facture = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'marquage'
        verbose_name = 'marquage'


class Profil(models.Model):
    id_profil = models.AutoField(primary_key=True)
    nomprofil = models.CharField(max_length=255)
    id_societe = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'profil'
        verbose_name = 'profil'

    def __str__(self):
        return self.nomprofil


class UtilisateurLegacy(models.Model):
    """Table `user` de l'application PHP.

    Le mot de passe y est stocké en clair (char(100)). Ne pas l'utiliser tel quel
    pour l'authentification Django : il faudra le rehacher à la première connexion.
    """
    id_user = models.AutoField(primary_key=True)
    login = models.CharField(max_length=255)
    password = models.CharField(max_length=100)
    id_societe = models.IntegerField()
    profil = models.ForeignKey(Profil, models.DO_NOTHING, db_column='id_profil', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'user'
        verbose_name = 'utilisateur (legacy)'


def _vers_nombre(texte):
    """Convertit un montant stocké en texte (ex. '15 000', '15000.00') en entier."""
    if texte is None:
        return 0
    nettoye = ''.join(c for c in str(texte) if c.isdigit() or c in '.-')
    try:
        return int(float(nettoye)) if nettoye not in ('', '-', '.') else 0
    except ValueError:
        return 0


class Article(models.Model):
    """Table `article` (utilisée par article.php)."""
    id_article = models.AutoField(primary_key=True)
    type_article = models.IntegerField()
    longueur = models.IntegerField()
    couleur = models.CharField(max_length=255)
    id_societe = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'article'
        verbose_name = 'article'
