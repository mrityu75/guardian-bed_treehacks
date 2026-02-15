#!/usr/bin/env python3
"""
VitalGuard Live Experiment Runner
====================================
Runs experiments in real-time with:
- Live encryption logging (every frame)
- Dashboard-ready JSON output via API
- Email alert triggering
- Detailed phase tracking

Usage:
    python experiments/run_live.py --exp 1          # Experiment 1 only
    python experiments/run_live.py --exp 2          # Experiment 2 only
    python experiments/run_live.py --exp all        # Both experiments
    python experiments/run_live.py --exp 1 --speed 4  # 4x speed
"""

import sys
import os
import json
import time
import argparse
import asyncio
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scenarios import experiment_1_normal_to_critical, experiment_2_pressure_and_posture
from analysis.risk_engine import RiskEngine
from analysis.pressure import compute_zone_scores
from digital_twin.twin_state import DigitalTwin
from alerts.alert_manager import AlertManager
from alerts.email_notifier import EmailNotifier
from security.quantum_crypto import SecureChannel
from reporting.groq_report import generate_report


# Terminal colors
class C:
    R = "\033[91m"   # Red
    G = "\033[92m"   # Green
    Y = "\033[93m"   # Yellow
    B = "\033[94m"   # Blue
    M = "\033[95m"   # Magenta
    CY = "\033[96m"  # Cyan
    W = "\033[97m"   # White
    D = "\033[90m"   # Dim
    BOLD = "\033[1m"
    END = "\033[0m"


def level_color(level):
    if level in ("critical", "warning"):
        return C.R
    elif level == "caution":
        return C.Y
    return C.G


def risk_bar(score, width=20):
    filled = int(score / 100 * width)
    bar = "█" * filled + "░" * (width - filled)
    color = C.R if score > 60 else C.Y if score > 30 else C.G
    return f"{color}{bar}{C.END}"


def run_experiment(exp_num, frames, patient, speed=1.0, enable_email=True):
    """
    Run a single experiment with real-time logging.
    """
    print(f"\n{C.BOLD}{'═' * 64}{C.END}")
    print(f"{C.BOLD}{C.CY}  EXPERIMENT {exp_num}: {patient.name} ({patient.patient_id}){C.END}")
    print(f"{C.D}  Surgery: {patient.surgery_type} | Day: {patient.post_op_day} | Age: {patient.age}{C.END}")
    print(f"{C.D}  Doctor: {patient.assigned_doctor} | Nurse: {patient.assigned_nurse}{C.END}")
    print(f"{C.D}  Frames: {len(frames)} | Speed: {speed}x{C.END}")
    print(f"{C.BOLD}{'═' * 64}{C.END}\n")

    # Initialize pipeline
    engine = RiskEngine(patient)
    twin = DigitalTwin(patient)

    # Email notifier (real if configured)
    email = EmailNotifier()
    notifiers = [email] if enable_email else []
    alert_mgr = AlertManager(notifiers=notifiers)

    # Quantum encryption channel
    server_ch = SecureChannel()
    client_ch = SecureChannel()
    server_info = server_ch.init_server()
    client_resp = client_ch.init_client(server_info["public_key"])
    server_ch.complete_handshake(client_resp["ciphertext"])

    print(f"{C.B}  🔐 Quantum channel established{C.END}")
    print(f"{C.D}     Algorithm: {server_info['algorithm']}")
    print(f"     Session: {server_info['session_id'][:16]}...{C.END}\n")

    # Tracking
    interval = 2.0 / speed
    total_frames = len(frames)
    phase_names = {1: "Phase 1", 2: "Phase 2", 3: "Phase 3", 4: "Phase 4", 5: "Phase 5"}
    last_phase = None
    last_level = None
    alerts_sent = []
    encryption_log = []

    # Phase definitions per experiment
    if exp_num == 1:
        phases = [
            (0.0, 0.4, "STABLE — Normal vitals, low risk"),
            (0.4, 0.6, "TRANSITION — Vitals deteriorating"),
            (0.6, 0.8, "WARNING — Elevated risk, monitoring"),
            (0.8, 1.0, "CRITICAL — Immediate intervention needed"),
        ]
    else:
        phases = [
            (0.0, 0.25, "NORMAL — Low pressure, supine"),
            (0.25, 0.50, "BUILDING — Pressure increasing"),
            (0.50, 0.65, "OVERDUE — Reposition needed"),
            (0.65, 0.75, "REPOSITION — Changing posture"),
            (0.75, 1.0, "RELIEF — Pressure decreasing"),
        ]

    start_time = time.time()

    for i, frame in enumerate(frames):
        progress = i / total_frames
        elapsed_min = i * 2.0 / 60  # simulated time in minutes

        # Determine current phase
        current_phase = None
        for pi, (ps, pe, pname) in enumerate(phases):
            if ps <= progress < pe:
                current_phase = (pi + 1, pname)
                break
        if current_phase is None:
            current_phase = (len(phases), phases[-1][2])

        # Phase change announcement
        if current_phase[0] != last_phase:
            last_phase = current_phase[0]
            phase_color = C.G if current_phase[0] <= 1 else C.Y if current_phase[0] <= 2 else C.R
            print(f"\n{phase_color}{C.BOLD}  ▶ Phase {current_phase[0]}: {current_phase[1]}{C.END}")
            print(f"{C.D}    Time: {elapsed_min:.1f} min | Frame: {i}/{total_frames}{C.END}\n")

        # === PIPELINE ===

        # 1. Analysis
        assessment = engine.assess(frame)
        risk_score = assessment.get("risk_score", 0)
        risk_level = assessment.get("risk_level", "info")

        # 2. Twin update
        bed = frame.get("bed", {})
        fsr_values = bed.get("fsrs", [0] * 12)
        duration = frame.get("vitals_snapshot", {}).get("posture_duration_min", 0)
        zone_scores = compute_zone_scores(fsr_values, duration, patient.pressure_multiplier)
        twin.update_pressure_zones(zone_scores)
        twin.update_from_assessment(assessment)

        # 3. Encrypt
        dashboard_state = twin.to_dashboard_state()
        t0 = time.time()
        envelope = server_ch.encrypt_patient_data(dashboard_state)
        decrypted = client_ch.decrypt_patient_data(envelope)
        enc_ms = (time.time() - t0) * 1000

        enc_entry = {
            "frame": i,
            "time_min": round(elapsed_min, 2),
            "risk": round(risk_score, 1),
            "level": risk_level,
            "encrypted_bytes": len(json.dumps(envelope)),
            "enc_ms": round(enc_ms, 3),
            "mac": envelope["encrypted"]["mac"][:12] + "...",
            "nonce": envelope["encrypted"]["nonce"][:12] + "...",
            "verified": decrypted is not None,
        }
        encryption_log.append(enc_entry)

        # 4. Alert check
        alert_result = alert_mgr.evaluate(assessment)

        # === LOGGING ===

        # Every 15 frames (~30 sec simulated), print status
        if i % 15 == 0:
            vs = frame.get("vitals_snapshot", {})
            hr = vs.get("heart_rate", 0)
            sp = vs.get("spo2", 0)
            tp = vs.get("body_temp", 0)
            hrv_val = vs.get("hrv", 0)
            rr = vs.get("resp_rate", 0)
            posture = vs.get("posture", "?")
            pos_dur = vs.get("posture_duration_min", 0)

            lc = level_color(risk_level)
            rbar = risk_bar(risk_score)

            print(f"  {C.D}[{elapsed_min:5.1f}m]{C.END} "
                  f"Risk: {rbar} {lc}{risk_score:5.1f}{C.END} "
                  f"HR:{C.W}{hr:5.1f}{C.END} "
                  f"SpO2:{C.W}{sp:5.1f}{C.END} "
                  f"T:{C.W}{tp:5.2f}{C.END} "
                  f"HRV:{C.W}{hrv_val:4.1f}{C.END} "
                  f"RR:{C.W}{rr:4.1f}{C.END} "
                  f"{C.D}[{posture}/{pos_dur:.0f}m]{C.END}")

        # Encryption log every 30 frames
        if i % 30 == 0 and i > 0:
            e = enc_entry
            print(f"  {C.B}  🔐 Encrypted: {e['encrypted_bytes']}B | "
                  f"{e['enc_ms']:.2f}ms | MAC:{e['mac']} | "
                  f"{'✓' if e['verified'] else '✗'}{C.END}")

        # Level change
        if risk_level != last_level and last_level is not None:
            color = level_color(risk_level)
            print(f"\n  {color}{C.BOLD}  ⚠ STATUS CHANGE: {last_level.upper()} → {risk_level.upper()} "
                  f"(Risk: {risk_score:.1f}){C.END}")
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"  {C.D}    Timestamp: {ts}{C.END}\n")
        last_level = risk_level

        # Alert fired
        if alert_result["should_alert"]:
            ts = datetime.now().strftime("%H:%M:%S")
            sent_count = alert_result.get("alerts_sent", 0)
            if isinstance(sent_count, list):
                sent_count = len(sent_count)
            alerts_sent.append({
                "time": ts,
                "frame": i,
                "risk": round(risk_score, 1),
                "level": risk_level,
                "reason": alert_result["reason"],
                "emails": sent_count,
            })
            print(f"\n  {C.R}{C.BOLD}  🚨 ALERT FIRED at {ts}{C.END}")
            print(f"  {C.R}     Risk: {risk_score:.1f} | Level: {risk_level}")
            print(f"     Reason: {alert_result['reason']}")
            if sent_count > 0:
                print(f"     📧 Email sent! ({sent_count} notification(s))")
            print(f"{C.END}")

        # Pace the simulation
        time.sleep(interval)

    elapsed_real = time.time() - start_time

    # === FINAL SUMMARY ===
    print(f"\n{C.BOLD}{'─' * 64}{C.END}")
    print(f"{C.BOLD}  EXPERIMENT {exp_num} COMPLETE{C.END}")
    print(f"{'─' * 64}")
    print(f"  Duration: {elapsed_real:.1f}s real | {len(frames)*2/60:.1f}min simulated")
    print(f"  Final risk: {risk_score:.1f}/100 ({risk_level})")
    print(f"  Alerts: {len(alerts_sent)}")
    print(f"  Encrypted frames: {len(encryption_log)}")
    print(f"  Avg encryption: {sum(e['enc_ms'] for e in encryption_log)/len(encryption_log):.2f}ms")

    if alerts_sent:
        print(f"\n  {C.R}Alert Timeline:{C.END}")
        for a in alerts_sent:
            print(f"    [{a['time']}] Risk {a['risk']} — {a['reason']}")

    # Save results
    results = {
        "experiment": exp_num,
        "patient": patient.patient_id,
        "timestamp": datetime.now().isoformat(),
        "frames_total": len(frames),
        "duration_real_sec": round(elapsed_real, 2),
        "final_risk": round(risk_score, 1),
        "final_level": risk_level,
        "alerts": alerts_sent,
        "encryption_samples": encryption_log[::30],  # Every 30th entry
    }

    out_dir = os.path.join(os.path.dirname(__file__), "..")
    out_path = os.path.join(out_dir, f"experiment_{exp_num}_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved: experiment_{exp_num}_results.json")

    return results


def main():
    parser = argparse.ArgumentParser(description="VitalGuard Live Experiments")
    parser.add_argument("--exp", default="all", choices=["1", "2", "all"])
    parser.add_argument("--duration", type=int, default=8, help="Duration per experiment (minutes)")
    parser.add_argument("--speed", type=float, default=2.0, help="Playback speed multiplier")
    parser.add_argument("--no-email", action="store_true", help="Disable email alerts")
    args = parser.parse_args()

    print(f"\n{C.BOLD}{C.CY}╔══════════════════════════════════════════════════════════════╗{C.END}")
    print(f"{C.BOLD}{C.CY}║         VitalGuard — Live Experiment Runner                  ║{C.END}")
    print(f"{C.BOLD}{C.CY}╚══════════════════════════════════════════════════════════════╝{C.END}")
    print(f"\n{C.D}  Experiments: {args.exp} | Duration: {args.duration}min | Speed: {args.speed}x{C.END}")
    print(f"{C.D}  Email alerts: {'OFF' if args.no_email else 'ON'}{C.END}")

    if args.exp in ("1", "all"):
        frames, patient = experiment_1_normal_to_critical(
            duration_min=args.duration, interval_sec=2.0
        )
        run_experiment(1, frames, patient, speed=args.speed, enable_email=not args.no_email)

    if args.exp in ("2", "all"):
        frames, patient = experiment_2_pressure_and_posture(
            duration_min=args.duration, interval_sec=2.0
        )
        run_experiment(2, frames, patient, speed=args.speed, enable_email=not args.no_email)

    print(f"\n{C.BOLD}{C.G}  All experiments complete! ✓{C.END}\n")


if __name__ == "__main__":
    main()