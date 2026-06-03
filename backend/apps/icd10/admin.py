"""
apps/icd10/admin.py
-------------------
Django Admin paneline ICD-10 modellerini kayıt eder.
"""

from django.contrib import admin
from .models import ICD10Category, ICD10Code, TreatmentProtocol


@admin.register(ICD10Category)
class ICD10CategoryAdmin(admin.ModelAdmin):
    list_display = ['code_range_start', 'code_range_end', 'name']
    search_fields = ['name', 'code_range_start']


@admin.register(ICD10Code)
class ICD10CodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'severity', 'is_active']
    list_filter = ['severity', 'is_active', 'category']
    search_fields = ['code', 'name', 'keywords']
    ordering = ['code']


@admin.register(TreatmentProtocol)
class TreatmentProtocolAdmin(admin.ModelAdmin):
    list_display = ['name', 'icd10_code', 'protocol_type', 'min_recovery_days',
                    'max_recovery_days', 'version', 'is_active']
    list_filter = ['protocol_type', 'is_active']
    search_fields = ['name', 'icd10_code__code', 'icd10_code__name']
    readonly_fields = ['created_at', 'updated_at']
