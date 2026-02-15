"""
Step 7 Tests: Dashboard Integration
======================================
Verifies dashboard file exists, is valid HTML, and server components work together.
"""

import sys, os
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


print("=" * 60)
print("TEST 1: Dashboard File")
print("=" * 60)

dashboard_path = os.path.join(os.path.dirname(__file__), "..", "dashboard", "vitalguard.html")
check("Dashboard file exists", os.path.exists(dashboard_path))

with open(dashboard_path) as f:
    html = f.read()

check("Is valid HTML", html.startswith("<!DOCTYPE html>"))
check("Has Three.js", "three.min.js" in html)
check("Has Chart.js", "chart.umd.min.js" in html)
check("Has WebSocket code", "WebSocket" in html)
check("Has fallback data", "loadFallbackData" in html)
check("Has PIN login", "PIN" in html)
check("Has patient grid", "id=\"grid\"" in html)
check("Has 3D viewer", "id=\"tbox\"" in html)
check("Has charts", "id=\"c1\"" in html)
check("Has connection indicator", "wsStatus" in html)
check("Has risk score display", "Risk:" in html or "risk" in html)
check("Has stress-based skin", "stressLevel" in html)
check("Has dynamic wristband pulse", "pulseSpeed" in html)


print(f"\n{'=' * 60}")
print("TEST 2: End-to-End Pipeline (Simulation → Twin → Dashboard JSON)")
print("=" * 60)

import json
from synthetic.scenarios import scenario_a_stable, scenario_b_gradual, scenario_c_acute
from analysis.risk_engine import RiskEngine
from analysis.pressure import compute_zone_scores
from digital_twin.twin_state import DigitalTwin

# Run all 3 scenarios
scenarios = {
    "A": scenario_a_stable(duration_min=5, interval_sec=2.0),
    "B": scenario_b_gradual(duration_min=5, interval_sec=2.0),
    "C": scenario_c_acute(duration_min=10, interval_sec=2.0),
}

all_states = {}
for key, (frames, patient) in scenarios.items():
    engine = RiskEngine(patient)
    twin = DigitalTwin(patient)

    for frame in frames:
        assessment = engine.assess(frame)
        bed = frame.get("bed", {})
        fsr_values = bed.get("fsrs", [0] * 12)
        duration = frame.get("vitals_snapshot", {}).get("posture_duration_min", 0)
        zone_scores = compute_zone_scores(fsr_values, duration, patient.pressure_multiplier)
        twin.update_pressure_zones(zone_scores)
        twin.update_from_assessment(assessment)

    state = twin.to_dashboard_state()
    all_states[key] = state

check("All 3 scenarios produced states", len(all_states) == 3)

# Simulate broadcast message (what WS would send)
broadcast = {
    "type": "update",
    "frame": 100,
    "patients": {s["patient_id"]: s for s in all_states.values()},
}

broadcast_json = json.dumps(broadcast)
check("Broadcast serializable", len(broadcast_json) > 500)
check("Broadcast has 3 patients", len(broadcast["patients"]) == 3)
print(f"  \u2139\uFE0F  Broadcast size: {len(broadcast_json)} bytes")

# Verify each patient has what dashboard needs
for key, state in all_states.items():
    check(f"Scenario {key}: has risk_score", "risk_score" in state)
    check(f"Scenario {key}: has vitals", "vitals" in state)
    check(f"Scenario {key}: has posture", "posture" in state)
    check(f"Scenario {key}: has pressure_zones", "pressure_zones" in state)
    check(f"Scenario {key}: has history", "history" in state)
    check(f"Scenario {key}: has stress_level", "stress_level" in state)

# Verify risk ordering makes sense
risk_a = all_states["A"]["risk_score"]
risk_c = all_states["C"]["risk_score"]
check("Crisis > Stable risk", risk_c > risk_a, f"A={risk_a} C={risk_c}")


print(f"\n{'=' * 60}")
print("TEST 3: Server Import Check")
print("=" * 60)

try:
    from api.server import app
    check("FastAPI app imports", True)
    from api.ws_handler import ConnectionManager
    check("WS manager imports", True)
    from api.routes import router
    check("Router imports", True)
except Exception as e:
    check("Server imports", False, str(e))


print(f"\n{'=' * 60}")
print(f"RESULTS: {passed} passed, {failed} failed out of {passed + failed}")
print("=" * 60)