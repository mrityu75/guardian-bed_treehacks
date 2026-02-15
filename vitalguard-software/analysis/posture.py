"""
Posture Classification
=======================
Classifies patient posture from MPU6050 accelerometer data.
Uses gravity vector orientation to determine body position.

Postures:
- supine: lying face up (gravity on -Y)
- prone: lying face down (gravity on +Y)
- left_lateral: lying on left side (gravity on +X)
- right_lateral: lying on right side (gravity on -X)
- unknown: cannot determine
"""

import math
from typing import Tuple


# Gravity vector signatures for each posture (normalized)
# These represent the dominant axis where gravity pulls
POSTURE_SIGNATURES = {
    "supine":        (0.0, -1.0, 0.0),
    "prone":         (0.0,  1.0, 0.0),
    "left_lateral":  (1.0,  0.0, 0.0),
    "right_lateral": (-1.0, 0.0, 0.0),
}

# Minimum confidence to classify (cosine similarity threshold)
CONFIDENCE_THRESHOLD = 0.6


def _normalize(x: float, y: float, z: float) -> Tuple[float, float, float]:
    """Normalize a 3D vector to unit length."""
    mag = math.sqrt(x**2 + y**2 + z**2)
    if mag < 0.001:
        return (0.0, 0.0, 0.0)
    return (x / mag, y / mag, z / mag)


def _cosine_similarity(a: Tuple, b: Tuple) -> float:
    """Compute cosine similarity between two 3D vectors."""
    dot = sum(ai * bi for ai, bi in zip(a, b))
    return dot  # Already normalized, so this IS the cosine similarity


def classify_posture(accel_x: float, accel_y: float, accel_z: float) -> dict:
    """
    Classify patient posture from a single accelerometer reading.

    The accelerometer measures gravity + movement. We strip out the
    gravity component (subtract ~9.81 from z) to get the orientation.

    Args:
        accel_x: X-axis acceleration (m/s^2)
        accel_y: Y-axis acceleration (m/s^2)
        accel_z: Z-axis acceleration (m/s^2)

    Returns:
        dict with 'posture', 'confidence', and 'scores' for each posture
    """
    # Remove gravity bias from Z (sensor mounted with Z pointing up)
    gravity_removed_z = accel_z - 9.81
    normalized = _normalize(accel_x, accel_y, gravity_removed_z)

    scores = {}
    for posture, sig in POSTURE_SIGNATURES.items():
        scores[posture] = round(_cosine_similarity(normalized, sig), 4)

    # Best match
    best_posture = max(scores, key=scores.get)
    best_score = scores[best_posture]

    if best_score < CONFIDENCE_THRESHOLD:
        best_posture = "unknown"

    return {
        "posture": best_posture,
        "confidence": round(best_score, 4),
        "scores": scores,
    }


def classify_from_frame(bed_frame: dict) -> dict:
    """
    Classify posture from a bed module data frame.
    Uses mpu1 (center of mattress) as primary sensor.

    Args:
        bed_frame: Bed module JSON frame with mpu1.accel data
    """
    accel = bed_frame.get("mpu1", {}).get("accel", {})
    x = accel.get("x", 0.0)
    y = accel.get("y", 0.0)
    z = accel.get("z", 9.81)
    return classify_posture(x, y, z)


def detect_posture_change(
    current: str,
    previous: str,
    current_confidence: float,
    min_confidence: float = 0.65,
) -> dict:
    """
    Detect if a posture change has occurred.

    Args:
        current: Current classified posture
        previous: Previous classified posture
        current_confidence: Confidence of current classification
        min_confidence: Minimum confidence to confirm a change

    Returns:
        dict with 'changed', 'from', 'to', 'confidence'
    """
    changed = (
        current != previous
        and current != "unknown"
        and current_confidence >= min_confidence
    )

    return {
        "changed": changed,
        "from_posture": previous,
        "to_posture": current if changed else previous,
        "confidence": current_confidence,
    }