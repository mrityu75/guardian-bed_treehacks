"""
Report Prompt Templates
========================
Structured prompts for Groq LLM to generate clinical reports.
Templates adapt based on patient risk level and available data.
"""

SYSTEM_PROMPT = """You are a clinical decision support AI assistant for VitalGuard, 
a post-surgical patient monitoring system. You generate concise, professional 
clinical status reports for nursing staff based on real-time sensor data.

Guidelines:
- Use precise medical terminology
- Be concise but thorough
- Highlight critical findings first
- Include specific numerical values
- Provide actionable recommendations
- Format with clear sections
- Never speculate beyond the data provided
- Always note the patient's personalized risk factors"""


def build_report_prompt(assessment: dict) -> str:
    """
    Build a structured prompt from a risk engine assessment result.

    Args:
        assessment: Output from RiskEngine.assess()

    Returns:
        Formatted prompt string for the LLM
    """
    patient_id = assessment.get("patient_id", "Unknown")
    patient_name = assessment.get("patient_name", "Unknown")
    elapsed = assessment.get("elapsed_min", 0)
    risk_score = assessment.get("risk_score", 0)
    risk_level = assessment.get("risk_level", "info")
    sub_scores = assessment.get("sub_scores", {})
    profile = assessment.get("patient_profile", {})

    # Vitals
    vitals = assessment.get("vitals_analysis", {}).get("parameters", {})
    vitals_str = ""
    for key, data in vitals.items():
        v = data.get("value", "N/A")
        cls = data.get("classification", {}).get("level", "unknown")
        trend = data.get("trend", {}).get("direction", "unknown")
        vitals_str += f"  - {key}: {v} [{cls}] (trend: {trend})\n"

    # Posture
    posture = assessment.get("posture", {})
    posture_str = (f"Position: {posture.get('current', 'unknown')}, "
                   f"Duration: {posture.get('duration_min', 0):.0f} min")

    # Pressure
    pressure = assessment.get("pressure_analysis", {}).get("overall", {})
    pressure_str = (f"Overall risk: {pressure.get('overall_risk', 0):.2f}, "
                    f"Worst zone: {pressure.get('worst_zone', 'N/A')} "
                    f"({pressure.get('worst_zone_risk', 0):.2f}), "
                    f"High-risk zones: {pressure.get('high_risk_count', 0)}")

    # Repositioning
    repo = assessment.get("repositioning", {})
    repo_str = (f"Status: {repo.get('status', 'unknown')}, "
                f"Remaining: {repo.get('remaining_min', 0):.0f} min, "
                f"Total repositions: {repo.get('total_repositions', 0)}")

    # Sound
    sound = assessment.get("sound", {})
    sound_str = (f"Classification: {sound.get('classification', 'N/A')}, "
                 f"Distress events: {sound.get('distress_count', 0)}")

    # Alerts
    alerts = assessment.get("alerts", [])
    alerts_str = "\n".join(f"  - {a}" for a in alerts[:10]) if alerts else "  None"

    prompt = f"""Generate a clinical status report for the following patient:

PATIENT: {patient_name} ({patient_id})
RISK SCORE: {risk_score}/100 [{risk_level.upper()}]
MONITORING DURATION: {elapsed:.0f} minutes

PATIENT PROFILE:
  Age: {profile.get('age', 'N/A')}
  BMI: {profile.get('bmi', 'N/A')}
  Elderly: {profile.get('is_elderly', False)}
  Diabetic: {profile.get('is_diabetic', False)}
  Pressure multiplier: {profile.get('pressure_multiplier', 1.0)}

SUB-SCORES (0-100):
  Vitals: {sub_scores.get('vitals', 0):.0f}
  Pressure: {sub_scores.get('pressure', 0):.0f}
  Repositioning: {sub_scores.get('repositioning', 0):.0f}
  Movement: {sub_scores.get('movement', 0):.0f}
  Sound: {sub_scores.get('sound', 0):.0f}

VITAL SIGNS:
{vitals_str}
POSTURE & PRESSURE:
  {posture_str}
  {pressure_str}

REPOSITIONING:
  {repo_str}

SOUND MONITORING:
  {sound_str}

ACTIVE ALERTS:
{alerts_str}

Please generate a report with these sections:
1. STATUS SUMMARY (2-3 sentences)
2. VITAL SIGNS ANALYSIS (key findings with values)
3. PRESSURE ULCER RISK ASSESSMENT
4. CLINICAL RECOMMENDATIONS (numbered, actionable)
"""
    return prompt


def build_comparison_prompt(assessments: list) -> str:
    """
    Build a prompt for comparing multiple patient risk assessments.
    Useful for shift handover reports.

    Args:
        assessments: List of risk engine assessment dicts

    Returns:
        Formatted prompt for multi-patient summary
    """
    patients_str = ""
    for a in assessments:
        patients_str += (
            f"- {a.get('patient_name', '?')} ({a.get('patient_id', '?')}): "
            f"Risk {a.get('risk_score', 0):.0f}/100 [{a.get('risk_level', '?')}], "
            f"Alerts: {len(a.get('alerts', []))}\n"
        )

    return f"""Generate a brief shift handover summary for the following patients.
Prioritize patients by risk level (critical first).

PATIENTS:
{patients_str}

Format:
1. PRIORITY PATIENTS (immediate attention needed)
2. MONITORING PATIENTS (close watch)
3. STABLE PATIENTS (routine care)
"""