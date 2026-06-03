"""
apps/analysis/nlp_service.py
-----------------------------
Klinik belge (epikriz/rapor) metninden tıbbi varlıkları çıkaran NLP servisi.

Hibrit yaklaşım:
  1. Regex  → ICD-10 kodları, tarihler, süreler
  2. Keyword matching → ilaçlar, prosedürler
  3. Teşhis eşleme → Türkçe tanı adı → ICD-10 kodu
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Türkçe teşhis adı → ICD-10 kodu eşleme tablosu
# ─────────────────────────────────────────────────────────────────────────────
DIAGNOSIS_MAP = {
    # Pnömoni / Zatürre
    "pnömoni": "J18.9", "zatürre": "J18.9", "pnomoni": "J18.9",
    "toplum kökenli pnömoni": "J18.9", "pulmoner enfeksiyon": "J18.9",
    "akciğer iltihabı": "J18.9", "bronkopnömoni": "J18.0",

    # Kardiyoloji
    "stemi": "I21.9", "miyokard enfarktüsü": "I21.9",
    "kalp krizi": "I21.9", "akut miyokard enfarktüsü": "I21.9",
    "ami": "I21.9", "akut mi": "I21.9",
    "anjina": "I20.9", "göğüs ağrısı": "I20.9",

    # Ortopedi
    "lomber disk hernisi": "M51.1", "bel fıtığı": "M51.1",
    "disk hernisi": "M51.1", "lumbar herni": "M51.1",
    "lomber kırık": "S32.0", "vertebra kırığı": "S32.0",
    "omurga kırığı": "S32.0", "bel kırığı": "S32.0",

    # Diyabet
    "diyabet": "E11.9", "tip 2 diyabet": "E11.9",
    "şeker hastalığı": "E11.9", "diabetes mellitus": "E11.9",
    "tip 1 diyabet": "E10.9",

    # Hipertansiyon
    "hipertansiyon": "I10", "yüksek tansiyon": "I10",
    "hiper tansiyon": "I10", "ht": "I10",

    # Genel
    "apandisit": "K37", "safra kesesi": "K81.9",
    "kolesistit": "K81.0", "böbrek taşı": "N20.0",
}

# ─────────────────────────────────────────────────────────────────────────────
# Bilinen ilaç / etken madde listesi
# ─────────────────────────────────────────────────────────────────────────────
KNOWN_MEDICATIONS = [
    # Antibiyotikler
    "amoksisilin", "amoksisilin-klavulanat", "augmentin",
    "azitromisin", "azitromisin", "zithromax",
    "seftriakson", "sefuroksim", "meropenem", "piperasilin",
    "metronidazol", "siprofloksasin", "levofloksasin",
    "vankomisin", "teikoplanin", "linezolid",
    # Kardiyoloji
    "aspirin", "klopidogrel", "plavix", "tikagrelol",
    "enoksaparin", "heparin", "warfarin",
    "metoprolol", "bisoprolol", "karvedilol",
    "atorvastatin", "rosuvastatin", "simvastatin",
    "ramipril", "enalapril", "lisinopril",
    "nitrogliserin", "isosorbid", "diltiazem", "verapamil",
    "furosemid", "spironolakton", "hidroklorotiazid",
    # Analjezik / Antienflamatuar
    "parasetamol", "ibuprofen", "naproksen", "indometasin",
    "tramadol", "morfin", "kodein", "opioid",
    "metilprednizolon", "prednizolon", "deksametazon",
    # Diğer
    "ranitidin", "omeprazol", "pantoprazol", "lansoprazol",
    "n-asetilsistein", "salbutamol", "ipratropium",
    "insülin", "metformin", "glibenklamid",
    "serum fizyolojik", "ringer laktat", "dekstroz",
]

# ─────────────────────────────────────────────────────────────────────────────
# Bilinen klinik prosedürler
# ─────────────────────────────────────────────────────────────────────────────
KNOWN_PROCEDURES = [
    "ekg", "elektrokardiyogram", "ekokardiyografi", "ekokardiyogram",
    "anjiyografi", "koroner anjiyografi", "pkg", "perkutan koroner girişim",
    "bilgisayarlı tomografi", "bt", "mri", "mr görüntüleme",
    "röntgen", "akciğer grafisi", "ultrason", "ultrasonografi",
    "kan kültürü", "balgam kültürü", "idrar kültürü",
    "tam kan sayımı", "tks", "biyokimya",
    "spo2", "oksijen saturasyonu", "pulse oksimetre",
    "mekanik ventilasyon", "entübasyon", "yoğun bakım",
    "ameliyat", "operasyon", "cerrahi",
    "troponin", "ck-mb", "bnp",
    "spinal", "lomber ponksiyon",
]


# ─────────────────────────────────────────────────────────────────────────────
# Sonuç veri sınıfı
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class ExtractedClinicalData:
    """NLP çıkarım sonucu."""
    raw_text: str = ""

    # Teşhis
    icd_codes: list = field(default_factory=list)          # ["J18.9", "I21"]
    diagnosis_text: str = ""                                 # "Pnömoni"
    matched_icd: Optional[str] = None                       # En olası ICD kodu

    # Tedavi
    medications: list = field(default_factory=list)         # ["aspirin", "klopidogrel"]
    procedures: list = field(default_factory=list)          # ["ekg", "anjiyografi"]

    # Zamanlama
    admission_date: Optional[str] = None
    discharge_date: Optional[str] = None
    duration_days: Optional[int] = None

    # Meta
    patient_name: Optional[str] = None
    patient_age: Optional[int] = None
    confidence: float = 0.0                                  # 0-1 arası güven skoru
    warnings: list = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Ana NLP Servisi
# ─────────────────────────────────────────────────────────────────────────────
class ClinicalNLPService:
    """
    Klinik metin belgesinden tıbbi varlıkları çıkarır.

    Kullanım:
        svc = ClinicalNLPService()
        result = svc.extract(metin)
        print(result.matched_icd, result.medications, result.duration_days)
    """

    def __init__(self):
        self._lower_med_map = {m.lower(): m for m in KNOWN_MEDICATIONS}
        self._lower_proc_map = {p.lower(): p for p in KNOWN_PROCEDURES}

    # ── Ana metod ──────────────────────────────────────────────────────────
    def extract(self, text: str) -> ExtractedClinicalData:
        result = ExtractedClinicalData(raw_text=text)
        t = text.lower()

        result.icd_codes    = self._extract_icd_codes(text)
        result.medications  = self._extract_medications(t)
        result.procedures   = self._extract_procedures(t)
        result.duration_days = self._extract_duration(t)
        result.patient_age  = self._extract_age(t)
        result.patient_name = self._extract_patient_name(text)
        result.admission_date, result.discharge_date = self._extract_dates(text)

        # Teşhis metni ve ICD eşleme
        diag, icd = self._match_diagnosis(t)
        result.diagnosis_text = diag
        result.matched_icd = icd or (result.icd_codes[0] if result.icd_codes else None)

        result.confidence = self._calc_confidence(result)
        result.warnings   = self._generate_warnings(result)

        logger.info(
            "NLP çıkarım tamamlandı → ICD=%s | ilaç=%d | prosedür=%d | süre=%s gün | güven=%.0f%%",
            result.matched_icd, len(result.medications),
            len(result.procedures), result.duration_days,
            result.confidence * 100
        )
        return result

    # ── ICD-10 Kodu ────────────────────────────────────────────────────────
    def _extract_icd_codes(self, text: str) -> list:
        """
        ICD-10 kodunu birden fazla formatda yakalar:
          J18.9  J18  I21.9  S32.0  E11  M51.1
        """
        pattern = r'\b([A-Z]\d{2}(?:\.\d{1,2})?)\b'
        codes = re.findall(pattern, text)
        # Tekrarları kaldır, sırayı koru
        seen = set()
        return [c for c in codes if not (c in seen or seen.add(c))]

    # ── İlaç Tespiti ───────────────────────────────────────────────────────
    def _extract_medications(self, text_lower: str) -> list:
        found = []
        for med in self._lower_med_map:
            if re.search(r'\b' + re.escape(med) + r'\b', text_lower):
                found.append(self._lower_med_map[med])
        return found

    # ── Prosedür Tespiti ───────────────────────────────────────────────────
    def _extract_procedures(self, text_lower: str) -> list:
        found = []
        for proc in self._lower_proc_map:
            if re.search(r'\b' + re.escape(proc) + r'\b', text_lower):
                found.append(self._lower_proc_map[proc])
        return found

    # ── Süre Çıkarımı ──────────────────────────────────────────────────────
    def _extract_duration(self, text_lower: str) -> Optional[int]:
        """
        Çeşitli formatları yakalar:
          "15 gün", "yatış süresi: 8 gün", "12 günlük", "toplam 20 gün"
        """
        patterns = [
            r'(?:yatış\s*(?:süresi)?[:\s]*|toplam\s+|süre[:\s]*)(\d+)\s*gün',
            r'(\d+)\s*günlük\s*(?:yatış|tedavi|hospitalizasyon)',
            r'(\d+)\s*gün\s*(?:yatış|tedavi|hospitalizasyon|süreyle)',
            r'hospitalizasyon\s*süresi[:\s]*(\d+)\s*gün',
            r'(\d+)\s*gün\s+(?:hastanede|klinikte|serviste)',
        ]
        for p in patterns:
            m = re.search(p, text_lower)
            if m:
                return int(m.group(1))

        # Giriş-çıkış tarihlerinden hesapla
        return None

    # ── Yaş Çıkarımı ───────────────────────────────────────────────────────
    def _extract_age(self, text_lower: str) -> Optional[int]:
        patterns = [
            r'(\d{1,3})\s*(?:yaş(?:ında)?|y/o|yo\b)',
            r'yaş[ı]?\s*[:\s]*(\d{1,3})',
            r'(\d{1,3})\s*yaşında\b',
        ]
        for p in patterns:
            m = re.search(p, text_lower)
            if m:
                age = int(m.group(1))
                if 0 < age < 120:
                    return age
        return None

    # ── İsim Çıkarımı ──────────────────────────────────────────────────────
    def _extract_patient_name(self, text: str) -> Optional[str]:
        patterns = [
            r'(?:Hasta\s*(?:Adı|Ad[ıi])[:\s]+)([A-ZÇĞİÖŞÜ][a-zçğışöüA-ZÇĞİÖŞÜ]+(?:\s+[A-ZÇĞİÖŞÜ][a-zçğışöüA-ZÇĞİÖŞÜ]+)+)',
            r'(?:Ad\s*Soyad[ı]?[:\s]+)([A-ZÇĞİÖŞÜ][a-zçğışöüA-ZÇĞİÖŞÜ]+(?:\s+[A-ZÇĞİÖŞÜ][a-zçğışöüA-ZÇĞİÖŞÜ]+)+)',
            r'(?:Sayın|Bay|Bayan)\s+([A-ZÇĞİÖŞÜ][a-zçğışöüA-ZÇĞİÖŞÜ]+(?:\s+[A-ZÇĞİÖŞÜ][a-zçğışöüA-ZÇĞİÖŞÜ]+)+)',
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                return m.group(1).strip()
        return None

    # ── Tarih Çıkarımı ─────────────────────────────────────────────────────
    def _extract_dates(self, text: str):
        """Giriş ve çıkış tarihlerini çıkarır."""
        date_pattern = r'(\d{1,2})[./\-](\d{1,2})[./\-](\d{2,4})'

        admission_patterns = [
            r'(?:yatış|kabul|giriş|başvuru|admisyon)\s*(?:tarihi?)?[:\s]*' + date_pattern,
            r'(?:yatış|kabul|giriş)\s*[:\s]*' + date_pattern,
        ]
        discharge_patterns = [
            r'(?:taburcu|çıkış|discharge)\s*(?:tarihi?)?[:\s]*' + date_pattern,
            r'(?:taburcu|çıkış)\s*[:\s]*' + date_pattern,
        ]

        admission_date = None
        discharge_date = None

        for p in admission_patterns:
            m = re.search(p, text.lower())
            if m:
                groups = m.groups()[-3:]  # son 3 grup = gün, ay, yıl
                admission_date = f"{groups[0].zfill(2)}.{groups[1].zfill(2)}.{groups[2]}"
                break

        for p in discharge_patterns:
            m = re.search(p, text.lower())
            if m:
                groups = m.groups()[-3:]
                discharge_date = f"{groups[0].zfill(2)}.{groups[1].zfill(2)}.{groups[2]}"
                break

        return admission_date, discharge_date

    # ── Teşhis Eşleme ──────────────────────────────────────────────────────
    def _match_diagnosis(self, text_lower: str):
        """
        Uzundan kısaya doğru eşleme yapar
        (önce "toplum kökenli pnömoni" dene, sonra "pnömoni")
        """
        sorted_keys = sorted(DIAGNOSIS_MAP.keys(), key=len, reverse=True)
        for term in sorted_keys:
            if term in text_lower:
                return term.title(), DIAGNOSIS_MAP[term]
        return "", None

    # ── Güven Skoru ────────────────────────────────────────────────────────
    def _calc_confidence(self, r: ExtractedClinicalData) -> float:
        score = 0.0
        if r.matched_icd:      score += 0.35
        if r.icd_codes:        score += 0.15
        if r.medications:      score += 0.25
        if r.procedures:       score += 0.15
        if r.duration_days:    score += 0.10
        return min(score, 1.0)

    # ── Uyarı Üretimi ──────────────────────────────────────────────────────
    def _generate_warnings(self, r: ExtractedClinicalData) -> list:
        w = []
        if not r.matched_icd and not r.icd_codes:
            w.append("ICD-10 kodu tespit edilemedi. Lütfen belgede teşhis bilgisi olduğundan emin olun.")
        if not r.medications:
            w.append("İlaç bilgisi tespit edilemedi.")
        if not r.duration_days:
            w.append("Yatış süresi tespit edilemedi. Tarih bilgisi mevcut değil.")
        if r.confidence < 0.4:
            w.append("Çıkarım güven skoru düşük. Belge formatını kontrol edin.")
        return w
