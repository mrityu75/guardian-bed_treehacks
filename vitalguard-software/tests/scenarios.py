"""
Experiment Scenarios
=====================
Specialized scenarios for live demonstration experiments.
Each scenario has clear phase transitions visible on the dashboard.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import random
import math
from config.patient_profiles import PatientProfile
from synthetic.generator import SyntheticState, generate_combined_frame


# ============================================
# EXPERIMENT 1: Normal → Critical Transition
# ============================================
# Patient starts perfectly stable, then deteriorates
# until risk engine triggers CRITICAL + email alert

def experiment_1_normal_to_critical(duration_min=10, interval_sec=2.0):
    """
    Experiment 1: Stable patient suddenly deteriorates.
    
    Timeline:
      Phase 1 (0-40%):   STABLE — HR 68, SpO2 99, Temp 36.6
      Phase 2 (40-60%):  TRANSITION — gradual worsening
      Phase 3 (60-80%):  WARNING — HR 95+, SpO2 94, Temp 37.8
      Phase 4 (80-100%): CRITICAL — HR 110+, SpO2 90, Temp 38.5+
    
    Expected dashboard behavior:
      - Patient card moves from bottom to top
      - Status dot changes green → amber → red
      - Charts show clear inflection points
      - Email alert fires at phase 3→4 transition
    """
    patient = PatientProfile(
        patient_id="EXP1-001",
        name="Patient Alpha",
        age=62,
        height_cm=170,
        weight_kg=78,
        room="ICU-301",
        surgery_type="Cardiac Bypass",
        post_op_day=2,
        is_diabetic=True,
        has_cardiovascular_risk=True,
        mobility_level="bed_bound",
        assigned_nurse="Nurse Kim",
        assigned_doctor="Dr. Han",
        surgical_history=["Appendectomy (2018)"],
        lab_results=[
            {"test": "CBC", "time": "-2h", "wbc": "7.8", "hgb": "13.1", "plt": "220", "status": "normal"},
            {"test": "BMP", "time": "-4h", "na": "141", "k": "4.0", "cr": "1.0", "glucose": "105", "status": "normal"},
        ],
        medications=["Morphine 2mg IV q4h PRN", "Cefazolin 1g IV q8h", "Enoxaparin 40mg SC daily",
                     "Metoprolol 25mg PO BID", "Insulin glargine 20u SC QHS"],
        allergies=["Penicillin (rash)"],
    )

    state = SyntheticState(patient, {
        "heart_rate": 68.0,
        "body_temp": 36.6,
        "spo2": 99.0,
        "hrv": 48.0,
        "resp_rate": 14.0,
        "movement_level": 0.4,
        "posture": "supine",
    })

    total_frames = int(duration_min * 60 / interval_sec)
    frames = []

    for i in range(total_frames):
        progress = i / total_frames  # 0.0 → 1.0

        # Phase 1: STABLE (0% - 40%)
        if progress < 0.4:
            state.heart_rate += random.gauss(0, 0.3)
            state.heart_rate = max(64, min(74, state.heart_rate))
            state.body_temp += random.gauss(0, 0.01)
            state.body_temp = max(36.4, min(36.8, state.body_temp))
            state.spo2 += random.gauss(0, 0.1)
            state.spo2 = max(97, min(100, state.spo2))
            state.hrv += random.gauss(0, 0.5)
            state.hrv = max(42, min(55, state.hrv))
            state.resp_rate += random.gauss(0, 0.2)
            state.resp_rate = max(13, min(16, state.resp_rate))
            state.movement_level = 0.35 + random.gauss(0, 0.02)

        # Phase 2: TRANSITION (40% - 60%)
        elif progress < 0.6:
            phase_progress = (progress - 0.4) / 0.2  # 0→1 within this phase
            target_hr = 68 + phase_progress * 27  # 68 → 95
            target_temp = 36.6 + phase_progress * 1.2  # 36.6 → 37.8
            target_spo2 = 99 - phase_progress * 5  # 99 → 94
            target_hrv = 48 - phase_progress * 20  # 48 → 28
            target_rr = 14 + phase_progress * 6  # 14 → 20

            state.heart_rate += (target_hr - state.heart_rate) * 0.05 + random.gauss(0, 0.5)
            state.body_temp += (target_temp - state.body_temp) * 0.03 + random.gauss(0, 0.02)
            state.spo2 += (target_spo2 - state.spo2) * 0.05 + random.gauss(0, 0.2)
            state.hrv += (target_hrv - state.hrv) * 0.05 + random.gauss(0, 0.5)
            state.resp_rate += (target_rr - state.resp_rate) * 0.05 + random.gauss(0, 0.3)
            state.movement_level = max(0.1, 0.35 - phase_progress * 0.2)

        # Phase 3: WARNING (60% - 80%)
        elif progress < 0.8:
            phase_progress = (progress - 0.6) / 0.2
            target_hr = 95 + phase_progress * 15  # 95 → 110
            target_temp = 37.8 + phase_progress * 0.7  # 37.8 → 38.5
            target_spo2 = 94 - phase_progress * 4  # 94 → 90
            target_hrv = 28 - phase_progress * 10  # 28 → 18
            target_rr = 20 + phase_progress * 4  # 20 → 24

            state.heart_rate += (target_hr - state.heart_rate) * 0.06 + random.gauss(0, 0.8)
            state.body_temp += (target_temp - state.body_temp) * 0.04 + random.gauss(0, 0.03)
            state.spo2 += (target_spo2 - state.spo2) * 0.06 + random.gauss(0, 0.3)
            state.hrv += (target_hrv - state.hrv) * 0.06 + random.gauss(0, 0.8)
            state.resp_rate += (target_rr - state.resp_rate) * 0.05 + random.gauss(0, 0.4)
            state.movement_level = max(0.05, 0.15 - phase_progress * 0.1)

        # Phase 4: CRITICAL (80% - 100%)
        else:
            phase_progress = (progress - 0.8) / 0.2
            target_hr = 110 + phase_progress * 8  # 110 → 118
            target_temp = 38.5 + phase_progress * 0.4  # 38.5 → 38.9
            target_spo2 = 90 - phase_progress * 2  # 90 → 88
            target_hrv = 18 - phase_progress * 5  # 18 → 13
            target_rr = 24 + phase_progress * 4  # 24 → 28

            state.heart_rate += (target_hr - state.heart_rate) * 0.08 + random.gauss(0, 1.0)
            state.body_temp += (target_temp - state.body_temp) * 0.05 + random.gauss(0, 0.03)
            state.spo2 += (target_spo2 - state.spo2) * 0.08 + random.gauss(0, 0.4)
            state.hrv += (target_hrv - state.hrv) * 0.08 + random.gauss(0, 0.5)
            state.resp_rate += (target_rr - state.resp_rate) * 0.06 + random.gauss(0, 0.5)
            state.movement_level = max(0.02, 0.05 - phase_progress * 0.03)
            state.is_vocalizing = random.random() < 0.3  # occasional distress sounds

        # Clamp values
        state.heart_rate = max(55, min(130, state.heart_rate))
        state.body_temp = max(36.0, min(39.5, state.body_temp))
        state.spo2 = max(85, min(100, state.spo2))
        state.hrv = max(8, min(60, state.hrv))
        state.resp_rate = max(10, min(32, state.resp_rate))

        state.advance(interval_sec)
        frame = generate_combined_frame(state)
        frames.append(frame)

    return frames, patient


# ============================================
# EXPERIMENT 2: Pressure Change + Posture Shift
# ============================================

def experiment_2_pressure_and_posture(duration_min=10, interval_sec=2.0):
    """
    Experiment 2: Pressure buildup triggers repositioning need.
    
    Timeline:
      Phase 1 (0-25%):   NORMAL — Supine, low pressure, normal vitals
      Phase 2 (25-50%):  BUILDING — Same position too long, pressure increases
      Phase 3 (50-65%):  OVERDUE — High sacral/heel pressure, alert triggered
      Phase 4 (65-75%):  REPOSITION — Posture changes to left_lateral
      Phase 5 (75-100%): RELIEF — Pressure drops, new pressure pattern
    
    Expected dashboard behavior:
      - Pressure zones change color (green → yellow → red)
      - Posture indicator updates
      - "Reposition overdue" alert appears
      - After repositioning: pressure relief visible
      - 3D mannequin posture updates
    """
    patient = PatientProfile(
        patient_id="EXP2-001",
        name="Patient Beta",
        age=74,
        height_cm=165,
        weight_kg=82,
        room="ICU-302",
        surgery_type="Hip Replacement",
        post_op_day=1,
        is_diabetic=False,
        has_cardiovascular_risk=False,
        mobility_level="bed_bound",
        assigned_nurse="Nurse Park",
        assigned_doctor="Dr. Yoon",
        surgical_history=["Cataract surgery (2022)"],
        lab_results=[
            {"test": "CBC", "time": "-3h", "wbc": "8.1", "hgb": "11.9", "plt": "198", "status": "normal"},
            {"test": "BMP", "time": "-3h", "na": "139", "k": "4.2", "cr": "1.1", "glucose": "110", "status": "normal"},
        ],
        medications=["Morphine 2mg IV q4h PRN", "Cefazolin 1g IV q8h", "Enoxaparin 40mg SC daily"],
        allergies=["NKDA"],
    )

    state = SyntheticState(patient, {
        "heart_rate": 72.0,
        "body_temp": 36.7,
        "spo2": 98.0,
        "hrv": 42.0,
        "resp_rate": 15.0,
        "movement_level": 0.25,
        "posture": "supine",
        "posture_duration_min": 0.0,
    })

    total_frames = int(duration_min * 60 / interval_sec)
    frames = []
    posture_changed = False

    for i in range(total_frames):
        progress = i / total_frames

        # Stable vitals throughout (this experiment focuses on pressure)
        state.heart_rate = 72 + random.gauss(0, 1.5)
        state.heart_rate = max(65, min(82, state.heart_rate))
        state.body_temp = 36.7 + random.gauss(0, 0.05)
        state.spo2 = 98 + random.gauss(0, 0.3)
        state.spo2 = max(95, min(100, state.spo2))
        state.hrv = 42 + random.gauss(0, 1)
        state.resp_rate = 15 + random.gauss(0, 0.5)

        # Phase 1 & 2: Stay supine, pressure building naturally
        if progress < 0.65:
            state.posture = "supine"
            # Movement decreases over time (patient falls asleep)
            state.movement_level = max(0.05, 0.25 - progress * 0.3)

        # Phase 3: Reposition event at 65%
        elif progress >= 0.65 and not posture_changed:
            state.posture = "left_lateral"
            state.posture_duration_min = 0.0
            state.movement_level = 0.4  # brief movement spike during repositioning
            posture_changed = True

        # Phase 4 & 5: New position, pressure relief
        else:
            state.posture = "left_lateral"
            state.movement_level = max(0.1, 0.2 + random.gauss(0, 0.03))

        state.advance(interval_sec)
        frame = generate_combined_frame(state)
        frames.append(frame)

    return frames, patient


if __name__ == "__main__":
    # Quick verification
    print("Generating Experiment 1...")
    f1, p1 = experiment_1_normal_to_critical(duration_min=5)
    print(f"  {p1.name}: {len(f1)} frames")
    print(f"  First HR: {f1[0]['vitals_snapshot']['heart_rate']:.1f}")
    print(f"  Last HR: {f1[-1]['vitals_snapshot']['heart_rate']:.1f}")

    print("\nGenerating Experiment 2...")
    f2, p2 = experiment_2_pressure_and_posture(duration_min=5)
    print(f"  {p2.name}: {len(f2)} frames")
    print(f"  First posture: {f2[0]['vitals_snapshot']['posture']}")
    mid = len(f2) // 2
    print(f"  Mid posture: {f2[mid]['vitals_snapshot']['posture']}")
    print(f"  Last posture: {f2[-1]['vitals_snapshot']['posture']}")