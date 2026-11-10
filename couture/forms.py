from django import forms

from .models import Client, Mesure, Modele, Produit, Tarification


class ClientForm(forms.ModelForm):
    genre = forms.ChoiceField(
        choices=[('Homme', 'Homme'), ('Femme', 'Femme')],
        widget=forms.RadioSelect,
        required=False,
    )

    class Meta:
        model = Client
        fields = ['prenom_nom', 'genre', 'telephone', 'adresse']
        labels = {
            'prenom_nom': 'Prénom et nom',
            'genre': 'Genre',
            'telephone': 'Téléphone',
            'adresse': 'Adresse',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['prenom_nom'].required = True

    def clean_prenom_nom(self):
        # espaces internes normalisés, majuscules comme dans le formulaire PHP
        return ' '.join((self.cleaned_data.get('prenom_nom') or '').split()).upper()


# ---------------------------------------------------------------- Mesures
# Mêmes colonnes que le PHP enregistre (insert_client.php, bt_mesure et bt_mesure_1).
CHAMPS_HOMME = [
    'longueur', 'epaule', 'manche', 'cou', 'longueurpantalon', 'thiaya', 'ceinture',
    'cuisse', 'tourfess', 'bas', 'poitrine', 'tourmanche', 'longueurgrandboubou',
]
# Le formulaire femme n'a pas de champ `thiaya` ; les champs propres à la femme
# (hanche, pince, blouse...) n'ont pas de colonne dans `mesure` : ils ne sont pas saisis.
CHAMPS_FEMME = [
    'longueur', 'epaule', 'manche', 'cou', 'longueurpantalon', 'ceinture',
    'cuisse', 'tourfess', 'bas', 'poitrine', 'tourmanche', 'longueurgrandboubou',
]

LIBELLES_MESURE = {
    'longueur': 'Longueur', 'epaule': 'Épaule', 'manche': 'Manche', 'cou': 'Cou',
    'longueurpantalon': 'Longueur pantalon', 'thiaya': 'Thiaya', 'ceinture': 'Ceinture',
    'cuisse': 'Cuisse', 'tourfess': 'Tour de fesses', 'bas': 'Bas', 'poitrine': 'Poitrine',
    'tourmanche': 'Tour de manche', 'longueurgrandboubou': 'Longueur grand boubou',
}


class _MesureBaseForm(forms.ModelForm):
    class Meta:
        model = Mesure
        fields = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.update({'min': 0, 'inputmode': 'numeric'})


class MesureHommeForm(_MesureBaseForm):
    class Meta(_MesureBaseForm.Meta):
        fields = CHAMPS_HOMME
        labels = {c: LIBELLES_MESURE[c] for c in CHAMPS_HOMME}


class MesureFemmeForm(_MesureBaseForm):
    class Meta(_MesureBaseForm.Meta):
        fields = CHAMPS_FEMME
        labels = {c: LIBELLES_MESURE[c] for c in CHAMPS_FEMME}


# ---------------------------------------------------------------- Articles (table produit)
class ArticleForm(forms.ModelForm):
    catp = forms.ChoiceField(choices=[('PAP', 'PAP'), ('TISSU', 'Tissu')], label='Catégorie')
    genre = forms.ChoiceField(choices=[('Homme', 'Homme'), ('Femme', 'Femme')], label='Genre')
    modele = forms.ModelChoiceField(queryset=Modele.objects.none(), label='Modèle')

    class Meta:
        model = Produit
        fields = ['des', 'pu', 'catp', 'modele', 'genre', 'couleur']
        labels = {'des': 'Désignation', 'pu': 'Prix unitaire', 'couleur': 'Couleur'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['modele'].queryset = Modele.objects.order_by('libmod')

    def clean_des(self):
        return ' '.join((self.cleaned_data.get('des') or '').split()).upper()


# ---------------------------------------------------------------- Modèles et tarifs
class ModeleForm(forms.ModelForm):
    class Meta:
        model = Modele
        fields = ['libmod']
        labels = {'libmod': 'Libellé du modèle'}


class TarificationForm(forms.ModelForm):
    class Meta:
        model = Tarification
        fields = ['tarif_simple', 'tarif_brodeur', 'tarif_bouton']
        labels = {
            'tarif_simple': 'Tarif simple',
            'tarif_brodeur': 'Tarif brodeur',
            'tarif_bouton': 'Tarif bouton',
        }


# ---------------------------------------------------------------- Factures
class FactureForm(forms.Form):
    client = forms.ModelChoiceField(queryset=Client.objects.none(), label='Client')
    numero_facture = forms.IntegerField(min_value=1, label='N° facture')
    date_echeance = forms.DateField(label='Date d’échéance', widget=forms.DateInput(attrs={'type': 'date'}))
    montpaye = forms.IntegerField(min_value=0, required=False, initial=0, label='Acompte versé')

    def __init__(self, *args, societe_id, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['client'].queryset = Client.objects.filter(
            id_societe=societe_id, etat=1).order_by('prenom_nom')


class LigneFactureForm(forms.Form):
    produit = forms.ModelChoiceField(queryset=Produit.objects.none(), required=False, label='Article')
    qty = forms.IntegerField(min_value=1, required=False, initial=1, label='Quantité')
    prix = forms.IntegerField(min_value=0, required=False, label='Prix unitaire')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['produit'].queryset = Produit.objects.order_by('des')


class PaiementForm(forms.Form):
    montant = forms.IntegerField(min_value=1, label='Montant encaissé')


class ConnexionForm(forms.Form):
    login = forms.CharField(label="Nom d'utilisateur", max_length=255,
                            widget=forms.TextInput(attrs={'autofocus': True, 'autocomplete': 'username'}))
    password = forms.CharField(label='Mot de passe', max_length=100,
                               widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}))


class ConfirmationFactureForm(forms.Form):
    """Étape 4 : confirmation de la facture (numéro, dates, acompte), comme fact.php."""
    numero_facture = forms.IntegerField(min_value=1, label='N° facture')
    date_facture = forms.DateField(label='Date de la facture', widget=forms.DateInput(attrs={'type': 'date'}))
    date_echeance = forms.DateField(label='Date de livraison', widget=forms.DateInput(attrs={'type': 'date'}))
    montpaye = forms.IntegerField(min_value=0, label='Acompte versé', initial=0)
