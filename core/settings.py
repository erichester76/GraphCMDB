# core/settings.py
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'ycqttn9384ny8tqp9[erw98tyg3298yr238yfewsifsd]'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_htmx',
    'graphene_django',          # GraphQL support
    'users.apps.UsersConfig',   # Users & RBAC
    'cmdb.apps.CmdbConfig',     # our app
    'core.apps.CoreConfig',     # core app with feature pack loading
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',      # Required
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',   # Required
    'django.contrib.messages.middleware.MessageMiddleware',      # Required
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
]

# Required for templates (admin, Graphene introspection, etc.)
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],  # You can add custom template dirs later
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.csrf',
                'cmdb.context_processors.categories_context',
            ],
        },
    },
]
# Graphene / GraphQL
GRAPHENE = {
    'SCHEMA': 'cmdb.schema.schema'   
}

# Neo4j connection (used by neomodel)
NEO4J_BOLT_URL = 'bolt://neo4j:23r9u4230rusfd@neo4j:7687'

ALLOWED_HOSTS = ['*']           # only for local dev!
DEBUG = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/ref/settings/#static-url
STATIC_URL = '/static/'

# Optional but recommended for development:
STATICFILES_DIRS = [
    BASE_DIR / "static",  # ← points to your /workspace/static folder
]

# Only needed when you deploy (collectstatic), but good to have:
STATIC_ROOT = BASE_DIR / "staticfiles"

ROOT_URLCONF = 'core.urls'

# Authentication settings
LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = '/cmdb/'
LOGOUT_REDIRECT_URL = '/users/login/'

# Database configuration for Django auth
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}