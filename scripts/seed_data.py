"""
scripts/seed_data.py
--------------------
Gerçekçi Tıbbi Seed Verisi

Bu script Django shell veya yönetim komutu ile çalıştırılabilir:
    python manage.py shell < scripts/seed_data.py
    veya:
    python scripts/seed_data.py  (DJANGO_SETTINGS_MODULE ayarlı ise)

İçerik:
  - 5 Popüler ICD-10 kodu + standart tedavi protokolleri
  - 3 Protokole UYAN örnek hasta + yatış verisi
  - 3 Protokolden SAPAN örnek hasta + yatış verisi (malpraktis senaryoları)

NOT: Bu script idempotent tasarlanmıştır.
     get_or_create kullandığı için tekrar çalıştırılabilir.
"""

import os
import sys
import django
from datetime import timedelta, date

# ──────────────────────────────────────────────────────────────────────────
# Django ortamını başlat (doğrudan çalıştırma için)
# ──────────────────────────────────────────────────────────────────────────
# scripts/ klasöründen bir üst dizin → proje kökü
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# backend/ klasörünü ekle — burada manage.py ve config/ var
BACKEND_DIR = os.path.join(PROJECT_ROOT, 'backend')
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

# ──────────────────────────────────────────────────────────────────────────
# Import'lar (Django setup'tan sonra yapılmalıdır)
# ──────────────────────────────────────────────────────────────────────────
import hashlib
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.icd10.models import ICD10Category, ICD10Code, TreatmentProtocol
from apps.patients.models import Patient, Admission, ClinicalReport
from apps.treatments.models import MedicationRecord, ClinicalProcedure, AppliedProtocol
from apps.analysis.models import DeviationLog, MalpracticeAssessment

User = get_user_model()

# Zaman yardımcısı
now = timezone.now()


def tc_hash(tc: str) -> str:
    """TC kimlik numarasını SHA-256 ile hashler (KVKK uyumu)."""
    return hashlib.sha256(tc.encode()).hexdigest()


# ══════════════════════════════════════════════════════════════════════════
# 1. KULLANICI (Admin/Hekim)
# ══════════════════════════════════════════════════════════════════════════
print("▶ Kullanıcılar oluşturuluyor...")

admin_user, _ = User.objects.get_or_create(
    username='dr_admin',
    defaults={
        'first_name': 'Ali',
        'last_name': 'Yılmaz',
        'email': 'dr.admin@hastane.gov.tr',
        'is_staff': True,
    }
)
admin_user.set_password('Admin1234!')
admin_user.save()

dr_ortho, _ = User.objects.get_or_create(
    username='dr_ortho',
    defaults={
        'first_name': 'Mehmet',
        'last_name': 'Kaya',
        'email': 'dr.ortho@hastane.gov.tr',
    }
)
dr_ortho.set_password('Ortho1234!')
dr_ortho.save()

dr_internal, _ = User.objects.get_or_create(
    username='dr_internal',
    defaults={
        'first_name': 'Ayşe',
        'last_name': 'Demir',
        'email': 'dr.internal@hastane.gov.tr',
    }
)
dr_internal.set_password('Internal1234!')
dr_internal.save()

print("  ✓ 3 kullanıcı hazır.")

# ══════════════════════════════════════════════════════════════════════════
# 2. ICD-10 KATEGORİLERİ
# ══════════════════════════════════════════════════════════════════════════
print("▶ ICD-10 kategorileri oluşturuluyor...")

cat_injury, _ = ICD10Category.objects.get_or_create(
    code_range_start='S00', code_range_end='T98',
    defaults={
        'name': 'Yaralanmalar, Zehirlenmeler ve Dış Nedenlerin Bazı Diğer Sonuçları',
        'description': 'Kırıklar, burkulmalar, yanıklar ve travma sonuçlarını kapsar.'
    }
)

cat_respiratory, _ = ICD10Category.objects.get_or_create(
    code_range_start='J00', code_range_end='J99',
    defaults={
        'name': 'Solunum Sistemi Hastalıkları',
        'description': 'Pnömoni, KOAH, astım ve diğer solunum yolu hastalıkları.'
    }
)

cat_circulatory, _ = ICD10Category.objects.get_or_create(
    code_range_start='I00', code_range_end='I99',
    defaults={
        'name': 'Dolaşım Sistemi Hastalıkları',
        'description': 'Kalp hastalıkları, inme, hipertansiyon.'
    }
)

cat_musculoskeletal, _ = ICD10Category.objects.get_or_create(
    code_range_start='M00', code_range_end='M99',
    defaults={
        'name': 'Kas-İskelet Sistemi ve Bağ Dokusu Hastalıkları',
        'description': 'Artrit, osteoporoz, disk hernisi.'
    }
)

print("  ✓ 4 kategori hazır.")

# ══════════════════════════════════════════════════════════════════════════
# 3. ICD-10 KODLARI
# ══════════════════════════════════════════════════════════════════════════
print("▶ ICD-10 kodları oluşturuluyor...")

# ── S32.0 — Lomber vertebra kırığı ──────────────────────────────────────
icd_s32, _ = ICD10Code.objects.get_or_create(
    code='S32.0',
    defaults={
        'category': cat_injury,
        'name': 'Lomber Vertebra Kırığı',
        'description': (
            'Bel omurlarından birinin veya birkaçının kırılması. '
            'Genellikle yüksekten düşme, trafik kazası veya osteoporoz zemininde gelişir. '
            'Sinir kökü basısı ve nörolojik defisit riski yüksektir.'
        ),
        'keywords': 'lomber kırık, bel kırığı, omurga kırığı, vertebra fraktürü, kompresyon kırığı',
        'severity': ICD10Code.Severity.HIGH,
    }
)

# ── J18.9 — Pnömoni, tanımlanmamış ──────────────────────────────────────
icd_j18, _ = ICD10Code.objects.get_or_create(
    code='J18.9',
    defaults={
        'category': cat_respiratory,
        'name': 'Pnömoni, Tanımlanmamış',
        'description': (
            'Akciğer parankim dokusunun enfeksiyöz iltihabı. '
            'Toplum kökenli pnömoni genellikle Streptococcus pneumoniae kaynaklıdır. '
            'Ateş, öksürük, balgam ve dispne ile karakterizedir.'
        ),
        'keywords': 'pnömoni, akciğer iltihabı, zatürre, bronkopnömoni, ateş, öksürük',
        'severity': ICD10Code.Severity.MODERATE,
    }
)

# ── I21.0 — Ön duvar miyokard enfarktüsü ────────────────────────────────
icd_i21, _ = ICD10Code.objects.get_or_create(
    code='I21.0',
    defaults={
        'category': cat_circulatory,
        'name': 'Ön Duvar Akut Miyokard Enfarktüsü (AMI)',
        'description': (
            'Sol ön inen koroner arterin (LAD) tıkanmasına bağlı miyokard nekrozu. '
            'Göğüs ağrısı, ST elevasyonu, troponin yüksekliği ile tanı konur. '
            'Hayatı tehdit eden acil kardiyoloji durumudur.'
        ),
        'keywords': 'kalp krizi, miyokard enfarktüsü, STEMI, koroner arter, LAD, troponin',
        'severity': ICD10Code.Severity.CRITICAL,
    }
)

# ── M51.1 — Disk hernisi ─────────────────────────────────────────────────
icd_m51, _ = ICD10Code.objects.get_or_create(
    code='M51.1',
    defaults={
        'category': cat_musculoskeletal,
        'name': 'Lomber Disk Hernisi ile Sinir Kökü Tutulumu',
        'description': (
            'Lomber intervertebral diskin nükleus pulposusunun posterior/posterolateral'
            ' yönde protrüzyon veya ekstrüzyonu. '
            'Siyatik ağrı, bacakta uyuşma, güç kaybı ile prezente olabilir.'
        ),
        'keywords': 'disk hernisi, bel fıtığı, siyatik, lomber disk, nükleus pulposus, HNP',
        'severity': ICD10Code.Severity.MODERATE,
    }
)

# ── T30.0 — Yanık, yüzey alanı tanımlanmamış ────────────────────────────
icd_t30, _ = ICD10Code.objects.get_or_create(
    code='T30.0',
    defaults={
        'category': cat_injury,
        'name': 'Genel Vücut Yanığı (TBSA Tanımlanmamış)',
        'description': (
            'Termal, kimyasal veya elektriksel nedenle oluşan doku hasarı. '
            'TBSA (Total Body Surface Area) ≥%10 yanıklar ciddi kabul edilir. '
            'Sıvı resüsitasyonu, enfeksiyon kontrolü ve greftleme gerektirir.'
        ),
        'keywords': 'yanık, TBSA, termal yaralanma, greftleme, sıvı resüsitasyonu',
        'severity': ICD10Code.Severity.HIGH,
    }
)

print("  ✓ 5 ICD-10 kodu hazır.")

# ══════════════════════════════════════════════════════════════════════════
# 4. STANDART TEDAVİ PROTOKOLLERİ
# ══════════════════════════════════════════════════════════════════════════
print("▶ Tedavi protokolleri oluşturuluyor...")

# ── Protokol 1: Lomber Vertebra Kırığı ──────────────────────────────────
proto_spine, _ = TreatmentProtocol.objects.get_or_create(
    icd10_code=icd_s32,
    protocol_type=TreatmentProtocol.ProtocolType.STANDARD,
    version='2.0',
    defaults={
        'name': 'Stabil Lomber Vertebra Kırığı Konservatif Tedavi Protokolü',
        'min_recovery_days': 75,
        'max_recovery_days': 105,   # Ortalama 90 gün
        'clinical_thresholds': {
            'max_pain_score_discharge': 3,       # NRS 0-10 arası
            'min_mobilization_day': 3,            # Yatış 3. günde mobilizasyon başlamalı
            'physiotherapy_session_min': 20,      # En az 20 seans FTR
            'corset_use_weeks': 12,               # 12 hafta korse kullanımı
        },
        'required_steps': [
            {"step": 1, "action": "Omurga MR ve BT çekimi", "mandatory": True},
            {"step": 2, "action": "Nörolojik muayene ve belgeleme", "mandatory": True},
            {"step": 3, "action": "Korse uygulaması", "mandatory": True},
            {"step": 4, "action": "Fizik tedavi ve rehabilitasyon", "mandatory": True},
            {"step": 5, "action": "Ağrı skoru takibi (günlük)", "mandatory": True},
            {"step": 6, "action": "Kontrol BT çekimi (6. hafta)", "mandatory": False},
        ],
        'first_line_medications': (
            'Parasetamol, İbuprofen, Tramadol, Kalsitonin, Kalsiyum+Vitamin D'
        ),
        'contraindications': (
            'Steroid kullanımı (osteoporoz riski), NSAID uzun süreli kullanımı (>4 hafta), '
            'Nörölojik defisit varlığında konservatif tedavi geciktirilmemeli'
        ),
        'reference_guideline': 'AOSpine 2022 Kılavuzu, Türk Nöroşirurji Derneği Omurga Kırığı Rehberi 2021',
    }
)

# ── Protokol 2: Pnömoni ──────────────────────────────────────────────────
proto_pneumonia, _ = TreatmentProtocol.objects.get_or_create(
    icd10_code=icd_j18,
    protocol_type=TreatmentProtocol.ProtocolType.STANDARD,
    version='3.1',
    defaults={
        'name': 'Toplum Kökenli Pnömoni Standart Tedavi Protokolü (PSI I-III)',
        'min_recovery_days': 5,
        'max_recovery_days': 10,
        'clinical_thresholds': {
            'target_spo2': 95,                    # SpO2 hedef %95 ve üzeri
            'max_fever_days': 3,                  # 3 günden uzun ateş → antibiyotik değişimi
            'antibiotic_switch_day': 5,           # Yanıt yoksa 5. günde AB değişimi
            'crp_target_discharge': 50,           # Taburculukta CRP < 50 mg/L
        },
        'required_steps': [
            {"step": 1, "action": "Akciğer grafisi çekimi", "mandatory": True},
            {"step": 2, "action": "Balgam kültürü alınması", "mandatory": True},
            {"step": 3, "action": "Antibiyotik başlanması (ilk 4 saat)", "mandatory": True},
            {"step": 4, "action": "SpO2 monitorizasyonu", "mandatory": True},
            {"step": 5, "action": "Kontrol akciğer grafisi (3-5. gün)", "mandatory": False},
        ],
        'first_line_medications': (
            'Amoksisilin-Klavulanat, Azitromisin, Parasetamol, '
            'Serum fizyolojik (IV hidrasyon), N-Asetilsistein'
        ),
        'contraindications': (
            'Florokinolonlar (dirençli suş endişesi olmaksızın ilk seçenek olarak kullanılmamalı), '
            'NSAID (plevral komplikasyon riski)'
        ),
        'reference_guideline': 'Türk Toraks Derneği Pnömoni Tanı ve Tedavi Rehberi 2022, IDSA/ATS 2019',
    }
)

# ── Protokol 3: AMI / Kalp Krizi ────────────────────────────────────────
proto_ami, _ = TreatmentProtocol.objects.get_or_create(
    icd10_code=icd_i21,
    protocol_type=TreatmentProtocol.ProtocolType.EMERGENCY,
    version='4.0',
    defaults={
        'name': 'STEMI Akut Yönetim Protokolü (Primer PKG)',
        'min_recovery_days': 4,
        'max_recovery_days': 7,
        'clinical_thresholds': {
            'door_to_balloon_minutes': 90,        # Kapıdan balona ≤90 dakika
            'lvef_target': 50,                    # Taburculukta EF ≥%50 ideal
            'troponin_peak_fold': 10,             # Pik troponin: normalin 10 katı
        },
        'required_steps': [
            {"step": 1, "action": "12 derivasyonlu EKG çekimi (ilk 10 dk)", "mandatory": True},
            {"step": 2, "action": "Aspirin ve Klopidogrel yükleme dozu", "mandatory": True},
            {"step": 3, "action": "Primer PKG (Anjiyografi)", "mandatory": True},
            {"step": 4, "action": "Troponin seri ölçümü (0-3-6-12 saat)", "mandatory": True},
            {"step": 5, "action": "Ekokardiyografi (yatış içinde)", "mandatory": True},
            {"step": 6, "action": "Kardiyak rehabilitasyon başvurusu", "mandatory": False},
        ],
        'first_line_medications': (
            'Aspirin, Klopidogrel, Enoksaparin, Metoprolol, '
            'Ramipril, Atorvastatin, Nitrogliserin (sublingual)'
        ),
        'contraindications': (
            'Morfin (P2Y12 inhibitörü emilimini azaltır — dikkatli kullan), '
            'Beta-bloker (akut kalp yetersizliğinde kontrendike), '
            'NSAID (miyokard hasarını artırır)'
        ),
        'reference_guideline': 'ESC STEMI Kılavuzu 2023, ACC/AHA STEMI Guideline 2022',
    }
)

# ── Protokol 4: Disk Hernisi ─────────────────────────────────────────────
proto_disc, _ = TreatmentProtocol.objects.get_or_create(
    icd10_code=icd_m51,
    protocol_type=TreatmentProtocol.ProtocolType.STANDARD,
    version='1.5',
    defaults={
        'name': 'Lomber Disk Hernisi Konservatif Tedavi Protokolü (6 Hafta)',
        'min_recovery_days': 35,
        'max_recovery_days': 50,
        'clinical_thresholds': {
            'conservative_trial_weeks': 6,       # 6 haftada yanıt yoksa cerrahi değerlendirme
            'vas_score_surgery_threshold': 7,    # VAS ≥7 → cerrahi endikasyon
            'physiotherapy_sessions_min': 15,    # En az 15 seans
        },
        'required_steps': [
            {"step": 1, "action": "Lomber MR görüntüleme", "mandatory": True},
            {"step": 2, "action": "Nörolojik muayene (motor+duyu+refleks)", "mandatory": True},
            {"step": 3, "action": "Fizik tedavi ve egzersiz programı", "mandatory": True},
            {"step": 4, "action": "Epidural steroid enjeksiyonu (gerekirse)", "mandatory": False},
            {"step": 5, "action": "VAS ağrı skoru günlük takibi", "mandatory": True},
        ],
        'first_line_medications': (
            'İbuprofen, Parasetamol, Tiyokolşikozid (kas gevşetici), '
            'Pregabalin, Metilprednizolon (kısa kür)'
        ),
        'contraindications': (
            'Kauda ekuina sendromu → Acil cerrahi gerektir (konservatif değil), '
            'Opioid uzun süreli kullanımı (bağımlılık riski)'
        ),
        'reference_guideline': 'NASS Kılavuzu 2020, Türk Nöroşirurji Derneği Disk Hernisi Rehberi',
    }
)

# ── Protokol 5: Yanık ────────────────────────────────────────────────────
proto_burn, _ = TreatmentProtocol.objects.get_or_create(
    icd10_code=icd_t30,
    protocol_type=TreatmentProtocol.ProtocolType.STANDARD,
    version='2.2',
    defaults={
        'name': 'Orta-Ağır Yanık Resüsitasyon ve Tedavi Protokolü (TBSA %10-30)',
        'min_recovery_days': 21,
        'max_recovery_days': 45,
        'clinical_thresholds': {
            'parkland_formula_ml_per_kg_per_tbsa': 4,   # Parkland formülü
            'urine_output_target_ml_per_hour': 0.5,     # İdrar çıkışı hedefi
            'wound_coverage_target_day': 7,             # 7. günde yara kapanması hedefi
        },
        'required_steps': [
            {"step": 1, "action": "TBSA hesaplama (Lund-Browder)", "mandatory": True},
            {"step": 2, "action": "IV sıvı resüsitasyonu (Parkland)", "mandatory": True},
            {"step": 3, "action": "Yanık yara bakımı ve pansuman", "mandatory": True},
            {"step": 4, "action": "Profilaktik antibiyotik", "mandatory": True},
            {"step": 5, "action": "Ağrı yönetimi (morfin titrasyonu)", "mandatory": True},
            {"step": 6, "action": "Split-thickness greftleme (gerekirse)", "mandatory": False},
        ],
        'first_line_medications': (
            'Serum fizyolojik (Ringer Laktat IV), Morfin, Parasetamol, '
            'Piperasilin-Tazobaktam, Gümüş sülfa krem, Tetanoz profilaksisi'
        ),
        'contraindications': (
            'Süksinilkolin (yanıkta hiperkalemi riski), '
            'Adrenalin (yanık bölgesi periferik dolaşımı bozar)'
        ),
        'reference_guideline': 'ABA Yanık Bakım Standartları 2022, ISBI Yanık Tedavi Kılavuzu',
    }
)

print("  ✓ 5 protokol hazır.")

# ══════════════════════════════════════════════════════════════════════════
# 5. UYUMLU HASTALAR (3 Adet — Protokole Tam Uyum)
# ══════════════════════════════════════════════════════════════════════════
print("▶ Protokole UYAN hastalar oluşturuluyor...")


def make_datetime(days_ago, hour=8):
    return now - timedelta(days=days_ago, hours=(now.hour - hour))


# ── Hasta U1: Lomber Kırık — Protokole Uyumlu ───────────────────────────
patient_u1, _ = Patient.objects.get_or_create(
    tc_identity_hash=tc_hash('10000000001'),
    defaults={
        'first_name': 'Fatma', 'last_name': 'Arslan',
        'date_of_birth': date(1968, 4, 15),
        'gender': Patient.Gender.FEMALE,
        'blood_type': Patient.BloodType.A_POS,
        'chronic_conditions': 'Osteoporoz (5 yıllık), Tip 2 Diyabet',
        'known_allergies': 'Penisilin grubu ilaçlara alerjisi var',
    }
)

admission_u1, _ = Admission.objects.get_or_create(
    patient=patient_u1,
    admission_date=make_datetime(days_ago=95),
    defaults={
        'admitting_physician': dr_ortho,
        'admission_type': Admission.AdmissionType.EMERGENCY,
        'primary_diagnosis': icd_s32,
        'discharge_date': make_datetime(days_ago=7),   # 88 gün yatış (protokol 75-105)
        'discharge_type': Admission.DischargeType.RECOVERED,
        'ward': 'Ortopedi ve Travmatoloji',
        'bed_number': 'A-14',
        'notes': 'Merdivenden düşme sonucu L2 kompresyon kırığı. Konservatif tedavi uygulandı.',
    }
)

# Uyumlu ilaçlar
for drug, dose, route, freq in [
    ('Parasetamol', '500mg', MedicationRecord.RouteOfAdministration.ORAL, '3x1'),
    ('İbuprofen', '400mg', MedicationRecord.RouteOfAdministration.ORAL, '2x1'),
    ('Tramadol', '50mg', MedicationRecord.RouteOfAdministration.ORAL, '2x1'),
    ('Kalsitonin', '100 IU', MedicationRecord.RouteOfAdministration.INTRAMUSCULAR, '1x1'),
    ('Kalsiyum+Vitamin D', '500mg/400IU', MedicationRecord.RouteOfAdministration.ORAL, '2x1'),
]:
    MedicationRecord.objects.get_or_create(
        admission=admission_u1, drug_name=drug,
        defaults={
            'ordered_by': dr_ortho, 'administered_by': dr_ortho,
            'dose': dose, 'route': route, 'frequency': freq,
            'start_datetime': admission_u1.admission_date + timedelta(days=1),
            'end_datetime': admission_u1.discharge_date,
            'status': MedicationRecord.MedicationStatus.ADMINISTERED,
        }
    )

# Zorunlu prosedürler
for proc_name, day_offset in [
    ('Omurga MR ve BT çekimi', 0),
    ('Nörolojik muayene ve belgeleme', 0),
    ('Korse uygulaması', 1),
    ('Fizik tedavi ve rehabilitasyon', 5),
    ('Ağrı skoru takibi (günlük)', 1),
]:
    ClinicalProcedure.objects.get_or_create(
        admission=admission_u1, procedure_name=proc_name,
        defaults={
            'performed_by': dr_ortho,
            'status': ClinicalProcedure.ProcedureStatus.PERFORMED,
            'performed_datetime': admission_u1.admission_date + timedelta(days=day_offset),
        }
    )

AppliedProtocol.objects.get_or_create(
    admission=admission_u1, protocol=proto_spine,
    defaults={'selected_by': dr_ortho, 'compliance_score': None}
)
print("  ✓ Hasta U1: Fatma Arslan (Lomber Kırık - Uyumlu)")

# ── Hasta U2: Pnömoni — Protokole Uyumlu ────────────────────────────────
patient_u2, _ = Patient.objects.get_or_create(
    tc_identity_hash=tc_hash('10000000002'),
    defaults={
        'first_name': 'Kemal', 'last_name': 'Şahin',
        'date_of_birth': date(1945, 9, 22),
        'gender': Patient.Gender.MALE,
        'blood_type': Patient.BloodType.B_POS,
        'chronic_conditions': 'KOAH (evre 2), Hipertansiyon',
        'known_allergies': 'Yok',
    }
)

admission_u2, _ = Admission.objects.get_or_create(
    patient=patient_u2,
    admission_date=make_datetime(days_ago=14),
    defaults={
        'admitting_physician': dr_internal,
        'admission_type': Admission.AdmissionType.EMERGENCY,
        'primary_diagnosis': icd_j18,
        'discharge_date': make_datetime(days_ago=7),   # 7 gün yatış (protokol 5-10)
        'discharge_type': Admission.DischargeType.RECOVERED,
        'ward': 'Göğüs Hastalıkları',
        'bed_number': 'B-08',
        'notes': 'Toplum kökenli pnömoni. Ateş 3. günde geriledi. Balgam kültürü: S. pneumoniae.',
    }
)

for drug, dose, route, freq in [
    ('Amoksisilin-Klavulanat', '1g', MedicationRecord.RouteOfAdministration.INTRAVENOUS, '3x1'),
    ('Azitromisin', '500mg', MedicationRecord.RouteOfAdministration.ORAL, '1x1'),
    ('Parasetamol', '1g', MedicationRecord.RouteOfAdministration.INTRAVENOUS, '4x1'),
    ('Serum fizyolojik', '1000ml', MedicationRecord.RouteOfAdministration.INTRAVENOUS, '2x1'),
    ('N-Asetilsistein', '600mg', MedicationRecord.RouteOfAdministration.ORAL, '2x1'),
]:
    MedicationRecord.objects.get_or_create(
        admission=admission_u2, drug_name=drug,
        defaults={
            'ordered_by': dr_internal, 'administered_by': dr_internal,
            'dose': dose, 'route': route, 'frequency': freq,
            'start_datetime': admission_u2.admission_date + timedelta(hours=2),
            'end_datetime': admission_u2.discharge_date,
            'status': MedicationRecord.MedicationStatus.ADMINISTERED,
        }
    )

for proc_name, day_offset in [
    ('Akciğer grafisi çekimi', 0),
    ('Balgam kültürü alınması', 0),
    ('Antibiyotik başlanması (ilk 4 saat)', 0),
    ('SpO2 monitorizasyonu', 0),
]:
    ClinicalProcedure.objects.get_or_create(
        admission=admission_u2, procedure_name=proc_name,
        defaults={
            'performed_by': dr_internal,
            'status': ClinicalProcedure.ProcedureStatus.PERFORMED,
            'performed_datetime': admission_u2.admission_date + timedelta(hours=day_offset * 4),
        }
    )

AppliedProtocol.objects.get_or_create(
    admission=admission_u2, protocol=proto_pneumonia,
    defaults={'selected_by': dr_internal}
)
print("  ✓ Hasta U2: Kemal Şahin (Pnömoni - Uyumlu)")

# ── Hasta U3: Disk Hernisi — Protokole Uyumlu ───────────────────────────
patient_u3, _ = Patient.objects.get_or_create(
    tc_identity_hash=tc_hash('10000000003'),
    defaults={
        'first_name': 'Zeynep', 'last_name': 'Çelik',
        'date_of_birth': date(1982, 6, 30),
        'gender': Patient.Gender.FEMALE,
        'blood_type': Patient.BloodType.O_POS,
        'chronic_conditions': 'Yok',
        'known_allergies': 'Yok',
    }
)

admission_u3, _ = Admission.objects.get_or_create(
    patient=patient_u3,
    admission_date=make_datetime(days_ago=44),
    defaults={
        'admitting_physician': dr_ortho,
        'admission_type': Admission.AdmissionType.ELECTIVE,
        'primary_diagnosis': icd_m51,
        'discharge_date': make_datetime(days_ago=5),   # 39 gün yatış (protokol 35-50)
        'discharge_type': Admission.DischargeType.RECOVERED,
        'ward': 'Fizik Tedavi ve Rehabilitasyon',
        'bed_number': 'C-03',
        'notes': 'L4-L5 disk hernisi. Konservatif tedaviyle düzeldi. VAS: başlangıç 7 → taburculuk 2.',
    }
)

for drug, dose, route, freq in [
    ('İbuprofen', '400mg', MedicationRecord.RouteOfAdministration.ORAL, '3x1'),
    ('Parasetamol', '500mg', MedicationRecord.RouteOfAdministration.ORAL, '3x1'),
    ('Tiyokolşikozid', '4mg', MedicationRecord.RouteOfAdministration.ORAL, '2x1'),
    ('Pregabalin', '75mg', MedicationRecord.RouteOfAdministration.ORAL, '2x1'),
]:
    MedicationRecord.objects.get_or_create(
        admission=admission_u3, drug_name=drug,
        defaults={
            'ordered_by': dr_ortho, 'administered_by': dr_ortho,
            'dose': dose, 'route': route, 'frequency': freq,
            'start_datetime': admission_u3.admission_date + timedelta(days=1),
            'end_datetime': admission_u3.discharge_date,
            'status': MedicationRecord.MedicationStatus.ADMINISTERED,
        }
    )

for proc_name, day_offset in [
    ('Lomber MR görüntüleme', 0),
    ('Nörolojik muayene (motor+duyu+refleks)', 0),
    ('Fizik tedavi ve egzersiz programı', 2),
    ('VAS ağrı skoru günlük takibi', 1),
]:
    ClinicalProcedure.objects.get_or_create(
        admission=admission_u3, procedure_name=proc_name,
        defaults={
            'performed_by': dr_ortho,
            'status': ClinicalProcedure.ProcedureStatus.PERFORMED,
            'performed_datetime': admission_u3.admission_date + timedelta(days=day_offset),
        }
    )

AppliedProtocol.objects.get_or_create(
    admission=admission_u3, protocol=proto_disc,
    defaults={'selected_by': dr_ortho}
)
print("  ✓ Hasta U3: Zeynep Çelik (Disk Hernisi - Uyumlu)")

# ══════════════════════════════════════════════════════════════════════════
# 6. SAPAN HASTALAR (3 Adet — Malpraktis Senaryoları)
# ══════════════════════════════════════════════════════════════════════════
print("▶ Protokolden SAPAN hastalar oluşturuluyor...")

# ── Hasta M1: Lomber Kırık — 210 Gün Yatış + Gereksiz Cerrahi ───────────
# Senaryo: Lomber kırık hastaları konservatif tedaviyle 75-105 günde taburcu olur.
# Bu hasta 210 gün yatmış (%133 zaman sapması) + protokol dışı 3 ameliyat faturası.
patient_m1, _ = Patient.objects.get_or_create(
    tc_identity_hash=tc_hash('20000000001'),
    defaults={
        'first_name': 'Hasan', 'last_name': 'Koç',
        'date_of_birth': date(1955, 11, 10),
        'gender': Patient.Gender.MALE,
        'blood_type': Patient.BloodType.A_NEG,
        'chronic_conditions': 'Hipertansiyon, Hiperlipidemi',
        'known_allergies': 'Yok',
    }
)

admission_m1, _ = Admission.objects.get_or_create(
    patient=patient_m1,
    admission_date=make_datetime(days_ago=215),
    defaults={
        'admitting_physician': dr_ortho,
        'admission_type': Admission.AdmissionType.EMERGENCY,
        'primary_diagnosis': icd_s32,
        'discharge_date': make_datetime(days_ago=5),   # 210 gün! Beklenen: 75-105 gün
        'discharge_type': Admission.DischargeType.RECOVERED,
        'ward': 'Ortopedi ve Travmatoloji',
        'bed_number': 'A-22',
        'notes': (
            'L3 kompresyon kırığı. Konservatif tedavi yeterli olmasına rağmen '
            'hastaya 3 kez ameliyat yapıldı. Son ameliyat tıbbi gereklilik dışıdır. '
            'Aile şikayeti mevcut. HEKİM NOTU: Konsültasyon talep edildi.'
        ),
    }
)

# Protokol dışı ilaçlar (opioid bağımlılığı + protokol ilaçları EKSİK)
for drug, dose, route, freq in [
    ('Morfin', '10mg', MedicationRecord.RouteOfAdministration.INTRAMUSCULAR, '3x1'),
    ('Deksametazon', '8mg', MedicationRecord.RouteOfAdministration.INTRAVENOUS, '2x1'),
    ('Gabapentin', '300mg', MedicationRecord.RouteOfAdministration.ORAL, '3x1'),
    # NOT: Protokol ilaçları (Parasetamol, Kalsitonin vb.) EKSİK
]:
    MedicationRecord.objects.get_or_create(
        admission=admission_m1, drug_name=drug,
        defaults={
            'ordered_by': dr_ortho, 'administered_by': dr_ortho,
            'dose': dose, 'route': route, 'frequency': freq,
            'start_datetime': admission_m1.admission_date + timedelta(days=2),
            'end_datetime': admission_m1.discharge_date,
            'status': MedicationRecord.MedicationStatus.ADMINISTERED,
        }
    )

# Gereksiz ameliyatlar
for proc_name, day_offset, duration in [
    ('Vertebroplasti ameliyatı (1. operasyon)', 10, 120),
    ('Açık redüksiyon ve internal fiksasyon (2. operasyon)', 45, 180),
    ('Lomber füzyon ameliyatı (3. operasyon - şüpheli endikasyon)', 120, 240),
]:
    ClinicalProcedure.objects.get_or_create(
        admission=admission_m1, procedure_name=proc_name,
        defaults={
            'performed_by': dr_ortho,
            'status': ClinicalProcedure.ProcedureStatus.PERFORMED,
            'performed_datetime': admission_m1.admission_date + timedelta(days=day_offset),
            'duration_minutes': duration,
            'complications': 'Ameliyat sonrası enfeksiyon gelişti.' if day_offset > 40 else '',
        }
    )

AppliedProtocol.objects.get_or_create(
    admission=admission_m1, protocol=proto_spine,
    defaults={'selected_by': dr_ortho}
)
print("  ⚠ Hasta M1: Hasan Koç (Lomber Kırık - 210 Gün + 3 Gereksiz Ameliyat)")

# ── Hasta M2: Pnömoni — Antibiyotik Verilmedi + 30 Gün Uzatılmış Yatış ──
# Senaryo: Pnömoni 5-10 günde taburcu edilmeli. Bu hasta 30 gün yattı,
# protokol antibiyotiği hiç verilmedi, yanlış ilaçlar uygulandı.
patient_m2, _ = Patient.objects.get_or_create(
    tc_identity_hash=tc_hash('20000000002'),
    defaults={
        'first_name': 'Sercan', 'last_name': 'Bulut',
        'date_of_birth': date(1978, 3, 5),
        'gender': Patient.Gender.MALE,
        'blood_type': Patient.BloodType.B_NEG,
        'chronic_conditions': 'Diyabet Tip 2',
        'known_allergies': 'Yok',
    }
)

admission_m2, _ = Admission.objects.get_or_create(
    patient=patient_m2,
    admission_date=make_datetime(days_ago=35),
    defaults={
        'admitting_physician': dr_internal,
        'admission_type': Admission.AdmissionType.EMERGENCY,
        'primary_diagnosis': icd_j18,
        'discharge_date': make_datetime(days_ago=5),   # 30 gün! Beklenen: 5-10 gün
        'discharge_type': Admission.DischargeType.RECOVERED,
        'ward': 'İç Hastalıkları',
        'bed_number': 'D-11',
        'notes': (
            'Pnömoni tanısı. Yanlış antibiyotik seçimi yapıldı (Metronidazol — anaerop kapsama '
            'yönelik, pnömoni protokolü dışı). Kültür alınmadı. '
            '3. günde ateş devam etmesine rağmen antibiyotik değiştirilmedi. '
            'Balgam kültürü hiç alınmadı!'
        ),
    }
)

# Yanlış ilaçlar (protokol dışı)
for drug, dose, route, freq in [
    ('Metronidazol', '500mg', MedicationRecord.RouteOfAdministration.INTRAVENOUS, '3x1'),
    ('Ranitidin', '150mg', MedicationRecord.RouteOfAdministration.ORAL, '2x1'),
    ('Metilprednizolon', '40mg', MedicationRecord.RouteOfAdministration.INTRAVENOUS, '1x1'),
    # NOT: Amoksisilin-Klavulanat ve Azitromisin (protokol ilaçları) HİÇ VERİLMEDİ
]:
    MedicationRecord.objects.get_or_create(
        admission=admission_m2, drug_name=drug,
        defaults={
            'ordered_by': dr_internal, 'administered_by': dr_internal,
            'dose': dose, 'route': route, 'frequency': freq,
            'start_datetime': admission_m2.admission_date + timedelta(hours=6),
            'end_datetime': admission_m2.discharge_date,
            'status': MedicationRecord.MedicationStatus.ADMINISTERED,
        }
    )

# Zorunlu prosedürlerden bazıları yapılmadı
ClinicalProcedure.objects.get_or_create(
    admission=admission_m2,
    procedure_name='Akciğer grafisi çekimi',
    defaults={
        'performed_by': dr_internal,
        'status': ClinicalProcedure.ProcedureStatus.PERFORMED,
        'performed_datetime': admission_m2.admission_date + timedelta(hours=2),
    }
)
# SpO2 monitorizasyonu = YAPILMADI (Cancelled)
ClinicalProcedure.objects.get_or_create(
    admission=admission_m2,
    procedure_name='SpO2 monitorizasyonu',
    defaults={
        'performed_by': dr_internal,
        'status': ClinicalProcedure.ProcedureStatus.CANCELLED,
        'scheduled_datetime': admission_m2.admission_date,
        'notes': 'Cihaz arızası gerekçesiyle iptal edildi.',
    }
)
# Balgam kültürü ve antibiyotik başlanması HİÇ YAPILMADI (kayıt yok)

AppliedProtocol.objects.get_or_create(
    admission=admission_m2, protocol=proto_pneumonia,
    defaults={'selected_by': dr_internal}
)
print("  ⚠ Hasta M2: Sercan Bulut (Pnömoni - Yanlış AB + 30 Gün Uzama)")

# ── Hasta M3: AMI — Kapıdan Balona 6 Saat + Aspirin Verilmedi ───────────
# Senaryo: STEMI'de kapıdan balona <90 dk kritik. Bu hastada 360 dk geçmiş.
# Aspirin verilmemiş, anjiyografi gecikmiş → hayatı tehdit eden malpraktis.
patient_m3, _ = Patient.objects.get_or_create(
    tc_identity_hash=tc_hash('20000000003'),
    defaults={
        'first_name': 'Mustafa', 'last_name': 'Erdoğan',
        'date_of_birth': date(1960, 7, 18),
        'gender': Patient.Gender.MALE,
        'blood_type': Patient.BloodType.O_NEG,
        'chronic_conditions': 'Tip 2 Diyabet, Sigara (30 paket-yıl), Hipertansiyon',
        'known_allergies': 'Yok',
    }
)

admission_m3, _ = Admission.objects.get_or_create(
    patient=patient_m3,
    admission_date=make_datetime(days_ago=10),
    defaults={
        'admitting_physician': dr_internal,
        'admission_type': Admission.AdmissionType.EMERGENCY,
        'primary_diagnosis': icd_i21,
        'discharge_date': make_datetime(days_ago=4),   # 6 gün yatış (zaman uyumlu ama süreç sapmalı)
        'discharge_type': Admission.DischargeType.RECOVERED,
        'ward': 'Koroner Yoğun Bakım',
        'bed_number': 'KYB-02',
        'notes': (
            'STEMI tanısı. Kapıdan balona süre: 360 dakika (standart: ≤90 dk). '
            'Aspirin ve Klopidogrel yükleme dozu VERİLMEDİ. '
            'Hastayla iletişim güçlüğü gerekçesiyle anjiyografi geciktirilmiş. '
            'Taburculukta EF %30 (ciddi miyokard hasarı). '
            'Hasta yakınları şikayetçi. Olay tutanağı düzenlendi.'
        ),
    }
)

# Aspirin VERİLMEDİ, sadece heparin verildi
for drug, dose, route, freq in [
    ('Enoksaparin', '1mg/kg', MedicationRecord.RouteOfAdministration.SUBCUTANEOUS, '2x1'),
    ('Metoprolol', '25mg', MedicationRecord.RouteOfAdministration.ORAL, '2x1'),
    ('Atorvastatin', '80mg', MedicationRecord.RouteOfAdministration.ORAL, '1x1'),
    ('Ramipril', '5mg', MedicationRecord.RouteOfAdministration.ORAL, '1x1'),
    # NOT: Aspirin ve Klopidogrel (ZORUNLUlar) HİÇ VERİLMEDİ
]:
    MedicationRecord.objects.get_or_create(
        admission=admission_m3, drug_name=drug,
        defaults={
            'ordered_by': dr_internal, 'administered_by': dr_internal,
            'dose': dose, 'route': route, 'frequency': freq,
            'start_datetime': admission_m3.admission_date + timedelta(hours=7),  # 7 saat gecikme!
            'end_datetime': admission_m3.discharge_date,
            'status': MedicationRecord.MedicationStatus.ADMINISTERED,
        }
    )

# EKG yapıldı ama anjiyografi 6 saat gecikti
ClinicalProcedure.objects.get_or_create(
    admission=admission_m3,
    procedure_name='12 derivasyonlu EKG çekimi (ilk 10 dk)',
    defaults={
        'performed_by': dr_internal,
        'status': ClinicalProcedure.ProcedureStatus.PERFORMED,
        'performed_datetime': admission_m3.admission_date + timedelta(minutes=15),
    }
)
ClinicalProcedure.objects.get_or_create(
    admission=admission_m3,
    procedure_name='Primer PKG (Anjiyografi)',
    defaults={
        'performed_by': dr_internal,
        'status': ClinicalProcedure.ProcedureStatus.PERFORMED,
        'performed_datetime': admission_m3.admission_date + timedelta(minutes=360),  # 6 SAAT GECİKME
        'duration_minutes': 75,
        'complications': 'İşlem gecikmesine bağlı geniş anterior MI. Post-PKG EF: %30.',
    }
)
# Ekokardiyografi, Troponin serisi → YAPILMADI

AppliedProtocol.objects.get_or_create(
    admission=admission_m3, protocol=proto_ami,
    defaults={'selected_by': dr_internal}
)
print("  ⚠ Hasta M3: Mustafa Erdoğan (STEMI - 360 dk Gecikme + Aspirin Eksik)")

# ══════════════════════════════════════════════════════════════════════════
# ÖZET
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("✅ SEED VERİSİ BAŞARIYLA YÜKLENDİ")
print("═"*60)
print(f"  ICD-10 Kategorisi : {ICD10Category.objects.count()}")
print(f"  ICD-10 Kodu       : {ICD10Code.objects.count()}")
print(f"  Tedavi Protokolü  : {TreatmentProtocol.objects.count()}")
print(f"  Hasta             : {Patient.objects.count()}")
print(f"  Yatış             : {Admission.objects.count()}")
print(f"  İlaç Kaydı        : {MedicationRecord.objects.count()}")
print(f"  Klinik Prosedür   : {ClinicalProcedure.objects.count()}")
print(f"  Uygulanan Protokol: {AppliedProtocol.objects.count()}")
print("═"*60)
print("\nKural motorunu çalıştırmak için:")
print("  from apps.analysis.services import RuleEngineService")
print(f"  for a_id in {list(Admission.objects.values_list('id', flat=True))}:")
print("      result = RuleEngineService().analyze_admission(a_id)")
print("      print(result.risk_level, result.overall_compliance_score)")
