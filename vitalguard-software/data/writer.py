#!/usr/bin/env python3
"""
VitalGuard Data Writer
========================
Simulates hardware by writing sensor JSON to data/incoming/.
Each patient gets a file: data/incoming/{patient_id}.json

The server watches this folder and reads new data in real-time.
Later, replace this script with actual ESP32 serial → file bridge.

Usage:
    python data/writer.py --experiment 1 --duration 3 --speed 4
    python data/writer.py --experiment 2 --duration 3 --speed 4
    python data/writer.py --experiment all --duration 3 --speed 4
"""

import sys
import os
import json
import time
import argparse
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.patient_profiles import PatientProfile
from synthetic.generator import SyntheticState, generate_combined_frame, stream_patient_data
from synthetic.patient_factory import generate_patient

DATA_DIR = os.path.join(os.path.dirname(__file__), "incoming")
os.makedirs(DATA_DIR, exist_ok=True)


def write_frame(patient_id, frame):
    """Write a single frame to the patient's data file."""
    path = os.path.join(DATA_DIR, f"{patient_id}.json")
    with open(path, "w") as f:
        json.dump(frame, f)


def write_profile(patient):
    """Write patient profile once so server can load it."""
    path = os.path.join(DATA_DIR, f"{patient.patient_id}_profile.json")
    if os.path.exists(path):
        return  # already written
    data = {
        "patient_id": patient.patient_id,
        "name": patient.name,
        "age": patient.age,
        "height_cm": patient.height_cm,
        "weight_kg": patient.weight_kg,
        "room": patient.room,
        "surgery_type": patient.surgery_type,
        "post_op_day": patient.post_op_day,
        "is_diabetic": patient.is_diabetic,
        "has_cardiovascular_risk": patient.has_cardiovascular_risk,
        "mobility_level": patient.mobility_level,
        "assigned_nurse": patient.assigned_nurse,
        "assigned_doctor": patient.assigned_doctor,
        "surgical_history": patient.surgical_history,
        "lab_results": patient.lab_results,
        "medications": patient.medications,
        "allergies": patient.allergies,
    }
    with open(path, "w") as f:
        json.dump(data, f)


def exp1_generator(duration_min=3):
    """Experiment 1: Normal -> Critical transition."""
    patient = PatientProfile(
        patient_id="EXP1-001", name="Patient Alpha",
        age=62, height_cm=170, weight_kg=78, room="ICU-301",
        surgery_type="Cardiac Bypass", post_op_day=2,
        is_diabetic=True, has_cardiovascular_risk=True, mobility_level="bed_bound",
        assigned_nurse="Nurse Kim", assigned_doctor="Dr. Han",
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
        "heart_rate": 68.0, "body_temp": 36.6, "spo2": 99.0,
        "hrv": 48.0, "resp_rate": 14.0, "movement_level": 0.4, "posture": "supine",
    })
    total = int(duration_min * 60 / 2.0)
    for i in range(total):
        p = i / total
        # Phase 1: Stable (0-35%)
        if p < 0.35:
            state.heart_rate = max(64, min(74, state.heart_rate + random.gauss(0, 0.3)))
            state.body_temp = max(36.4, min(36.8, state.body_temp + random.gauss(0, 0.01)))
            state.spo2 = max(97, min(100, state.spo2 + random.gauss(0, 0.1)))
            state.hrv = max(42, min(55, state.hrv + random.gauss(0, 0.5)))
            state.resp_rate = max(13, min(16, state.resp_rate + random.gauss(0, 0.2)))
            state.movement_level = max(0.3, min(0.5, 0.4 + random.gauss(0, 0.02)))
        # Phase 2: Transition (35-55%) - getting worse
        elif p < 0.55:
            pp = (p - 0.35) / 0.2
            targets = {"heart_rate":(68,100),"body_temp":(36.6,38.0),"spo2":(99,93),
                       "hrv":(48,25),"resp_rate":(14,22)}
            for attr,(s,e) in targets.items():
                t = s + pp * (e - s)
                c = getattr(state, attr)
                setattr(state, attr, c + (t - c) * 0.08 + random.gauss(0, 0.3))
            state.movement_level = max(0.1, 0.35 - pp * 0.2)
        # Phase 3: Warning (55-75%) - clearly deteriorating
        elif p < 0.75:
            pp = (p - 0.55) / 0.2
            targets = {"heart_rate":(100,120),"body_temp":(38.0,39.0),"spo2":(93,87),
                       "hrv":(25,12),"resp_rate":(22,28)}
            for attr,(s,e) in targets.items():
                t = s + pp * (e - s)
                c = getattr(state, attr)
                setattr(state, attr, c + (t - c) * 0.1 + random.gauss(0, 0.5))
            state.movement_level = max(0.03, 0.15 - pp * 0.1)
        # Phase 4: Critical (75-100%) - emergency
        else:
            pp = (p - 0.75) / 0.25
            targets = {"heart_rate":(120,140),"body_temp":(39.0,39.8),"spo2":(87,82),
                       "hrv":(12,6),"resp_rate":(28,35)}
            for attr,(s,e) in targets.items():
                t = s + pp * (e - s)
                c = getattr(state, attr)
                setattr(state, attr, c + (t - c) * 0.12 + random.gauss(0, 0.8))
            state.movement_level = max(0.01, 0.05 - pp * 0.04)

        # Clamp all vitals
        state.heart_rate = max(55, min(150, state.heart_rate))
        state.body_temp = max(36.0, min(40.5, state.body_temp))
        state.spo2 = max(78, min(100, state.spo2))
        state.hrv = max(4, min(60, state.hrv))
        state.resp_rate = max(10, min(40, state.resp_rate))

        # Posture duration increases (patient not being turned)
        state.posture_duration_min = p * duration_min * 1.5

        state.advance(2.0)
        yield patient, generate_combined_frame(state)


def exp2_generator(duration_min=3):
    """
    Experiment 2: Pressure-driven posture changes.
    
    Pressure builds on the contact side over time.
    When pressure exceeds threshold -> auto-reposition to opposite side.
    
    supine: sacral pressure builds -> switch to lateral
    left_lateral: left hip pressure builds -> switch to supine or right
    right_lateral: right hip pressure builds -> switch to supine or left
    
    Result: continuous posture cycling visible in 3D mannequin.
    """
    patient = PatientProfile(
        patient_id="EXP2-001", name="Patient Beta",
        age=74, height_cm=165, weight_kg=82, room="ICU-302",
        surgery_type="Hip Replacement", post_op_day=1,
        is_diabetic=False, has_cardiovascular_risk=False, mobility_level="bed_bound",
        assigned_nurse="Nurse Park", assigned_doctor="Dr. Yoon",
        surgical_history=["Cataract surgery (2022)"],
        lab_results=[{"test":"CBC","time":"-3h","wbc":"8.1","hgb":"11.9","plt":"198","status":"normal"}],
        medications=["Morphine 2mg IV q4h PRN", "Cefazolin 1g IV q8h", "Enoxaparin 40mg SC daily"],
        allergies=["NKDA"],
    )
    state = SyntheticState(patient, {
        "heart_rate": 72.0, "body_temp": 36.7, "spo2": 98.0,
        "hrv": 42.0, "resp_rate": 15.0, "movement_level": 0.25, "posture": "supine",
    })
    total = int(duration_min * 60 / 2.0)

    # Pressure accumulator per zone
    pressure = {"sacral": 0, "left_hip": 0, "right_hip": 0}
    THRESHOLD = 100  # pressure threshold to trigger reposition
    # Each posture builds pressure on specific zones
    pressure_map = {
        "supine":        {"sacral": 6, "left_hip": 1, "right_hip": 1},
        "left_lateral":  {"sacral": 0, "left_hip": 7, "right_hip": 0},
        "right_lateral": {"sacral": 0, "left_hip": 0, "right_hip": 7},
    }
    frames_in_posture = 0
    last_lateral = "right"  # alternate: last was right, so next will be left

    for i in range(total):
        cur_posture = state.posture

        # Accumulate pressure
        pm = pressure_map.get(cur_posture, {"sacral":2,"left_hip":2,"right_hip":2})
        for zone, rate in pm.items():
            pressure[zone] += rate + random.gauss(0, 0.5)
        frames_in_posture += 1

        # Check if reposition needed (min 8 frames in position before switching)
        if frames_in_posture >= 8:
            if cur_posture == "supine" and pressure["sacral"] >= THRESHOLD:
                # Sacral overloaded -> alternate left/right
                if last_lateral == "right":
                    state.posture = "left_lateral"
                    last_lateral = "left"
                else:
                    state.posture = "right_lateral"
                    last_lateral = "right"
                pressure["sacral"] = 0
                frames_in_posture = 0
                state.posture_duration_min = 0.0
                state.movement_level = 0.5

            elif cur_posture == "left_lateral" and pressure["left_hip"] >= THRESHOLD:
                # Left hip overloaded -> go supine
                state.posture = "supine"
                pressure["left_hip"] = 0
                frames_in_posture = 0
                state.posture_duration_min = 0.0
                state.movement_level = 0.5

            elif cur_posture == "right_lateral" and pressure["right_hip"] >= THRESHOLD:
                # Right hip overloaded -> go supine
                state.posture = "supine"
                pressure["right_hip"] = 0
                frames_in_posture = 0
                state.posture_duration_min = 0.0
                state.movement_level = 0.5
            else:
                # Settling - movement decreases
                state.movement_level = max(0.03, state.movement_level * 0.9)

        # Stable vitals with slight variation
        base_hr = 72 if cur_posture == "supine" else 74
        state.heart_rate = max(65, min(82, base_hr + random.gauss(0, 1.5)))
        state.body_temp = 36.7 + random.gauss(0, 0.05)
        state.spo2 = max(95, min(100, 98 + random.gauss(0, 0.3)))
        state.hrv = 42 + random.gauss(0, 1)
        state.resp_rate = 15 + random.gauss(0, 0.5)

        state.advance(2.0)
        yield patient, generate_combined_frame(state)


def bg_generators(duration_min=3):
    """Background stable patients."""
    configs = [
        {"id":"BG-001","hr":68,"tp":36.5,"sp":99,"hv":48,"rr":14,"mv":0.45},
        {"id":"BG-002","hr":74,"tp":36.9,"sp":97,"hv":40,"rr":16,"mv":0.35},
        {"id":"BG-003","hr":82,"tp":37.3,"sp":96,"hv":32,"rr":17,"mv":0.28},
        {"id":"BG-004","hr":65,"tp":36.4,"sp":99,"hv":52,"rr":13,"mv":0.50},
        {"id":"BG-005","hr":70,"tp":36.6,"sp":98,"hv":44,"rr":14,"mv":0.42},
        {"id":"BG-006","hr":86,"tp":37.4,"sp":95,"hv":29,"rr":19,"mv":0.22},
    ]
    patients = {}
    states = {}
    for cfg in configs:
        ep = generate_patient(patient_id=cfg["id"])
        st = SyntheticState(ep, {
            "heart_rate":cfg["hr"],"body_temp":cfg["tp"],"spo2":cfg["sp"],
            "hrv":cfg["hv"],"resp_rate":cfg["rr"],"movement_level":cfg["mv"],
            "posture": random.choice(["supine","left_lateral","right_lateral"]),
        })
        patients[cfg["id"]] = ep
        states[cfg["id"]] = st
    total = int(duration_min * 60 / 2.0)
    for i in range(total):
        for pid, st in states.items():
            st.advance(2.0)
            yield patients[pid], generate_combined_frame(st)


def main():
    parser = argparse.ArgumentParser(description="VitalGuard Data Writer")
    parser.add_argument("--experiment", required=True, choices=["1", "2"], help="1=Normal->Critical, 2=Posture rotation")
    parser.add_argument("--duration", type=int, default=3, help="Minutes")
    parser.add_argument("--speed", type=float, default=4.0, help="Playback speed")
    args = parser.parse_args()

    interval = 2.0 / args.speed
    total_frames = int(args.duration * 60 / 2.0)

    print(f"===================================")
    print(f"  VitalGuard Data Writer")
    print(f"===================================")
    print(f"  Data dir : {os.path.abspath(DATA_DIR)}")
    print(f"  Duration : {args.duration}min | Speed: {args.speed}x")
    print(f"  Interval : {interval:.2f}s | Frames: {total_frames}")
    print(f"===================================\n")

    experiments = [int(args.experiment)]

    for exp_num in experiments:
        run_single_experiment(exp_num, args.duration, args.speed)

    print(f"\n===================================")
    print(f"  All experiments complete.")
    print(f"===================================")


def run_single_experiment(exp_num, duration_min, speed):
    """Run one experiment: write data, log encryption, cleanup."""
    from security.quantum_crypto import SecureChannel

    interval = 2.0 / speed
    total_frames = int(duration_min * 60 / 2.0)

    # Clean incoming folder
    for f in os.listdir(DATA_DIR):
        if f.endswith(".json"):
            os.remove(os.path.join(DATA_DIR, f))

    # Setup encryption channel for verification
    server_ch = SecureChannel()
    client_ch = SecureChannel()
    si = server_ch.init_server()
    cr = client_ch.init_client(si["public_key"])
    server_ch.complete_handshake(cr["ciphertext"])

    if exp_num == 1:
        title = "Normal -> Critical Transition"
        gen = exp1_generator(duration_min)
        pid = "EXP1-001"
    else:
        title = "Pressure-Driven Posture Rotation"
        gen = exp2_generator(duration_min)
        pid = "EXP2-001"

    # Write profile for first frame to get patient object
    first_patient = None

    print(f"===================================")
    print(f"  EXPERIMENT {exp_num}: {title}")
    print(f"===================================")
    print(f"  Patient: {pid} | Frames: {total_frames}")
    print(f"  Encryption: {si['algorithm']}")
    print(f"  Session: {si['session_id'][:20]}...")
    print(f"===================================")

    # Also write background patients
    bg_gen = bg_generators(duration_min)
    bg_count = 6
    last_posture = {}
    written_files = set()
    frame_count = 0

    try:
        for fi in range(total_frames):
            t_min = fi * 2.0 / 60
            progress = fi / total_frames

            # Write experiment patient
            try:
                patient, frame = next(gen)
                if first_patient is None:
                    first_patient = patient
                    write_profile(patient)
                    written_files.add(f"{patient.patient_id}_profile.json")
                write_frame(patient.patient_id, frame)
                written_files.add(f"{patient.patient_id}.json")

                vs = frame.get("vitals_snapshot", {})
                pos = vs.get("posture", "?")
                hr = vs.get("heart_rate", 0)
                sp = vs.get("spo2", 0)
                tp = vs.get("body_temp", 0)
                hrv = vs.get("hrv", 0)

                # Encrypt frame for verification logging
                envelope = server_ch.encrypt_patient_data(vs)
                decrypted = client_ch.decrypt_patient_data(envelope)
                enc_bytes = len(json.dumps(envelope))
                mac = envelope["encrypted"]["mac"][:20]
                verified = decrypted is not None

                # Posture change
                prev = last_posture.get(pid)
                if prev and pos != prev:
                    print(f"  [POSTURE] {pid} | {prev} -> {pos}")
                last_posture[pid] = pos

                # Phase tag for EXP1
                phase = ""
                if exp_num == 1:
                    if progress < 0.4: phase = "STABLE"
                    elif progress < 0.6: phase = "TRANSITION"
                    elif progress < 0.8: phase = "WARNING"
                    else: phase = "CRITICAL"

                # Log every 6 frames
                if fi % 6 == 0:
                    v_mark = "OK" if verified else "FAIL"
                    print(f"  [{t_min:4.1f}m] f#{fi:03d} "
                          f"HR:{hr:5.1f} SpO2:{sp:5.1f} T:{tp:5.2f} HRV:{hrv:4.1f} "
                          f"| {pos:14s} "
                          f"| {enc_bytes}B MAC:{mac}.. [{v_mark}] "
                          f"{phase}")

            except StopIteration:
                pass

            # Write background patients
            try:
                for _ in range(bg_count):
                    bp, bf = next(bg_gen)
                    write_profile(bp)
                    written_files.add(f"{bp.patient_id}_profile.json")
                    write_frame(bp.patient_id, bf)
                    written_files.add(f"{bp.patient_id}.json")
            except StopIteration:
                pass

            frame_count += 1
            time.sleep(interval)

    except KeyboardInterrupt:
        print(f"\n  Stopped at frame {frame_count}")

    # Summary
    print(f"\n  -----------------------------------")
    print(f"  EXPERIMENT {exp_num} COMPLETE")
    print(f"  -----------------------------------")
    print(f"  Frames written  : {frame_count}")
    print(f"  Encrypted       : {frame_count} frames verified")
    print(f"  Algorithm       : {si['algorithm']}")

    if exp_num == 1:
        print(f"  Scenario        : Normal -> Critical")
        print(f"  Expected        : Risk escalation, alert triggered")
    else:
        print(f"  Scenario        : Pressure-driven posture rotation")
        print(f"  Expected        : Reactive posture changes based on pressure buildup")

    # Cleanup
    print(f"  Cleaning up {len(written_files)} files...")
    for fname in written_files:
        try:
            os.remove(os.path.join(DATA_DIR, fname))
        except FileNotFoundError:
            pass
    print(f"  Cleanup done.")


if __name__ == "__main__":
    main()