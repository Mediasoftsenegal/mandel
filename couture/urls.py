from django.urls import path

from . import caisse_journal as journal
from . import facture_nouvelle as nouvelle
from . import views

app_name = 'couture'

urlpatterns = [
    path('connexion/', views.connexion, name='connexion'),
    path('deconnexion/', views.deconnexion, name='deconnexion'),
    path('', views.tableau_de_bord, name='dashboard'),

    path('clients/', views.client_liste, name='client_liste'),
    path('clients/nouveau/', views.client_creer, name='client_creer'),
    path('clients/<int:pk>/', views.client_detail, name='client_detail'),
    path('clients/<int:pk>/modifier/', views.client_modifier, name='client_modifier'),
    path('clients/<int:pk>/etat/', views.client_basculer_etat, name='client_basculer_etat'),
    path('clients/<int:pk>/mesures/', views.mesure_creer, name='mesure_creer'),
    path('clients/<int:pk>/mesures/<int:mesure_pk>/modifier/', views.mesure_modifier, name='mesure_modifier'),

    path('articles/', views.article_liste, name='article_liste'),
    path('articles/nouveau/', views.article_creer, name='article_creer'),
    path('articles/<int:pk>/modifier/', views.article_modifier, name='article_modifier'),

    path('modeles/', views.modele_liste, name='modele_liste'),
    path('modeles/nouveau/', views.modele_creer, name='modele_creer'),
    path('modeles/<int:pk>/modifier/', views.modele_modifier, name='modele_modifier'),
    path('modeles/<int:pk>/photos/', views.modele_galerie, name='modele_galerie'),
    path('photos/evaluation/', views.photos_evaluation, name='photos_evaluation'),
    path('photos/<int:pk>/voter/', views.photo_voter, name='photo_voter'),

    path('caisse/', views.caisse, name='caisse'),
    path('caisse/jour/', journal.caisse_jour, name='caisse_jour'),
    path('caisse/livre/', journal.livre_caisse, name='livre_caisse'),
    path('caisse/depense/ajouter/', journal.depense_ajouter, name='depense_ajouter'),
    path('caisse/depense/<int:pk>/supprimer/', journal.depense_supprimer, name='depense_supprimer'),
    path('comptabilite/', views.comptabilite, name='comptabilite'),
    path('marquage/', views.marquage, name='marquage'),
    path('marquage/<str:section>/', views.marquage, name='marquage_section'),

    path('mesures/', views.mesure_liste, name='mesure_liste'),
    path('parametres/profils/', views.profils_liste, name='profils_liste'),
    path('parametres/utilisateurs/', views.utilisateurs_liste, name='utilisateurs_liste'),

    path('factures/', views.facture_liste, name='facture_liste'),
    path('factures/suivi/', views.facture_suivi, name='facture_suivi'),
    path('factures/nouvelle/', nouvelle.facture_creer, name='facture_creer'),
    path('factures/nouvelle/articles/', nouvelle.facture_articles, name='facture_articles'),
    path('factures/nouvelle/articles/<int:pk>/ajouter/', nouvelle.facture_ajouter, name='facture_ajouter'),
    path('factures/nouvelle/panier/', nouvelle.facture_panier, name='facture_panier'),
    path('factures/nouvelle/panier/<int:pk>/supprimer/', nouvelle.facture_supprimer_ligne, name='facture_supprimer_ligne'),
    path('factures/nouvelle/annuler/', nouvelle.facture_annuler, name='facture_annuler'),
    path('factures/nouvelle/confirmation/', nouvelle.facture_confirmation, name='facture_confirmation'),
    path('factures/<int:numero>/', views.facture_detail, name='facture_detail'),
    path('factures/<int:numero>/pdf/', views.facture_imprimer, name='facture_imprimer'),
    path('factures/<int:numero>/paiement/', views.facture_encaisser, name='facture_encaisser'),
]
