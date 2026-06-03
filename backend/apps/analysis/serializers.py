"""
apps/analysis/serializers.py
-----------------------------
DRF serileştiricileri: Sapma Logu ve Malpraktis Değerlendirmesi.
"""

from rest_framework import serializers
from .models import DeviationLog, MalpracticeAssessment


class DeviationLogSerializer(serializers.ModelSerializer):
    deviation_type_display = serializers.CharField(
        source='get_deviation_type_display', read_only=True
    )
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    review_status_display = serializers.CharField(
        source='get_review_status_display', read_only=True
    )

    class Meta:
        model = DeviationLog
        fields = '__all__'
        read_only_fields = ['detected_at', 'rule_output_data', 'triggered_rule_id']


class MalpracticeAssessmentSerializer(serializers.ModelSerializer):
    risk_level_display = serializers.CharField(source='get_risk_level_display', read_only=True)
    deviation_logs = DeviationLogSerializer(many=True, read_only=True)

    class Meta:
        model = MalpracticeAssessment
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'automated_summary',
                            'overall_compliance_score']


class AnalysisTriggerSerializer(serializers.Serializer):
    """
    POST /api/v1/analysis/run/ için istek gövdesi.
    Kural motorunu tetikler.
    """
    admission_id = serializers.IntegerField(
        help_text="Analiz edilecek yatışın ID'si"
    )
