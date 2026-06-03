"""
apps/patients/views.py
-----------------------
Hasta ve Yatış CRUD API endpoint'leri.
"""

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Patient, Admission, ClinicalReport
from .serializers import (
    PatientSerializer,
    AdmissionListSerializer,
    AdmissionDetailSerializer,
    ClinicalReportSerializer,
)


class PatientViewSet(viewsets.ModelViewSet):
    """Hasta CRUD."""
    queryset = Patient.objects.filter(is_active=True).order_by('last_name')
    serializer_class = PatientSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['gender', 'blood_type', 'is_active']
    search_fields = ['first_name', 'last_name']
    ordering_fields = ['last_name', 'date_of_birth']

    @action(detail=True, methods=['get'])
    def admissions(self, request, pk=None):
        """Bir hastanın tüm yatış kayıtlarını döner."""
        patient = self.get_object()
        qs = patient.admissions.select_related('primary_diagnosis').order_by('-admission_date')
        serializer = AdmissionListSerializer(qs, many=True)
        return Response(serializer.data)


class AdmissionViewSet(viewsets.ModelViewSet):
    """Yatış CRUD."""
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['admission_type', 'discharge_type', 'ward', 'primary_diagnosis']
    search_fields = ['patient__first_name', 'patient__last_name', 'primary_diagnosis__code']
    ordering_fields = ['admission_date', 'discharge_date']
    ordering = ['-admission_date']

    def get_queryset(self):
        return Admission.objects.select_related(
            'patient', 'primary_diagnosis', 'admitting_physician'
        ).prefetch_related('secondary_diagnoses')

    def get_serializer_class(self):
        if self.action == 'list':
            return AdmissionListSerializer
        return AdmissionDetailSerializer

    @action(detail=True, methods=['get'])
    def reports(self, request, pk=None):
        """Bir yatışın klinik raporlarını döner."""
        admission = self.get_object()
        qs = admission.clinical_reports.order_by('-report_date')
        serializer = ClinicalReportSerializer(qs, many=True)
        return Response(serializer.data)


class ClinicalReportViewSet(viewsets.ModelViewSet):
    """Klinik Rapor CRUD."""
    queryset = ClinicalReport.objects.select_related('admission', 'author')
    serializer_class = ClinicalReportSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['report_type', 'nlp_processed', 'is_finalized', 'admission']
    ordering = ['-report_date']
