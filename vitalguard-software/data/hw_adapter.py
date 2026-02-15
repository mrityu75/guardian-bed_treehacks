"""
Hardware Data Adapter
=====================
Converts real hardware merged_data.json format into VitalGuard's internal frame format.

Real hardware sources:
- bed_esp1: 6 FSR pressures, 3 temps, 2 MPUs
- bed_esp2: 6 FSR pressures
- hand: temperature, accel, gyro, heart rate (MAX30102)
- radar: distance, moving, presence, stationary
- voice_latest: speech-to-text transcript

Maps 12 named pressure sensors to VitalGuard's 12-zone array.
"""

import math
import time

# ============================================
# PRESSURE SENSOR MAPPING
# ============================================
# Real hardware labels → VitalGuard zone index
# bed_esp1 has 6 sensors, bed_esp2 has 6 sensors = 12 total
PRESSURE_MAP = {
    # bed_esp1
    "head_left": 0,           # head
    "head_center": 0,         # head (averaged)
    "head_right": 0,          # head (averaged)
    "upper_back_left_shoulder": 1,   # left_shoulder
    "upper_back_right_shoulder": 2,  # right_shoulder
    "lower_back_left_hip": 7,        # sacrum_left / hip_L
    # bed_esp2
    "lower_back_right_hip": 8,       # sacrum_right / hip_R
    "upper_leg_left_thigh": 9,       # left_thigh
    "upper_leg_right_thigh": 10,     # right_thigh
    "lower_leg_left_calf": 9,        # map to thigh_L (closest)
    "lower_leg_right_calf": 10,      # map to thigh_R (closest)
    "lower_back_center_spine": 5,    # mid_back_left (spine center)
}

# VitalGuard zone names (index → name)
ZONE_NAMES = {
    0: "head", 1: "shoulder_L", 2: "shoulder_R",
    3: "upper_back", 4: "mid_back", 5: "lower_back",
    6: "sacrum", 7: "hip_L", 8: "hip_R",
    9: "thigh_L", 10: "thigh_R", 11: "heel",
}

# Dashboard pressure zone names for frontend
DASHBOARD_ZONES = [
    "head", "shoulder_L", "shoulder_R",
    "upper_back", "mid_back", "lower_back",
    "sacrum", "hip_L", "hip_R",
    "thigh_L", "thigh_R", "heel",
]


def convert_hardware_frame(hw_data: dict) -> dict:
    """
    Convert merged_data.json format to VitalGuard internal frame.

    Args:
        hw_data: Raw hardware data dict with bed_esp1, bed_esp2, hand, radar, voice_latest

    Returns:
        VitalGuard frame dict with bed, vitals_snapshot, voice, radar sections
    """
    bed_esp1 = hw_data.get("bed_esp1", {})
    bed_esp2 = hw_data.get("bed_esp2", {})
    hand = hw_data.get("hand", {})
    radar = hw_data.get("radar", {})
    voice = hw_data.get("voice_latest", {})

    # --- Pressure: merge 12 sensors into zone array ---
    pressures_raw = {}
    for src in [bed_esp1.get("pressures", {}), bed_esp2.get("pressures", {})]:
        pressures_raw.update(src)

    # Normalize to 0-4095 raw ADC (keep raw scale for pressure analyzer)
    fsrs = [0] * 12
    zone_counts = [0] * 12
    for sensor_name, raw_val in pressures_raw.items():
        zone_idx = PRESSURE_MAP.get(sensor_name)
        if zone_idx is not None:
            fsrs[zone_idx] += raw_val  # Keep raw ADC value
            zone_counts[zone_idx] += 1

    # Average zones with multiple sensors
    for i in range(12):
        if zone_counts[i] > 1:
            fsrs[i] /= zone_counts[i]
        fsrs[i] = min(4095, fsrs[i])  # Cap at ADC max

    # --- Temperature: bed temps (surface) + hand temp (body) ---
    bed_temps_raw = bed_esp1.get("temperatures", {})
    bed_temps = list(bed_temps_raw.values()) if isinstance(bed_temps_raw, dict) else bed_temps_raw
    if not bed_temps:
        bed_temps = [25.0, 25.0, 25.0]

    hand_temp_data = hand.get("temperature", {})
    body_temp = hand_temp_data.get("corrected", hand_temp_data.get("raw", 36.5))
    # Validate body temp range
    if body_temp < 30 or body_temp > 45:
        body_temp = 36.5

    # --- MPU data for posture detection ---
    mpu1 = bed_esp1.get("mpu1", {})
    mpu2 = bed_esp1.get("mpu2", {})

    # --- Heart rate from MAX30102 ---
    hr_data = hand.get("heart_rate", {})
    hand_detected = hr_data.get("hand_detected", False)
    # Prefer computed values (from real algorithm or simulator)
    if "computed_hr" in hr_data:
        heart_rate = hr_data["computed_hr"]
    else:
        ir_val = hr_data.get("ir", 0)
        heart_rate = _estimate_hr(ir_val, hand_detected)

    # SpO2
    if "computed_spo2" in hr_data:
        spo2 = hr_data["computed_spo2"]
    else:
        spo2 = _estimate_spo2(hr_data)

    # --- Movement from hand accelerometer ---
    hand_movement = hand.get("movement", {})
    accel_mag = math.sqrt(
        hand_movement.get("accel_x", 0) ** 2 +
        hand_movement.get("accel_y", 0) ** 2 +
        hand_movement.get("accel_z", 9.8) ** 2
    )
    # Movement level: deviation from gravity (9.8)
    movement_level = min(1.0, abs(accel_mag - 9.8) / 5.0)

    # --- Posture from bed MPU ---
    posture = _detect_posture(mpu1, mpu2, fsrs)

    # --- Fall risk from radar + MPU ---
    fall_risk = _assess_fall_risk(radar, mpu1, mpu2, hand_movement)

    # --- Build VitalGuard frame ---
    frame = {
        "timestamp_ms": int(hw_data.get("last_update", time.time()) * 1000),
        "elapsed_min": 0,  # Set by caller
        "bed": {
            "fsrs": fsrs,
            "temperatures": bed_temps,
            "mpu1": {
                "accel": {"x": mpu1.get("accel_x", 0), "y": mpu1.get("accel_y", 0), "z": mpu1.get("accel_z", 9.8)},
                "gyro": {"x": mpu1.get("gyro_x", 0), "y": mpu1.get("gyro_y", 0), "z": mpu1.get("gyro_z", 0)},
            },
            "mpu2": {
                "accel": {"x": mpu2.get("accel_x", 0), "y": mpu2.get("accel_y", 0), "z": mpu2.get("accel_z", 9.8)},
                "gyro": {"x": mpu2.get("gyro_x", 0), "y": mpu2.get("gyro_y", 0), "z": mpu2.get("gyro_z", 0)},
            },
            "microphones": [0, 0, 0],
        },
        "vitals_snapshot": {
            "heart_rate": heart_rate,
            "spo2": spo2,
            "body_temp": round(body_temp, 1),
            "hrv": _estimate_hrv(heart_rate),
            "resp_rate": _estimate_resp_rate(mpu1),
            "movement_level": round(movement_level, 3),
            "posture": posture,
            "posture_duration_min": 0,  # Tracked by caller
            "blood_pressure": "120/80",
        },
        "pressure_zones_named": _build_pressure_zones(fsrs),
        "radar": {
            "distance_cm": radar.get("distance_cm", 0),
            "moving": radar.get("moving", False),
            "presence": radar.get("presence", 0),
            "stationary": radar.get("stationary", False),
        },
        "voice": {
            "text": voice.get("text", ""),
            "timestamp": voice.get("timestamp", 0),
            "id": voice.get("id", 0),
        },
        "fall_risk": fall_risk,
    }
    return frame


def _estimate_hr(ir_val: int, hand_detected: bool) -> float:
    """Estimate heart rate. If no hand, return default."""
    if not hand_detected or ir_val == 0:
        return 72.0  # Default resting HR
    # Simplified: real uses peak detection algorithm
    return max(40, min(180, 60 + (ir_val % 60)))


def _estimate_spo2(hr_data: dict) -> float:
    """Estimate SpO2 from red/IR ratio."""
    ir = hr_data.get("ir", 0)
    red = hr_data.get("red", 0)
    if ir == 0 or red == 0:
        return 98.0
    ratio = red / max(1, ir)
    return max(70, min(100, 110 - 25 * ratio))


def _estimate_hrv(hr: float) -> float:
    """Rough HRV estimate from HR."""
    return max(5, 60 - (hr - 60) * 0.5)


def _estimate_resp_rate(mpu1: dict) -> float:
    """Estimate respiratory rate from chest MPU periodic motion."""
    # Simplified - real uses FFT on accel_z
    return 16.0


def _detect_posture(mpu1: dict, mpu2: dict, fsrs: list) -> str:
    """
    Detect patient posture from bed MPU accelerometers + pressure distribution.
    fsrs are raw ADC values (0-4095).
    """
    ax1 = mpu1.get("accel_x", 0)
    ay1 = mpu1.get("accel_y", 0)
    az1 = mpu1.get("accel_z", 9.8)

    # Primary: accelerometer tilt angle
    roll = math.atan2(ay1, az1) * 180 / math.pi

    # Secondary: pressure asymmetry (left vs right) using raw ADC
    left_pressure = sum(fsrs[i] for i in [1, 3, 5, 7, 9] if i < len(fsrs))
    right_pressure = sum(fsrs[i] for i in [2, 4, 6, 8, 10] if i < len(fsrs))
    total = left_pressure + right_pressure + 1  # avoid div by 0
    asymmetry = (left_pressure - right_pressure) / total

    if abs(roll) > 30 or asymmetry > 0.3:
        return "left_lateral"
    elif abs(roll) > 30 or asymmetry < -0.3:
        return "right_lateral"
    elif abs(roll) < 15:
        return "supine"
    else:
        return "supine"


def _assess_fall_risk(radar: dict, mpu1: dict, mpu2: dict, hand_movement: dict) -> dict:
    """
    Assess fall risk from radar + MPU + hand movement.

    Fall indicators:
    - Radar: presence moving + distance changing rapidly
    - Bed MPU: sudden tilt (large gyro values)
    - Hand: high acceleration spike
    """
    risk_score = 0.0
    indicators = []

    # Radar: patient moving near bed edge
    if radar.get("moving", False):
        risk_score += 0.2
        indicators.append("patient_moving")

    distance = radar.get("distance_cm", 0)
    if 0 < distance < 50:  # Very close to radar = edge of bed
        risk_score += 0.3
        indicators.append("near_bed_edge")

    # Bed MPU: tilt spike
    gyro_mag = math.sqrt(
        mpu1.get("gyro_x", 0) ** 2 +
        mpu1.get("gyro_y", 0) ** 2 +
        mpu1.get("gyro_z", 0) ** 2
    )
    if gyro_mag > 2.0:  # Significant rotation
        risk_score += 0.3
        indicators.append("bed_tilt_detected")

    # Hand accel: sudden spike (impact or flailing)
    hand_accel = math.sqrt(
        hand_movement.get("accel_x", 0) ** 2 +
        hand_movement.get("accel_y", 0) ** 2 +
        hand_movement.get("accel_z", 9.8) ** 2
    )
    if hand_accel > 15:  # Well above gravity
        risk_score += 0.3
        indicators.append("hand_impact")

    level = "critical" if risk_score > 0.6 else "warning" if risk_score > 0.3 else "low"

    return {
        "score": round(min(1.0, risk_score), 2),
        "level": level,
        "indicators": indicators,
    }


def _build_pressure_zones(fsrs: list) -> dict:
    """Build named pressure zone dict for dashboard."""
    zones = {}
    for i, name in ZONE_NAMES.items():
        raw = fsrs[i] if i < len(fsrs) else 0
        normalized = min(1.0, raw / 4095.0)
        zones[name] = {
            "pressure": round(normalized, 3),
            "raw_adc": round(raw),
            "risk_score": round(min(1.0, normalized * 1.5), 3),
        }
    return zones