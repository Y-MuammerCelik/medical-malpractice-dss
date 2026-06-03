"""
apps/patients/urls.py
----------------------
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PatientViewSet, AdmissionViewSet, ClinicalReportViewSet

# Hastalar — /api/v1/patients/
patient_router = DefaultRouter()
patient_router.register(r'', PatientViewSet, basename='patient')

# Yatışlar — /api/v1/admissions/  (ana urls.py'den bağlanır)
admission_router = DefaultRouter()
admission_router.register(r'', AdmissionViewSet, basename='admission')

# Raporlar — /api/v1/reports/
report_router = DefaultRouter()
report_router.register(r'', ClinicalReportViewSet, basename='clinical-report')

urlpatterns = [path('', include(patient_router.urls))]
admission_urlpatterns = [path('', include(admission_router.urls))]
report_urlpatterns = [path('', include(report_router.urls))]
