"""
apps/accounts/urls.py
---------------------
Token tabanlı kimlik doğrulama endpoint'leri.
"""
from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    # POST /api/v1/auth/token/ → {"username": "...", "password": "..."} → token
    path('token/', obtain_auth_token, name='api-token-auth'),
]
