"""
Experiment Scenarios
=====================
Defines 3 distinct test scenarios with time-series state evolution.
Each scenario manipulates the SyntheticState over time to simulate
different clinical trajectories.

Scenario A: Stable patient — all vitals normal, regular repositioning
Scenario B: Gradual deterioration — slow fever rise, decreasing movement, pressure buildup
Scenario C: Acute crisis — sudden tachycardia, hypoxemia, no repositioning for 2+ hours
"""

import random
from synthetic.generator import SyntheticState, generate_combined_frame
from synthetic.patient_factory import generate_patient
from config.patient_profiles import PatientProfile


def scenario_a_stable(duration_min: float = 120, interval_sec: float = 2.0) -> list:
    """
    Scenario A: Stable Recovery
    ----------------------------
    - HR: 65-75 bpm, stable
    - Temp: 36.5-36.9°C
    - SpO2: 97-99%
    - Repositioned every 80 min
    - Moderate movement
    - Expected risk score: 5-20 (low)
    """
    patient = generate_patient(
        patient_id="PID-A001",
        surgery_type="Knee Arthroplasty",
    )
    patient.name = "Alice Stable"
    patient.age = 52

    state = SyntheticState(patient, {
        "heart_rate": 70,
        "body_temp": 36.6,
        "spo2": 98,
        "hrv": 45,
        "resp_rate": 15,
        "posture": "supine",
        "movement_level": 0.4,
    })

    frames = []
    total_steps = int((duration_min * 60) / interval_sec)
    reposition_interval = 80 * 60  # 80 min in seconds
    last_reposition = 0

    for step in range(total_steps):
        elapsed_sec = step * interval_sec
        state.advance(interval_sec)

        # Stable vitals with mild natural variation
        state.apply_trend("heart_rate", 70 + 3 * random.gauss(0, 1), rate=0.02)
        state.apply_trend("body_temp", 36.65 + 0.1 * random.gauss(0, 1), rate=0.01)
        state.apply_trend("spo2", 98 + random.gauss(0, 0.3), rate=0.02)
        state.apply_trend("hrv", 45 + random.gauss(0, 2), rate=0.015)
        state.apply_trend("resp_rate", 15 + random.gauss(0, 0.5), rate=0.02)
        state.movement_level = max(0.1, min(0.6, 0.35 + random.gauss(0, 0.05)))

        # Clamp vitals to realistic bounds
        state.heart_rate = max(55, min(85, state.heart_rate))
        state.body_temp = max(36.2, min(37.2, state.body_temp))
        state.spo2 = max(96, min(100, state.spo2))

        # Reposition regularly
        if elapsed_sec - last_reposition > reposition_interval:
            postures = ["supine", "left_lateral", "right_lateral"]
            postures.remove(state.posture)
            state.posture = random.choice(postures)
            state.posture_duration_min = 0
            last_reposition = elapsed_sec

        frames.append(generate_combined_frame(state))

    return frames, patient


def scenario_b_gradual(duration_min: float = 180, interval_sec: float = 2.0) -> list:
    """
    Scenario B: Gradual Deterioration
    -----------------------------------
    - Starts normal, then over 3 hours:
    - HR: 72 → 95 (slow climb)
    - Temp: 36.7 → 38.2 (developing fever)
    - SpO2: 98 → 94 (gradual decline)
    - Movement decreases over time
    - Repositioning becomes less frequent
    - Expected risk: starts 10, reaches 60-70 (caution→warning)
    """
    patient = generate_patient(
        patient_id="PID-B001",
        force_elderly=True,
        force_diabetic=True,
        surgery_type="Hip Replacement",
    )
    patient.name = "Bob Gradual"

    state = SyntheticState(patient, {
        "heart_rate": 72,
        "body_temp": 36.7,
        "spo2": 98,
        "hrv": 40,
        "resp_rate": 16,
        "posture": "supine",
        "movement_level": 0.35,
    })

    frames = []
    total_steps = int((duration_min * 60) / interval_sec)

    for step in range(total_steps):
        progress = step / total_steps  # 0.0 → 1.0
        state.advance(interval_sec)

        # Gradual targets that worsen over time
        hr_target = 72 + progress * 25 + random.gauss(0, 1)
        temp_target = 36.7 + progress * 1.6 + random.gauss(0, 0.05)
        spo2_target = 98 - progress * 5 + random.gauss(0, 0.3)
        hrv_target = 40 - progress * 18 + random.gauss(0, 1)
        rr_target = 16 + progress * 6 + random.gauss(0, 0.3)

        state.apply_trend("heart_rate", hr_target, rate=0.008)
        state.apply_trend("body_temp", temp_target, rate=0.005)
        state.apply_trend("spo2", spo2_target, rate=0.008)
        state.apply_trend("hrv", hrv_target, rate=0.008)
        state.apply_trend("resp_rate", rr_target, rate=0.008)

        # Movement decreases
        state.movement_level = max(0.05, 0.35 - progress * 0.30 + random.gauss(0, 0.02))

        # Less frequent repositioning (only once early on)
        if step == int(total_steps * 0.3):
            state.posture = "left_lateral"
            state.posture_duration_min = 0

        # Occasional vocalization in later stages (pain)
        state.is_vocalizing = progress > 0.6 and random.random() < 0.05

        # Clamp
        state.heart_rate = max(55, min(115, state.heart_rate))
        state.body_temp = max(36.2, min(39.0, state.body_temp))
        state.spo2 = max(90, min(100, state.spo2))
        state.hrv = max(12, min(55, state.hrv))

        frames.append(generate_combined_frame(state))

    return frames, patient


def scenario_c_acute(duration_min: float = 60, interval_sec: float = 1.0) -> list:
    """
    Scenario C: Acute Crisis
    -------------------------
    - First 20 min: normal
    - Min 20-25: sudden spike in HR (72 → 110+)
    - SpO2 drops rapidly (98 → 90)
    - Temperature already elevated (38.0 → 38.8)
    - No repositioning for entire period
    - Movement drops to near zero
    - Vocalizations (distress)
    - Expected risk: 10 → 85+ (critical)
    """
    patient = generate_patient(
        patient_id="PID-C001",
        force_cardio_risk=True,
        surgery_type="Craniotomy",
    )
    patient.name = "Charlie Crisis"
    patient.age = 68

    state = SyntheticState(patient, {
        "heart_rate": 74,
        "body_temp": 37.8,
        "spo2": 97,
        "hrv": 32,
        "resp_rate": 18,
        "posture": "supine",
        "posture_duration_min": 45,  # Already been 45 min without reposition
        "movement_level": 0.25,
    })

    frames = []
    total_steps = int((duration_min * 60) / interval_sec)
    crisis_start = 20 * 60  # 20 minutes in seconds

    for step in range(total_steps):
        elapsed_sec = step * interval_sec
        state.advance(interval_sec)

        if elapsed_sec < crisis_start:
            # Pre-crisis: mildly elevated but manageable
            state.apply_trend("heart_rate", 76 + random.gauss(0, 1), rate=0.02)
            state.apply_trend("body_temp", 37.8 + random.gauss(0, 0.03), rate=0.01)
            state.apply_trend("spo2", 97 + random.gauss(0, 0.2), rate=0.02)
            state.movement_level = max(0.1, 0.25 + random.gauss(0, 0.03))
        else:
            # CRISIS: rapid deterioration
            crisis_progress = (elapsed_sec - crisis_start) / (5 * 60)  # over 5 min
            crisis_progress = min(1.0, crisis_progress)

            hr_target = 76 + crisis_progress * 38 + random.gauss(0, 2)
            temp_target = 37.8 + crisis_progress * 1.0
            spo2_target = 97 - crisis_progress * 7
            hrv_target = 32 - crisis_progress * 16
            rr_target = 18 + crisis_progress * 8

            state.apply_trend("heart_rate", hr_target, rate=0.05)
            state.apply_trend("body_temp", temp_target, rate=0.02)
            state.apply_trend("spo2", spo2_target, rate=0.04)
            state.apply_trend("hrv", hrv_target, rate=0.04)
            state.apply_trend("resp_rate", rr_target, rate=0.04)

            # Movement drops to near zero
            state.movement_level = max(0.02, 0.1 - crisis_progress * 0.08)

            # Distress vocalizations
            state.is_vocalizing = random.random() < 0.15

        # Never repositioned — pressure keeps building
        # posture_duration_min increases automatically via state.advance()

        # Clamp
        state.heart_rate = max(50, min(135, state.heart_rate))
        state.body_temp = max(36.5, min(39.5, state.body_temp))
        state.spo2 = max(85, min(100, state.spo2))
        state.hrv = max(8, min(50, state.hrv))
        state.resp_rate = max(12, min(32, state.resp_rate))

        frames.append(generate_combined_frame(state))

    return frames, patient


# --- Convenience mapping ---
SCENARIOS = {
    "A": {"name": "Stable Recovery", "func": scenario_a_stable},
    "B": {"name": "Gradual Deterioration", "func": scenario_b_gradual},
    "C": {"name": "Acute Crisis", "func": scenario_c_acute},
}


if __name__ == "__main__":
    import json

    for key, info in SCENARIOS.items():
        print(f"\n{'='*60}")
        print(f"SCENARIO {key}: {info['name']}")
        print(f"{'='*60}")

        frames, patient = info["func"](duration_min=5, interval_sec=2.0)
        print(f"Patient: {patient.name} ({patient.patient_id})")
        print(f"Frames generated: {len(frames)}")

        # Show first and last frame vitals
        first = frames[0]["vitals_snapshot"]
        last = frames[-1]["vitals_snapshot"]
        print(f"  Start -> HR:{first['heart_rate']} Temp:{first['body_temp']} "
              f"SpO2:{first['spo2']} HRV:{first['hrv']}")
        print(f"  End   -> HR:{last['heart_rate']} Temp:{last['body_temp']} "
              f"SpO2:{last['spo2']} HRV:{last['hrv']}")
        print(f"  Posture duration: {last['posture_duration_min']} min")
