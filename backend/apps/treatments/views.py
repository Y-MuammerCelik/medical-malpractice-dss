"""
apps/treatments/views.py
-------------------------
İlaç, prosedür ve uygulanan protokol için API view'ları.
"""
from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend

from .models import MedicationRecord, ClinicalProcedure, AppliedProtocol
from .serializers import (
    MedicationRecordSerializer,
    ClinicalProcedureSerializer,
    AppliedProtocolSerializer,
)


class MedicationRecordViewSet(viewsets.ModelViewSet):
    queryset = MedicationRecord.objects.select_related(
        'admission__patient', 'ordered_by'
    ).order_by('-start_datetime')
    serializer_class = MedicationRecordSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status', 'admission', 'route']
    search_fields = ['drug_name']


class ClinicalProcedureViewSet(viewsets.ModelViewSet):
    queryset = ClinicalProcedure.objects.select_related(
        'admission__patient', 'performed_by'
    ).order_by('-scheduled_datetime')
    serializer_class = ClinicalProcedureSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status', 'admission']
    search_fields = ['procedure_name']


class AppliedProtocolViewSet(viewsets.ModelViewSet):
    queryset = AppliedProtocol.objects.select_related(
        'admission__patient', 'protocol'
    ).order_by('-selected_at')
    serializer_class = AppliedProtocolSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['admission', 'protocol']
