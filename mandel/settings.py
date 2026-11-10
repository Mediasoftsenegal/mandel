"""
Réglages Django du projet mandel.

Principe de migration :
- la base MySQL existante (`mediapla_mandel`) est branchée comme alias `legacy` ;
- les tables métier sont décrites par des modèles `managed = False` (Django ne les crée
  ni ne les modifie) ;
- les tables propres à Django (sessions, admin, auth) vivent dans l'alias `default`.

Tous les secrets et l'hôte de base viennent de variables d'environnement : rien de
sensible n'est écrit dans le code.
"""

import os
from pathlib import Path

try:  # hébergement sans compilateur : PyMySQL remplace mysqlclient
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).lower() in ('1', 'true', 'yes', 'on')


DEBUG = env_bool('DJANGO_DEBUG', default=True)
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'dev-only-insecure-key-a-remplacer-en-production',
)
if not DEBUG and SECRET_KEY.startswith('dev-only'):
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured('DJANGO_SECRET_KEY doit être défini en production.')
ALLOWED_HOSTS = [h for h in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h]
CSRF_TRUSTED_ORIGINS = [o for o in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if o]
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'couture',
    'comptes',
    'scores',
    'photos',
    'depenses',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'couture.middleware.AccesMiddleware',
]

ROOT_URLCONF = 'mandel.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'comptes.context_processors.acces',
            ],
        },
    },
]

WSGI_APPLICATION = 'mandel.wsgi.application'


# Bases de données
# Alias `default` : Django interne (sessions, admin, auth). SQLite en local.
# Alias `legacy`  : base MySQL existante de l'application PHP, en lecture/écriture métier.
#                   Activée seulement si MANDEL_DB_HOST est défini.

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.environ.get('DJANGO_SQLITE_PATH', BASE_DIR / 'db.sqlite3'),
    }
}

if os.environ.get('MANDEL_DB_HOST'):
    DATABASES['legacy'] = {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('MANDEL_DB_NAME', 'mediapla_mandel'),
        'USER': os.environ['MANDEL_DB_USER'],
        'PASSWORD': os.environ['MANDEL_DB_PASSWORD'],
        'HOST': os.environ['MANDEL_DB_HOST'],
        'PORT': os.environ.get('MANDEL_DB_PORT', '3306'),
        'OPTIONS': {'charset': 'utf8mb4'},
    }

DATABASE_ROUTERS = ['couture.routers.LegacyRouter']


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Dakar'
USE_I18N = True
USE_TZ = True


STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = os.environ.get('DJANGO_STATIC_ROOT', str(BASE_DIR / 'staticfiles'))

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Société utilisée par l'application PHP (id_societe = 1 en dur dans tout le code).
SOCIETE_ID = int(os.environ.get('MANDEL_SOCIETE_ID', '1'))

# Photos téléversées (photos de modèles)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.environ.get('DJANGO_MEDIA_ROOT', str(BASE_DIR / 'media'))
