"""
config/wsgi.py
--------------
WSGI uyumlu web sunucuları için giriş noktası (Gunicorn, uWSGI).
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
application = get_wsgi_application()
