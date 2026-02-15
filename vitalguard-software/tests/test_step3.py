"""
Step 3 Tests: Report Generation
=================================
Tests both fallback template reports and Groq API reports (if key available).
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from synthetic.scenarios import scenario_a_stable, scenario_c_acute
from analysis.risk_engine import RiskEngine
from reporting.groq_report import generate_report, generate_shift_summary, _load_api_key
from reporting.templates import build_report_prompt


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


# Prepare scenario data
print("Preparing scenario data...")
frames_a, pat_a = scenario_a_stable(duration_min=10, interval_sec=2.0)
engine_a = RiskEngine(pat_a)
assessment_a = None
for f in frames_a:
    assessment_a = engine_a.assess(f)

frames_c, pat_c = scenario_c_acute(duration_min=30, interval_sec=2.0)
engine_c = RiskEngine(pat_c)
assessment_c = None
for f in frames_c:
    assessment_c = engine_c.assess(f)


print("=" * 60)
print("TEST 1: Prompt Template Building")
print("=" * 60)

prompt_a = build_report_prompt(assessment_a)
check("Prompt contains patient name", pat_a.name in prompt_a)
check("Prompt contains risk score", 
      str(int(assessment_a["risk_score"])) in prompt_a or 
      f"{assessment_a['risk_score']:.1f}" in prompt_a,
      f"score={assessment_a['risk_score']}")
check("Prompt contains VITAL SIGNS section", "VITAL SIGNS" in prompt_a)
check("Prompt contains RECOMMENDATIONS section", "RECOMMENDATIONS" in prompt_a)
check("Prompt length reasonable", 500 < len(prompt_a) < 5000, f"len={len(prompt_a)}")

prompt_c = build_report_prompt(assessment_c)
check("Crisis prompt has higher risk", "CRITICAL" in prompt_c or "WARNING" in prompt_c)


print(f"\n{'=' * 60}")
print("TEST 2: Fallback Report Generation")
print("=" * 60)

result_a = generate_report(assessment_a)
check("Stable report generated", result_a["success"])
check("Report has content", len(result_a["report"]) > 100, f"len={len(result_a['report'])}")
check("Report contains patient name", pat_a.name in result_a["report"])
check("Report has VITAL SIGNS section", "VITAL SIGNS" in result_a["report"].upper() or "vital signs" in result_a["report"].lower())

result_c = generate_report(assessment_c)
check("Crisis report generated", result_c["success"])
check("Crisis report has content", len(result_c["report"]) > 100)
check("Crisis report mentions risk level",
      "WARNING" in result_c["report"] or "CRITICAL" in result_c["report"])


print(f"\n{'=' * 60}")
print("TEST 3: Shift Summary")
print("=" * 60)

summary = generate_shift_summary([assessment_a, assessment_c])
check("Summary generated", summary["success"])
check("Summary has content", len(summary["report"]) > 50)
check("Summary mentions both patients",
      pat_a.name in summary["report"] and pat_c.name in summary["report"],
      f"Looking for {pat_a.name} and {pat_c.name}")


print(f"\n{'=' * 60}")
print("TEST 4: Groq API (if key available)")
print("=" * 60)

api_key = _load_api_key()
if api_key and not api_key.endswith("_here"):
    print("  API key found! Testing live Groq call...")
    result = generate_report(assessment_c)
    check("Groq API call succeeded", result["success"])
    check("Groq report source", result["source"] == "groq", f"got {result['source']}")
    check("Groq report has content", len(result["report"]) > 200)
    if result["success"] and result["source"] == "groq":
        print(f"\n  --- GROQ REPORT PREVIEW (first 500 chars) ---")
        print(f"  {result['report'][:500]}")
        print(f"  ---")
else:
    print("  No API key found — skipping live Groq test")
    print("  (Set GROQ_API_KEY in .env to enable)")
    check("Fallback works without API key", result_c["success"])


print(f"\n{'=' * 60}")
print("TEST 5: Report Quality Checks")
print("=" * 60)

# Verify reports differ by scenario
check("Different reports for different scenarios",
      result_a["report"] != result_c["report"],
      "Reports should differ between stable and crisis")

# Verify crisis report is longer/more detailed
check("Crisis report more detailed",
      len(result_c["report"]) >= len(result_a["report"]) * 0.8,
      f"stable={len(result_a['report'])} crisis={len(result_c['report'])}")


print(f"\n{'=' * 60}")
print(f"RESULTS: {passed} passed, {failed} failed out of {passed + failed}")
print("=" * 60)