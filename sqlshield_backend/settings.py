from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure'
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'host.docker.internal']

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'rest_framework',
    'api',
    'chat',
]

MIDDLEWARE = [
    'whitenoise.middleware.WhiteNoiseMiddleware'
]

ROOT_URLCONF = 'sqlshield_backend.urls'
TEMPLATES = []
WSGI_APPLICATION = 'sqlshield_backend.wsgi.application'

DATABASES = {}
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

import os

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "frontend", "dist"),
]

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_PARSER_CLASSES': ['rest_framework.parsers.JSONParser'],
    'DEFAULT_AUTHENTICATION_CLASSES': [],  # ← disables DRF auth system
}
