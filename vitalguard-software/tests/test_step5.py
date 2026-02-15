"""
Step 5 Tests: Digital Twin
============================
Validates twin state model, pressure map, and stress model.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from synthetic.scenarios import scenario_a_stable, scenario_c_acute
from analysis.risk_engine import RiskEngine
from analysis.pressure import compute_zone_scores
from digital_twin.twin_state import DigitalTwin, _risk_to_color
from digital_twin.pressure_map import compute_pressure_map, ZONE_BODY_COORDS
from digital_twin.stress_model import StressModel


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
print("TEST 1: Digital Twin — Stable Patient")
print("=" * 60)

frames_a, pat_a = scenario_a_stable(duration_min=10, interval_sec=2.0)
engine_a = RiskEngine(pat_a)
twin_a = DigitalTwin(pat_a)

for frame in frames_a:
    assessment = engine_a.assess(frame)
    twin_a.update_from_assessment(assessment)

state_a = twin_a.to_dashboard_state()

check("Has patient_id", state_a["patient_id"] == pat_a.patient_id)
check("Has patient_name", state_a["patient_name"] == pat_a.name)
check("Has risk_score", 0 <= state_a["risk_score"] <= 100)
check("Risk level is info/caution", state_a["risk_level"] in ("info", "caution"))
check("Stress level low (<0.5)", state_a["stress_level"] < 0.5,
      f"stress={state_a['stress_level']}")
check("Consciousness responsive", state_a["consciousness"] == "responsive")
check("Has posture data", "current" in state_a["posture"])
check("Has vitals data", "heart_rate" in state_a["vitals"])
check("Vitals HR has value+level", 
      "value" in state_a["vitals"]["heart_rate"] and "level" in state_a["vitals"]["heart_rate"])
check("Has 12 pressure zones", len(state_a["pressure_zones"]) == 12)
check("Pressure zones have color", 
      all("color" in z for z in state_a["pressure_zones"].values()))
check("Has history arrays", len(state_a["history"]["heart_rate"]) > 0)
check("Has profile", "age" in state_a["profile"])
check("Has alerts list", isinstance(state_a["alerts"], list))


# =========================================
print(f"\n{'=' * 60}")
print("TEST 2: Digital Twin — Crisis Patient")
print("=" * 60)

frames_c, pat_c = scenario_c_acute(duration_min=30, interval_sec=2.0)
engine_c = RiskEngine(pat_c)
twin_c = DigitalTwin(pat_c)

for frame in frames_c:
    assessment = engine_c.assess(frame)
    twin_c.update_from_assessment(assessment)

state_c = twin_c.to_dashboard_state()

check("Crisis risk > stable risk", 
      state_c["risk_score"] > state_a["risk_score"],
      f"crisis={state_c['risk_score']} stable={state_a['risk_score']}")
check("Crisis stress higher", 
      state_c["stress_level"] > state_a["stress_level"],
      f"crisis={state_c['stress_level']} stable={state_a['stress_level']}")
check("Crisis has alerts", state_c["alert_count"] > 0)
check("Posture duration long", state_c["posture"]["duration_min"] > 50,
      f"duration={state_c['posture']['duration_min']}")


# =========================================
print(f"\n{'=' * 60}")
print("TEST 3: Pressure Map")
print("=" * 60)

test_fsrs = [500, 1400, 1300, 1000, 1050, 800, 850, 2000, 1900, 600, 650, 1200]
pmap = compute_pressure_map(test_fsrs, duration_min=45, pressure_multiplier=1.2)

check("Has 12 zones", len(pmap["zones"]) == 12)
check("Zones have body coordinates", 
      all("body_x" in z and "body_y" in z for z in pmap["zones"].values()))
check("Coordinates in 0-1 range",
      all(0 <= z["body_x"] <= 1 and 0 <= z["body_y"] <= 1 for z in pmap["zones"].values()))
check("Has summary", "avg_pressure" in pmap["summary"])
check("Summary has max zone", pmap["summary"]["max_zone"] != "")
check("12 body coords defined", len(ZONE_BODY_COORDS) == 12)


# =========================================
print(f"\n{'=' * 60}")
print("TEST 4: Stress Model")
print("=" * 60)

sm = StressModel()

# Low stress: normal HR + good HRV
r = sm.update(70, 45)
check("Low stress index", r["stress_index"] < 0.35, f"stress={r['stress_index']}")
check("Green glow for low stress", r["visual"]["glow_color"][1] > r["visual"]["glow_color"][0])

# High stress: high HR + low HRV
for _ in range(15):
    r = sm.update(110, 15)
check("High stress index", r["stress_index"] > 0.6, f"stress={r['stress_index']}")
check("Red glow for high stress", r["visual"]["glow_color"][0] > r["visual"]["glow_color"][1])
check("High breathing rate", r["visual"]["breathing_rate_hz"] > 1.5)
check("Has trend", r["trend"] in ("stable", "increasing", "decreasing"))


# =========================================
print(f"\n{'=' * 60}")
print("TEST 5: Risk-to-Color Mapping")
print("=" * 60)

c_low = _risk_to_color(0.1)
c_mid = _risk_to_color(0.5)
c_high = _risk_to_color(0.9)

check("Low risk = greenish", c_low[1] > c_low[0], f"color={c_low}")
check("High risk = reddish", c_high[0] > c_high[1], f"color={c_high}")
check("Colors are RGB 0-1", all(0 <= v <= 1 for v in c_low + c_mid + c_high))


# =========================================
print(f"\n{'=' * 60}")
print("TEST 6: Dashboard State Serialization")
print("=" * 60)

import json
json_str = json.dumps(state_c)
check("Serializable to JSON", len(json_str) > 100)
parsed = json.loads(json_str)
check("Roundtrip preserves data", parsed["patient_id"] == pat_c.patient_id)
check("JSON size reasonable", len(json_str) < 10000, f"size={len(json_str)}")
print(f"  \u2139\uFE0F  Dashboard state JSON size: {len(json_str)} bytes")


print(f"\n{'=' * 60}")
print(f"RESULTS: {passed} passed, {failed} failed out of {passed + failed}")
print("=" * 60)