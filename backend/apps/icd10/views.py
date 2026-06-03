"""
apps/icd10/views.py
--------------------
ICD-10 kod ve protokol CRUD API endpoint'leri.
"""

from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend

from .models import ICD10Category, ICD10Code, TreatmentProtocol
from .serializers import (
    ICD10CategorySerializer,
    ICD10CodeSerializer,
    ICD10CodeListSerializer,
    TreatmentProtocolSerializer,
)


class ICD10CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ICD10Category.objects.order_by('code_range_start')
    serializer_class = ICD10CategorySerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'code_range_start']


class ICD10CodeViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['severity', 'is_active', 'category']
    search_fields = ['code', 'name', 'keywords']
    ordering_fields = ['code', 'severity']
    ordering = ['code']

    def get_queryset(self):
        return ICD10Code.objects.select_related('category').prefetch_related('protocols')

    def get_serializer_class(self):
        if self.action == 'list':
            return ICD10CodeListSerializer
        return ICD10CodeSerializer


class TreatmentProtocolViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TreatmentProtocol.objects.select_related('icd10_code').filter(is_active=True)
    serializer_class = TreatmentProtocolSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['protocol_type', 'icd10_code']
    search_fields = ['name', 'icd10_code__code']
