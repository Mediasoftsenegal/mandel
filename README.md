# Mandel — version Django

Migration de l'application PHP `php_mandel` vers Django, avec la base MySQL existante `mediapla_mandel`.

## État de la migration

- [x] Projet Django, alias de base `legacy` (MySQL) et routeur (`couture/routers.py`)
- [x] Thème : navbar et boutons de validation `#00ACC1`, boutons du tableau de bord `#1E88E5`, sidebar `#28373E` (texte blanc), lignes de tableau alternées `#F2F2F2` / blanc
- [x] Tableau de bord (statistiques + dernières factures)
- [x] Modèles (non gérés par Django) pour les 11 tables utiles : `modele`, `client`, `factures`, `detail_facture`, `produit`, `tarification`, `mesure`, `tailleur`, `marquage`, `profil`, `user`. Types vérifiés contre `mediapla_mandel.sql` (structure seule, sans données).
- [x] Table `article` mappée (seule table non métier utilisée par le code PHP).
- [ ] Tables non utilisées par le code PHP, non mappées : `categorie`, `etat`, `facturation`, `status`, `societe`, `type_tailleur`, `type_tenue`.
- [ ] Dérive de schéma : le code PHP lit/écrit `client.etat`, `user.etat` et `profil.etat`, colonnes absentes du dump. Demander un export plus récent.
- [ ] Authentification sur la table `user` existante (mot de passe en clair à rehacher)
- [x] Module **clients** : liste et recherche, fiche (mesures et factures), création, modification. Filtré par `id_societe`. Suppression non portée : le PHP fait un passage à `etat = 0`, colonne absente du dump.
- [x] Clients : filtres prénom/nom, téléphone et état ; pagination de 35 par page ; activation/désactivation (pas de suppression).
- [x] Mesures : après création, formulaire **homme** (13 champs) ou **femme** (12 champs) selon le genre. Mêmes colonnes que le PHP. Les champs propres au formulaire femme (hanche, pince, blouse, taille, longueur de jupe, etc.) ne sont pas saisis : le PHP ne les enregistre pas non plus, et il n'y a pas de colonne pour eux.
- [ ] À confirmer : la colonne `client.etat` existe-t-elle sur la base de production ? Le PHP la lit déjà (panier, désactivation), mais le dump ne la contient pas. Aucune modification de base n'a été faite.
- [x] Clients ↔ mesures : fiche avec mesures, saisie selon le genre, modification d'une mesure (même formulaire que la saisie).
- [x] Articles (table `produit`, menu « Articles ») : liste filtrée et paginée, création, modification. La table `article` n'est pas migrée (voir ci-dessous).
- [x] Modèles et tarifs (`modele`, `tarification`) : liste, création, modification avec le tarif.
- [x] Factures (`factures`, `detail_facture`) : liste filtrée et paginée, détail, création avec lignes, encaissement (acompte) qui met à jour l'état comme le PHP (`ajout_ac.php`, `fonction.php`).
- [x] Impression PDF de la facture (`couture/pdf.py`, ReportLab) : en-tête, articles, total en lettres, acomptes, reste, conditions, fiche de mesures. Bouton « Imprimer (PDF) » sur la facture.
- [x] Page de connexion (fond et logo de production, liste des modules) ; connexion sur la table `user` existante, lecture seule ; toutes les pages exigent une session.
- [ ] Caisse, comptabilité.
- [ ] Vérification avec les données réelles (le dump ne contient aucune ligne) et encodage latin1
- [ ] Proposition tissus : voir `docs/proposition_modeles_tissus.md`

## Lancer en local

Développement : base SQLite locale (aucune donnée de production).

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Les tables métier n'existent pas dans SQLite : pour voir le tableau de bord avec des données de test, créer les tables et les lignes de test (script hors dépôt) ou brancher la base de développement (voir ci-dessous).

## Brancher la base MySQL (`legacy`)

Variables d'environnement, à définir hors du code :

```bash
export MANDEL_DB_HOST=localhost
export MANDEL_DB_NAME=mediapla_mandel
export MANDEL_DB_USER=...
export MANDEL_DB_PASSWORD=...
export DJANGO_SECRET_KEY=...
export DJANGO_DEBUG=0
export DJANGO_ALLOWED_HOSTS=mandel.exemple.sn
```

## Règles de sécurité pour la mise en production

- **Ne jamais lancer `migrate` contre `legacy`.** Le routeur l'interdit, mais vérifier avant chaque déploiement.
- Les identifiants MySQL présents dans le code PHP actuel doivent être changés et retirés du code source avant la bascule.
- Sauvegarder la base `mediapla_mandel` avant toute bascule ; l'application PHP reste en place pendant la transition.
- Le login PHP compare le mot de passe en clair et concatène le login dans le SQL : ne pas reprendre ce mécanisme. Les mots de passe devront être rehachés au premier login.
- Vérifier l'encodage : le code PHP mélange `utf8` et `utf8_encode`/`utf8_decode`. Des accents peuvent être doublement encodés en base ; contrôler avant la migration des données.
- Vérifier les schémas de la table `mesure` : plusieurs `INSERT` du code PHP n'ont pas les mêmes colonnes.

## Ce qui n'est pas porté (à décider)

- **PDF** : mise en page reprise du FPDF PHP. Écarts : « Soldée le » n'apparaît que si la facture est soldée (PHP : toujours) ; la fiche de mesures n'affiche que les champs enregistrés (les champs femme propres ne le sont pas).
- **Suppressions** : suppression d'articles (`articles/supp.php`), de modèles (`annul_modele.php`) et de factures (`facture/supp.php`) ne sont pas portées. Les clients sont désactivés, pas supprimés.
- **Lien facture ↔ marquage** : la création de facture en PHP écrit aussi dans la table `marquage` (`facture/facture.php`). Non porté : à confirmer avec le suivi de fabrication.
- **Table `article`** (`type_article`, `longueur`, `couleur`) : lue seulement par la page racine `article.php`, qui n'est pas dans le menu. Non migrée.
- **Numérotation** : le numéro suivant est `max(numero_facture) + 1` sur la société (le PHP le calcule sur toute la table). Identique tant qu'une seule société existe.
- **Détail de facture** : le PHP stocke articles, prix et quantités dans des listes séparées par des virgules. Django garde ce format pour rester compatible pendant la transition ; un nom d'article contenant une virgule casserait l'affichage. Une table de lignes serait plus propre, à décider avec le schéma.
- **Limite de 250 caractères** sur le détail d'une facture (colonne `varchar(250)`).

## Tableau de bord

- Liste déroulante de période : Jour, Semaine, Quinzaine, Mois, Trimestre, Semestriel, Annuel. Chaque période est la période **en cours** (ex. « Mois » = mois de la date du jour).
- Activité de la période : factures créées (chiffre en orange `#FFB22B`), total facturé, encaissé, taux d'encaissement, panier moyen.
- Situation à ce jour : reste à encaisser, factures en retard, échéances dans 7 jours, clients actifs.
- Graphe : paiements encaissés par mois sur l'année en cours (Chart.js, chargé depuis cdnjs).
- Listes : clients à relancer (reste le plus élevé) et articles les plus vendus sur la période.
- Les dates de paiement sont celles des lignes de facture (acomptes inclus). Les clients n'ont pas de date de création dans la base : pas d'indicateur « nouveaux clients ».

## Mise en page (listes et fiches)

- Toutes les listes sont paginées à 35 éléments. La barre de pagination est toujours affichée : nombre d'éléments, numéros de page, « ‹ » et « › ». Les filtres sont conservés d'une page à l'autre.

- En-tête de chaque liste : titre à gauche, bouton « Nouveau… » en haut à droite.
- Filtres en 4 zones ; la 4e regroupe « Filtrer » et « Réinitialiser ».
- Libellés cliquables : nom du client, désignation d'article, libellé de modèle, numéro de facture.
- Fiches de saisie : cartes à libellés à gauche et champs à droite, sections numérotées (modèle Fab Admin « forms/general »).

## Modèles et photos

- Le tarif n'est plus saisi dans la fiche modèle (les anciennes lignes de tarification restent en base, non modifiées).
- **Galerie** : chaque modèle a **5 photos exactement, ou aucune**. Depuis la fiche modèle, « Gérer les 5 photos » ouvre la galerie. Une photo peut être ajoutée, remplacée ou supprimée, mais le résultat doit compter 5 photos ou 0.
- **15 modèles au maximum** peuvent avoir leur galerie complète. Le 16e est refusé tant qu'un modèle n'a pas été vidé.
- Chaque photo est réduite à 800 px en JPEG, 2 Mo maximum à l'envoi.
- **Évaluation** : le bouton « Voter » ajoute +1 au score d'une photo. La page « Évaluation des photos » classe toutes les photos par score. La liste des modèles affiche la photo la mieux notée de chaque modèle.
- Les photos sont dans le dossier `media/` (base Django).

## Score des modèles

- Chaque fois qu'un modèle est choisi dans une facture (une ligne d'article), son score augmente de +1. Deux lignes du même modèle = +2.
- Le score est stocké dans la base Django (application `scores`), pas dans la table PHP `modele`.
- Visible dans la liste des modèles (triable) et sur la fiche modèle. Non modifiable à la main.

## WhatsApp

- **Relance** (tableau de bord, « Clients à relancer ») : le bouton ouvre WhatsApp avec un message prérempli (nom, reste à payer). Rien n'est envoyé automatiquement : c'est vous qui validez.
- **Impression** : le PDF imprimé (« Imprimer (PDF) ») affiche les mesures du client juste sous le tableau des articles. Le PDF envoyé par WhatsApp ne les contient pas.
- **Facture** (fiche facture, « Envoyer par WhatsApp ») : sur téléphone, la feuille de partage s'ouvre avec le PDF joint. Sur ordinateur, le PDF est téléchargé et WhatsApp s'ouvre avec le texte : il faut joindre le fichier à la main.
- Numéros sénégalais à 9 chiffres (ex. 77 123 45 67) convertis automatiquement au format international (221…). Sans numéro valide, le bouton est désactivé.

## Menu

Ordre du menu de gauche : Clients, Mesures, Articles, Modèles, Facturation (Factures, Acomptes, État de suivi, Indicateur), Marquage (Tailleur, Tarif, Marquage, Honoraires), Paramètres (Profil, Utilisateurs). Le tableau de bord reste en tête, réservé à l'administrateur.

- **Acomptes** = la caisse (`acompte.php` dans le PHP). **Indicateur** = la synthèse comptable.
- **Marquage** : les quatre sous-pages sont des pages « en cours de migration ».
- **Paramètres** : Profil et Utilisateurs sont en lecture seule. Les comptes sont créés à la première connexion.

## Connexion et profils

- **Pas de mot de passe en clair dans Django** : les comptes sont des comptes Django (`django.contrib.auth`), avec mot de passe haché.
- **Première connexion** : si le compte n'existe pas encore dans Django, le mot de passe est vérifié une seule fois contre la table `user` (lecture seule), puis le compte est créé avec le mot de passe haché. La table `user` n'est jamais modifiée.
- **Ensuite** : seul le mot de passe Django fait foi. Un changement de mot de passe fait dans l'application PHP n'est pas repris.
- **Reste à traiter** : les mots de passe en clair restent dans `mediapla_mandel.user` tant que la base n'est pas modifiée. À décider en fin de migration (rehachage ou suppression de la colonne).
- **Profils** (`comptes/acces.py`) : 1 administrateur (tout), 2 client (clients), 3 caisse (caisse et factures), 4 comptable (comptabilité et factures), 5 marquage (marquage). Chaque profil arrive sur sa page d'accueil, et l'accès est refusé aux autres modules. Un profil ajusté ici reflète le dossier PHP de chaque profil ; à valider avec l'équipe.
- **Compte sans profil** : accès refusé.
- **Créer un compte administrateur Django** (pour `/admin/`) : `python manage.py createsuperuser`.
- **Compte désactivé** : `user.etat` n'est pas vérifié (colonne absente du dump).
- **Sessions** : stockées dans la base `default` (SQLite en local). En production, prévoir une base dédiée.

## Points à décider en fin de migration (après déploiement final)

Aucune modification de la base `mediapla_mandel` n'est faite pendant la migration. Les points suivants sont reportés à la fin, une fois la version Django déployée.

1. **Champs femme absents de la table `mesure`** : hanche, pince, blouse, taille, longueur de robe, longueur de jupe, tour de bras, poignet, taille du cou. Le formulaire PHP les saisit, mais ne les enregistre pas. Options : ne jamais les saisir, ou ajouter les colonnes correspondantes (`ALTER TABLE mesure ADD COLUMN ...`) puis les activer dans `couture/forms.py` (`CHAMPS_FEMME`).
2. **Colonne `client.etat`** : le PHP la lit déjà (panier, désactivation), mais elle n'est pas dans le dump. Si elle n'existe pas en production, la désactivation d'un client échouera, et le filtre « actifs / désactivés » ne fonctionnera pas. À vérifier sur la base réelle. Si elle manque, l'ajouter avec `DEFAULT 1` pour garder les clients existants actifs.
3. **Tables non utilisées** : `categorie`, `etat`, `facturation`, `status`, `societe`, `type_tailleur`, `type_tenue` ne sont pas mappées. Décider si elles seront supprimées ou gardées pour référence.
4. **Encodage** : vérifier sur une copie de la base que les accents ne sont pas doublement encodés (tables en latin1 et code PHP mêlant `utf8_encode` / `utf8_decode`).
5. **Mots de passe** : les mots de passe de la table `user` sont en clair. À rehacher à la première connexion sur la version Django, puis à décider si l'on garde l'ancienne colonne.
