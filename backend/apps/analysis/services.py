"""
analysis/services.py
--------------------
Kural Tabanlı Karar Destek Motoru (Rule Engine)

Mimari:
  ┌─────────────────────────────────────────────────────────┐
  │  RuleEngineService                                       │
  │   ├── analyze_admission(admission_id)  ← Ana giriş      │
  │   ├── _check_length_of_stay()          ← Zaman kuralı   │
  │   ├── _check_medications()             ← İlaç kuralı    │
  │   ├── _check_procedures()              ← Prosedür kuralı│
  │   ├── _calculate_compliance_score()    ← NumPy skoru    │
  │   └── _persist_results()              ← DB'ye yaz       │
  └─────────────────────────────────────────────────────────┘

Bağımlılıklar:
  pip install pandas numpy django

Kullanım:
  from apps.analysis.services import RuleEngineService
  result = RuleEngineService().analyze_admission(admission_id=42)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
from django.db import transaction
from django.utils import timezone

from apps.analysis.models import DeviationLog, MalpracticeAssessment
from apps.patients.models import Admission
from apps.treatments.models import AppliedProtocol, MedicationRecord, ClinicalProcedure

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Kural motoru sabitleri
# ---------------------------------------------------------------------------
# Zaman sapması için eşik değerler
TIMING_DEVIATION_WARN_PCT: float = 0.20     # %20 sapma → UYARI
TIMING_DEVIATION_CRITICAL_PCT: float = 0.50 # %50 sapma → KRİTİK

# Protokol dışı ilaç → otomatik CRITICAL
UNAUTHORIZED_MEDICATION_SEVERITY = DeviationLog.Severity.CRITICAL

# Risk eşikleri (uyum skoru 0–100)
RISK_THRESHOLDS = {
    "NONE":      (80, 101),   # %80 ve üzeri → Risk Yok
    "LOW":       (60, 80),    # %60–80 → Düşük Risk
    "MODERATE":  (40, 60),    # %40–60 → Orta Risk
    "HIGH":      (20, 40),    # %20–40 → Yüksek Risk
    "CONFIRMED": (0,  20),    # %0–20  → Malpraktis Tespit
}


# ---------------------------------------------------------------------------
# Veri transfer nesnesi: tek bir kural çalışmasının sonucu
# ---------------------------------------------------------------------------
@dataclass
class RuleResult:
    """Bir kuralın çıktısını taşıyan immutable benzeri veri nesnesi."""
    rule_id: str
    deviation_type: str                            # DeviationLog.DeviationType
    severity: str                                  # DeviationLog.Severity
    description: str
    raw_data: dict = field(default_factory=dict)   # İzlenebilirlik için ham veri
    weight: float = 1.0                            # Uyum skoru hesabında ağırlık


@dataclass
class AnalysisResult:
    """analyze_admission() metodunun dönüş tipi."""
    admission_id: int
    risk_level: str
    overall_compliance_score: float
    rule_results: list[RuleResult] = field(default_factory=list)
    deviation_log_ids: list[int] = field(default_factory=list)
    assessment_id: Optional[int] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Ana Servis Sınıfı
# ---------------------------------------------------------------------------
class RuleEngineService:
    """
    Kural tabanlı karar destek motoru.

    Kullanım:
        svc = RuleEngineService()
        result: AnalysisResult = svc.analyze_admission(42)
        print(result.risk_level, result.overall_compliance_score)
    """

    def __init__(self, deviation_warn_pct: float = TIMING_DEVIATION_WARN_PCT,
                 deviation_critical_pct: float = TIMING_DEVIATION_CRITICAL_PCT):
        self.deviation_warn_pct = deviation_warn_pct
        self.deviation_critical_pct = deviation_critical_pct

    # -----------------------------------------------------------------------
    # Genel Giriş Noktası
    # -----------------------------------------------------------------------
    def analyze_admission(self, admission_id: int) -> AnalysisResult:
        """
        Belirtilen yatış için tüm kuralları çalıştırır, sonuçları
        DeviationLog ve MalpracticeAssessment olarak kaydeder.

        Hata oluşursa AnalysisResult.error alanı doldurulur; exception
        yukarıya iletilmez.
        """
        logger.info("Kural motoru başlatıldı → admission_id=%s", admission_id)
        try:
            admission = (
                Admission.objects
                .select_related(
                    'patient',
                    'primary_diagnosis',
                    'admitting_physician',
                )
                .prefetch_related(
                    'secondary_diagnoses',
                    'applied_protocols__protocol',
                    'medications',
                    'procedures',
                )
                .get(pk=admission_id)
            )
        except Admission.DoesNotExist:
            return AnalysisResult(
                admission_id=admission_id,
                risk_level="NONE",
                overall_compliance_score=100.0,
                error=f"Admission #{admission_id} bulunamadı."
            )

        # Uygulanan protokol yoksa analiz yapılamaz
        applied_protocols = list(admission.applied_protocols.all())
        if not applied_protocols:
            return AnalysisResult(
                admission_id=admission_id,
                risk_level="NONE",
                overall_compliance_score=100.0,
                error="Bu yatışa protokol atanmamış. Analiz yapılamadı."
            )

        all_results: list[RuleResult] = []

        # Her uygulanan protokol için kuralları çalıştır
        for ap in applied_protocols:
            protocol = ap.protocol
            all_results.extend(self._check_length_of_stay(admission, protocol))
            all_results.extend(self._check_medications(admission, protocol))
            all_results.extend(self._check_required_steps(admission, protocol, ap))

        # Uyum skoru hesapla (NumPy ağırlıklı ortalama)
        compliance_score = self._calculate_compliance_score(all_results)

        # Risk seviyesini belirle
        risk_level = self._determine_risk_level(compliance_score)

        # Veritabanına kaydet (atomik)
        deviation_ids, assessment_id = self._persist_results(
            admission=admission,
            applied_protocols=applied_protocols,
            rule_results=all_results,
            compliance_score=compliance_score,
            risk_level=risk_level,
        )

        logger.info(
            "Analiz tamamlandı → admission=%s | risk=%s | score=%.1f",
            admission_id, risk_level, compliance_score
        )
        return AnalysisResult(
            admission_id=admission_id,
            risk_level=risk_level,
            overall_compliance_score=compliance_score,
            rule_results=all_results,
            deviation_log_ids=deviation_ids,
            assessment_id=assessment_id,
        )

    # -----------------------------------------------------------------------
    # KURAL 1: Yatış Süresi Kontrolü
    # -----------------------------------------------------------------------
    def _check_length_of_stay(
        self, admission: Admission, protocol
    ) -> list[RuleResult]:
        """
        Gerçek yatış süresini protokolün beklenen süresiyle karşılaştırır.

        Formül:
            deviation_pct = |actual - expected_mid| / expected_mid

        expected_mid = (min + max) / 2  ← NumPy ile hesaplanır
        """
        results: list[RuleResult] = []

        if not admission.discharge_date:
            # Hâlâ yatan hasta — zaman analizi yapılamaz
            return results

        actual_days: int = admission.length_of_stay  # model property
        expected_min = protocol.min_recovery_days
        expected_max = protocol.max_recovery_days

        # NumPy ile merkez ve standart sapma hesabı
        expected_range = np.array([expected_min, expected_max], dtype=float)
        expected_mid: float = float(np.mean(expected_range))
        expected_std: float = float(np.std(expected_range))

        # Sapma yüzdesi (simetrik)
        deviation_pct: float = abs(actual_days - expected_mid) / max(expected_mid, 1)

        raw = {
            "actual_days": actual_days,
            "expected_min": expected_min,
            "expected_max": expected_max,
            "expected_mid": round(expected_mid, 2),
            "expected_std": round(expected_std, 2),
            "deviation_pct": round(deviation_pct * 100, 2),
        }

        if deviation_pct > self.deviation_critical_pct:
            # %50+ sapma → KRİTİK
            results.append(RuleResult(
                rule_id="RULE_TIMING_001",
                deviation_type=DeviationLog.DeviationType.TIMING,
                severity=DeviationLog.Severity.CRITICAL,
                description=(
                    f"Yatış süresi kritik sapma: Gerçekleşen {actual_days} gün, "
                    f"beklenen ortalama {expected_mid:.0f} gün "
                    f"(sapma: %{deviation_pct*100:.1f}). "
                    f"Protokol: {protocol.name}"
                ),
                raw_data=raw,
                weight=3.0,   # Zaman sapması yüksek ağırlıklı
            ))
        elif deviation_pct > self.deviation_warn_pct:
            # %20–50 sapma → UYARI
            results.append(RuleResult(
                rule_id="RULE_TIMING_002",
                deviation_type=DeviationLog.DeviationType.TIMING,
                severity=DeviationLog.Severity.WARNING,
                description=(
                    f"Yatış süresi uyarı sapması: Gerçekleşen {actual_days} gün, "
                    f"beklenen {expected_min}–{expected_max} gün aralığı "
                    f"(sapma: %{deviation_pct*100:.1f})."
                ),
                raw_data=raw,
                weight=1.5,
            ))

        return results

    # -----------------------------------------------------------------------
    # KURAL 2: İlaç Uyumu Kontrolü
    # -----------------------------------------------------------------------
    def _check_medications(
        self, admission: Admission, protocol
    ) -> list[RuleResult]:
        """
        Uygulanan ilaçları protokolün birinci basamak ilaç listesiyle karşılaştırır.

        Pandas DataFrame kullanarak:
          a) Protokol ilaçlarından hangisi UYGULANMADı → eksik ilaç
          b) Protokol dışı ilaç uygulandı mı → yetkisiz ilaç
        """
        results: list[RuleResult] = []

        # Protokol ilaç listesini ayrıştır (virgülle ayrılmış)
        if not protocol.first_line_medications:
            return results

        protocol_meds: list[str] = [
            m.strip().lower()
            for m in protocol.first_line_medications.split(',')
            if m.strip()
        ]

        # Uygulanan ilaçları Pandas ile analiz et
        med_qs = admission.medications.filter(
            status=MedicationRecord.MedicationStatus.ADMINISTERED
        ).values('drug_name', 'dose', 'route', 'status')

        if not med_qs.exists():
            if protocol_meds:
                results.append(RuleResult(
                    rule_id="RULE_MED_001",
                    deviation_type=DeviationLog.DeviationType.MEDICATION,
                    severity=DeviationLog.Severity.CRITICAL,
                    description=(
                        f"Hiç ilaç uygulanmamış! Protokol şu ilaçları gerektiriyor: "
                        f"{', '.join(protocol_meds)}"
                    ),
                    raw_data={"expected_meds": protocol_meds, "actual_meds": []},
                    weight=2.5,
                ))
            return results

        df_meds = pd.DataFrame(list(med_qs))
        df_meds['drug_name_lower'] = df_meds['drug_name'].str.lower().str.strip()

        applied_meds: list[str] = df_meds['drug_name_lower'].tolist()

        # ── Eksik protokol ilaçları ──────────────────────────────────────
        missing_meds = [
            med for med in protocol_meds
            if not any(med in applied for applied in applied_meds)
        ]
        if missing_meds:
            results.append(RuleResult(
                rule_id="RULE_MED_002",
                deviation_type=DeviationLog.DeviationType.MEDICATION,
                severity=DeviationLog.Severity.WARNING,
                description=(
                    f"Protokol ilacı uygulanmamış: {', '.join(missing_meds)}. "
                    f"Protokol: {protocol.name}"
                ),
                raw_data={
                    "missing_medications": missing_meds,
                    "applied_medications": applied_meds,
                },
                weight=2.0,
            ))

        # ── Protokol dışı ilaçlar ────────────────────────────────────────
        unauthorized_meds = [
            med for med in applied_meds
            if not any(proto_med in med for proto_med in protocol_meds)
        ]
        if unauthorized_meds:
            # İlaç sayısını ve oranını NumPy ile hesapla
            total = len(applied_meds)
            unauthorized_ratio = float(np.round(len(unauthorized_meds) / max(total, 1), 3))

            results.append(RuleResult(
                rule_id="RULE_MED_003",
                deviation_type=DeviationLog.DeviationType.MEDICATION,
                severity=(
                    DeviationLog.Severity.CRITICAL
                    if unauthorized_ratio > 0.5
                    else DeviationLog.Severity.WARNING
                ),
                description=(
                    f"Protokol dışı ilaç uygulandı ({len(unauthorized_meds)}/{total}, "
                    f"%{unauthorized_ratio*100:.1f}): {', '.join(unauthorized_meds[:5])}"
                ),
                raw_data={
                    "unauthorized_medications": unauthorized_meds,
                    "unauthorized_ratio": unauthorized_ratio,
                },
                weight=2.5 if unauthorized_ratio > 0.5 else 1.5,
            ))

        return results

    # -----------------------------------------------------------------------
    # KURAL 3: Zorunlu Adım Kontrolü
    # -----------------------------------------------------------------------
    def _check_required_steps(
        self, admission: Admission, protocol, applied_protocol: AppliedProtocol
    ) -> list[RuleResult]:
        """
        Protokolün 'required_steps' JSON listesindeki zorunlu adımları
        uygulanan prosedürlerle karşılaştırır.

        required_steps format:
          [{"step": 1, "action": "Omurga MR", "mandatory": true}, ...]
        """
        results: list[RuleResult] = []

        required_steps: list[dict] = protocol.required_steps or []
        mandatory_steps = [s for s in required_steps if s.get('mandatory', False)]

        if not mandatory_steps:
            return results

        # Uygulanan prosedürleri Pandas ile analiz et
        proc_qs = admission.procedures.filter(
            status=ClinicalProcedure.ProcedureStatus.PERFORMED
        ).values('procedure_name')

        applied_procedures: list[str] = []
        if proc_qs.exists():
            df_procs = pd.DataFrame(list(proc_qs))
            applied_procedures = df_procs['procedure_name'].str.lower().str.strip().tolist()

        # Hangi zorunlu adımlar yapılmamış?
        missing_steps = []
        for step in mandatory_steps:
            action = step.get('action', '').lower()
            if not any(action in proc for proc in applied_procedures):
                missing_steps.append(step)

        if missing_steps:
            # Adım tamamlanma oranı
            completion_rate = float(np.round(
                1 - len(missing_steps) / len(mandatory_steps), 3
            ))
            results.append(RuleResult(
                rule_id="RULE_PROC_001",
                deviation_type=DeviationLog.DeviationType.PROTOCOL_SKIP,
                severity=(
                    DeviationLog.Severity.CRITICAL
                    if completion_rate < 0.5
                    else DeviationLog.Severity.WARNING
                ),
                description=(
                    f"Zorunlu protokol adımları tamamlanmadı "
                    f"(%{completion_rate*100:.0f} tamamlandı). "
                    f"Eksik adımlar: "
                    f"{', '.join(s.get('action','?') for s in missing_steps)}"
                ),
                raw_data={
                    "missing_steps": missing_steps,
                    "completion_rate": completion_rate,
                    "applied_procedures": applied_procedures,
                },
                weight=2.0,
            ))

        return results

    # -----------------------------------------------------------------------
    # Uyum Skoru Hesaplama (NumPy Ağırlıklı Ortalama)
    # -----------------------------------------------------------------------
    @staticmethod
    def _calculate_compliance_score(rule_results: list[RuleResult]) -> float:
        """
        100 üzerinden ağırlıklı uyum skoru hesaplar.

        Algoritma:
          - Her kural sonucu bir "ceza puanı" taşır:
              CRITICAL  → 100 puan * weight
              WARNING   → 50  puan * weight
              INFO      → 10  puan * weight
          - Toplam mümkün ceza = Σ(100 * weight)
          - Uyum skoru = 100 - (toplam ceza / mümkün ceza) * 100

        Sapma yoksa (rule_results boş) → 100 döner.
        """
        if not rule_results:
            return 100.0

        severity_penalty_map = {
            DeviationLog.Severity.CRITICAL: 100.0,
            DeviationLog.Severity.WARNING:  50.0,
            DeviationLog.Severity.INFO:     10.0,
        }

        weights = np.array([r.weight for r in rule_results], dtype=float)
        penalties = np.array(
            [severity_penalty_map.get(r.severity, 50.0) for r in rule_results],
            dtype=float
        )

        # Ağırlıklı toplam ceza
        total_penalty = float(np.dot(penalties, weights))
        # Mümkün maksimum ceza (tüm kurallar CRITICAL olsaydı)
        max_possible_penalty = float(np.dot(np.full_like(weights, 100.0), weights))

        raw_score = 100.0 - (total_penalty / max_possible_penalty) * 100.0
        return float(np.clip(np.round(raw_score, 2), 0.0, 100.0))

    # -----------------------------------------------------------------------
    # Risk Seviyesi Belirleme
    # -----------------------------------------------------------------------
    @staticmethod
    def _determine_risk_level(score: float) -> str:
        """
        Uyum skoruna göre MalpracticeAssessment.RiskLevel döner.
        Eşikler RISK_THRESHOLDS sabitinde tanımlıdır.
        """
        for level, (low, high) in RISK_THRESHOLDS.items():
            if low <= score < high:
                return level
        return "NONE"

    # -----------------------------------------------------------------------
    # Sonuçları DB'ye Kaydet (Atomik İşlem)
    # -----------------------------------------------------------------------
    @transaction.atomic
    def _persist_results(
        self,
        admission: Admission,
        applied_protocols: list,
        rule_results: list[RuleResult],
        compliance_score: float,
        risk_level: str,
    ) -> tuple[list[int], Optional[int]]:
        """
        Kural sonuçlarını DeviationLog olarak, özeti ise
        MalpracticeAssessment olarak kaydeder.

        Tüm işlem tek bir DB transaction'ında gerçekleşir.
        Hata olursa tamamen geri alınır.
        """
        deviation_ids: list[int] = []
        now = timezone.now()

        # Referans protokol (ilk uygulanan protokolü referans al)
        ref_protocol = applied_protocols[0].protocol if applied_protocols else None
        ref_applied = applied_protocols[0] if applied_protocols else None

        # Her kural sonucu için DeviationLog oluştur
        for result in rule_results:
            log = DeviationLog.objects.create(
                admission=admission,
                reference_protocol=ref_protocol,
                applied_protocol=ref_applied,
                deviation_type=result.deviation_type,
                severity=result.severity,
                description=result.description,
                triggered_rule_id=result.rule_id,
                rule_output_data=result.raw_data,
                review_status=DeviationLog.ReviewStatus.PENDING,
            )
            deviation_ids.append(log.pk)

        # MalpracticeAssessment oluştur ya da güncelle (OneToOne)
        assessment_summary = self._build_summary(rule_results, compliance_score, risk_level)

        assessment, created = MalpracticeAssessment.objects.update_or_create(
            admission=admission,
            defaults={
                "risk_level": risk_level,
                "overall_compliance_score": compliance_score,
                "automated_summary": assessment_summary,
                "assessed_at": now,
                "finalized": False,
            }
        )

        # İlişkili deviation logları M2M olarak bağla
        if deviation_ids:
            assessment.deviation_logs.add(*DeviationLog.objects.filter(pk__in=deviation_ids))

        # AppliedProtocol uyum skorunu güncelle
        for ap in applied_protocols:
            ap.compliance_score = compliance_score
            ap.compliance_calculated_at = now
            ap.save(update_fields=['compliance_score', 'compliance_calculated_at'])

        logger.info(
            "Kayıt tamamlandı → %d deviation_log, assessment_id=%s",
            len(deviation_ids), assessment.pk
        )
        return deviation_ids, assessment.pk

    @staticmethod
    def _build_summary(
        rule_results: list[RuleResult],
        compliance_score: float,
        risk_level: str,
    ) -> str:
        """Analiz sonucunun insan okunabilir özetini üretir."""
        if not rule_results:
            return (
                f"Analiz tamamlandı. Protokole uyum tam (%{compliance_score:.1f}). "
                "Herhangi bir sapma tespit edilmedi."
            )

        severity_counts = pd.Series(
            [r.severity for r in rule_results]
        ).value_counts().to_dict()

        lines = [
            f"Risk Seviyesi : {risk_level}",
            f"Uyum Skoru   : %{compliance_score:.1f}",
            f"Tespit Edilen Sapma Sayısı: {len(rule_results)}",
            f"  - KRİTİK : {severity_counts.get(DeviationLog.Severity.CRITICAL, 0)}",
            f"  - UYARI  : {severity_counts.get(DeviationLog.Severity.WARNING, 0)}",
            f"  - BİLGİ  : {severity_counts.get(DeviationLog.Severity.INFO, 0)}",
            "",
            "Sapma Detayları:",
        ]
        for i, r in enumerate(rule_results, 1):
            lines.append(f"  {i}. [{r.rule_id}] {r.description}")

        return "\n".join(lines)
