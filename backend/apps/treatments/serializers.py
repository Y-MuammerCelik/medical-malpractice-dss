"""
apps/treatments/serializers.py
-------------------------------
DRF serileştiricileri: İlaç, Prosedür, Uygulanan Protokol.
"""
from rest_framework import serializers
from .models import MedicationRecord, ClinicalProcedure, AppliedProtocol


class MedicationRecordSerializer(serializers.ModelSerializer):
    route_display = serializers.CharField(source='get_route_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = MedicationRecord
        fields = '__all__'
        read_only_fields = ['created_at']


class ClinicalProcedureSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ClinicalProcedure
        fields = '__all__'
        read_only_fields = ['created_at']


class AppliedProtocolSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppliedProtocol
        fields = '__all__'
        read_only_fields = ['selected_at', 'compliance_calculated_at']
