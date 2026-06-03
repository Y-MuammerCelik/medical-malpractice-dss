"""
apps/icd10/apps.py
"""
from django.apps import AppConfig


class Icd10Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.icd10'
    verbose_name = 'ICD-10 Kodları ve Protokoller'
