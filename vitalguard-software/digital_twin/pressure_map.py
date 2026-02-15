"""
Pressure Map
==============
Computes real-time pressure distribution across the patient's body
for digital twin visualization. Maps 12 FSR zones to body regions
and generates heatmap data.
"""

from analysis.pressure import compute_zone_scores, normalize_fsr
from config.settings import FSR_ZONES


# 2D body map coordinates for each zone (normalized 0-1, for overlay rendering)
# (x, y) where (0,0) = top-left of body outline
ZONE_BODY_COORDS = {
    "head":              (0.50, 0.05),
    "left_shoulder":     (0.30, 0.18),
    "right_shoulder":    (0.70, 0.18),
    "upper_back_left":   (0.38, 0.28),
    "upper_back_right":  (0.62, 0.28),
    "mid_back_left":     (0.40, 0.40),
    "mid_back_right":    (0.60, 0.40),
    "sacrum_left":       (0.43, 0.55),
    "sacrum_right":      (0.57, 0.55),
    "left_thigh":        (0.38, 0.70),
    "right_thigh":       (0.62, 0.70),
    "heels":             (0.50, 0.95),
}


def compute_pressure_map(
    fsr_values: list,
    duration_min: float,
    pressure_multiplier: float = 1.0,
) -> dict:
    """
    Compute full pressure map with zone scores and 2D coordinates.
    Ready for digital twin visualization.

    Args:
        fsr_values: 12 raw FSR ADC values
        duration_min: Minutes in current position
        pressure_multiplier: Patient-specific multiplier

    Returns:
        dict with zones (scores + coordinates), summary stats
    """
    zone_scores = compute_zone_scores(fsr_values, duration_min, pressure_multiplier)

    # Enrich with body coordinates
    pressure_map = {}
    total_pressure = 0
    max_pressure = 0
    max_zone = ""

    for zone_name, data in zone_scores.items():
        coords = ZONE_BODY_COORDS.get(zone_name, (0.5, 0.5))
        pressure_map[zone_name] = {
            **data,
            "body_x": coords[0],
            "body_y": coords[1],
        }
        total_pressure += data["pressure"]
        if data["pressure"] > max_pressure:
            max_pressure = data["pressure"]
            max_zone = zone_name

    return {
        "zones": pressure_map,
        "summary": {
            "avg_pressure": round(total_pressure / max(len(zone_scores), 1), 4),
            "max_pressure": round(max_pressure, 4),
            "max_zone": max_zone,
            "duration_min": round(duration_min, 1),
        },
    }