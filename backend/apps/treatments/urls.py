"""
apps/treatments/urls.py
------------------------
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MedicationRecordViewSet, ClinicalProcedureViewSet, AppliedProtocolViewSet

router = DefaultRouter()
router.register(r'medications', MedicationRecordViewSet, basename='medication-record')
router.register(r'procedures', ClinicalProcedureViewSet, basename='clinical-procedure')
router.register(r'applied-protocols', AppliedProtocolViewSet, basename='applied-protocol')

urlpatterns = [path('', include(router.urls))]
