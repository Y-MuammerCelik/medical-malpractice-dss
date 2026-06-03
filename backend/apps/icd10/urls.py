"""
apps/icd10/urls.py
------------------
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ICD10CategoryViewSet, ICD10CodeViewSet, TreatmentProtocolViewSet

router = DefaultRouter()
router.register(r'categories', ICD10CategoryViewSet, basename='icd10-category')
router.register(r'codes', ICD10CodeViewSet, basename='icd10-code')
router.register(r'protocols', TreatmentProtocolViewSet, basename='treatment-protocol')

urlpatterns = [path('', include(router.urls))]
