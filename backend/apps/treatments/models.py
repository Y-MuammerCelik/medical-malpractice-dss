"""
treatments/models.py
--------------------
Yatışlar sırasında uygulanan gerçek tedavileri (ilaç, prosedür, cerrahi)
tutan modeller.

Bu modeller, TreatmentProtocol (standart) ile karşılaştırılarak
sapma/malpraktis tespitinin hammaddesi olur.
"""

from django.db import models
from django.contrib.auth import get_user_model
from apps.patients.models import Admission
from apps.icd10.models import TreatmentProtocol

User = get_user_model()


class MedicationRecord(models.Model):
    """
    Yatış boyunca verilen ilaç kayıtları.

    Standart protokoldeki 'first_line_medications' ile karşılaştırılarak
    ilaç sapmaları (yanlış ilaç, yanlış doz, atlanmış ilaç) tespit edilir.
    """

    class RouteOfAdministration(models.TextChoices):
        ORAL = 'PO', 'Oral (Ağızdan)'
        INTRAVENOUS = 'IV', 'İntravenöz (Damardan)'
        INTRAMUSCULAR = 'IM', 'İntramusküler (Kas içine)'
        SUBCUTANEOUS = 'SC', 'Subkütan (Deri altı)'
        TOPICAL = 'TOP', 'Topikal'
        INHALATION = 'INH', 'İnhalasyon'
        RECTAL = 'PR', 'Rektal'
        OTHER = 'OTH', 'Diğer'

    class MedicationStatus(models.TextChoices):
        ORDERED = 'ORDERED', 'Orderlanmış'
        ADMINISTERED = 'ADMINISTERED', 'Uygulandı'
        SKIPPED = 'SKIPPED', 'Atlandı / Uygulanmadı'
        CANCELLED = 'CANCELLED', 'İptal Edildi'

    admission = models.ForeignKey(
        Admission,
        on_delete=models.CASCADE,
        related_name='medications',
        verbose_name="Yatış"
    )
    ordered_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='ordered_medications',
        verbose_name="Orderlayen Hekim"
    )
    administered_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='administered_medications',
        verbose_name="Uygulayan (Hemşire/Hekim)"
    )
    drug_name = models.CharField(
        max_length=300,
        verbose_name="İlaç Adı",
        help_text="Örn: Amoksisilin-Klavulanik Asit"
    )
    drug_code = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="ATC/Barkod Kodu",
        help_text="ATC sınıflandırması veya ürün barkodu"
    )
    dose = models.CharField(
        max_length=100,
        verbose_name="Doz",
        help_text="Örn: 1g, 500mg, 2 ünite"
    )
    route = models.CharField(
        max_length=5,
        choices=RouteOfAdministration.choices,
        verbose_name="Uygulama Yolu"
    )
    frequency = models.CharField(
        max_length=100,
        verbose_name="Sıklık",
        help_text="Örn: 2x1, 3x1, 12 saatte bir"
    )
    start_datetime = models.DateTimeField(verbose_name="Başlangıç Tarihi")
    end_datetime = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Bitiş Tarihi"
    )
    status = models.CharField(
        max_length=15,
        choices=MedicationStatus.choices,
        default=MedicationStatus.ORDERED,
        verbose_name="Durum"
    )
    # Varsa protokolden sapma nedeni
    skip_reason = models.TextField(
        blank=True,
        verbose_name="Atlanma / İptal Nedeni"
    )
    notes = models.TextField(blank=True, verbose_name="Notlar")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'medication_record'
        verbose_name = 'İlaç Kaydı'
        verbose_name_plural = 'İlaç Kayıtları'
        ordering = ['-start_datetime']
        indexes = [
            models.Index(fields=['admission', 'status']),
            models.Index(fields=['drug_name']),
        ]

    def __str__(self):
        return f"{self.drug_name} {self.dose} — {self.admission.patient}"


class ClinicalProcedure(models.Model):
    """
    Yatış süresince uygulanan klinik prosedürler.

    Ameliyat, endoskopi, kateterizasyon, biyopsi gibi invazif/non-invazif
    tüm tıbbi girişimler bu modelde tutulur.
    """

    class ProcedureStatus(models.TextChoices):
        PLANNED = 'PLANNED', 'Planlandı'
        PERFORMED = 'PERFORMED', 'Uygulandı'
        CANCELLED = 'CANCELLED', 'İptal Edildi'
        POSTPONED = 'POSTPONED', 'Ertelendi'

    admission = models.ForeignKey(
        Admission,
        on_delete=models.CASCADE,
        related_name='procedures',
        verbose_name="Yatış"
    )
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='performed_procedures',
        verbose_name="Uygulayan Hekim"
    )
    procedure_name = models.CharField(
        max_length=300,
        verbose_name="Prosedür Adı",
        help_text="Örn: Laparoskopik Apendektomi"
    )
    # ICD-10 PCS veya SNOMED kodu (opsiyonel)
    procedure_code = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Prosedür Kodu (ICD-10-PCS)"
    )
    status = models.CharField(
        max_length=15,
        choices=ProcedureStatus.choices,
        default=ProcedureStatus.PLANNED,
        verbose_name="Durum"
    )
    scheduled_datetime = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Planlanan Tarih/Saat"
    )
    performed_datetime = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Gerçekleştirildiği Tarih/Saat"
    )
    duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Süre (dakika)"
    )
    complications = models.TextField(
        blank=True,
        verbose_name="Komplikasyonlar",
        help_text="İşlem sırasında/sonrasında gelişen komplikasyonlar"
    )
    notes = models.TextField(blank=True, verbose_name="Operatör Notları")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'clinical_procedure'
        verbose_name = 'Klinik Prosedür'
        verbose_name_plural = 'Klinik Prosedürler'
        ordering = ['-scheduled_datetime']

    def __str__(self):
        return f"{self.procedure_name} — {self.admission.patient} ({self.status})"


class AppliedProtocol(models.Model):
    """
    Yatışta hangi tedavi protokolünün uygulandığını takip eden model.

    Her yatış için hangi standart protokolün seçildiği ve bu protokole
    ne ölçüde uyulduğu buraya yazılır.
    Sapma tespiti bu model üzerinden yapılır.
    """
    admission = models.ForeignKey(
        Admission,
        on_delete=models.CASCADE,
        related_name='applied_protocols',
        verbose_name="Yatış"
    )
    protocol = models.ForeignKey(
        TreatmentProtocol,
        on_delete=models.PROTECT,
        related_name='applied_instances',
        verbose_name="Seçilen Protokol"
    )
    selected_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Protokolü Seçen Hekim"
    )
    selected_at = models.DateTimeField(auto_now_add=True)
    # Protokole uyum yüzdesi (kural motoru tarafından hesaplanır)
    compliance_score = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Uyum Skoru (%)",
        help_text="0-100 arası; kural motoru tarafından otomatik hesaplanır"
    )
    compliance_calculated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Skor Hesaplama Tarihi"
    )
    notes = models.TextField(blank=True, verbose_name="Hekim Notu")

    class Meta:
        db_table = 'applied_protocol'
        verbose_name = 'Uygulanan Protokol'
        verbose_name_plural = 'Uygulanan Protokoller'

    def __str__(self):
        return f"{self.protocol.name} → {self.admission.patient}"
