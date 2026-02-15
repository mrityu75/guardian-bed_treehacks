"""
Groq Report Generator
=======================
Uses Groq's free-tier LLM API to generate natural language clinical reports
from risk engine assessment data. Falls back to template-based reports
if API key is unavailable.
"""

import os
import json
import urllib.request
import urllib.error
from config.settings import GROQ_MODEL, GROQ_MAX_TOKENS, GROQ_TEMPERATURE
from reporting.templates import SYSTEM_PROMPT, build_report_prompt, build_comparison_prompt


def _load_api_key() -> str:
    """Load Groq API key from environment or .env file."""
    key = os.environ.get("GROQ_API_KEY", "")
    if key:
        return key

    # Try loading from .env file
    env_paths = [
        os.path.join(os.path.dirname(__file__), "..", ".env"),
        ".env",
    ]
    for path in env_paths:
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GROQ_API_KEY=") and not line.endswith("_here"):
                        return line.split("=", 1)[1].strip()
        except FileNotFoundError:
            continue

    return ""


def call_groq(prompt: str, system: str = SYSTEM_PROMPT) -> dict:
    """
    Call the Groq API with a prompt.
    Uses urllib (no external dependencies needed).

    Args:
        prompt: User message content
        system: System message content

    Returns:
        dict with 'success', 'content' (the report text), 'model', 'usage'
    """
    api_key = _load_api_key()
    if not api_key:
        return {
            "success": False,
            "content": "",
            "error": "No GROQ_API_KEY found. Set it in .env or environment.",
        }

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": GROQ_MAX_TOKENS,
        "temperature": GROQ_TEMPERATURE,
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"]
            return {
                "success": True,
                "content": content,
                "model": result.get("model", GROQ_MODEL),
                "usage": result.get("usage", {}),
            }
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else str(e)
        return {"success": False, "content": "", "error": f"HTTP {e.code}: {error_body}"}
    except Exception as e:
        return {"success": False, "content": "", "error": str(e)}


def generate_fallback_report(assessment: dict) -> str:
    """
    Generate a template-based report when Groq API is unavailable.
    Uses the same data but with hardcoded formatting.
    """
    name = assessment.get("patient_name", "Unknown")
    pid = assessment.get("patient_id", "")
    risk = assessment.get("risk_score", 0)
    level = assessment.get("risk_level", "info").upper()
    sub = assessment.get("sub_scores", {})
    vitals = assessment.get("vitals_analysis", {}).get("parameters", {})
    posture = assessment.get("posture", {})
    pressure = assessment.get("pressure_analysis", {}).get("overall", {})
    repo = assessment.get("repositioning", {})
    alerts = assessment.get("alerts", [])

    # Build vitals summary
    vitals_lines = []
    for key, data in vitals.items():
        v = data.get("value", "N/A")
        cls = data.get("classification", {}).get("level", "")
        vitals_lines.append(f"  {key}: {v} [{cls}]")

    # Build recommendations based on level
    recs = []
    if level in ("WARNING", "CRITICAL"):
        recs.append("Immediate physician notification recommended")
        if sub.get("vitals", 0) > 50:
            recs.append("Review vital signs — multiple parameters outside normal range")
        if sub.get("pressure", 0) > 50:
            recs.append(f"Reposition patient — {pressure.get('worst_zone', 'sacrum')} zone at elevated risk")
        if sub.get("repositioning", 0) > 50:
            recs.append(f"Repositioning overdue — {repo.get('duration_min', 0):.0f} min in current position")
    else:
        recs.append("Continue routine monitoring schedule")
        recs.append("Maintain standard repositioning protocol")

    report = f"""CLINICAL STATUS REPORT
{'=' * 40}
Patient: {name} ({pid})
Risk Score: {risk:.0f}/100 [{level}]

STATUS SUMMARY:
Patient {name} is currently classified as {level} with an integrated
risk score of {risk:.0f}/100. {"Immediate attention recommended." if risk > 60 else "Routine monitoring continues."}

VITAL SIGNS:
{chr(10).join(vitals_lines)}

PRESSURE ASSESSMENT:
  Position: {posture.get('current', 'N/A')} ({posture.get('duration_min', 0):.0f} min)
  Overall pressure risk: {pressure.get('overall_risk', 0):.2f}
  Worst zone: {pressure.get('worst_zone', 'N/A')}
  Repositioning: {repo.get('status', 'N/A')}

RECOMMENDATIONS:
{chr(10).join(f'  {i+1}. {r}' for i, r in enumerate(recs))}

ALERTS ({len(alerts)}):
{chr(10).join(f'  - {a}' for a in alerts[:5]) if alerts else '  None'}
"""
    return report


def generate_report(assessment: dict) -> dict:
    """
    Generate a clinical report — uses Groq if available, fallback otherwise.

    Args:
        assessment: Output from RiskEngine.assess()

    Returns:
        dict with 'report' (text), 'source' ('groq' or 'fallback'), 'success'
    """
    prompt = build_report_prompt(assessment)
    result = call_groq(prompt)

    if result["success"]:
        return {
            "report": result["content"],
            "source": "groq",
            "model": result.get("model", GROQ_MODEL),
            "success": True,
        }
    else:
        # Fallback to template
        report = generate_fallback_report(assessment)
        return {
            "report": report,
            "source": "fallback",
            "groq_error": result.get("error", "Unknown"),
            "success": True,  # Fallback still produces a report
        }


def generate_shift_summary(assessments: list) -> dict:
    """
    Generate a multi-patient shift handover summary.

    Args:
        assessments: List of risk engine assessment dicts

    Returns:
        dict with 'report', 'source', 'success'
    """
    prompt = build_comparison_prompt(assessments)
    result = call_groq(prompt)

    if result["success"]:
        return {
            "report": result["content"],
            "source": "groq",
            "success": True,
        }
    else:
        # Simple fallback
        lines = ["SHIFT HANDOVER SUMMARY", "=" * 40]
        sorted_a = sorted(assessments, key=lambda x: x.get("risk_score", 0), reverse=True)
        for a in sorted_a:
            lines.append(
                f"  {a.get('patient_name', '?')} ({a.get('patient_id', '?')}): "
                f"Risk {a.get('risk_score', 0):.0f}/100 [{a.get('risk_level', '?')}] "
                f"| Alerts: {len(a.get('alerts', []))}"
            )
        return {
            "report": "\n".join(lines),
            "source": "fallback",
            "success": True,
        }


if __name__ == "__main__":
    # Quick test with fallback (no API key needed)
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    from synthetic.scenarios import scenario_c_acute
    from analysis.risk_engine import RiskEngine

    frames, patient = scenario_c_acute(duration_min=30, interval_sec=2.0)
    engine = RiskEngine(patient)

    last_assessment = None
    for frame in frames:
        last_assessment = engine.assess(frame)

    result = generate_report(last_assessment)
    print(f"Source: {result['source']}")
    print(result["report"][:1000])