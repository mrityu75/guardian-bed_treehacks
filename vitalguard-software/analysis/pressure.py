"""
Pressure Zone Risk Scoring
============================
Analyzes 12 FSR pressure sensors to compute per-zone and overall
pressure ulcer risk scores. Accounts for:
- Current pressure intensity
- Duration under sustained pressure
- Patient-specific risk multipliers (elderly, diabetic)
- Body region vulnerability weighting
"""

from config.settings import (
    FSR_ZONES,
    FSR_ADC_MAX,
    PRESSURE_RISK_THRESHOLD,
    SACRAL_WEIGHT_MULTIPLIER,
)


# Body region vulnerability weights (some areas ulcerate faster)
ZONE_VULNERABILITY = {
    "head": 0.6,
    "left_shoulder": 0.8,
    "right_shoulder": 0.8,
    "upper_back_left": 0.7,
    "upper_back_right": 0.7,
    "mid_back_left": 0.7,
    "mid_back_right": 0.7,
    "sacrum_left": 1.0,    # Highest risk area
    "sacrum_right": 1.0,
    "left_thigh": 0.6,
    "right_thigh": 0.6,
    "heels": 0.9,          # Second highest risk
}


def normalize_fsr(adc_value: int) -> float:
    """Convert raw ADC value (0-4095) to normalized pressure (0-1)."""
    return max(0.0, min(1.0, adc_value / FSR_ADC_MAX))


def compute_zone_scores(
    fsr_values: list,
    duration_min: float,
    pressure_multiplier: float = 1.0,
) -> dict:
    """
    Compute risk score for each of the 12 pressure zones.

    Risk formula per zone:
        risk = pressure_normalized * vulnerability * time_factor * patient_multiplier

    Time factor increases with duration (logarithmic growth):
        time_factor = 1 + ln(1 + duration_min / 30)

    Args:
        fsr_values: List of 12 raw ADC values from FSR sensors
        duration_min: Minutes in current position
        pressure_multiplier: Patient-specific multiplier (elderly/diabetic)

    Returns:
        dict mapping zone_name -> {pressure, risk, level}
    """
    import math

    if len(fsr_values) != 12:
        raise ValueError(f"Expected 12 FSR values, got {len(fsr_values)}")

    # Time factor: increases with duration, flattens after ~120 min
    time_factor = 1.0 + math.log(1 + duration_min / 30)

    zones = {}
    for idx, adc_val in enumerate(fsr_values):
        zone_name = FSR_ZONES.get(idx, f"zone_{idx}")
        pressure = normalize_fsr(adc_val)
        vulnerability = ZONE_VULNERABILITY.get(zone_name, 0.7)

        # Sacrum gets extra weighting
        if "sacrum" in zone_name:
            vulnerability *= SACRAL_WEIGHT_MULTIPLIER

        # Compute risk (0-1 scale, can exceed 1 for very high risk)
        risk = pressure * vulnerability * time_factor * pressure_multiplier
        risk = min(1.0, risk)  # Cap at 1.0

        # Classify level
        if risk < 0.3:
            level = "low"
        elif risk < 0.5:
            level = "moderate"
        elif risk < PRESSURE_RISK_THRESHOLD:
            level = "elevated"
        else:
            level = "high"

        zones[zone_name] = {
            "pressure": round(pressure, 4),
            "risk": round(risk, 4),
            "level": level,
            "adc_raw": adc_val,
        }

    return zones


def compute_overall_pressure_risk(zone_scores: dict) -> dict:
    """
    Compute a single overall pressure risk score from all zones.

    Uses weighted average of top-3 highest risk zones (worst case focus).

    Args:
        zone_scores: Output from compute_zone_scores()

    Returns:
        dict with overall_risk (0-1), worst_zone, high_risk_zones list
    """
    risks = [(name, data["risk"]) for name, data in zone_scores.items()]
    risks.sort(key=lambda x: x[1], reverse=True)

    # Weighted average of top 3
    top3 = risks[:3]
    weights = [0.5, 0.3, 0.2]
    overall = sum(r * w for (_, r), w in zip(top3, weights))

    # Identify high-risk zones
    high_risk = [name for name, data in zone_scores.items()
                 if data["level"] == "high"]

    return {
        "overall_risk": round(overall, 4),
        "worst_zone": top3[0][0] if top3 else "none",
        "worst_zone_risk": round(top3[0][1], 4) if top3 else 0.0,
        "high_risk_zones": high_risk,
        "high_risk_count": len(high_risk),
        "level": (
            "critical" if overall >= 0.8 else
            "high" if overall >= PRESSURE_RISK_THRESHOLD else
            "elevated" if overall >= 0.5 else
            "moderate" if overall >= 0.3 else
            "low"
        ),
    }


def analyze_pressure(
    bed_frame: dict,
    duration_min: float,
    pressure_multiplier: float = 1.0,
) -> dict:
    """
    Full pressure analysis from a bed module frame.

    Args:
        bed_frame: Bed module JSON with 'fsrs' array
        duration_min: Minutes in current position
        pressure_multiplier: From patient profile

    Returns:
        dict with zone_scores and overall assessment
    """
    fsr_values = bed_frame.get("fsrs", [0] * 12)
    zones = compute_zone_scores(fsr_values, duration_min, pressure_multiplier)
    overall = compute_overall_pressure_risk(zones)

    return {
        "zones": zones,
        "overall": overall,
        "duration_min": round(duration_min, 1),
    }