"""
apps/patients/admin.py
----------------------
Django Admin paneline hasta modellerini kayıt eder.
"""

from django.contrib import admin
from .models import Patient, Admission, ClinicalReport


class AdmissionInline(admin.TabularInline):
    """Hasta detay sayfasında yatışları göster."""
    model = Admission
    extra = 0
    fields = ['admission_date', 'discharge_date', 'primary_diagnosis',
              'admission_type', 'discharge_type']
    readonly_fields = ['admission_date']


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['id', 'last_name', 'first_name', 'date_of_birth',
                    'gender', 'blood_type', 'is_active']
    list_filter = ['gender', 'blood_type', 'is_active']
    search_fields = ['first_name', 'last_name', 'tc_identity_hash']
    readonly_fields = ['tc_identity_hash', 'created_at', 'updated_at']
    inlines = [AdmissionInline]

    fieldsets = (
        ('Kimlik Bilgileri', {
            'fields': ('tc_identity_hash', 'first_name', 'last_name',
                       'date_of_birth', 'gender', 'blood_type')
        }),
        ('Tıbbi Geçmiş', {
            'fields': ('chronic_conditions', 'known_allergies'),
            'classes': ('collapse',),
        }),
        ('Sistem', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(Admission)
class AdmissionAdmin(admin.ModelAdmin):
    list_display = ['id', 'patient', 'admission_type', 'primary_diagnosis',
                    'admission_date', 'discharge_date', 'discharge_type', 'ward']
    list_filter = ['admission_type', 'discharge_type', 'ward']
    search_fields = ['patient__first_name', 'patient__last_name',
                     'primary_diagnosis__code']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'admission_date'


@admin.register(ClinicalReport)
class ClinicalReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'admission', 'report_type', 'author',
                    'report_date', 'nlp_processed', 'is_finalized']
    list_filter = ['report_type', 'nlp_processed', 'is_finalized']
    search_fields = ['admission__patient__last_name']
    readonly_fields = ['nlp_processed_at', 'created_at', 'updated_at']
