"""
Step 1 Tests: Synthetic Data Generator
========================================
Validates:
1. Patient factory generates valid profiles
2. Bed module JSON matches real ESP32 format
3. Hand module JSON matches real ESP32 format
4. All 3 scenarios produce expected trajectories
"""

import sys
import json

import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from synthetic.patient_factory import generate_patient, generate_patient_pool
from synthetic.generator import (
    SyntheticState,
    generate_bed_frame,
    generate_hand_frame,
    generate_combined_frame,
)
from synthetic.scenarios import scenario_a_stable, scenario_b_gradual, scenario_c_acute


passed = 0
failed = 0

def check(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  \u2705 {name}")
        passed += 1
    else:
        print(f"  \u274C {name} — {detail}")
        failed += 1


print("=" * 60)
print("TEST 1: Patient Factory")
print("=" * 60)

p = generate_patient()
check("Patient has ID", p.patient_id.startswith("PID-"))
check("Patient has name", len(p.name.split()) == 2)
check("Patient has age", 25 <= p.age <= 90)
check("Patient has height", 148 <= p.height_cm <= 198)
check("Patient has weight", 42 <= p.weight_kg <= 130)
check("Patient has BMI", 15 <= p.bmi <= 50, f"BMI={p.bmi}")
check("Patient has room", p.room.startswith("ICU-"))
check("Patient has surgery", len(p.surgery_type) > 3)
check("Elderly flag auto-set", generate_patient(force_elderly=True).is_elderly)
check("Diabetic multiplier applied",
      generate_patient(force_diabetic=True).pressure_multiplier > 1.0)

pool = generate_patient_pool(6)
check("Pool has 6 patients", len(pool) == 6)
check("Pool IDs unique", len(set(p.patient_id for p in pool)) == 6)
check("Pool has elderly", any(p.is_elderly for p in pool))
check("Pool has diabetic", any(p.is_diabetic for p in pool))

print(f"\n{'=' * 60}")
print("TEST 2: Bed Module JSON Format")
print("=" * 60)

state = SyntheticState(generate_patient())
bed = generate_bed_frame(state)

check("Has 'timestamp'", "timestamp" in bed)
check("Has 'module'='bed'", bed.get("module") == "bed")
check("Has 'fsrs' with 12 values", len(bed.get("fsrs", [])) == 12)
check("FSR values are integers", all(isinstance(v, int) for v in bed["fsrs"]))
check("FSR values in ADC range", all(0 <= v <= 4095 for v in bed["fsrs"]))
check("Has 'temperatures' with 3 values", len(bed.get("temperatures", [])) == 3)
check("Temps are floats", all(isinstance(v, float) for v in bed["temperatures"]))
check("Has 'mpu1' with accel+gyro",
      "accel" in bed.get("mpu1", {}) and "gyro" in bed.get("mpu1", {}))
check("mpu1.accel has x,y,z",
      all(k in bed["mpu1"]["accel"] for k in ["x", "y", "z"]))
check("Has 'mpu2'", "mpu2" in bed)
check("Has 'microphones' with 3 values", len(bed.get("microphones", [])) == 3)
check("Mic values are integers", all(isinstance(v, int) for v in bed["microphones"]))

print(f"\n{'=' * 60}")
print("TEST 3: Hand Module JSON Format")
print("=" * 60)

hand = generate_hand_frame(state)

check("Has 'timestamp'", "timestamp" in hand)
check("Has 'module'='hand'", hand.get("module") == "hand")
check("Has 'temperature'", "temperature" in hand)
check("Temp is float", isinstance(hand["temperature"], float))
check("Has 'accel' with x,y,z,mag",
      all(k in hand.get("accel", {}) for k in ["x", "y", "z", "mag"]))
check("Has 'gyro' with x,y,z,mag",
      all(k in hand.get("gyro", {}) for k in ["x", "y", "z", "mag"]))
check("Has 'hr' with ir,red",
      all(k in hand.get("hr", {}) for k in ["ir", "red"]))
check("HR IR is positive int", isinstance(hand["hr"]["ir"], int) and hand["hr"]["ir"] > 0)

print(f"\n{'=' * 60}")
print("TEST 4: Combined Frame Format")
print("=" * 60)

combined = generate_combined_frame(state)
check("Has patient_id", "patient_id" in combined)
check("Has patient_name", "patient_name" in combined)
check("Has bed data", "bed" in combined)
check("Has hand data", "hand" in combined)
check("Has vitals_snapshot", "vitals_snapshot" in combined)
vs = combined["vitals_snapshot"]
check("Snapshot has heart_rate", "heart_rate" in vs)
check("Snapshot has posture", "posture" in vs)
check("Snapshot has posture_duration_min", "posture_duration_min" in vs)

print(f"\n{'=' * 60}")
print("TEST 5: Scenario A (Stable)")
print("=" * 60)

frames_a, pat_a = scenario_a_stable(duration_min=5, interval_sec=2.0)
check("Scenario A generates frames", len(frames_a) > 100)
last_a = frames_a[-1]["vitals_snapshot"]
check("HR stays normal (55-90)", 55 <= last_a["heart_rate"] <= 90,
      f"HR={last_a['heart_rate']}")
check("Temp stays normal (36-37.5)", 36.0 <= last_a["body_temp"] <= 37.5,
      f"Temp={last_a['body_temp']}")
check("SpO2 stays normal (>=95)", last_a["spo2"] >= 95,
      f"SpO2={last_a['spo2']}")

print(f"\n{'=' * 60}")
print("TEST 6: Scenario B (Gradual)")
print("=" * 60)

frames_b, pat_b = scenario_b_gradual(duration_min=10, interval_sec=2.0)
first_b = frames_b[0]["vitals_snapshot"]
last_b = frames_b[-1]["vitals_snapshot"]
check("HR increases", last_b["heart_rate"] > first_b["heart_rate"],
      f"{first_b['heart_rate']} -> {last_b['heart_rate']}")
check("Temp increases", last_b["body_temp"] > first_b["body_temp"],
      f"{first_b['body_temp']} -> {last_b['body_temp']}")
check("SpO2 decreases", last_b["spo2"] < first_b["spo2"],
      f"{first_b['spo2']} -> {last_b['spo2']}")
check("Movement decreases", last_b["movement_level"] < first_b["movement_level"],
      f"{first_b['movement_level']} -> {last_b['movement_level']}")

print(f"\n{'=' * 60}")
print("TEST 7: Scenario C (Acute Crisis)")
print("=" * 60)

frames_c, pat_c = scenario_c_acute(duration_min=30, interval_sec=2.0)
first_c = frames_c[0]["vitals_snapshot"]
last_c = frames_c[-1]["vitals_snapshot"]
check("HR spikes high (>95)", last_c["heart_rate"] > 95,
      f"HR={last_c['heart_rate']}")
check("SpO2 drops (<94)", last_c["spo2"] < 94,
      f"SpO2={last_c['spo2']}")
check("Posture duration long (>50 min)", last_c["posture_duration_min"] > 50,
      f"Duration={last_c['posture_duration_min']}")

# Sample output for visual inspection
print(f"\n{'=' * 60}")
print("SAMPLE OUTPUT: Scenario C last frame (bed module)")
print("=" * 60)
print(json.dumps(frames_c[-1]["bed"], indent=2))

print(f"\n{'=' * 60}")
print(f"RESULTS: {passed} passed, {failed} failed out of {passed + failed}")
print("=" * 60)
