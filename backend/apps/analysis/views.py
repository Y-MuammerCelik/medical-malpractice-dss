"""
apps/analysis/views.py
-----------------------
Analiz motoru API endpoint'leri.
"""

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from .models import DeviationLog, MalpracticeAssessment
from .serializers import (
    DeviationLogSerializer,
    MalpracticeAssessmentSerializer,
    AnalysisTriggerSerializer,
)
from .services import RuleEngineService
from .nlp_service import ClinicalNLPService


class RunAnalysisView(APIView):
    """
    POST /api/v1/analysis/run/

    Belirtilen yatış için kural motorunu çalıştırır.

    İstek:
        {"admission_id": 42}

    Yanıt:
        {
          "admission_id": 42,
          "risk_level": "HIGH",
          "overall_compliance_score": 34.5,
          "deviation_log_ids": [1, 2, 3],
          "assessment_id": 7
        }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AnalysisTriggerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        admission_id = serializer.validated_data['admission_id']
        svc = RuleEngineService()
        result = svc.analyze_admission(admission_id)

        if result.error:
            return Response(
                {"detail": result.error},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({
            "admission_id": result.admission_id,
            "risk_level": result.risk_level,
            "overall_compliance_score": result.overall_compliance_score,
            "deviation_count": len(result.rule_results),
            "deviation_log_ids": result.deviation_log_ids,
            "assessment_id": result.assessment_id,
        }, status=status.HTTP_200_OK)


class DeviationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Sapma loglarını listele / detay göster."""
    queryset = DeviationLog.objects.select_related(
        'admission__patient', 'reference_protocol', 'reviewed_by'
    ).order_by('-detected_at')
    serializer_class = DeviationLogSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['severity', 'deviation_type', 'review_status', 'admission']
    search_fields = ['description', 'triggered_rule_id',
                     'admission__patient__last_name']
    ordering_fields = ['detected_at', 'severity']

    @action(detail=True, methods=['patch'])
    def review(self, request, pk=None):
        """
        PATCH /api/v1/analysis/deviations/{id}/review/
        Uzman hekimin inceleme sonucunu kaydeder.
        """
        log = self.get_object()
        new_status = request.data.get('review_status')
        comment = request.data.get('review_comment', '')

        allowed = [s[0] for s in DeviationLog.ReviewStatus.choices]
        if new_status not in allowed:
            return Response(
                {"detail": f"Geçersiz review_status. Seçenekler: {allowed}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        from django.utils import timezone
        log.review_status = new_status
        log.review_comment = comment
        log.reviewed_by = request.user
        log.reviewed_at = timezone.now()
        log.save(update_fields=['review_status', 'review_comment',
                                'reviewed_by', 'reviewed_at'])

        return Response(DeviationLogSerializer(log).data)


class MalpracticeAssessmentViewSet(viewsets.ReadOnlyModelViewSet):
    """Malpraktis değerlendirmelerini listele / detay göster."""
    queryset = MalpracticeAssessment.objects.select_related(
        'admission__patient', 'assessed_by'
    ).prefetch_related('deviation_logs').order_by('-created_at')
    serializer_class = MalpracticeAssessmentSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['risk_level', 'finalized', 'admission']
    ordering_fields = ['created_at', 'overall_compliance_score']


class AnalyzeDocumentView(APIView):
    """
    POST /api/v1/analysis/analyze-document/

    Klinik belge metnini NLP ile analiz eder.

    İstek:
        {
          "text": "Hasta Adı: Ali Veli. Teşhis: Pnömoni (J18.9). Yatış süresi: 15 gün...",
          "run_rule_engine": false   // opsiyonel: true ise kural motoru da çalışır
        }

    Yanıt:
        {
          "extracted": { icd_codes, medications, procedures, duration_days, ... },
          "confidence": 0.85,
          "warnings": [...],
          "rule_engine_result": null  // run_rule_engine=true ise dolu gelir
        }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        text = request.data.get('text', '').strip()
        run_engine = request.data.get('run_rule_engine', False)

        if not text:
            return Response(
                {"detail": "Metin boş olamaz. 'text' alanını doldurun."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(text) < 20:
            return Response(
                {"detail": "Metin çok kısa. Lütfen tam epikriz/rapor metnini yapıştırın."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ── NLP Çıkarımı ─────────────────────────────────────────────────
        nlp = ClinicalNLPService()
        extracted = nlp.extract(text)

        response_data = {
            "extracted": {
                "icd_codes":       extracted.icd_codes,
                "matched_icd":     extracted.matched_icd,
                "diagnosis_text":  extracted.diagnosis_text,
                "medications":     extracted.medications,
                "procedures":      extracted.procedures,
                "duration_days":   extracted.duration_days,
                "patient_name":    extracted.patient_name,
                "patient_age":     extracted.patient_age,
                "admission_date":  extracted.admission_date,
                "discharge_date":  extracted.discharge_date,
            },
            "confidence":        round(extracted.confidence * 100, 1),
            "confidence_label":  self._confidence_label(extracted.confidence),
            "warnings":          extracted.warnings,
            "rule_engine_result": None,
        }

        # ── Kural Motoru (opsiyonel) ──────────────────────────────────────
        if run_engine and extracted.matched_icd:
            # Veritabanında bu ICD koduna ait protokol var mı?
            from apps.icd10.models import ICD10Code
            try:
                icd_obj = ICD10Code.objects.filter(
                    code__startswith=extracted.matched_icd[:3]
                ).first()
                if icd_obj:
                    response_data["rule_engine_result"] = {
                        "icd_found": icd_obj.code,
                        "icd_name": icd_obj.name,
                        "protocol_count": icd_obj.protocols.count(),
                        "message": "Protokol bulundu. Tam analiz için hasta yatış kaydı oluşturun."
                    }
                else:
                    response_data["rule_engine_result"] = {
                        "icd_found": None,
                        "message": f"Veritabanında {extracted.matched_icd} için protokol bulunamadı."
                    }
            except Exception as e:
                response_data["rule_engine_result"] = {"error": str(e)}

        return Response(response_data, status=status.HTTP_200_OK)

    @staticmethod
    def _confidence_label(conf: float) -> str:
        if conf >= 0.8: return "Yüksek"
        if conf >= 0.5: return "Orta"
        if conf >= 0.3: return "Düşük"
        return "Çok Düşük"
