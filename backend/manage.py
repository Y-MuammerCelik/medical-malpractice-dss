#!/usr/bin/env python
"""
manage.py
---------
Django'nun komut satırı yönetim aracı.

Kullanım örnekleri:
  python manage.py runserver
  python manage.py makemigrations
  python manage.py migrate
  python manage.py createsuperuser
  python manage.py shell
"""

import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django import edilemedi. Sanal ortamın aktif olduğundan "
            "ve Django'nun kurulu olduğundan emin olun."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
