"""
apps/patients/serializers.py
-----------------------------
DRF serileştiricileri: Hasta, Yatış, Klinik Rapor.
"""

from rest_framework import serializers
from .models import Patient, Admission, ClinicalReport
from apps.icd10.serializers import ICD10CodeListSerializer


class PatientSerializer(serializers.ModelSerializer):
    age = serializers.IntegerField(read_only=True)
    gender_display = serializers.CharField(source='get_gender_display', read_only=True)
    blood_type_display = serializers.CharField(source='get_blood_type_display', read_only=True)

    class Meta:
        model = Patient
        fields = [
            'id', 'first_name', 'last_name', 'date_of_birth', 'age',
            'gender', 'gender_display', 'blood_type', 'blood_type_display',
            'chronic_conditions', 'known_allergies', 'is_active',
            'created_at', 'updated_at',
        ]
        # TC hash asla API'den dışa verilmez
        read_only_fields = ['created_at', 'updated_at']

    def create(self, validated_data):
        # TC kimlik hash'i view katmanında oluşturulup inject edilmeli
        return super().create(validated_data)


class AdmissionListSerializer(serializers.ModelSerializer):
    """Liste için hafif versiyon."""
    patient_name = serializers.SerializerMethodField()
    primary_diagnosis_code = serializers.CharField(
        source='primary_diagnosis.code', read_only=True
    )
    length_of_stay = serializers.IntegerField(read_only=True)

    class Meta:
        model = Admission
        fields = [
            'id', 'patient', 'patient_name', 'admission_type',
            'primary_diagnosis', 'primary_diagnosis_code',
            'admission_date', 'discharge_date', 'discharge_type',
            'ward', 'length_of_stay',
        ]

    def get_patient_name(self, obj):
        return f"{obj.patient.last_name}, {obj.patient.first_name}"


class AdmissionDetailSerializer(serializers.ModelSerializer):
    """Detay için tam versiyon (nested)."""
    patient = PatientSerializer(read_only=True)
    primary_diagnosis = ICD10CodeListSerializer(read_only=True)
    length_of_stay = serializers.IntegerField(read_only=True)

    class Meta:
        model = Admission
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class ClinicalReportSerializer(serializers.ModelSerializer):
    report_type_display = serializers.CharField(source='get_report_type_display', read_only=True)

    class Meta:
        model = ClinicalReport
        fields = '__all__'
        read_only_fields = ['nlp_processed', 'nlp_processed_at', 'created_at', 'updated_at']
