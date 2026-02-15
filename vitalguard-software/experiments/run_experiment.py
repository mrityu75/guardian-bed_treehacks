#!/usr/bin/env python3
"""
VitalGuard End-to-End Experiment Runner
=========================================
Runs the complete pipeline and generates a comprehensive results report.

Pipeline:
  ESP32 Sensors → Synthetic Data → Analysis Engine → Risk Scoring
  → Digital Twin → Quantum Encryption → LLM Report → Email Alerts

Usage:
    python scripts/run_experiment.py
    python scripts/run_experiment.py --scenario C --duration 30
"""

import sys
import os
import json
import time
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config.patient_profiles import PatientProfile
from synthetic.scenarios import scenario_a_stable, scenario_b_gradual, scenario_c_acute
from analysis.risk_engine import RiskEngine
from analysis.pressure import compute_zone_scores
from digital_twin.twin_state import DigitalTwin
from digital_twin.stress_model import StressModel
from alerts.alert_manager import AlertManager
from alerts.email_notifier import EmailNotifier
from reporting.groq_report import generate_report, generate_fallback_report
from security.quantum_crypto import SecureChannel, QuantumCipher


def run_scenario(name, frames, patient, encrypt=True):
    """Run a single scenario through the full pipeline."""
    print(f"\n{'─' * 50}")
    print(f"  Scenario {name}: {patient.name} ({patient.patient_id})")
    print(f"  Surgery: {patient.surgery_type} | Day: {patient.post_op_day}")
    print(f"  Frames: {len(frames)} | Duration: {len(frames)*2/60:.0f} min")
    print(f"{'─' * 50}")

    engine = RiskEngine(patient)
    twin = DigitalTwin(patient)
    stress = StressModel()
    alert_mgr = AlertManager(notifiers=[])  # No email in experiment
    
    # Setup encryption
    server_channel = None
    client_channel = None
    if encrypt:
        server_channel = SecureChannel()
        client_channel = SecureChannel()
        server_info = server_channel.init_server()
        client_resp = client_channel.init_client(server_info["public_key"])
        server_channel.complete_handshake(client_resp["ciphertext"])

    # Metrics
    stats = {
        "risk_scores": [],
        "risk_levels": {"info": 0, "caution": 0, "warning": 0, "critical": 0},
        "alerts_total": 0,
        "alert_details": [],
        "encryption_times_ms": [],
        "hr_values": [],
        "spo2_values": [],
        "temp_values": [],
        "max_risk": 0,
        "min_risk": 100,
        "posture_changes": 0,
        "last_posture": None,
    }

    start_time = time.time()

    for i, frame in enumerate(frames):
        # 1. Analysis
        assessment = engine.assess(frame)
        risk = assessment.get("risk_score", 0)
        level = assessment.get("risk_level", "info")

        # 2. Update twin
        bed = frame.get("bed", {})
        fsr_values = bed.get("fsrs", [0] * 12)
        duration = frame.get("vitals_snapshot", {}).get("posture_duration_min", 0)
        zone_scores = compute_zone_scores(fsr_values, duration, patient.pressure_multiplier)
        twin.update_pressure_zones(zone_scores)
        twin.update_from_assessment(assessment)

        # 3. Stress model
        va = assessment.get("vitals_analysis", {})
        params = va.get("parameters", {})
        hr_data = params.get("heart_rate", {})
        hrv_data = params.get("hrv", {})
        stress_result = {"stress_index": 0, "trend": "stable"}
        if hr_data.get("value") and hrv_data.get("value"):
            stress_result = stress.update(hr_data["value"], hrv_data["value"])

        # 4. Alerts
        alert_result = alert_mgr.evaluate(assessment)
        if alert_result["should_alert"]:
            stats["alerts_total"] += 1
            stats["alert_details"].append({
                "frame": i,
                "risk": round(risk, 1),
                "level": level,
                "reason": alert_result["reason"],
            })

        # 5. Encrypt (sample every 10th frame)
        if encrypt and i % 10 == 0:
            dashboard_state = twin.to_dashboard_state()
            t0 = time.time()
            envelope = server_channel.encrypt_patient_data(dashboard_state)
            decrypted = client_channel.decrypt_patient_data(envelope)
            enc_ms = (time.time() - t0) * 1000
            stats["encryption_times_ms"].append(enc_ms)
            assert decrypted is not None, "Decryption failed!"

        # Track metrics
        stats["risk_scores"].append(round(risk, 2))
        stats["risk_levels"][level] = stats["risk_levels"].get(level, 0) + 1

        if risk > stats["max_risk"]:
            stats["max_risk"] = risk
        if risk < stats["min_risk"]:
            stats["min_risk"] = risk

        posture = assessment.get("repositioning", {}).get("posture", "unknown")
        if stats["last_posture"] and posture != stats["last_posture"]:
            stats["posture_changes"] += 1
        stats["last_posture"] = posture

        hr = hr_data.get("value", 0)
        sp = params.get("spo2", {}).get("value", 0)
        tp = params.get("body_temp", {}).get("value", 0)
        if hr: stats["hr_values"].append(hr)
        if sp: stats["spo2_values"].append(sp)
        if tp: stats["temp_values"].append(tp)

    elapsed = time.time() - start_time

    # Generate final report
    final_assessment = engine.assess(frames[-1])
    report = generate_fallback_report(final_assessment)

    # Compute summary
    avg_risk = sum(stats["risk_scores"]) / len(stats["risk_scores"])
    avg_hr = sum(stats["hr_values"]) / len(stats["hr_values"]) if stats["hr_values"] else 0
    avg_spo2 = sum(stats["spo2_values"]) / len(stats["spo2_values"]) if stats["spo2_values"] else 0
    avg_enc = sum(stats["encryption_times_ms"]) / len(stats["encryption_times_ms"]) if stats["encryption_times_ms"] else 0

    result = {
        "scenario": name,
        "patient": {
            "id": patient.patient_id,
            "name": patient.name,
            "surgery": patient.surgery_type,
            "post_op_day": patient.post_op_day,
            "age": patient.age,
            "bmi": round(patient.bmi, 1),
        },
        "duration": {
            "frames": len(frames),
            "minutes": round(len(frames) * 2 / 60, 1),
            "processing_sec": round(elapsed, 2),
            "fps": round(len(frames) / elapsed, 1),
        },
        "risk": {
            "average": round(avg_risk, 2),
            "max": round(stats["max_risk"], 2),
            "min": round(stats["min_risk"], 2),
            "final": round(stats["risk_scores"][-1], 2),
            "level_distribution": stats["risk_levels"],
        },
        "vitals": {
            "avg_hr": round(avg_hr, 1),
            "avg_spo2": round(avg_spo2, 1),
            "avg_temp": round(sum(stats["temp_values"]) / len(stats["temp_values"]), 2) if stats["temp_values"] else 0,
        },
        "alerts": {
            "total": stats["alerts_total"],
            "details": stats["alert_details"][:10],  # Top 10
        },
        "posture_changes": stats["posture_changes"],
        "encryption": {
            "enabled": encrypt,
            "avg_ms": round(avg_enc, 3),
            "samples": len(stats["encryption_times_ms"]),
        },
        "stress": {
            "final_index": round(stress_result.get("stress_index", 0), 3),
            "trend": stress_result.get("trend", "stable"),
        },
        "report_preview": (report if isinstance(report, str) else report.get("content", ""))[:300],
    }

    # Print summary
    risk_bar = "█" * int(avg_risk / 5) + "░" * (20 - int(avg_risk / 5))
    print(f"\n  Risk: [{risk_bar}] {avg_risk:.1f}/100 (max: {stats['max_risk']:.1f})")
    print(f"  HR: {avg_hr:.0f} bpm | SpO2: {avg_spo2:.0f}% | Alerts: {stats['alerts_total']}")
    print(f"  Encryption: {avg_enc:.2f}ms/frame | FPS: {result['duration']['fps']}")
    print(f"  Stress: {stress_result.get('stress_index', 0):.2f} ({stress_result.get('trend', 'stable')})")

    return result


def main():
    parser = argparse.ArgumentParser(description="VitalGuard E2E Experiment")
    parser.add_argument("--scenario", default="ALL", choices=["A", "B", "C", "ALL"])
    parser.add_argument("--duration", type=int, default=30, help="Duration in minutes")
    parser.add_argument("--no-encrypt", action="store_true", help="Skip encryption")
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════════╗")
    print("║      VitalGuard — End-to-End Experiment Runner      ║")
    print("╚══════════════════════════════════════════════════════╝")
    print(f"\n  Scenarios: {args.scenario}")
    print(f"  Duration: {args.duration} min per scenario")
    print(f"  Encryption: {'OFF' if args.no_encrypt else 'ON (Quantum-safe)'}")

    results = []
    total_start = time.time()

    if args.scenario in ("A", "ALL"):
        frames, pat = scenario_a_stable(duration_min=args.duration, interval_sec=2.0)
        results.append(run_scenario("A — Stable Recovery", frames, pat, not args.no_encrypt))

    if args.scenario in ("B", "ALL"):
        frames, pat = scenario_b_gradual(duration_min=args.duration, interval_sec=2.0)
        results.append(run_scenario("B — Gradual Deterioration", frames, pat, not args.no_encrypt))

    if args.scenario in ("C", "ALL"):
        frames, pat = scenario_c_acute(duration_min=min(args.duration, 30), interval_sec=2.0)
        results.append(run_scenario("C — Acute Crisis", frames, pat, not args.no_encrypt))

    total_elapsed = time.time() - total_start

    # Final summary
    print(f"\n{'═' * 56}")
    print(f"  EXPERIMENT COMPLETE")
    print(f"{'═' * 56}")
    print(f"  Total time: {total_elapsed:.1f}s")
    print(f"  Scenarios: {len(results)}")

    total_frames = sum(r["duration"]["frames"] for r in results)
    total_alerts = sum(r["alerts"]["total"] for r in results)
    print(f"  Total frames: {total_frames}")
    print(f"  Total alerts: {total_alerts}")

    for r in results:
        level = r["risk"]["level_distribution"]
        crit = level.get("critical", 0) + level.get("warning", 0)
        status = "🔴 CRITICAL" if crit > 0 else "🟡 CAUTION" if level.get("caution", 0) > 0 else "🟢 STABLE"
        print(f"\n  {r['scenario']}:")
        print(f"    {status} | Risk: {r['risk']['average']:.1f} (max {r['risk']['max']:.1f})")
        print(f"    Alerts: {r['alerts']['total']} | Encrypt: {r['encryption']['avg_ms']:.2f}ms")

    # Save results
    output = {
        "experiment": "VitalGuard E2E",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "config": {
            "scenarios": args.scenario,
            "duration_min": args.duration,
            "encryption": not args.no_encrypt,
        },
        "total_elapsed_sec": round(total_elapsed, 2),
        "results": results,
    }

    out_path = os.path.join(os.path.dirname(__file__), "..", "experiment_results.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Results saved: experiment_results.json")
    print(f"{'═' * 56}")


if __name__ == "__main__":
    main()