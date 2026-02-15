"""
Step 6 Tests: API Server
==========================
Tests REST endpoints and simulation logic.
Uses FastAPI TestClient (no actual server needed).
"""

import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

passed = 0
failed = 0

def check(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  \u2705 {name}")
        passed += 1
    else:
        print(f"  \u274C {name} \u2014 {detail}")
        failed += 1


# =========================================
print("=" * 60)
print("TEST 1: WebSocket Manager")
print("=" * 60)

from api.ws_handler import ConnectionManager
wm = ConnectionManager()
check("Initial: 0 clients", wm.client_count == 0)


# =========================================
print(f"\n{'=' * 60}")
print("TEST 2: Simulation Pipeline (No Server)")
print("=" * 60)

from synthetic.scenarios import scenario_a_stable, scenario_c_acute
from analysis.risk_engine import RiskEngine
from analysis.pressure import compute_zone_scores
from digital_twin.twin_state import DigitalTwin
from alerts.alert_manager import AlertManager
from alerts.email_notifier import EmailNotifier
from reporting.groq_report import generate_report

# Simulate what server.py does
frames_a, pat_a = scenario_a_stable(duration_min=5, interval_sec=2.0)
frames_c, pat_c = scenario_c_acute(duration_min=10, interval_sec=2.0)

engines = {
    pat_a.patient_id: RiskEngine(pat_a),
    pat_c.patient_id: RiskEngine(pat_c),
}
twins = {
    pat_a.patient_id: DigitalTwin(pat_a),
    pat_c.patient_id: DigitalTwin(pat_c),
}

email = EmailNotifier()
alert_mgr = AlertManager(notifiers=[email])

all_data = {
    pat_a.patient_id: frames_a,
    pat_c.patient_id: frames_c,
}

broadcast_count = 0
alert_count = 0
report_count = 0

for frame_idx in range(min(len(frames_a), len(frames_c))):
    broadcast_data = {"type": "update", "patients": {}}

    for pid, frames in all_data.items():
        if frame_idx >= len(frames):
            continue

        frame = frames[frame_idx]
        assessment = engines[pid].assess(frame)

        # Update twin
        bed = frame.get("bed", {})
        fsr_values = bed.get("fsrs", [0] * 12)
        duration = frame.get("vitals_snapshot", {}).get("posture_duration_min", 0)
        zone_scores = compute_zone_scores(fsr_values, duration, 1.0)
        twins[pid].update_pressure_zones(zone_scores)
        twins[pid].update_from_assessment(assessment)

        # Check alerts
        alert_result = alert_mgr.evaluate(assessment)
        if alert_result["should_alert"]:
            alert_count += 1

        # Generate report every 30 frames
        if frame_idx % 30 == 0:
            report = generate_report(assessment)
            report_count += 1

        broadcast_data["patients"][pid] = twins[pid].to_dashboard_state()

    broadcast_count += 1

check("Simulation ran", broadcast_count > 50, f"broadcasts={broadcast_count}")
check("Both patients in twin state", len(twins) == 2)

# Verify twin states
state_a = twins[pat_a.patient_id].to_dashboard_state()
state_c = twins[pat_c.patient_id].to_dashboard_state()

check("Stable twin has data", state_a["risk_score"] >= 0)
check("Crisis twin has data", state_c["risk_score"] >= 0)
check("Crisis risk > stable risk",
      state_c["risk_score"] > state_a["risk_score"],
      f"crisis={state_c['risk_score']} stable={state_a['risk_score']}")
check("Alerts triggered", alert_count > 0, f"alerts={alert_count}")
check("Reports generated", report_count > 0, f"reports={report_count}")
check("Pressure zones updated",
      any(z["pressure"] > 0 for z in state_c["pressure_zones"].values()))

# Verify broadcast data structure
check("Broadcast has type", broadcast_data["type"] == "update")
check("Broadcast has patients", len(broadcast_data["patients"]) >= 1)

# Verify patient data in broadcast
for pid, pdata in broadcast_data["patients"].items():
    check(f"Patient {pid} has risk_score", "risk_score" in pdata)
    check(f"Patient {pid} has vitals", "vitals" in pdata)
    check(f"Patient {pid} has posture", "posture" in pdata)
    break  # Just check first one


# =========================================
print(f"\n{'=' * 60}")
print("TEST 3: REST API Routes (import test)")
print("=" * 60)

from api.routes import router, set_sim_state

# Set up mock state
set_sim_state({
    "twins": twins,
    "engines": engines,
    "reports": {},
    "alert_manager": alert_mgr,
    "ws_manager": wm,
    "scenario_name": "TEST",
})

check("Router has routes", len(router.routes) > 0, f"routes={len(router.routes)}")

# Test route functions directly
loop = asyncio.new_event_loop()

from api.routes import get_patients, get_patient_detail, get_alerts, get_system_status

patients_resp = loop.run_until_complete(get_patients())
check("GET /patients returns list", "patients" in patients_resp)
check("Patient count correct", patients_resp["count"] == 2, f"count={patients_resp['count']}")
check("Patients sorted by risk",
      patients_resp["patients"][0]["risk_score"] >= patients_resp["patients"][1]["risk_score"])

detail_resp = loop.run_until_complete(get_patient_detail(pat_c.patient_id))
check("GET /patients/{id} returns data", "patient_id" in detail_resp)
check("Detail has vitals", "vitals" in detail_resp)

alerts_resp = loop.run_until_complete(get_alerts())
check("GET /alerts returns list", "alerts" in alerts_resp)

status_resp = loop.run_until_complete(get_system_status())
check("GET /status returns info", status_resp["status"] == "running")
check("Status shows patient count", status_resp["patients_monitored"] == 2)

loop.close()


print(f"\n{'=' * 60}")
print(f"RESULTS: {passed} passed, {failed} failed out of {passed + failed}")
print("=" * 60)