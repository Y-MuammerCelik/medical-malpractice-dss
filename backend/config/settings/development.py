"""
config/settings/development.py
-------------------------------
Geliştirme ortamı ayarları. Base'i import eder ve üzerine yazar.
"""
from .base import *  # noqa

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# ✅ SQLite — kurulum gerektirmez, Python ile birlikte gelir
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',  # noqa: F405
    }
}

# Geliştirmede CORS'u tam aç
CORS_ALLOW_ALL_ORIGINS = True

# E-posta → konsola yaz
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ✅ Geliştirme: Herkese açık API — Auth YOK
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
}
