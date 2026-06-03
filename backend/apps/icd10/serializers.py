"""
apps/icd10/serializers.py
--------------------------
DRF serileştiricileri: ICD-10 kodları ve protokoller için.
"""

from rest_framework import serializers
from .models import ICD10Category, ICD10Code, TreatmentProtocol


class ICD10CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ICD10Category
        fields = '__all__'


class TreatmentProtocolSerializer(serializers.ModelSerializer):
    class Meta:
        model = TreatmentProtocol
        fields = '__all__'


class ICD10CodeSerializer(serializers.ModelSerializer):
    """Okuma için protokolleri de içerir (nested)."""
    protocols = TreatmentProtocolSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)

    class Meta:
        model = ICD10Code
        fields = [
            'id', 'code', 'name', 'description', 'keywords',
            'severity', 'severity_display', 'category', 'category_name',
            'is_active', 'protocols', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class ICD10CodeListSerializer(serializers.ModelSerializer):
    """Liste görünümü için hafif versiyon (protokolsüz)."""
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)

    class Meta:
        model = ICD10Code
        fields = ['id', 'code', 'name', 'severity', 'severity_display', 'is_active']
