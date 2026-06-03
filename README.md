# 🏥 MalpraktisDSS — Tıbbi Malpraktis Tespit Sistemi

> **Kural Tabanlı Yapay Zeka Destekli Tıbbi Karar Destek Sistemi**

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![Django](https://img.shields.io/badge/Django-4.2-green?logo=django)
![DRF](https://img.shields.io/badge/DRF-3.15-red)
![SQLite](https://img.shields.io/badge/DB-SQLite-lightgrey?logo=sqlite)

---

## 📌 Proje Hakkında

Bu sistem, hastanelerde uygulanan tedavilerin **ICD-10 standart protokollerine** uygunluğunu otomatik olarak analiz eden bir karar destek sistemidir.

### 🎯 Temel Özellikler

| Özellik | Açıklama |
|---------|----------|
| **Kural Motoru** | Tedaviyi standart protokolle karşılaştırır |
| **NLP Belge Analizi** | Epikriz metninden ICD-10, ilaç, prosedür çıkarır |
| **Sapma Tespiti** | %20+ protokol sapmasını malpraktis olarak işaretler |
| **Risk Skorlama** | NONE / LOW / MODERATE / HIGH / CONFIRMED seviyeleri |
| **REST API** | 20+ endpoint, DRF ile dokümante |
| **Dashboard** | Canlı analiz arayüzü |

---

## 🏗 Sistem Mimarisi

```
Kullanıcı
  │
  ├─► Epikriz Metni  →  NLP Servisi  →  ICD-10 + İlaç + Prosedür
  │                                              │
  └─► Yatış Verisi   →  Kural Motoru →  DeviationLog + MalpracticeAssessment
                               │
                    ICD10Code ─┤
                    Protocol  ─┘
```

### 📂 Klasör Yapısı

```
medical_malpractice_dss/
├── backend/
│   ├── apps/
│   │   ├── accounts/       # Kullanıcı yönetimi
│   │   ├── icd10/          # ICD-10 kodları & protokoller
│   │   ├── patients/       # Hasta & yatış kayıtları
│   │   ├── treatments/     # İlaç & prosedür kayıtları
│   │   └── analysis/       # Kural motoru, NLP, değerlendirme
│   │       ├── services.py     # RuleEngineService
│   │       └── nlp_service.py  # ClinicalNLPService
│   └── config/             # Django ayarları
├── scripts/
│   └── seed_data.py        # Gerçekçi test verisi
├── dashboard.html          # Ana arayüz
└── requirements.txt
```

---

## 🚀 Kurulum

### Gereksinimler
- Python 3.12+
- Git

### Adımlar

```bash
# 1. Repoyu klonla
git clone https://github.com/KULLANICI_ADI/medical-malpractice-dss.git
cd medical-malpractice-dss

# 2. Sanal ortam oluştur
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Bağımlılıkları yükle
pip install -r requirements.txt

# 4. Veritabanını oluştur
python backend/manage.py migrate

# 5. Test verisi yükle
python scripts/seed_data.py

# 6. Sunucuyu başlat
python backend/manage.py runserver
```

### 🌐 Erişim

| Adres | Açıklama |
|-------|----------|
| `http://127.0.0.1:8000/` | Dashboard |
| `http://127.0.0.1:8000/admin/` | Admin Panel (`admin` / `Admin1234!`) |
| `http://127.0.0.1:8000/api/v1/` | REST API |

---

## 🔬 NLP Belge Analizi

Epikriz metnini `POST /api/v1/analysis/analyze-document/` endpoint'ine gönderin:

```json
{
  "text": "Hasta: Ali Veli. Teşhis: Pnömoni (J18.9). Yatış süresi: 8 gün. İlaçlar: amoksisilin-klavulanat, azitromisin.",
  "run_rule_engine": true
}
```

**Yanıt:**
```json
{
  "extracted": {
    "matched_icd": "J18.9",
    "diagnosis_text": "Pnömoni",
    "medications": ["amoksisilin-klavulanat", "azitromisin"],
    "duration_days": 8
  },
  "confidence": 90.0,
  "confidence_label": "Yüksek"
}
```

---

## ⚙️ Kural Motoru Kuralları

| Kural ID | Açıklama | Eşik |
|----------|----------|------|
| `RULE_TIMING_001` | Yatış süresi sapması | >%20 |
| `RULE_MED_002` | Eksik protokol ilacı | Herhangi biri |
| `RULE_MED_003` | Protokol dışı ilaç | >%0 |
| `RULE_PROC_001` | Eksik protokol adımı | <%80 tamamlama |

---

## 📊 Test Veritabanı

`seed_data.py` ile 6 hasta senaryosu yüklenir:

| Hasta | Teşhis | Senaryo | Beklenen Risk |
|-------|--------|---------|---------------|
| Fatma Arslan | J18.9 Pnömoni | Protokole uyumlu | NONE |
| Kemal Şahin | J18.9 Pnömoni | Hafif sapma | MODERATE |
| Zeynep Çelik | M51.1 Disk Hernisi | Hafif sapma | MODERATE |
| Hasan Koç | S32.0 Lomber Kırık | 210 gün + gereksiz ameliyat | CONFIRMED |
| Sercan Bulut | J18.9 Pnömoni | Yanlış AB + 30 gün | CONFIRMED |
| Mustafa Erdoğan | I21.9 STEMI | 360 dk gecikme + eksik ilaç | HIGH |

---

## 🛠 Teknoloji Yığını

- **Backend:** Django 4.2, Django REST Framework
- **Veritabanı:** SQLite (geliştirme) / PostgreSQL (üretim)
- **NLP:** Regex tabanlı hibrit kural motoru (spaCy opsiyonel)
- **Veri Analizi:** Pandas, NumPy
- **Frontend:** Vanilla HTML/CSS/JS (dependency-free)

---

## 📄 Lisans

MIT License — Akademik ve eğitim amaçlı kullanıma açıktır.
