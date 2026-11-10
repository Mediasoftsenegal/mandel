# Déploiement sur cPanel (hébergement mutualisé)

Cible : `public_html/neo_mand` sur le serveur, à côté de l'application PHP actuelle, qui n'est pas modifiée.

## 1. Préparer l'hébergement
1. cPanel → **Setup Python App** → Créer une application :
   - Python 3.11 ou plus récent
   - Application root : `neo_mand`
   - Application URL : le domaine ou le sous-dossier choisi
   - Startup file : `passenger_wsgi.py`
2. Dans cette même page, ajouter les variables d'environnement de `deploy/.env.example`.
   Ne pas écrire le mot de passe MySQL dans un fichier partagé.
3. Noter la commande d'activation du virtualenv affichée par cPanel.

## 2. Envoyer les fichiers
- Envoyer l'archive `mandel_django_deploy.zip` dans `public_html/neo_mand` (gestionnaire de fichiers ou SFTP).
- Décompresser. Ne pas envoyer `db.sqlite3`, `media/`, ni `.env` depuis le poste de développement.

## 3. Installer et initialiser (terminal cPanel, dans le virtualenv)
```bash
pip install -r requirements.txt
mkdir -p data media
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser     # compte administrateur Django (/admin/)
```
- `migrate` ne touche qu'à la base Django (`DJANGO_SQLITE_PATH`). La base MySQL `mediapla_mandel` n'est jamais migrée.

## 4. Fichiers statiques et photos
- Les fichiers `staticfiles/` doivent être servis sur `/static/`, et `media/` sur `/media/`.
  Si cPanel ne le fait pas, ajouter dans `public_html/neo_mand/.htaccess` une règle d'alias (à valider sur l'hébergement).

## 5. HTTPS avant ouverture
- Activer le certificat SSL dans cPanel, puis mettre `DJANGO_CSRF_TRUSTED_ORIGINS=https://…`.
- Ensuite seulement, activer `SECURE_SSL_REDIRECT` et HSTS (avertissements `security.W004` et `W008` de `check --deploy`).

## 6. Points à vérifier avant la bascule
- `DJANGO_DEBUG=0` et `DJANGO_SECRET_KEY` long et aléatoire (l'application refuse de démarrer sans clé).
- Les mots de passe en clair restent dans `mediapla_mandel.user` (décision en fin de migration).
- Sauvegarde de la base MySQL avant toute connexion de la version Django.
