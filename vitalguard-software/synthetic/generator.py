"""
Synthetic Data Generator
=========================
Generates fake sensor data in EXACTLY the same JSON format as real ESP32 hardware.
Supports time-series generation with configurable patient states.

Real bed module format:
{
  "timestamp": 659063,
  "module": "bed",
  "fsrs": [0,0,0,0,0,0,0,0,0,0,0,0],
  "temperatures": [25.375, 26.0625, 25.3125],
  "mpu1": {"accel": {"x":..,"y":..,"z":..}, "gyro": {"x":..,"y":..,"z":..}},
  "mpu2": {"accel": {"x":..,"y":..,"z":..}, "gyro": {"x":..,"y":..,"z":..}},
  "microphones": [0, 0, 0]
}

Real hand module format:
{
  "timestamp": 659063,
  "module": "hand",
  "temperature": 36.8,
  "accel": {"x":..,"y":..,"z":..,"mag":..},
  "gyro": {"x":..,"y":..,"z":..,"mag":..},
  "hr": {"ir":..,"red":..}
}
"""

import time
import math
import random
from typing import Generator
from config.patient_profiles import PatientProfile
from synthetic.noise import (
    adc_noise,
    imu_noise,
    temperature_noise,
    heart_rate_noise,
    microphone_noise,
    pressure_drift,
)


# --- Posture definitions ---
# Each posture defines base pressure distribution across 12 FSR zones (0-1 normalized)
POSTURE_PROFILES = {
    "supine": [0.15, 0.35, 0.35, 0.25, 0.25, 0.20, 0.20, 0.50, 0.50, 0.15, 0.15, 0.30],
    "left_lateral": [0.05, 0.55, 0.10, 0.40, 0.08, 0.35, 0.05, 0.35, 0.10, 0.20, 0.05, 0.15],
    "right_lateral": [0.05, 0.10, 0.55, 0.08, 0.40, 0.05, 0.35, 0.10, 0.35, 0.05, 0.20, 0.15],
    "prone": [0.20, 0.15, 0.15, 0.30, 0.30, 0.25, 0.25, 0.15, 0.15, 0.10, 0.10, 0.10],
}

# Accelerometer signatures per posture (body orientation gravity vector)
POSTURE_ACCEL = {
    "supine":        {"x": 0.0,  "y": -1.0, "z": 0.0},
    "left_lateral":  {"x": 1.0,  "y": 0.0,  "z": 0.0},
    "right_lateral": {"x": -1.0, "y": 0.0,  "z": 0.0},
    "prone":         {"x": 0.0,  "y": 1.0,  "z": 0.0},
}


class SyntheticState:
    """Tracks the evolving state of a synthetic patient over time."""

    def __init__(self, patient: PatientProfile, initial_state: dict = None):
        self.patient = patient
        self.timestamp_ms = 0
        self.elapsed_min = 0.0

        # Defaults or override with initial_state
        state = initial_state or {}
        self.heart_rate = state.get("heart_rate", 72.0)
        self.body_temp = state.get("body_temp", 36.7)
        self.spo2 = state.get("spo2", 98.0)
        self.hrv = state.get("hrv", 42.0)
        self.resp_rate = state.get("resp_rate", 16.0)
        self.posture = state.get("posture", "supine")
        self.posture_duration_min = state.get("posture_duration_min", 0.0)
        self.movement_level = state.get("movement_level", 0.3)  # 0=immobile, 1=active
        self.is_vocalizing = False
        self.stress_level = 0.0  # 0-1

    def advance(self, delta_sec: float = 1.0):
        """Advance the simulation by delta_sec seconds."""
        self.timestamp_ms += int(delta_sec * 1000)
        self.elapsed_min += delta_sec / 60.0
        self.posture_duration_min += delta_sec / 60.0

    def apply_trend(self, param: str, target: float, rate: float = 0.01):
        """Gradually move a parameter toward a target value."""
        current = getattr(self, param)
        diff = target - current
        step = diff * rate + random.gauss(0, abs(diff) * 0.05)
        setattr(self, param, current + step)


def generate_bed_frame(state: SyntheticState) -> dict:
    """
    Generate a single bed module data frame.
    Format matches real ESP32 bed module JSON output exactly.
    """
    # Pressure from posture + time drift
    base_pressure = POSTURE_PROFILES[state.posture]
    fsrs = []
    for i, bp in enumerate(base_pressure):
        # Apply time-based drift (longer in position = more pressure)
        drifted = pressure_drift(bp, state.posture_duration_min, rate=0.001)
        # Apply patient weight factor (heavier = more pressure)
        weight_factor = state.patient.weight_kg / 75.0
        drifted *= weight_factor
        # Convert to ADC value
        fsrs.append(adc_noise(min(1.0, drifted), jitter=0.015))

    # Bed temperature probes (ambient + body heat transfer)
    body_heat_offset = (state.body_temp - 36.5) * 0.3
    temps = [
        temperature_noise(25.0 + body_heat_offset + random.gauss(0, 0.2)),
        temperature_noise(26.0 + body_heat_offset + random.gauss(0, 0.2)),
        temperature_noise(25.5 + body_heat_offset + random.gauss(0, 0.2)),
    ]

    # MPU1 (mattress center) — reflects posture + movement
    accel_base = POSTURE_ACCEL[state.posture]
    movement_jitter = state.movement_level * 0.5
    mpu1 = {
        "accel": {
            "x": imu_noise(accel_base["x"], movement_jitter),
            "y": imu_noise(accel_base["y"], movement_jitter),
            "z": imu_noise(accel_base["z"] + 9.81, movement_jitter),
        },
        "gyro": {
            "x": imu_noise(0, movement_jitter * 2),
            "y": imu_noise(0, movement_jitter * 2),
            "z": imu_noise(0, movement_jitter * 2),
        },
    }

    # MPU2 (mattress edge) — less movement
    mpu2 = {
        "accel": {
            "x": imu_noise(accel_base["x"] * 0.3, 0.1),
            "y": imu_noise(accel_base["y"] * 0.3, 0.1),
            "z": imu_noise(9.81, 0.1),
        },
        "gyro": {
            "x": imu_noise(0, 0.1),
            "y": imu_noise(0, 0.1),
            "z": imu_noise(0, 0.1),
        },
    }

    # Microphones
    mics = [
        microphone_noise(state.is_vocalizing, ambient_db=38),
        microphone_noise(state.is_vocalizing, ambient_db=36),
        microphone_noise(state.is_vocalizing, ambient_db=37),
    ]

    return {
        "timestamp": state.timestamp_ms,
        "module": "bed",
        "fsrs": fsrs,
        "temperatures": temps,
        "mpu1": mpu1,
        "mpu2": mpu2,
        "microphones": mics,
    }


def generate_hand_frame(state: SyntheticState) -> dict:
    """
    Generate a single hand module data frame.
    Format matches real ESP32 hand module JSON output exactly.
    """
    # Body temperature from MAX30205
    temp = temperature_noise(state.body_temp, noise_std=0.03)

    # Wrist accelerometer — reflects arm movement
    arm_movement = state.movement_level * 0.8
    accel = {
        "x": imu_noise(0.1, arm_movement),
        "y": imu_noise(-0.3, arm_movement),
        "z": imu_noise(9.75, arm_movement * 0.5),
    }
    accel["mag"] = round(math.sqrt(accel["x"]**2 + accel["y"]**2 + accel["z"]**2), 6)

    gyro = {
        "x": imu_noise(0, arm_movement * 3),
        "y": imu_noise(0, arm_movement * 3),
        "z": imu_noise(0, arm_movement * 3),
    }
    gyro["mag"] = round(math.sqrt(gyro["x"]**2 + gyro["y"]**2 + gyro["z"]**2), 6)

    # Heart rate from MAX30102
    hr_data = heart_rate_noise(state.heart_rate, noise_std=1.0)

    return {
        "timestamp": state.timestamp_ms,
        "module": "hand",
        "temperature": temp,
        "accel": accel,
        "gyro": gyro,
        "hr": {"ir": hr_data["ir"], "red": hr_data["red"]},
    }


def generate_combined_frame(state: SyntheticState) -> dict:
    """
    Generate a combined frame with both modules + patient metadata.
    This is the enriched format used by the analysis pipeline.
    """
    bed = generate_bed_frame(state)
    hand = generate_hand_frame(state)

    return {
        "patient_id": state.patient.patient_id,
        "patient_name": state.patient.name,
        "timestamp_ms": state.timestamp_ms,
        "elapsed_min": round(state.elapsed_min, 2),
        "bed": bed,
        "hand": hand,
        # Derived vitals for convenience (analysis engine will recompute)
        "vitals_snapshot": {
            "heart_rate": round(state.heart_rate, 1),
            "body_temp": round(state.body_temp, 2),
            "spo2": round(state.spo2, 1),
            "hrv": round(state.hrv, 1),
            "resp_rate": round(state.resp_rate, 1),
            "posture": state.posture,
            "posture_duration_min": round(state.posture_duration_min, 1),
            "movement_level": round(state.movement_level, 3),
        },
    }


def stream_patient_data(
    state: SyntheticState,
    duration_min: float = 60,
    interval_sec: float = 1.0,
) -> Generator[dict, None, None]:
    """
    Generator that yields combined frames over a time period.
    Use this for streaming simulation.

    Args:
        state: SyntheticState to evolve
        duration_min: Total simulation duration in minutes
        interval_sec: Time between frames in seconds
    """
    total_frames = int((duration_min * 60) / interval_sec)

    for _ in range(total_frames):
        state.advance(interval_sec)
        yield generate_combined_frame(state)


if __name__ == "__main__":
    import json
    from synthetic.patient_factory import generate_patient

    # Quick test: generate 5 frames
    patient = generate_patient()
    state = SyntheticState(patient)

    print(f"Patient: {patient.name} ({patient.patient_id})")
    print(f"Surgery: {patient.surgery_type}, Day {patient.post_op_day}")
    print(f"Age: {patient.age}, BMI: {patient.bmi}")
    print("-" * 60)

    for i, frame in enumerate(stream_patient_data(state, duration_min=0.1, interval_sec=1.0)):
        if i < 3:
            print(json.dumps(frame, indent=2)[:500])
            print("...")
        elif i == 3:
            print(f"... ({i} more frames)")
    print(f"Total elapsed: {state.elapsed_min:.1f} min")
