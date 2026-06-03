"""
icd10/models.py
---------------
ICD-10 Uluslararası Hastalık Sınıflandırması kodlarını ve bu kodlara
bağlı standart tedavi protokollerini tutan modeller.

IleridekI NLP entegrasyonu için 'description' alanları uzun metin
olarak tasarlanmıştır.
"""

from django.db import models
from django.core.validators import RegexValidator


# ---------------------------------------------------------------------------
# ICD-10 Kod Doğrulayıcı
# Örnek geçerli formatlar: A01, B23.4, C45.67
# ---------------------------------------------------------------------------
icd10_code_validator = RegexValidator(
    regex=r'^[A-Z][0-9]{2}(\.[0-9A-Z]{1,4})?$',
    message="ICD-10 kodu geçersiz format. Örnek: A01, B23.4, C45.67"
)


class ICD10Category(models.Model):
    """
    ICD-10 ana kategorilerini (bölümleri) tutar.
    Örnek: 'A00-B99' → 'Belirli Enfeksiyöz ve Paraziter Hastalıklar'
    """
    code_range_start = models.CharField(
        max_length=10,
        verbose_name="Başlangıç Kodu",
        help_text="Örn: A00"
    )
    code_range_end = models.CharField(
        max_length=10,
        verbose_name="Bitiş Kodu",
        help_text="Örn: B99"
    )
    name = models.CharField(
        max_length=255,
        verbose_name="Kategori Adı",
        help_text="Örn: Belirli Enfeksiyöz ve Paraziter Hastalıklar"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Açıklama"
    )

    class Meta:
        db_table = 'icd10_category'
        verbose_name = 'ICD-10 Kategorisi'
        verbose_name_plural = 'ICD-10 Kategorileri'
        ordering = ['code_range_start']

    def __str__(self):
        return f"{self.code_range_start}-{self.code_range_end}: {self.name}"


class ICD10Code(models.Model):
    """
    Tekil ICD-10 tanı kodlarını tutar.

    Her kod bir kategoriye bağlıdır ve NLP aşamasında metin eşleştirme
    için 'keywords' alanı kullanılacaktır.
    """

    # Hastalığın şiddet seviyesi için seçenekler
    class Severity(models.TextChoices):
        LOW = 'LOW', 'Düşük Risk'
        MODERATE = 'MODERATE', 'Orta Risk'
        HIGH = 'HIGH', 'Yüksek Risk'
        CRITICAL = 'CRITICAL', 'Kritik'

    category = models.ForeignKey(
        ICD10Category,
        on_delete=models.PROTECT,          # Kategori silinirse kodlar korunur
        related_name='codes',
        verbose_name="Kategori",
        null=True,
        blank=True
    )
    code = models.CharField(
        max_length=10,
        unique=True,
        validators=[icd10_code_validator],
        verbose_name="ICD-10 Kodu",
        help_text="Örn: J18.9"
    )
    name = models.CharField(
        max_length=500,
        verbose_name="Tanı Adı",
        help_text="Örn: Pnömoni, tanımlanmamış"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Klinik Açıklama",
        help_text="Hastalığın klinik tanımı. NLP için yapılandırılmış metin."
    )
    # Arama ve NLP eşleştirme için anahtar kelimeler (virgülle ayrılmış)
    keywords = models.TextField(
        blank=True,
        verbose_name="Anahtar Kelimeler",
        help_text="NLP eşleştirme için: pnömoni, akciğer iltihabı, ateş..."
    )
    severity = models.CharField(
        max_length=10,
        choices=Severity.choices,
        default=Severity.MODERATE,
        verbose_name="Klinik Ağırlık"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Aktif mi?",
        help_text="Artık kullanılmayan kodlar için False yapın."
    )

    # Zaman damgaları
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'icd10_code'
        verbose_name = 'ICD-10 Kodu'
        verbose_name_plural = 'ICD-10 Kodları'
        ordering = ['code']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['severity']),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


class TreatmentProtocol(models.Model):
    """
    Her ICD-10 koduna karşılık gelen STANDART tedavi protokolü.

    Bu model 'kural tabanlı karar destek' sisteminin temelini oluşturur.
    Gerçek tedaviyle bu protokol karşılaştırılarak sapma (malpraktis) tespiti yapılır.

    Bir ICD-10 kodunun birden fazla protokolü olabilir (örn: hafif vaka / ağır vaka).
    """

    class ProtocolType(models.TextChoices):
        STANDARD = 'STANDARD', 'Standart Protokol'
        EMERGENCY = 'EMERGENCY', 'Acil Protokol'
        PEDIATRIC = 'PEDIATRIC', 'Pediatrik Protokol'
        GERIATRIC = 'GERIATRIC', 'Geriatrik Protokol'

    icd10_code = models.ForeignKey(
        ICD10Code,
        on_delete=models.CASCADE,
        related_name='protocols',
        verbose_name="ICD-10 Tanısı"
    )
    protocol_type = models.CharField(
        max_length=20,
        choices=ProtocolType.choices,
        default=ProtocolType.STANDARD,
        verbose_name="Protokol Türü"
    )
    name = models.CharField(
        max_length=300,
        verbose_name="Protokol Adı",
        help_text="Örn: Toplum Kökenli Pnömoni - Standart Tedavi Protokolü"
    )
    # Beklenen iyileşme süreleri (gün cinsinden)
    min_recovery_days = models.PositiveIntegerField(
        verbose_name="Min. İyileşme Süresi (gün)",
        help_text="Beklenen minimum taburculuk süresi"
    )
    max_recovery_days = models.PositiveIntegerField(
        verbose_name="Max. İyileşme Süresi (gün)",
        help_text="Beklenen maksimum taburculuk süresi"
    )
    # Klinik eşik değerleri (JSON formatında esnek yapı)
    # Örn: {"max_fever_days": 3, "antibiotic_switch_day": 5}
    clinical_thresholds = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Klinik Eşik Değerleri",
        help_text="Kural motoru için sayısal eşik değerleri (JSON)"
    )
    # Zorunlu tedavi adımları (sıralı yapıda JSON listesi)
    # Örn: [{"step": 1, "action": "Oksijen ölçümü", "mandatory": true}]
    required_steps = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Zorunlu Tedavi Adımları",
        help_text="Sıralı ve zorunlu klinik adımlar (JSON listesi)"
    )
    # Birinci basamak önerilen ilaçlar
    first_line_medications = models.TextField(
        blank=True,
        verbose_name="Birinci Basamak İlaçlar",
        help_text="Protokol gereği önerilen ilaçlar (virgülle ayrılmış)"
    )
    # Kontrendikasyonlar
    contraindications = models.TextField(
        blank=True,
        verbose_name="Kontrendikasyonlar"
    )
    # Protokolün dayandığı kaynak / kılavuz
    reference_guideline = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Kaynak Kılavuz",
        help_text="Örn: WHO 2023, Türk Toraks Derneği Pnömoni Rehberi"
    )
    version = models.CharField(
        max_length=20,
        default='1.0',
        verbose_name="Protokol Versiyonu"
    )
    is_active = models.BooleanField(default=True, verbose_name="Aktif mi?")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'treatment_protocol'
        verbose_name = 'Tedavi Protokolü'
        verbose_name_plural = 'Tedavi Protokolleri'
        ordering = ['icd10_code', 'protocol_type']
        # Aynı kod için aynı türde yalnızca bir aktif protokol olabilir
        constraints = [
            models.UniqueConstraint(
                fields=['icd10_code', 'protocol_type', 'version'],
                name='unique_protocol_per_code_type_version'
            )
        ]

    def __str__(self):
        return f"[{self.icd10_code.code}] {self.name} v{self.version}"
