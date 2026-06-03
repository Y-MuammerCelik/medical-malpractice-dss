"""
apps/analysis/admin.py
----------------------
Django Admin paneline analiz modellerini kayıt eder.
"""

from django.contrib import admin
from .models import DeviationLog, MalpracticeAssessment


@admin.register(DeviationLog)
class DeviationLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'admission', 'deviation_type', 'severity',
                    'review_status', 'triggered_rule_id', 'detected_at']
    list_filter = ['severity', 'deviation_type', 'review_status']
    search_fields = ['admission__patient__last_name', 'triggered_rule_id',
                     'description']
    readonly_fields = ['detected_at', 'rule_output_data']
    date_hierarchy = 'detected_at'

    fieldsets = (
        ('Sapma Bilgisi', {
            'fields': ('admission', 'reference_protocol', 'applied_protocol',
                       'deviation_type', 'severity', 'description',
                       'triggered_rule_id', 'rule_output_data')
        }),
        ('İnceleme Süreci', {
            'fields': ('review_status', 'reviewed_by', 'reviewed_at',
                       'review_comment'),
        }),
        ('Sistem', {
            'fields': ('detected_at',),
            'classes': ('collapse',),
        }),
    )


@admin.register(MalpracticeAssessment)
class MalpracticeAssessmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'admission', 'risk_level',
                    'overall_compliance_score', 'finalized', 'created_at']
    list_filter = ['risk_level', 'finalized']
    search_fields = ['admission__patient__last_name']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['deviation_logs']
