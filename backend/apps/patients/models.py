"""
patients/models.py
------------------
Hasta demografik bilgileri, epikriz (klinik rapor) kayıtları
ve sistem tarafından tespit edilen hasar loglarını tutan modeller.

Epikriz verileri şimdilik yapılandırılmış metin olarak tutulmakta;
ileride NLP pipeline bu metinlerden otomatik veri çekecektir.
"""

from django.db import models
from django.contrib.auth import get_user_model
from apps.icd10.models import ICD10Code, TreatmentProtocol

User = get_user_model()


class Patient(models.Model):
    """
    Hasta temel bilgileri.

    TC kimlik numarası hash'lenerek saklanmalıdır (KVKK uyumu).
    Gerçek uygulamada 'tc_identity_hash' alanına SHA-256 hash yazılır.
    """

    class Gender(models.TextChoices):
        MALE = 'M', 'Erkek'
        FEMALE = 'F', 'Kadın'
        OTHER = 'O', 'Diğer / Belirtilmemiş'

    class BloodType(models.TextChoices):
        A_POS = 'A+', 'A Rh+'
        A_NEG = 'A-', 'A Rh-'
        B_POS = 'B+', 'B Rh+'
        B_NEG = 'B-', 'B Rh-'
        AB_POS = 'AB+', 'AB Rh+'
        AB_NEG = 'AB-', 'AB Rh-'
        O_POS = 'O+', '0 Rh+'
        O_NEG = 'O-', '0 Rh-'
        UNKNOWN = 'UNK', 'Bilinmiyor'

    # KVKK gereği TC kimlik hash'i (gerçek kimlik saklanmaz)
    tc_identity_hash = models.CharField(
        max_length=64,
        unique=True,
        verbose_name="TC Kimlik Hash (SHA-256)",
        help_text="Ham TC NO saklanmaz. SHA-256 hash değeri tutulur."
    )
    first_name = models.CharField(max_length=100, verbose_name="Ad")
    last_name = models.CharField(max_length=100, verbose_name="Soyad")
    date_of_birth = models.DateField(verbose_name="Doğum Tarihi")
    gender = models.CharField(
        max_length=1,
        choices=Gender.choices,
        verbose_name="Cinsiyet"
    )
    blood_type = models.CharField(
        max_length=4,
        choices=BloodType.choices,
        default=BloodType.UNKNOWN,
        verbose_name="Kan Grubu"
    )
    # Kronik hastalık ve alerji notları (NLP için yapılandırılmış metin)
    chronic_conditions = models.TextField(
        blank=True,
        verbose_name="Kronik Hastalıklar",
        help_text="Diyabet, hipertansiyon vb. — NLP için serbest metin"
    )
    known_allergies = models.TextField(
        blank=True,
        verbose_name="Bilinen Alerjiler",
        help_text="İlaç, besin alerjileri — NLP için serbest metin"
    )
    is_active = models.BooleanField(default=True, verbose_name="Aktif Hasta")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'patient'
        verbose_name = 'Hasta'
        verbose_name_plural = 'Hastalar'
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['tc_identity_hash']),
            models.Index(fields=['date_of_birth']),
        ]

    def __str__(self):
        return f"{self.last_name}, {self.first_name} (#{self.pk})"

    @property
    def age(self):
        """Hastanın yaşını hesaplar."""
        from datetime import date
        today = date.today()
        dob = self.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


class Admission(models.Model):
    """
    Hastane yatışı / başvuru kaydı.

    Her yatış bir hastaya aittir. Bir hasta birden çok kez yatış
    yapabilir. Yatış kaydı; epikriz, tedavi ve hasar loglarının
    bağlandığı temel kayıttır.
    """

    class AdmissionType(models.TextChoices):
        EMERGENCY = 'EMERGENCY', 'Acil'
        ELECTIVE = 'ELECTIVE', 'Elektif (Planlanmış)'
        TRANSFER = 'TRANSFER', 'Transfer'
        OUTPATIENT = 'OUTPATIENT', 'Ayakta Tedavi'

    class DischargeType(models.TextChoices):
        RECOVERED = 'RECOVERED', 'İyileşerek Taburcu'
        TRANSFERRED = 'TRANSFERRED', 'Transfer ile Taburcu'
        AGAINST_ADVICE = 'AOR', 'İsteğe Bağlı Taburcu (İmzalı Red)'
        DECEASED = 'DECEASED', 'Exitus'
        STILL_ADMITTED = 'ADMITTED', 'Hâlâ Yatıyor'

    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name='admissions',
        verbose_name="Hasta"
    )
    # Yatışı kabul eden doktor (sistemdeki kullanıcı)
    admitting_physician = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admitted_patients',
        verbose_name="Kabul Eden Hekim"
    )
    admission_type = models.CharField(
        max_length=20,
        choices=AdmissionType.choices,
        verbose_name="Başvuru Türü"
    )
    # Ana tanı (yatış sırasında konulan)
    primary_diagnosis = models.ForeignKey(
        ICD10Code,
        on_delete=models.PROTECT,
        related_name='primary_admissions',
        verbose_name="Ana Tanı (ICD-10)",
        null=True,
        blank=True
    )
    # Ek tanılar (çoka-çok ilişki)
    secondary_diagnoses = models.ManyToManyField(
        ICD10Code,
        related_name='secondary_admissions',
        blank=True,
        verbose_name="Ek Tanılar"
    )
    admission_date = models.DateTimeField(verbose_name="Yatış Tarihi")
    discharge_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Taburculuk Tarihi"
    )
    discharge_type = models.CharField(
        max_length=20,
        choices=DischargeType.choices,
        default=DischargeType.STILL_ADMITTED,
        verbose_name="Taburculuk Türü"
    )
    ward = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Klinik / Servis",
        help_text="Örn: Göğüs Hastalıkları, Kardiyoloji"
    )
    bed_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Yatak No"
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Genel Notlar"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'admission'
        verbose_name = 'Yatış'
        verbose_name_plural = 'Yatışlar'
        ordering = ['-admission_date']
        indexes = [
            models.Index(fields=['patient', 'admission_date']),
            models.Index(fields=['primary_diagnosis']),
        ]

    def __str__(self):
        return f"Yatış #{self.pk} — {self.patient} ({self.admission_date.date()})"

    @property
    def length_of_stay(self):
        """Hastanede kalış süresini gün olarak döner."""
        from django.utils import timezone
        end = self.discharge_date or timezone.now()
        return (end - self.admission_date).days


class ClinicalReport(models.Model):
    """
    Epikriz / klinik rapor modeli.

    Yapılandırılmış metin alanları NLP pipeline için hazır tutulmuştur.
    İleride 'raw_text' alanından otomatik veri çıkarımı yapılacaktır.
    """

    class ReportType(models.TextChoices):
        EPICRISIS = 'EPICRISIS', 'Epikriz (Taburculuk Özeti)'
        CONSULTATION = 'CONSULTATION', 'Konsültasyon Notu'
        OPERATION = 'OPERATION', 'Ameliyat Notu'
        RADIOLOGY = 'RADIOLOGY', 'Radyoloji Raporu'
        PATHOLOGY = 'PATHOLOGY', 'Patoloji Raporu'
        PROGRESS = 'PROGRESS', 'Günlük Takip Notu'

    admission = models.ForeignKey(
        Admission,
        on_delete=models.CASCADE,
        related_name='clinical_reports',
        verbose_name="Yatış"
    )
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='authored_reports',
        verbose_name="Raporun Yazarı (Hekim)"
    )
    report_type = models.CharField(
        max_length=20,
        choices=ReportType.choices,
        default=ReportType.EPICRISIS,
        verbose_name="Rapor Türü"
    )
    report_date = models.DateTimeField(verbose_name="Rapor Tarihi")

    # -----------------------------------------------------------------------
    # YAPILANDIRILMIŞ METİN ALANLARI (NLP için hazır)
    # Bu alanlar şimdi hekim tarafından doldurulur; ileride NLP
    # 'raw_text' alanından bu alanları otomatik dolduracaktır.
    # -----------------------------------------------------------------------
    complaint = models.TextField(
        blank=True,
        verbose_name="Şikayet",
        help_text="Hastanın başvuru şikayeti (serbest metin)"
    )
    history_of_present_illness = models.TextField(
        blank=True,
        verbose_name="Hastalık Öyküsü"
    )
    physical_examination = models.TextField(
        blank=True,
        verbose_name="Fizik Muayene Bulguları"
    )
    laboratory_results = models.TextField(
        blank=True,
        verbose_name="Laboratuvar Sonuçları",
        help_text="Serbest metin; ileride JSON'a dönüştürülecek"
    )
    imaging_results = models.TextField(
        blank=True,
        verbose_name="Görüntüleme Sonuçları",
        help_text="Röntgen, BT, MR, USG raporları"
    )
    clinical_course = models.TextField(
        blank=True,
        verbose_name="Klinik Seyir",
        help_text="Yatış süresince hastalığın seyri"
    )
    discharge_summary = models.TextField(
        blank=True,
        verbose_name="Taburculuk Özeti"
    )
    discharge_medications = models.TextField(
        blank=True,
        verbose_name="Taburculuk İlaçları",
        help_text="Reçete edilen ilaçlar (serbest metin)"
    )
    follow_up_instructions = models.TextField(
        blank=True,
        verbose_name="Kontrol Talimatları"
    )

    # Ham metin (OCR veya direkt girişten) — NLP bu alanı işleyecek
    raw_text = models.TextField(
        blank=True,
        verbose_name="Ham Rapor Metni",
        help_text="OCR/NLP pipeline'ı için işlenmemiş metin"
    )
    # NLP işleminden geçirildi mi?
    nlp_processed = models.BooleanField(
        default=False,
        verbose_name="NLP İşlendi mi?"
    )
    nlp_processed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="NLP İşlem Tarihi"
    )

    is_finalized = models.BooleanField(
        default=False,
        verbose_name="Sonuçlandırıldı mı?",
        help_text="True ise rapor değiştirilmez (imzalı)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'clinical_report'
        verbose_name = 'Klinik Rapor'
        verbose_name_plural = 'Klinik Raporlar'
        ordering = ['-report_date']
        indexes = [
            models.Index(fields=['admission', 'report_type']),
            models.Index(fields=['nlp_processed']),
        ]

    def __str__(self):
        return f"{self.get_report_type_display()} — {self.admission.patient} ({self.report_date.date()})"
