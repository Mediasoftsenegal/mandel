# Proposition : gestion des modèles de tissus (hommes et femmes)

## 1. Existant (application PHP)

- Table `modele` : seulement `libmod` (libellé). Aucune catégorie, aucune image.
- Table `produit` : `des`, `pu`, `catp`, `id_modele`, `genre`, `couleur`. Un produit lie un modèle à un genre et une couleur, sans notion de tissu.
- Table `tarification` : `tarif_simple`, `tarif_brodeur`, `tarif_bouton` par modèle. Le prix dépend du modèle seul.
- Table `mesure` : une colonne par mesure, dont beaucoup sont propres à un modèle (`longueurgrandboubou`, `thiaya`, `longueurjupe`, `longueurrobe`, `longueurpantalon`...). Rien ne dit quelles mesures sont requises pour quel modèle.
- Le type de tissu n'est pas modélisé (il apparaît seulement, peut-être, dans un libellé).

Conséquence : impossible de filtrer les modèles par genre ou tissu, de savoir quelles mesures prendre, ni de montrer un catalogue visuel au client.

## 2. Proposition

### 2.1 Catalogue structuré

| Entité | Champs proposés |
|---|---|
| **Catégorie de modèle** | nom (ex. Boubou, Grand boubou, Ensemble, Robe, Jupe, Chemise, Pantalon), genre (homme / femme / mixte) |
| **Modèle** | catégorie, libellé, description, photo, genre, actif (oui/non), mesures requises |
| **Type de tissu** | nom (ex. Bazin riche, Basin, Wax, Getzner, Lin, Dentelle/Guipure, Soie), prix au mètre indicatif, photo |
| **Variante** | modèle + tissu + couleur + motif, avec sa photo et son prix |

Une **variante** est l'unité vendue. Cela remplace la combinaison actuelle `produit` + `modele` et permet de répondre à « un boubou en bazin riche bleu nuit » sans créer un article par combinaison à la main.

### 2.2 Mesures liées au modèle

Chaque modèle déclare ses mesures requises (table de liaison `modele_mesure`). Au moment de la prise de mesure, le formulaire n'affiche que les champs utiles : pour un grand boubou, la longueur du grand boubou et le tour de poitrine ; pour une robe, la longueur de robe et la taille. Les champs non utilisés ne sont plus obligatoires.

### 2.3 Tarification par composants

Le prix d'une commande = prix de base du modèle + tissu (mètres × prix au mètre) + options (broderie, boutons, doublure). Les options existantes (`tarif_brodeur`, `tarif_bouton`) deviennent des lignes d'options réutilisables plutôt que des colonnes figées par modèle.

### 2.4 Affichage et choix pour le client

- Galerie filtrée par genre, catégorie et tissu, avec photos.
- Fiche modèle : photo, tissus disponibles, mesures demandées, fourchette de prix.
- Ajout direct au panier et à la facture depuis la galerie.

### 2.5 Suivi de fabrication (optionnel, phase 2)

Statut par pièce : à couper, en couture, essayage, terminé, livré. Affectation à un tailleur (`tailleur` existe déjà).

## 3. Migration depuis la base existante

- Créer les nouvelles tables à côté des anciennes, sans les supprimer.
- Script de reprise : chaque `modele` devient un modèle avec catégorie « à classer » ; chaque `produit` devient une variante ; le genre et la couleur sont repris tels quels.
- Les anciennes tables restent en lecture seule pendant la transition.

## 4. Questions à valider avec la couturière / le client

1. Liste exacte des modèles actuels et leurs catégories (boubou, grand boubou, thiaya, etc.).
2. Liste des tissus réellement utilisés et leur unité de vente (mètre, pièce, forfait).
3. Les prix sont-ils fixes par modèle ou négociés par client ?
4. Faut-il une photo obligatoire par modèle ?
5. Souhaitez-vous le suivi de fabrication dès la première version, ou plus tard ?

## 5. Ordre de réalisation suggéré

1. Catégories, tissus, modèles et variantes (modèles Django + admin).
2. Liaison modèle ↔ mesures et formulaire de mesure adaptatif.
3. Tarification par composants.
4. Galerie client et ajout au panier.
5. Suivi de fabrication (si validé).

## 6. Approche retenue pendant la migration (sans modifier la base)

Pour l'instant, les modèles, tarifs et articles sont migrés **tels quels** (`modele`, `tarification`, `produit`) : c'est la condition pour que l'application PHP et Django puissent tourner en parallèle sur la même base. Les points à corriger sont relevés ici, et la nouvelle structure ne sera créée qu'après la bascule.

Constats sur l'existant :
- La liste PHP des articles affiche `id_modele` (le numéro) au lieu du libellé du modèle. Django affiche le libellé.
- Un modèle peut avoir plusieurs lignes de tarification : la version Django prend la dernière enregistrée. À remplacer par une seule ligne par modèle et par société.
- La catégorie `catp` n'a que deux valeurs codées en dur (PAP, TISSU) : pas de référentiel.
- Le genre est répété sur le modèle et sur l'article (`produit.genre`) : une source de vérité suffirait.

Ordre proposé après la bascule :
1. Table des catégories et des tissus (référentiels).
2. Modèle = type de pièce (catégorie, genre, mesures requises), une seule tarification.
3. Article = variante (modèle + tissu + couleur), avec photo.
