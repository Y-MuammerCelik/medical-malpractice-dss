"""
apps/analysis/urls.py
----------------------
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RunAnalysisView,
    AnalyzeDocumentView,
    DeviationLogViewSet,
    MalpracticeAssessmentViewSet,
)

router = DefaultRouter()
router.register(r'deviations', DeviationLogViewSet, basename='deviation-log')
router.register(r'assessments', MalpracticeAssessmentViewSet, basename='malpractice-assessment')

urlpatterns = [
    # Kural motoru tetikleyici
    path('run/', RunAnalysisView.as_view(), name='run-analysis'),
    # NLP belge analizi
    path('analyze-document/', AnalyzeDocumentView.as_view(), name='analyze-document'),
    path('', include(router.urls)),
]
