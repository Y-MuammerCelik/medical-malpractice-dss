"""
analysis/models.py
------------------
Kural tabanlı karar destek motoru tarafından üretilen analiz sonuçları,
hasar logları ve malpraktis tespitlerini tutan modeller.

Bu modüldeki veriler:
  1. Kural motoru (rule_engine) tarafından otomatik oluşturulur.
  2. Uzman hekimler tarafından incelenir ve onaylanır/reddedilir.
  3. Hukuki süreçte kanıt niteliği taşıyabilir; bu yüzden
     hiçbir kayıt silinemez (soft-delete veya immutable tasarım).
"""

from django.db import models
from django.contrib.auth import get_user_model
from apps.patients.models import Admission, ClinicalReport
from apps.icd10.models import TreatmentProtocol
from apps.treatments.models import AppliedProtocol

User = get_user_model()


class DeviationLog(models.Model):
    """
    Standart protokolden tespit edilen her sapma olayını tutar.

    'Sapma', aşağıdaki durumlardan biri olabilir:
      - İlaç sapması    : Yanlış ilaç, yanlış doz, atlanmış ilaç
      - Zaman sapması   : Geç müdahale, aşırı uzun/kısa yatış süresi
      - Prosedür sapması: Yapılması gereken prosedürün yapılmaması
      - Protokol atlanması: Zorunlu adımın es geçilmesi

    Kural motoru bu logu oluşturduktan sonra uzman onayına sunar.
    """

    class DeviationType(models.TextChoices):
        MEDICATION = 'MEDICATION', 'İlaç Sapması'
        TIMING = 'TIMING', 'Zamanlama Sapması'
        PROCEDURE = 'PROCEDURE', 'Prosedür Sapması'
        PROTOCOL_SKIP = 'PROTOCOL_SKIP', 'Protokol Adımı Atlandı'
        DOSAGE = 'DOSAGE', 'Doz Sapması'
        MONITORING = 'MONITORING', 'İzlem Eksikliği'
        OTHER = 'OTHER', 'Diğer'

    class Severity(models.TextChoices):
        INFO = 'INFO', 'Bilgi'            # Sapma var ama klinik önemi düşük
        WARNING = 'WARNING', 'Uyarı'      # Dikkat gerektiren sapma
        CRITICAL = 'CRITICAL', 'Kritik'   # Hasta güvenliğini tehdit eden sapma

    class ReviewStatus(models.TextChoices):
        PENDING = 'PENDING', 'İnceleme Bekliyor'
        CONFIRMED = 'CONFIRMED', 'Sapma Doğrulandı'
        DISMISSED = 'DISMISSED', 'Reddedildi (Sapma Değil)'
        UNDER_REVIEW = 'UNDER_REVIEW', 'İncelemede'

    # Sapmanın ilgili olduğu yatış
    admission = models.ForeignKey(
        Admission,
        on_delete=models.PROTECT,       # Hukuki önem: yatış silinemez
        related_name='deviation_logs',
        verbose_name="İlgili Yatış"
    )
    # Hangi protokol baz alındı?
    reference_protocol = models.ForeignKey(
        TreatmentProtocol,
        on_delete=models.PROTECT,
        related_name='deviation_logs',
        verbose_name="Referans Protokol"
    )
    # Hangi uygulanan protokol incelendi?
    applied_protocol = models.ForeignKey(
        AppliedProtocol,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='deviations',
        verbose_name="Uygulanan Protokol"
    )
    deviation_type = models.CharField(
        max_length=20,
        choices=DeviationType.choices,
        verbose_name="Sapma Türü"
    )
    severity = models.CharField(
        max_length=10,
        choices=Severity.choices,
        default=Severity.WARNING,
        verbose_name="Ciddiyet"
    )
    # Kural motoru tarafından oluşturulan açıklama
    description = models.TextField(
        verbose_name="Sapma Açıklaması",
        help_text="Kural motorunun ürettiği otomatik açıklama"
    )
    # Sapmanın tespit edildiği klinik referans (opsiyonel)
    related_report = models.ForeignKey(
        ClinicalReport,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deviations',
        verbose_name="İlgili Klinik Rapor"
    )
    # Kural motorunda hangi kural tetikledi?
    triggered_rule_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Tetikleyen Kural ID",
        help_text="Örn: RULE_MED_001, RULE_TIMING_005"
    )
    # Kural çıktısı (ham JSON — izlenebilirlik için)
    rule_output_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Kural Motoru Ham Çıktısı"
    )
    # -----------------------------------------------------------------------
    # İnceleme süreci alanları
    # -----------------------------------------------------------------------
    review_status = models.CharField(
        max_length=15,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING,
        verbose_name="İnceleme Durumu"
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_deviations',
        verbose_name="İnceleyen Uzman"
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="İnceleme Tarihi"
    )
    review_comment = models.TextField(
        blank=True,
        verbose_name="Uzman Görüşü / Açıklaması"
    )

    # Değiştirilemezlik için: kayıt oluşturulduktan sonra güncellenmemeli
    detected_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Tespit Tarihi"
    )

    class Meta:
        db_table = 'deviation_log'
        verbose_name = 'Sapma Logu'
        verbose_name_plural = 'Sapma Logları'
        ordering = ['-detected_at']
        indexes = [
            models.Index(fields=['admission', 'severity']),
            models.Index(fields=['review_status']),
            models.Index(fields=['deviation_type']),
            models.Index(fields=['triggered_rule_id']),
        ]

    def __str__(self):
        return (
            f"[{self.severity}] {self.get_deviation_type_display()} "
            f"— {self.admission.patient} ({self.detected_at.date()})"
        )


class MalpracticeAssessment(models.Model):
    """
    Bir yatış için üretilen nihai malpraktis değerlendirmesi.

    Bu model; birden fazla DeviationLog'un bir araya getirilip
    kural motoru tarafından sentezlenmesiyle oluşturulur.

    Uzman hekim onayından geçtikten sonra 'finalized=True' yapılır
    ve kayıt immutable hale gelir (hukuki belge niteliği).
    """

    class RiskLevel(models.TextChoices):
        NONE = 'NONE', 'Risk Yok'
        LOW = 'LOW', 'Düşük Risk'
        MODERATE = 'MODERATE', 'Orta Risk'
        HIGH = 'HIGH', 'Yüksek Risk — Malpraktis Şüphesi'
        CONFIRMED = 'CONFIRMED', 'Malpraktis Tespit Edildi'

    admission = models.OneToOneField(
        Admission,
        on_delete=models.PROTECT,
        related_name='malpractice_assessment',
        verbose_name="Yatış"
    )
    # Bu değerlendirmeye dahil edilen sapma logları
    deviation_logs = models.ManyToManyField(
        DeviationLog,
        related_name='assessments',
        blank=True,
        verbose_name="İlişkili Sapma Logları"
    )
    risk_level = models.CharField(
        max_length=15,
        choices=RiskLevel.choices,
        default=RiskLevel.NONE,
        verbose_name="Risk Seviyesi"
    )
    # Kural motorunun hesapladığı genel uyum skoru
    overall_compliance_score = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Genel Uyum Skoru (%)"
    )
    # Kural motoru özet çıktısı
    automated_summary = models.TextField(
        blank=True,
        verbose_name="Otomatik Analiz Özeti"
    )
    # Uzman hekimin manuel değerlendirmesi
    expert_opinion = models.TextField(
        blank=True,
        verbose_name="Uzman Hekim Görüşü"
    )
    assessed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assessments',
        verbose_name="Değerlendiren Uzman"
    )
    assessed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Değerlendirme Tarihi"
    )
    # Rapor onaylandığında True olur — artık değiştirilemez
    finalized = models.BooleanField(
        default=False,
        verbose_name="Sonuçlandırıldı mı?",
        help_text="True ise rapor hukuki belge niteliğindedir."
    )
    finalized_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Sonuçlandırılma Tarihi"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'malpractice_assessment'
        verbose_name = 'Malpraktis Değerlendirmesi'
        verbose_name_plural = 'Malpraktis Değerlendirmeleri'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['risk_level']),
            models.Index(fields=['finalized']),
        ]

    def __str__(self):
        return (
            f"Değerlendirme #{self.pk} — {self.admission.patient} "
            f"| Risk: {self.get_risk_level_display()}"
        )
