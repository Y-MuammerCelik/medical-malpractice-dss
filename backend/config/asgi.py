"""
config/asgi.py
--------------
ASGI uyumlu sunucular için giriş noktası (Uvicorn, Daphne).
WebSocket ve async view desteği için.
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
application = get_asgi_application()
