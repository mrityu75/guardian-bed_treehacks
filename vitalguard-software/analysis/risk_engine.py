"""
Integrated Risk Engine
========================
Combines all analysis modules into a single patient risk assessment.
Produces a 0-100 risk score with personalized threshold adjustments.

Risk = weighted combination of:
  - Vitals score (30%)
  - Pressure score (30%)
  - Repositioning score (20%)
  - Movement score (10%)
  - Sound score (10%)
"""

from config.settings import RISK_WEIGHTS, ALERT_LEVELS
from config.patient_profiles import PatientProfile, RiskCategory
from analysis.posture import classify_from_frame
from analysis.pressure import analyze_pressure
from analysis.vitals import VitalSignsAnalyzer
from analysis.repositioning import RepositioningTracker
from analysis.sound import SoundAnalyzer


class RiskEngine:
    """
    Per-patient risk assessment engine.
    Maintains state across readings for trend and history analysis.
    """

    def __init__(self, patient: PatientProfile):
        """
        Args:
            patient: Patient profile with personalized thresholds
        """
        self.patient = patient
        self.vitals_analyzer = VitalSignsAnalyzer(window_size=120)
        self.reposition_tracker = RepositioningTracker(
            interval_min=patient.reposition_interval_min
        )
        self.sound_analyzer = SoundAnalyzer(window_size=30)
        self.risk_history = []
        self.all_alerts = []

    def _vitals_to_score(self, vitals_result: dict) -> float:
        """Convert vitals analysis to 0-100 sub-score."""
        level = vitals_result.get("overall_level", "normal")
        base = {"normal": 5, "caution": 45, "critical": 85}.get(level, 5)

        # Add points for each alert
        alert_count = len(vitals_result.get("alerts", []))
        return min(100, base + alert_count * 10)

    def _pressure_to_score(self, pressure_result: dict) -> float:
        """Convert pressure analysis to 0-100 sub-score."""
        overall_risk = pressure_result.get("overall", {}).get("overall_risk", 0)
        return min(100, overall_risk * 100)

    def _reposition_to_score(self, reposition_result: dict) -> float:
        """Convert repositioning status to 0-100 sub-score."""
        status = reposition_result.get("status", "ok")
        remaining = reposition_result.get("remaining_min", 90)
        interval = reposition_result.get("interval_min", 90)

        if status == "overdue":
            # How far overdue? More overdue = higher risk
            overdue_min = reposition_result.get("duration_min", 0) - interval
            return min(100, 70 + overdue_min * 0.5)
        elif status == "warning":
            return 30 + (1 - remaining / interval) * 40
        else:
            return max(0, 10 * (1 - remaining / interval))

    def _movement_to_score(self, movement_level: float) -> float:
        """Convert movement level (0-1) to risk score (less movement = higher risk)."""
        return min(100, max(0, (1 - movement_level) * 80))

    def _sound_to_score(self, sound_result: dict) -> float:
        """Convert sound analysis to 0-100 sub-score."""
        cls = sound_result.get("classification", "normal")
        base = {
            "normal": 0,
            "silence": 15,
            "vocalization": 20,
            "elevated_ambient": 10,
            "distress": 70,
        }.get(cls, 0)

        # Accumulate for repeated distress
        distress_count = sound_result.get("distress_count", 0)
        return min(100, base + distress_count * 5)

    def assess(self, frame: dict) -> dict:
        """
        Run full risk assessment on a combined data frame.

        Args:
            frame: Combined frame from generator with bed, hand, vitals_snapshot

        Returns:
            Complete risk assessment with score (0-100), level, sub-scores, alerts
        """
        bed = frame.get("bed", {})
        vitals = frame.get("vitals_snapshot", {})
        elapsed_min = frame.get("elapsed_min", 0)

        # --- Sub-analyses ---
        # 1. Posture
        posture_result = classify_from_frame(bed)
        current_posture = posture_result["posture"]

        # 2. Vitals
        vitals_result = self.vitals_analyzer.analyze_all(vitals)

        # 3. Pressure
        pressure_result = analyze_pressure(
            bed,
            duration_min=vitals.get("posture_duration_min", 0),
            pressure_multiplier=self.patient.pressure_multiplier,
        )

        # 4. Repositioning
        reposition_result = self.reposition_tracker.update(
            current_posture, elapsed_min
        )

        # 5. Sound
        sound_result = self.sound_analyzer.analyze(bed.get("microphones", []))

        # 6. Movement
        movement_level = vitals.get("movement_level", 0.3)

        # --- Compute sub-scores ---
        scores = {
            "vitals": self._vitals_to_score(vitals_result),
            "pressure": self._pressure_to_score(pressure_result),
            "repositioning": self._reposition_to_score(reposition_result),
            "movement": self._movement_to_score(movement_level),
            "sound": self._sound_to_score(sound_result),
        }

        # --- Weighted total ---
        total_score = sum(
            scores[k] * RISK_WEIGHTS[k] for k in RISK_WEIGHTS
        )
        total_score = round(min(100, max(0, total_score)), 1)

        # --- Classify risk level ---
        if total_score >= ALERT_LEVELS["critical"]["risk_min"]:
            risk_level = "critical"
            risk_category = RiskCategory.CRITICAL
        elif total_score >= ALERT_LEVELS["warning"]["risk_min"]:
            risk_level = "warning"
            risk_category = RiskCategory.HIGH
        elif total_score >= ALERT_LEVELS["caution"]["risk_min"]:
            risk_level = "caution"
            risk_category = RiskCategory.MODERATE
        else:
            risk_level = "info"
            risk_category = RiskCategory.LOW

        # Update patient risk category
        self.patient.current_risk_category = risk_category

        # --- Collect all alerts ---
        alerts = []
        alerts.extend(vitals_result.get("alerts", []))
        alerts.extend(reposition_result.get("alerts", []))
        alerts.extend(sound_result.get("alerts", []))
        alerts.extend(pressure_result.get("overall", {}).get("high_risk_zones", []))

        # Store in history
        result = {
            "patient_id": self.patient.patient_id,
            "patient_name": self.patient.name,
            "timestamp_ms": frame.get("timestamp_ms", 0),
            "elapsed_min": elapsed_min,
            "risk_score": total_score,
            "risk_level": risk_level,
            "sub_scores": scores,
            "posture": {
                "current": current_posture,
                "confidence": posture_result["confidence"],
                "duration_min": vitals.get("posture_duration_min", 0),
            },
            "vitals_analysis": vitals_result,
            "pressure_analysis": {
                "overall": pressure_result["overall"],
                # Omit per-zone detail for brevity; available if needed
            },
            "repositioning": reposition_result,
            "sound": sound_result,
            "movement_level": movement_level,
            "alerts": alerts,
            "patient_profile": {
                "age": self.patient.age,
                "bmi": self.patient.bmi,
                "is_elderly": self.patient.is_elderly,
                "is_diabetic": self.patient.is_diabetic,
                "pressure_multiplier": self.patient.pressure_multiplier,
            },
        }

        self.risk_history.append({
            "elapsed_min": elapsed_min,
            "risk_score": total_score,
            "risk_level": risk_level,
        })
        self.all_alerts.extend(alerts)

        return result

    def get_risk_summary(self) -> dict:
        """Get summary statistics of risk over time."""
        if not self.risk_history:
            return {"avg_risk": 0, "max_risk": 0, "current_risk": 0}

        scores = [r["risk_score"] for r in self.risk_history]
        return {
            "avg_risk": round(sum(scores) / len(scores), 1),
            "max_risk": round(max(scores), 1),
            "min_risk": round(min(scores), 1),
            "current_risk": scores[-1],
            "readings": len(scores),
            "total_alerts": len(self.all_alerts),
            "unique_alerts": len(set(self.all_alerts)),
        }