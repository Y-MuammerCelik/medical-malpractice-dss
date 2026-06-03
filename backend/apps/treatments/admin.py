"""
apps/treatments/admin.py
------------------------
Django Admin paneline tedavi modellerini kayıt eder.
"""

from django.contrib import admin
from .models import MedicationRecord, ClinicalProcedure, AppliedProtocol


@admin.register(MedicationRecord)
class MedicationRecordAdmin(admin.ModelAdmin):
    list_display = ['drug_name', 'dose', 'route', 'admission',
                    'start_datetime', 'status']
    list_filter = ['status', 'route']
    search_fields = ['drug_name', 'admission__patient__last_name']
    date_hierarchy = 'start_datetime'


@admin.register(ClinicalProcedure)
class ClinicalProcedureAdmin(admin.ModelAdmin):
    list_display = ['procedure_name', 'admission', 'status',
                    'performed_datetime', 'duration_minutes']
    list_filter = ['status']
    search_fields = ['procedure_name', 'admission__patient__last_name']


@admin.register(AppliedProtocol)
class AppliedProtocolAdmin(admin.ModelAdmin):
    list_display = ['admission', 'protocol', 'selected_by',
                    'compliance_score', 'selected_at']
    list_filter = ['protocol__protocol_type']
    search_fields = ['admission__patient__last_name', 'protocol__name']
    readonly_fields = ['selected_at', 'compliance_calculated_at']
