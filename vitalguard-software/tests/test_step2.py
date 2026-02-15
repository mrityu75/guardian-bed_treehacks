"""
Step 2 Tests: Analysis Engine
===============================
Validates all 6 analysis modules using synthetic scenario data.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from synthetic.scenarios import scenario_a_stable, scenario_b_gradual, scenario_c_acute
from analysis.posture import classify_posture, classify_from_frame
from analysis.pressure import analyze_pressure
from analysis.vitals import VitalSignsAnalyzer
from analysis.repositioning import RepositioningTracker
from analysis.sound import SoundAnalyzer
from analysis.risk_engine import RiskEngine


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
print("TEST 1: Posture Classification")
print("=" * 60)

# Supine: gravity on -Y
r = classify_posture(0.0, -1.0, 9.81)
check("Supine detected", r["posture"] == "supine", f"got {r['posture']}")

# Left lateral: gravity on +X
r = classify_posture(1.0, 0.0, 9.81)
check("Left lateral detected", r["posture"] == "left_lateral", f"got {r['posture']}")

# Right lateral: gravity on -X
r = classify_posture(-1.0, 0.0, 9.81)
check("Right lateral detected", r["posture"] == "right_lateral", f"got {r['posture']}")

# From bed frame
frames_a, _ = scenario_a_stable(duration_min=1, interval_sec=2.0)
bed_frame = frames_a[0]["bed"]
r = classify_from_frame(bed_frame)
check("classify_from_frame works", r["posture"] in ["supine", "left_lateral", "right_lateral", "prone", "unknown"])
check("Has confidence", 0 <= r["confidence"] <= 1.0)

# =========================================
print(f"\n{'=' * 60}")
print("TEST 2: Pressure Analysis")
print("=" * 60)

result = analyze_pressure(bed_frame, duration_min=30, pressure_multiplier=1.0)
check("Has zones", len(result["zones"]) == 12)
check("Has overall", "overall" in result)
check("Overall has risk score", 0 <= result["overall"]["overall_risk"] <= 1.0)
check("Has worst zone", result["overall"]["worst_zone"] != "none")

# High duration should increase risk
result_long = analyze_pressure(bed_frame, duration_min=120, pressure_multiplier=1.3)
check("Longer duration = higher risk",
      result_long["overall"]["overall_risk"] > result["overall"]["overall_risk"],
      f"{result_long['overall']['overall_risk']} vs {result['overall']['overall_risk']}")

# =========================================
print(f"\n{'=' * 60}")
print("TEST 3: Vital Signs Analyzer")
print("=" * 60)

va = VitalSignsAnalyzer()

# Normal reading
r = va.analyze_all({"heart_rate": 72, "body_temp": 36.7, "spo2": 98, "hrv": 42, "resp_rate": 15})
check("Normal vitals = normal level", r["overall_level"] == "normal", f"got {r['overall_level']}")
check("No alerts for normal", len(r["alerts"]) == 0)

# Critical reading
r = va.analyze_all({"heart_rate": 115, "body_temp": 38.5, "spo2": 89, "hrv": 12, "resp_rate": 26})
check("Critical vitals detected", r["overall_level"] == "critical", f"got {r['overall_level']}")
check("Alerts generated", len(r["alerts"]) > 0, f"alerts: {r['alerts']}")

# Trend detection (feed rising HR)
va2 = VitalSignsAnalyzer()
for i in range(30):
    va2.add_reading({"heart_rate": 70 + i * 0.5, "body_temp": 36.7, "spo2": 98, "hrv": 42, "resp_rate": 15})
trend = va2.detect_trend("heart_rate")
check("Rising HR trend detected", trend["direction"] == "rising", f"got {trend['direction']}")

# =========================================
print(f"\n{'=' * 60}")
print("TEST 4: Repositioning Tracker")
print("=" * 60)

rt = RepositioningTracker(interval_min=90)

# Start at minute 0
r = rt.update("supine", 0)
check("Initial status ok", r["status"] == "ok")

# At minute 80 — warning
r = rt.update("supine", 80)
check("Warning at 80 min", r["status"] == "warning", f"got {r['status']}")

# At minute 95 — overdue
r = rt.update("supine", 95)
check("Overdue at 95 min", r["status"] == "overdue", f"got {r['status']}")
check("Overdue alert generated", len(r["alerts"]) > 0)

# Reposition at minute 96
r = rt.update("left_lateral", 96)
check("After reposition = ok", r["status"] == "ok")
check("Reposition counted", r["total_repositions"] == 1)

compliance = rt.get_compliance()
check("Compliance tracked", compliance["total_events"] == 1)

# =========================================
print(f"\n{'=' * 60}")
print("TEST 5: Sound Analyzer")
print("=" * 60)

sa = SoundAnalyzer()

r = sa.analyze([1400, 1350, 1380])
check("Normal ambient classified", r["classification"] == "normal", f"got {r['classification']}")

r = sa.analyze([2900, 2800, 2700])
check("Distress detected", r["classification"] == "distress")
check("Distress alert", len(r["alerts"]) > 0)

# =========================================
print(f"\n{'=' * 60}")
print("TEST 6: Risk Engine — Scenario A (Stable)")
print("=" * 60)

frames_a, pat_a = scenario_a_stable(duration_min=30, interval_sec=2.0)
engine_a = RiskEngine(pat_a)

for frame in frames_a:
    result_a = engine_a.assess(frame)

summary_a = engine_a.get_risk_summary()
check("Stable avg risk < 35", summary_a["avg_risk"] < 35, f"avg={summary_a['avg_risk']}")
check("Stable max risk < 50", summary_a["max_risk"] < 50, f"max={summary_a['max_risk']}")
print(f"  \u2139\uFE0F  Scenario A: avg={summary_a['avg_risk']}, max={summary_a['max_risk']}")

# =========================================
print(f"\n{'=' * 60}")
print("TEST 7: Risk Engine — Scenario B (Gradual)")
print("=" * 60)

frames_b, pat_b = scenario_b_gradual(duration_min=30, interval_sec=2.0)
engine_b = RiskEngine(pat_b)

for frame in frames_b:
    result_b = engine_b.assess(frame)

summary_b = engine_b.get_risk_summary()
check("Gradual end risk > start risk",
      engine_b.risk_history[-1]["risk_score"] > engine_b.risk_history[0]["risk_score"],
      f"start={engine_b.risk_history[0]['risk_score']} end={engine_b.risk_history[-1]['risk_score']}")
print(f"  \u2139\uFE0F  Scenario B: avg={summary_b['avg_risk']}, max={summary_b['max_risk']}")

# =========================================
print(f"\n{'=' * 60}")
print("TEST 8: Risk Engine — Scenario C (Acute)")
print("=" * 60)

frames_c, pat_c = scenario_c_acute(duration_min=35, interval_sec=2.0)
engine_c = RiskEngine(pat_c)

for frame in frames_c:
    result_c = engine_c.assess(frame)

summary_c = engine_c.get_risk_summary()
check("Crisis max risk > 60", summary_c["max_risk"] > 60, f"max={summary_c['max_risk']}")
check("Crisis has alerts", summary_c["total_alerts"] > 0, f"alerts={summary_c['total_alerts']}")
check("Crisis final risk > Stable final risk",
      engine_c.risk_history[-1]["risk_score"] > engine_a.risk_history[-1]["risk_score"])
print(f"  \u2139\uFE0F  Scenario C: avg={summary_c['avg_risk']}, max={summary_c['max_risk']}, alerts={summary_c['total_alerts']}")

# =========================================
print(f"\n{'=' * 60}")
print(f"RESULTS: {passed} passed, {failed} failed out of {passed + failed}")
print("=" * 60)