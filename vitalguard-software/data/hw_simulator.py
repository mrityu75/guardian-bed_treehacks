# """
# Hardware Simulator
# ==================
# Generates sensor data in the EXACT same format as real hardware merged_data.json.
# Supports 3 test scenarios:
#   S1: Voice-only changes (speech text keeps updating)
#   S2: Patient deterioration (risk escalation → email alert)
#   S3: Full data changes (pressure + voice + vitals all changing)

# Usage:
#   python data/hw_simulator.py --scenario 1 --duration 3 --speed 4
#   python data/hw_simulator.py --scenario 2 --duration 3 --speed 4
#   python data/hw_simulator.py --scenario 3 --duration 3 --speed 4
# """

# import json
# import os
# import sys
# import time
# import random
# import math
# import argparse

# # Add project root to path
# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "incoming")

# # Conversation samples for voice simulation
# CONVERSATIONS = {
#     "normal": [
#         "I'm feeling okay, just a little tired.",
#         "Can I get some water please?",
#         "The bed is comfortable enough.",
#         "My family is coming to visit later today.",
#         "What time is dinner?",
#         "I slept pretty well last night.",
#         "The nurse was very helpful this morning.",
#         "I'm watching the news right now.",
#     ],
#     "pain": [
#         "My back is really hurting right now.",
#         "The pain is getting worse, can someone help?",
#         "I can't get comfortable in this position.",
#         "It hurts when I try to move.",
#         "I need pain medication, it's really bad.",
#         "The pressure on my hip is unbearable.",
#         "I'm in a lot of pain, please help me.",
#         "Can you reposition me? This is very painful.",
#     ],
#     "distress": [
#         "I feel dizzy, something is wrong.",
#         "I can't breathe properly, help!",
#         "My chest feels tight.",
#         "I think I'm going to fall, help me!",
#         "I'm feeling very nauseous and weak.",
#         "Something doesn't feel right at all.",
#         "I need a doctor right now!",
#         "Help! I think I'm falling off the bed!",
#     ],
# }


# def make_base_frame(t: float, patient_idx: int = 0) -> dict:
#     """Create a baseline hardware frame with stable vitals."""
#     return {
#         "last_update": t,
#         "bed_esp1": {
#             "module": "bed_esp1",
#             "pressures": {
#                 "head_left": random.randint(0, 50),
#                 "head_center": random.randint(20, 80),
#                 "head_right": random.randint(0, 50),
#                 "upper_back_left_shoulder": random.randint(100, 300),
#                 "upper_back_right_shoulder": random.randint(100, 300),
#                 "lower_back_left_hip": random.randint(200, 500),
#             },
#             "temperatures": {
#                 "temp_1": round(22 + random.gauss(0, 0.3), 4),
#                 "temp_2": round(22 + random.gauss(0, 0.3), 4),
#                 "temp_3": round(22 + random.gauss(0, 0.3), 4),
#             },
#             "mpu1": {
#                 "accel_x": round(random.gauss(0, 0.3), 6),
#                 "accel_y": round(random.gauss(-1, 0.3), 6),
#                 "accel_z": round(9.8 + random.gauss(0, 0.2), 6),
#                 "gyro_x": round(random.gauss(0, 0.05), 6),
#                 "gyro_y": round(random.gauss(0, 0.05), 6),
#                 "gyro_z": round(random.gauss(0, 0.05), 6),
#             },
#             "mpu2": {
#                 "accel_x": round(random.gauss(0, 0.3), 6),
#                 "accel_y": round(random.gauss(-0.5, 0.3), 6),
#                 "accel_z": round(9.8 + random.gauss(0, 0.2), 6),
#                 "gyro_x": round(random.gauss(0, 0.03), 6),
#                 "gyro_y": round(random.gauss(0, 0.03), 6),
#                 "gyro_z": round(random.gauss(0, 0.03), 6),
#             },
#             "timestamp_unified": t,
#             "timestamp_esp": int(t * 1000) % 10000000,
#         },
#         "bed_esp2": {
#             "module": "bed_esp2",
#             "pressures": {
#                 "lower_back_right_hip": random.randint(200, 500),
#                 "upper_leg_left_thigh": random.randint(50, 200),
#                 "upper_leg_right_thigh": random.randint(50, 200),
#                 "lower_leg_left_calf": random.randint(0, 100),
#                 "lower_leg_right_calf": random.randint(0, 100),
#                 "lower_back_center_spine": random.randint(100, 300),
#             },
#             "timestamp_unified": t,
#             "timestamp_esp": int(t * 1000) % 10000000,
#         },
#         "hand": {
#             "module": "hand",
#             "temperature": {
#                 "raw": round(36.5 + random.gauss(0, 0.2), 4),
#                 "corrected": round(36.5 + random.gauss(0, 0.2), 4),
#                 "status": "ok",
#             },
#             "movement": {
#                 "accel_x": round(random.gauss(0, 0.5), 6),
#                 "accel_y": round(random.gauss(0, 0.5), 6),
#                 "accel_z": round(9.8 + random.gauss(0, 0.3), 6),
#                 "gyro_x": round(random.gauss(0, 0.03), 6),
#                 "gyro_y": round(random.gauss(0, 0.03), 6),
#                 "gyro_z": round(random.gauss(0, 0.03), 6),
#             },
#             "heart_rate": {
#                 "ir": random.randint(50000, 80000),
#                 "red": random.randint(40000, 70000),
#                 "hand_detected": True,
#                 "computed_hr": round(72 + random.gauss(0, 2), 1),
#                 "computed_spo2": round(97.5 + random.gauss(0, 0.5), 1),
#             },
#             "timestamp_unified": t,
#             "timestamp_esp": int(t * 1000) % 10000000,
#         },
#         "voice_latest": {
#             "id": 0,
#             "source": "voice",
#             "text": "",
#             "timestamp": t,
#             "timestamp_unified": t,
#         },
#         "last_update_readable": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t)),
#         "radar": {
#             "distance_cm": random.randint(100, 300),
#             "moving": False,
#             "presence": random.randint(100, 200),
#             "stationary": True,
#             "timestamp": t,
#             "timestamp_unified": t,
#         },
#     }


# # ============================================
# # SCENARIO GENERATORS
# # ============================================

# def scenario1_voice(duration_min=3, total_frames=90):
#     """S1: Only voice text changes. All other data stable with minor noise."""
#     voice_idx = 0
#     convos = CONVERSATIONS["normal"] + CONVERSATIONS["pain"]
#     for i in range(total_frames):
#         p = i / total_frames
#         t = time.time() + i * 2
#         frame = make_base_frame(t)
#         # Voice changes every ~5 frames
#         if i % 5 == 0:
#             frame["voice_latest"]["text"] = convos[voice_idx % len(convos)]
#             frame["voice_latest"]["id"] = voice_idx
#             voice_idx += 1
#         else:
#             frame["voice_latest"]["text"] = convos[(voice_idx - 1) % len(convos)]
#             frame["voice_latest"]["id"] = voice_idx - 1
#         yield "EXP3-HW", frame


# def scenario2_deterioration(duration_min=3, total_frames=90):
#     """S2: Patient deterioration — pressure builds, temp rises, HR spikes."""
#     voice_idx = 0
#     for i in range(total_frames):
#         p = i / total_frames  # 0→1 progression
#         t = time.time() + i * 2
#         frame = make_base_frame(t)

#         # Phase progression
#         if p < 0.3:
#             # Stable phase
#             convos = CONVERSATIONS["normal"]
#             temp_add = 0
#             hr_boost = 0
#             pressure_mult = 1.0
#         elif p < 0.6:
#             # Warning phase
#             pp = (p - 0.3) / 0.3
#             convos = CONVERSATIONS["pain"]
#             temp_add = pp * 1.5
#             hr_boost = pp * 30
#             pressure_mult = 1.0 + pp * 2.0
#         else:
#             # Critical phase
#             pp = (p - 0.6) / 0.4
#             convos = CONVERSATIONS["distress"]
#             temp_add = 1.5 + pp * 1.0
#             hr_boost = 30 + pp * 30
#             pressure_mult = 3.0 + pp * 3.0

#         # Apply vitals deterioration
#         frame["hand"]["temperature"]["corrected"] = round(36.5 + temp_add + random.gauss(0, 0.1), 1)
#         frame["hand"]["temperature"]["raw"] = frame["hand"]["temperature"]["corrected"]
#         # HR and SpO2 deterioration
#         frame["hand"]["heart_rate"]["computed_hr"] = round(72 + hr_boost + random.gauss(0, 2), 1)
#         frame["hand"]["heart_rate"]["computed_spo2"] = round(max(85, 97.5 - hr_boost * 0.2 + random.gauss(0, 0.3)), 1)
#         # Increase IR to simulate elevated HR
#         frame["hand"]["heart_rate"]["ir"] = int(60000 + hr_boost * 500)

#         # Pressure buildup on sacral area
#         for key in ["lower_back_left_hip"]:
#             frame["bed_esp1"]["pressures"][key] = int(min(4000, 300 * pressure_mult))
#         for key in ["lower_back_right_hip", "lower_back_center_spine"]:
#             frame["bed_esp2"]["pressures"][key] = int(min(4000, 250 * pressure_mult))

#         # Radar: patient starts moving restlessly in critical phase
#         if p > 0.6:
#             frame["radar"]["moving"] = random.random() > 0.3
#             frame["radar"]["distance_cm"] = random.randint(30, 80)
#             # Bed tilt — patient trying to get up
#             frame["bed_esp1"]["mpu1"]["gyro_x"] = round(random.gauss(0, 1.5 + pp * 3), 3)
#             frame["bed_esp1"]["mpu1"]["gyro_y"] = round(random.gauss(0, 1.0 + pp * 2), 3)
#             frame["bed_esp1"]["mpu1"]["gyro_z"] = round(random.gauss(0, 0.5), 3)
#             # Hand flailing
#             frame["hand"]["movement"]["accel_x"] = round(random.gauss(0, 3 + pp * 8), 3)
#             frame["hand"]["movement"]["accel_y"] = round(random.gauss(0, 3 + pp * 8), 3)
#             frame["hand"]["movement"]["accel_z"] = round(9.8 + random.gauss(0, 2 + pp * 5), 3)
#         elif p > 0.5:
#             # Warning: slight restlessness
#             frame["radar"]["moving"] = random.random() > 0.7
#             frame["radar"]["distance_cm"] = random.randint(60, 150)

#         # Voice
#         if i % 6 == 0:
#             frame["voice_latest"]["text"] = convos[voice_idx % len(convos)]
#             frame["voice_latest"]["id"] = voice_idx
#             voice_idx += 1

#         yield "EXP3-HW", frame


# def scenario3_full(duration_min=3, total_frames=90):
#     """S3: Everything changes — pressure shifts, voice, vitals, posture rotation."""
#     voice_idx = 0
#     posture_cycle = ["supine", "left_lateral", "supine", "right_lateral"]
#     posture_phase = 0
#     frames_in_posture = 0

#     for i in range(total_frames):
#         p = i / total_frames
#         t = time.time() + i * 2
#         frame = make_base_frame(t)

#         # Posture rotation every ~20 frames
#         frames_in_posture += 1
#         if frames_in_posture > 20:
#             posture_phase = (posture_phase + 1) % len(posture_cycle)
#             frames_in_posture = 0

#         current_posture = posture_cycle[posture_phase]

#         # Adjust pressures for posture
#         if current_posture == "left_lateral":
#             frame["bed_esp1"]["pressures"]["upper_back_left_shoulder"] = random.randint(800, 1500)
#             frame["bed_esp1"]["pressures"]["lower_back_left_hip"] = random.randint(1000, 2000)
#             frame["bed_esp1"]["pressures"]["upper_back_right_shoulder"] = random.randint(0, 50)
#             frame["bed_esp2"]["pressures"]["lower_back_right_hip"] = random.randint(0, 50)
#             # MPU tilt
#             frame["bed_esp1"]["mpu1"]["accel_x"] = round(3.0 + random.gauss(0, 0.3), 3)
#             frame["bed_esp1"]["mpu1"]["accel_y"] = round(random.gauss(0, 0.3), 3)
#         elif current_posture == "right_lateral":
#             frame["bed_esp1"]["pressures"]["upper_back_right_shoulder"] = random.randint(800, 1500)
#             frame["bed_esp2"]["pressures"]["lower_back_right_hip"] = random.randint(1000, 2000)
#             frame["bed_esp1"]["pressures"]["upper_back_left_shoulder"] = random.randint(0, 50)
#             frame["bed_esp1"]["pressures"]["lower_back_left_hip"] = random.randint(0, 50)
#             frame["bed_esp1"]["mpu1"]["accel_x"] = round(-3.0 + random.gauss(0, 0.3), 3)
#         else:  # supine
#             frame["bed_esp1"]["mpu1"]["accel_x"] = round(random.gauss(0, 0.3), 3)
#             frame["bed_esp1"]["mpu1"]["accel_y"] = round(-1 + random.gauss(0, 0.3), 3)

#         # Gradual temp increase
#         new_temp = round(36.5 + p * 1.2 + random.gauss(0, 0.1), 1)
#         frame["hand"]["temperature"]["corrected"] = new_temp
#         frame["hand"]["temperature"]["raw"] = new_temp
#         frame["hand"]["heart_rate"]["computed_hr"] = round(72 + p * 15 + random.gauss(0, 2), 1)
#         frame["hand"]["heart_rate"]["computed_spo2"] = round(max(90, 97.5 - p * 3 + random.gauss(0, 0.3)), 1)

#         # Voice: mix of all types
#         all_convos = CONVERSATIONS["normal"] + CONVERSATIONS["pain"] + CONVERSATIONS["distress"]
#         if i % 4 == 0:
#             frame["voice_latest"]["text"] = all_convos[voice_idx % len(all_convos)]
#             frame["voice_latest"]["id"] = voice_idx
#             voice_idx += 1

#         yield "EXP3-HW", frame


# # ============================================
# # WRITER: Save frames to data/incoming/
# # ============================================

# def run_scenario(scenario_num: int, duration_min: float = 3, speed: float = 4):
#     """Run a scenario and write frames to data/incoming/."""
#     os.makedirs(DATA_DIR, exist_ok=True)

#     interval = 2.0 / speed
#     total_frames = int(duration_min * 60 / 2.0)

#     generators = {1: scenario1_voice, 2: scenario2_deterioration, 3: scenario3_full}
#     gen_func = generators.get(scenario_num)
#     if not gen_func:
#         print(f"Unknown scenario: {scenario_num}")
#         return

#     names = {1: "Voice Changes Only", 2: "Patient Deterioration", 3: "Full Data Changes"}

#     print("=" * 50, flush=True)
#     print(f"  SCENARIO {scenario_num}: {names[scenario_num]}", flush=True)
#     print("=" * 50, flush=True)
#     print(f"  Duration: {duration_min}min | Speed: {speed}x | Frames: {total_frames}", flush=True)
#     print(f"  Output: {DATA_DIR}", flush=True)
#     print("=" * 50, flush=True)

#     gen = gen_func(duration_min, total_frames)
#     written = []
#     voice_log = []

#     for i, (pid, frame) in enumerate(gen):
#         # Write merged_data.json (overwrite - like real hardware)
#         fpath = os.path.join(DATA_DIR, "merged_data.json")
#         with open(fpath, "w") as f:
#             json.dump(frame, f, indent=2)

#         # Also write patient profile
#         prof_path = os.path.join(DATA_DIR, f"{pid}_profile.json")
#         if not os.path.exists(prof_path):
#             prof = {
#                 "patient_id": pid,
#                 "name": "Seongjun Choi",
#                 "age": 72,
#                 "height_cm": 170,
#                 "weight_kg": 78,
#                 "room": "ICU-301",
#                 "surgery_type": "Hip Replacement",
#                 "post_op_day": 2,
#                 "is_diabetic": True,
#                 "has_cardiovascular_risk": True,
#                 "mobility_level": "bed_bound",
#                 "assigned_nurse": "Nurse Park",
#                 "assigned_doctor": "Dr. Kim",
#                 "surgical_history": ["Appendectomy (2018)"],
#                 "lab_results": [{"test": "CBC", "time": "-3h", "wbc": "12.1", "hgb": "11.2", "plt": "198", "status": "elevated WBC"}],
#                 "medications": ["Morphine 2mg IV q4h PRN", "Cefazolin 1g IV q8h", "Enoxaparin 40mg SC daily"],
#                 "allergies": ["Penicillin (rash)"],
#             }
#             with open(prof_path, "w") as f:
#                 json.dump(prof, f, indent=2)

#         # Log
#         voice_text = frame.get("voice_latest", {}).get("text", "")
#         temp = frame["hand"]["temperature"]["corrected"]
#         pressures = frame["bed_esp1"]["pressures"]
#         hip_p = pressures.get("lower_back_left_hip", 0)
#         moving = frame["radar"]["moving"]

#         if i % 6 == 0 or voice_text:
#             phase = ""
#             if scenario_num == 2:
#                 p = i / total_frames
#                 phase = " [stable]" if p < 0.3 else " [warning]" if p < 0.6 else " [CRITICAL]"

#             print(f"  [{i*2/60:.1f}m] f#{i:03d} T:{temp}° Hip:{hip_p} Mov:{'Y' if moving else 'N'}{phase}")
#             if voice_text and i % 6 == 0:
#                 print(f"         💬 \"{voice_text[:60]}\"")

#         # Collect voice for summary
#         if voice_text:
#             voice_log.append({"frame": i, "text": voice_text, "time": f"{i*2/60:.1f}m"})

#         if "merged_data.json" not in written:
#             written.append("merged_data.json")

#         time.sleep(interval)

#     # Write voice log for AI agent
#     vlog_path = os.path.join(DATA_DIR, "voice_log.json")
#     with open(vlog_path, "w") as f:
#         json.dump(voice_log, f, indent=2)

#     print(f"\n  SCENARIO {scenario_num} COMPLETE")
#     print(f"  Voice entries: {len(voice_log)}")
#     print(f"  Output: {DATA_DIR}/merged_data.json")
#     print(f"  Files remain in {DATA_DIR}/ for server to read.")
#     print(f"  Done!", flush=True)


# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(description="VitalGuard Hardware Simulator")
#     parser.add_argument("--scenario", type=int, required=True, choices=[1, 2, 3])
#     parser.add_argument("--duration", type=float, default=3, help="Duration in minutes")
#     parser.add_argument("--speed", type=float, default=4, help="Speed multiplier")
#     args = parser.parse_args()

#     run_scenario(args.scenario, args.duration, args.speed)
"""
Hardware Simulator
==================
Generates sensor data in the EXACT same format as real hardware merged_data.json.

Scenarios:
  S1: Risk escalation — vitals worsen, card rises to top (verify sorting)
  S2: Voice changes — speech text updates, verify AI summary
  S3: Fall risk — radar+MPU+hand triggers fall alert on sidebar
  S4: Final demo — continuous infinite loop, all features cycling

Usage:
  python data/hw_simulator.py --scenario 1 --speed 4
  python data/hw_simulator.py --scenario 2 --speed 4
  python data/hw_simulator.py --scenario 3 --speed 4
  python data/hw_simulator.py --scenario 4 --speed 2   # infinite, Ctrl+C to stop

With server (hybrid mode):
  Terminal 1: python -m api.server --hybrid --speed 4 --duration 10
  Terminal 2: python data/hw_simulator.py --scenario 4 --speed 2
"""

import json
import os
import sys
import time
import random
import math
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "incoming")

CONVERSATIONS = {
    "normal": [
        "I'm feeling okay, just a little tired.",
        "Can I get some water please?",
        "The bed is comfortable enough.",
        "My family is coming to visit later today.",
        "What time is dinner?",
        "I slept pretty well last night.",
        "The nurse was very helpful this morning.",
        "I'm watching the news right now.",
    ],
    "pain": [
        "My back is really hurting right now.",
        "The pain is getting worse, can someone help?",
        "I can't get comfortable in this position.",
        "It hurts when I try to move.",
        "I need pain medication, it's really bad.",
        "The pressure on my hip is unbearable.",
        "I'm in a lot of pain, please help me.",
        "Can you reposition me? This is very painful.",
    ],
    "distress": [
        "I feel dizzy, something is wrong.",
        "I can't breathe properly, help!",
        "My chest feels tight.",
        "I think I'm going to fall, help me!",
        "I'm feeling very nauseous and weak.",
        "Something doesn't feel right at all.",
        "I need a doctor right now!",
        "Help! I think I'm falling off the bed!",
    ],
}


def make_base_frame(t):
    return {
        "last_update": t,
        "bed_esp1": {
            "module": "bed_esp1",
            "pressures": {
                "head_left": random.randint(0, 50),
                "head_center": random.randint(20, 80),
                "head_right": random.randint(0, 50),
                "upper_back_left_shoulder": random.randint(100, 300),
                "upper_back_right_shoulder": random.randint(100, 300),
                "lower_back_left_hip": random.randint(200, 500),
            },
            "temperatures": {
                "temp_1": round(22 + random.gauss(0, 0.3), 4),
                "temp_2": round(22 + random.gauss(0, 0.3), 4),
                "temp_3": round(22 + random.gauss(0, 0.3), 4),
            },
            "mpu1": {
                "accel_x": round(random.gauss(0, 0.3), 6),
                "accel_y": round(random.gauss(-1, 0.3), 6),
                "accel_z": round(9.8 + random.gauss(0, 0.2), 6),
                "gyro_x": round(random.gauss(0, 0.05), 6),
                "gyro_y": round(random.gauss(0, 0.05), 6),
                "gyro_z": round(random.gauss(0, 0.05), 6),
            },
            "mpu2": {
                "accel_x": round(random.gauss(0, 0.3), 6),
                "accel_y": round(random.gauss(-0.5, 0.3), 6),
                "accel_z": round(9.8 + random.gauss(0, 0.2), 6),
                "gyro_x": round(random.gauss(0, 0.03), 6),
                "gyro_y": round(random.gauss(0, 0.03), 6),
                "gyro_z": round(random.gauss(0, 0.03), 6),
            },
            "timestamp_unified": t,
            "timestamp_esp": int(t * 1000) % 10000000,
        },
        "bed_esp2": {
            "module": "bed_esp2",
            "pressures": {
                "lower_back_right_hip": random.randint(200, 500),
                "upper_leg_left_thigh": random.randint(50, 200),
                "upper_leg_right_thigh": random.randint(50, 200),
                "lower_leg_left_calf": random.randint(0, 100),
                "lower_leg_right_calf": random.randint(0, 100),
                "lower_back_center_spine": random.randint(100, 300),
            },
            "timestamp_unified": t,
            "timestamp_esp": int(t * 1000) % 10000000,
        },
        "hand": {
            "module": "hand",
            "temperature": {
                "raw": round(36.5 + random.gauss(0, 0.2), 4),
                "corrected": round(36.5 + random.gauss(0, 0.2), 4),
                "status": "ok",
            },
            "movement": {
                "accel_x": round(random.gauss(0, 0.5), 6),
                "accel_y": round(random.gauss(0, 0.5), 6),
                "accel_z": round(9.8 + random.gauss(0, 0.3), 6),
                "gyro_x": round(random.gauss(0, 0.03), 6),
                "gyro_y": round(random.gauss(0, 0.03), 6),
                "gyro_z": round(random.gauss(0, 0.03), 6),
            },
            "heart_rate": {
                "ir": random.randint(50000, 80000),
                "red": random.randint(40000, 70000),
                "hand_detected": True,
                "computed_hr": round(72 + random.gauss(0, 2), 1),
                "computed_spo2": round(97.5 + random.gauss(0, 0.5), 1),
            },
            "timestamp_unified": t,
            "timestamp_esp": int(t * 1000) % 10000000,
        },
        "voice_latest": {
            "id": 0, "source": "voice", "text": "",
            "timestamp": t, "timestamp_unified": t,
        },
        "last_update_readable": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t)),
        "radar": {
            "distance_cm": random.randint(100, 300),
            "moving": False, "presence": random.randint(100, 200),
            "stationary": True, "timestamp": t, "timestamp_unified": t,
        },
    }


# ── S1: Risk Escalation ──
def scenario1_risk(total_frames=90):
    voice_idx = 0
    for i in range(total_frames):
        p = i / total_frames
        t = time.time() + i * 2
        frame = make_base_frame(t)
        if p < 0.3:
            hr, spo2, temp, convos = 72, 97.5, 36.5, CONVERSATIONS["normal"]
        elif p < 0.6:
            pp = (p - 0.3) / 0.3
            hr, spo2, temp = 72 + pp * 28, 97.5 - pp * 4, 36.5 + pp * 1.3
            convos = CONVERSATIONS["pain"]
            frame["bed_esp1"]["pressures"]["lower_back_left_hip"] = int(300 + pp * 1500)
            frame["bed_esp2"]["pressures"]["lower_back_right_hip"] = int(250 + pp * 1200)
        else:
            pp = (p - 0.6) / 0.4
            hr, spo2, temp = 100 + pp * 30, 93.5 - pp * 6, 37.8 + pp * 1.2
            convos = CONVERSATIONS["distress"]
            frame["bed_esp1"]["pressures"]["lower_back_left_hip"] = int(1800 + pp * 2000)
            frame["bed_esp2"]["pressures"]["lower_back_right_hip"] = int(1450 + pp * 1800)
        frame["hand"]["heart_rate"]["computed_hr"] = round(hr + random.gauss(0, 2), 1)
        frame["hand"]["heart_rate"]["computed_spo2"] = round(max(85, spo2 + random.gauss(0, 0.3)), 1)
        frame["hand"]["temperature"]["corrected"] = round(temp + random.gauss(0, 0.1), 1)
        frame["hand"]["temperature"]["raw"] = frame["hand"]["temperature"]["corrected"]
        if i % 8 == 0:
            frame["voice_latest"]["text"] = convos[voice_idx % len(convos)]
            frame["voice_latest"]["id"] = voice_idx
            voice_idx += 1
        yield "EXP3-HW", frame


# ── S2: Voice Summary ──
def scenario2_voice(total_frames=90):
    voice_idx = 0
    script = CONVERSATIONS["normal"][:4] + CONVERSATIONS["pain"] + CONVERSATIONS["distress"][:4]
    for i in range(total_frames):
        t = time.time() + i * 2
        frame = make_base_frame(t)
        frame["hand"]["heart_rate"]["computed_hr"] = round(72 + (i / total_frames) * 10 + random.gauss(0, 2), 1)
        frame["hand"]["temperature"]["corrected"] = round(36.5 + (i / total_frames) * 0.5 + random.gauss(0, 0.1), 1)
        frame["hand"]["temperature"]["raw"] = frame["hand"]["temperature"]["corrected"]
        if i % 4 == 0:
            frame["voice_latest"]["text"] = script[voice_idx % len(script)]
            frame["voice_latest"]["id"] = voice_idx
            voice_idx += 1
        yield "EXP3-HW", frame


# ── S3: Fall Risk ──
def scenario3_fall(total_frames=90):
    voice_idx = 0
    for i in range(total_frames):
        p = i / total_frames
        t = time.time() + i * 2
        frame = make_base_frame(t)
        if p < 0.4:
            convos = CONVERSATIONS["normal"]
        elif p < 0.7:
            pp = (p - 0.4) / 0.3
            convos = CONVERSATIONS["pain"]
            frame["radar"]["moving"] = random.random() > 0.5
            frame["radar"]["distance_cm"] = int(200 - pp * 160)
            frame["bed_esp1"]["mpu1"]["gyro_x"] = round(random.gauss(0, 0.5 + pp * 2), 3)
            frame["bed_esp1"]["mpu1"]["gyro_y"] = round(random.gauss(0, 0.3 + pp * 1), 3)
            frame["hand"]["heart_rate"]["computed_hr"] = round(80 + pp * 20 + random.gauss(0, 2), 1)
        else:
            pp = (p - 0.7) / 0.3
            convos = CONVERSATIONS["distress"]
            frame["radar"]["moving"] = True
            frame["radar"]["distance_cm"] = random.randint(20, 50)
            frame["bed_esp1"]["mpu1"]["gyro_x"] = round(random.gauss(0, 2 + pp * 5), 3)
            frame["bed_esp1"]["mpu1"]["gyro_y"] = round(random.gauss(0, 1.5 + pp * 3), 3)
            frame["bed_esp1"]["mpu1"]["gyro_z"] = round(random.gauss(0, 1), 3)
            frame["hand"]["movement"]["accel_x"] = round(random.gauss(0, 5 + pp * 10), 3)
            frame["hand"]["movement"]["accel_y"] = round(random.gauss(0, 5 + pp * 10), 3)
            frame["hand"]["movement"]["accel_z"] = round(9.8 + random.gauss(0, 3 + pp * 8), 3)
            frame["hand"]["heart_rate"]["computed_hr"] = round(100 + pp * 30 + random.gauss(0, 3), 1)
            frame["hand"]["heart_rate"]["computed_spo2"] = round(max(88, 96 - pp * 6 + random.gauss(0, 0.5)), 1)
        if i % 5 == 0:
            frame["voice_latest"]["text"] = convos[voice_idx % len(convos)]
            frame["voice_latest"]["id"] = voice_idx
            voice_idx += 1
        yield "EXP3-HW", frame


# ── S4: Final Demo (infinite) ──
def scenario4_final():
    voice_idx = 0
    i = 0
    cycle_frames = 210  # ~7min per cycle at 2s intervals
    while True:
        cp = (i % cycle_frames) / cycle_frames
        t = time.time()
        frame = make_base_frame(t)
        if cp < 0.28:
            phase = "STABLE"
            hr, spo2, temp, convos = 72, 97.5, 36.5, CONVERSATIONS["normal"]
        elif cp < 0.57:
            phase = "WARNING"
            pp = (cp - 0.28) / 0.29
            hr, spo2, temp = 72 + pp * 28, 97.5 - pp * 4, 36.5 + pp * 1.3
            convos = CONVERSATIONS["pain"]
            frame["bed_esp1"]["pressures"]["lower_back_left_hip"] = int(300 + pp * 1500)
            frame["bed_esp2"]["pressures"]["lower_back_right_hip"] = int(250 + pp * 1200)
            frame["radar"]["moving"] = random.random() > 0.7
        elif cp < 0.85:
            phase = "CRITICAL"
            pp = (cp - 0.57) / 0.28
            hr, spo2, temp = 100 + pp * 30, 93.5 - pp * 6, 37.8 + pp * 1.2
            convos = CONVERSATIONS["distress"]
            frame["bed_esp1"]["pressures"]["lower_back_left_hip"] = int(1800 + pp * 2000)
            frame["bed_esp2"]["pressures"]["lower_back_right_hip"] = int(1450 + pp * 1800)
            frame["radar"]["moving"] = True
            frame["radar"]["distance_cm"] = random.randint(20, 60)
            frame["bed_esp1"]["mpu1"]["gyro_x"] = round(random.gauss(0, 2 + pp * 4), 3)
            frame["bed_esp1"]["mpu1"]["gyro_y"] = round(random.gauss(0, 1.5 + pp * 3), 3)
            frame["hand"]["movement"]["accel_x"] = round(random.gauss(0, 4 + pp * 8), 3)
            frame["hand"]["movement"]["accel_y"] = round(random.gauss(0, 4 + pp * 8), 3)
            frame["hand"]["movement"]["accel_z"] = round(9.8 + random.gauss(0, 2 + pp * 5), 3)
        else:
            phase = "RECOVERY"
            pp = (cp - 0.85) / 0.15
            hr, spo2, temp = 130 - pp * 58, 87.5 + pp * 10, 39.0 - pp * 2.5
            convos = CONVERSATIONS["normal"]
        frame["hand"]["heart_rate"]["computed_hr"] = round(hr + random.gauss(0, 2), 1)
        frame["hand"]["heart_rate"]["computed_spo2"] = round(max(85, spo2 + random.gauss(0, 0.3)), 1)
        frame["hand"]["temperature"]["corrected"] = round(temp + random.gauss(0, 0.1), 1)
        frame["hand"]["temperature"]["raw"] = frame["hand"]["temperature"]["corrected"]
        if i % 5 == 0:
            frame["voice_latest"]["text"] = convos[voice_idx % len(convos)]
            frame["voice_latest"]["id"] = voice_idx
            voice_idx += 1
        yield "EXP3-HW", frame, phase
        i += 1


# ── WRITER ──
PATIENT_PROFILE = {
    "patient_id": "EXP3-HW",
    "name": "TESTER",
    "age": 72, "height_cm": 170, "weight_kg": 78,
    "room": "ICU-301", "surgery_type": "Hip Replacement", "post_op_day": 2,
    "is_diabetic": True, "has_cardiovascular_risk": True, "mobility_level": "bed_bound",
    "assigned_nurse": "Nurse Park", "assigned_doctor": "Dr. Kim",
    "surgical_history": ["Appendectomy (2018)"],
    "lab_results": [{"test": "CBC", "time": "-3h", "wbc": "12.1", "hgb": "11.2", "plt": "198", "status": "elevated WBC"}],
    "medications": ["Morphine 2mg IV q4h PRN", "Cefazolin 1g IV q8h", "Enoxaparin 40mg SC daily"],
    "allergies": ["Penicillin (rash)"],
}


def run_scenario(scenario_num, duration_min=3, speed=4):
    os.makedirs(DATA_DIR, exist_ok=True)
    interval = 2.0 / speed
    is_infinite = (scenario_num == 4)
    total_frames = None if is_infinite else int(duration_min * 60 / 2.0)

    generators = {1: scenario1_risk, 2: scenario2_voice, 3: scenario3_fall, 4: scenario4_final}
    names = {
        1: "Risk Escalation -> Card Sorting",
        2: "Voice Changes -> AI Summary",
        3: "Fall Risk Detection -> Sidebar Alert",
        4: "Final Demo (infinite, Ctrl+C to stop)",
    }

    print("=" * 60, flush=True)
    print(f"  SCENARIO {scenario_num}: {names[scenario_num]}", flush=True)
    print("=" * 60, flush=True)
    if is_infinite:
        print(f"  Mode: INFINITE | Speed: {speed}x | Ctrl+C to stop", flush=True)
        print(f"  Cycle: Stable(2m) -> Warning(2m) -> Critical+Fall(2m) -> Recovery(1m)", flush=True)
    else:
        print(f"  Duration: {duration_min}min | Speed: {speed}x | Frames: {total_frames}", flush=True)
    print(f"  Output: {DATA_DIR}/merged_data.json", flush=True)
    print("=" * 60, flush=True)

    with open(os.path.join(DATA_DIR, "EXP3-HW_profile.json"), "w") as f:
        json.dump(PATIENT_PROFILE, f, indent=2)

    gen = generators[scenario_num]() if is_infinite else generators[scenario_num](total_frames)
    voice_log = []
    fc = 0
    last_phase = ""

    try:
        for item in gen:
            if is_infinite:
                pid, frame, phase = item
            else:
                pid, frame = item
                p = fc / total_frames if total_frames else 0
                if scenario_num == 1:
                    phase = "STABLE" if p < 0.3 else "WARNING" if p < 0.6 else "CRITICAL"
                elif scenario_num == 3:
                    phase = "CALM" if p < 0.4 else "RESTLESS" if p < 0.7 else "FALL DANGER"
                else:
                    phase = ""

            with open(os.path.join(DATA_DIR, "merged_data.json"), "w") as f:
                json.dump(frame, f, indent=2)

            vt = frame.get("voice_latest", {}).get("text", "")
            if vt:
                voice_log.append({"frame": fc, "text": vt, "time": f"{fc*2/60:.1f}m"})

            temp = frame["hand"]["temperature"]["corrected"]
            hr = frame["hand"]["heart_rate"].get("computed_hr", "?")
            hip = frame["bed_esp1"]["pressures"].get("lower_back_left_hip", 0)
            mov = frame["radar"]["moving"]
            dist = frame["radar"]["distance_cm"]

            if phase != last_phase:
                print(f"\n  >>> Phase: {phase}", flush=True)
                last_phase = phase

            if fc % 6 == 0:
                extra = ""
                if scenario_num in (3, 4) and (mov or dist < 80):
                    extra = f" | RADAR:{dist}cm {'!!!MOVING' if mov else ''}"
                print(f"  [{fc*2/60:.1f}m] f#{fc:03d} HR:{hr} T:{temp} Hip:{hip}{extra}", flush=True)
                if vt:
                    print(f"         💬 \"{vt[:55]}\"", flush=True)

            fc += 1
            if not is_infinite and fc >= total_frames:
                break
            time.sleep(interval)

    except KeyboardInterrupt:
        print(f"\n  Stopped at frame {fc}.", flush=True)

    with open(os.path.join(DATA_DIR, "voice_log.json"), "w") as f:
        json.dump(voice_log, f, indent=2)

    print(f"\n  SCENARIO {scenario_num} COMPLETE", flush=True)
    print(f"  Frames: {fc} | Voice: {len(voice_log)} entries", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VitalGuard Hardware Simulator")
    parser.add_argument("--scenario", type=int, required=True, choices=[1, 2, 3, 4])
    parser.add_argument("--duration", type=float, default=3, help="Duration in min (ignored for S4)")
    parser.add_argument("--speed", type=float, default=4, help="Speed multiplier")
    args = parser.parse_args()
    run_scenario(args.scenario, args.duration, args.speed)