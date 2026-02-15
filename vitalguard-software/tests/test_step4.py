"""
Step 4 Tests: Alert System
============================
Tests alert triggering logic, cooldowns, escalation, and email formatting.
"""

import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from synthetic.scenarios import scenario_a_stable, scenario_c_acute
from analysis.risk_engine import RiskEngine
from alerts.alert_manager import AlertManager
from alerts.email_notifier import EmailNotifier, _format_alert_email


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
print("TEST 1: Email Formatting")
print("=" * 60)

mock_alert = {
    "patient_id": "PID-9999",
    "patient_name": "Test Patient",
    "risk_score": 82.5,
    "risk_level": "critical",
    "reason": "Escalated to CRITICAL",
    "alerts": ["HR elevated", "SpO2 dropping"],
    "timestamp": time.time(),
    "posture": {"current": "supine", "duration_min": 95},
    "sub_scores": {"vitals": 85, "pressure": 70, "repositioning": 80, "movement": 75, "sound": 30},
}

subject, body = _format_alert_email(mock_alert)
check("Subject contains CRITICAL", "CRITICAL" in subject)
check("Subject contains patient name", "Test Patient" in subject)
check("Subject contains score", "82" in subject)
check("Body is HTML", "<html>" in body)
check("Body contains risk score", "82" in body)
check("Body contains alerts", "HR elevated" in body)
check("Body contains sub-scores table", "Vitals" in body)


print(f"\n{'=' * 60}")
print("TEST 2: Email Notifier (Console Fallback)")
print("=" * 60)

notifier = EmailNotifier()
check("Not configured (no SMTP)", not notifier.is_configured())

result = notifier.send(mock_alert)
check("Send returns success (fallback)", result["success"])
check("Fallback detail message", "console" in result.get("detail", "").lower())
check("Send count incremented", notifier.sent_count == 1)
check("Log recorded", len(notifier.send_log) == 1)


print(f"\n{'=' * 60}")
print("TEST 3: Alert Manager — Stable Patient (No Alerts)")
print("=" * 60)

email = EmailNotifier()
manager = AlertManager(notifiers=[email])

frames_a, pat_a = scenario_a_stable(duration_min=10, interval_sec=2.0)
engine_a = RiskEngine(pat_a)

alert_count = 0
for frame in frames_a:
    assessment = engine_a.assess(frame)
    result = manager.evaluate(assessment)
    if result["should_alert"]:
        alert_count += 1

check("Stable patient: few or no alerts", alert_count <= 2,
      f"got {alert_count} alerts")


print(f"\n{'=' * 60}")
print("TEST 4: Alert Manager — Crisis Patient (Should Alert)")
print("=" * 60)

email2 = EmailNotifier()
manager2 = AlertManager(notifiers=[email2])

frames_c, pat_c = scenario_c_acute(duration_min=35, interval_sec=2.0)
engine_c = RiskEngine(pat_c)

alert_count_c = 0
alert_levels = []
for frame in frames_c:
    assessment = engine_c.assess(frame)
    result = manager2.evaluate(assessment)
    if result["should_alert"]:
        alert_count_c += 1
        alert_levels.append(result["risk_level"])

check("Crisis patient triggers alerts", alert_count_c >= 1,
      f"got {alert_count_c}")
check("Alert history recorded", len(manager2.get_alert_history()) >= 1)
check("Email notifier received alerts", email2.sent_count >= 1,
      f"sent={email2.sent_count}")


print(f"\n{'=' * 60}")
print("TEST 5: Cooldown Logic")
print("=" * 60)

# Simulate rapid evaluations — cooldown should prevent spam
email3 = EmailNotifier()
manager3 = AlertManager(notifiers=[email3])

fake_critical = {
    "patient_id": "PID-TEST",
    "patient_name": "Cooldown Test",
    "risk_score": 85,
    "risk_level": "critical",
    "alerts": ["test"],
    "posture": {},
    "sub_scores": {},
}

# First eval — should alert (new critical)
r1 = manager3.evaluate(fake_critical)
check("First critical: should alert", r1["should_alert"])

# Immediate second eval — same level, should be blocked by cooldown
r2 = manager3.evaluate(fake_critical)
check("Immediate repeat: blocked by cooldown", not r2["should_alert"])

# Escalation should override cooldown
fake_escalation = dict(fake_critical)
fake_escalation["risk_score"] = 95
# Need to reset prev level to test escalation from lower
manager3.last_alert_level["PID-TEST"] = "warning"
r3 = manager3.evaluate(fake_escalation)
check("Escalation overrides cooldown", r3["should_alert"])


print(f"\n{'=' * 60}")
print("TEST 6: Alert Filtering by Patient")
print("=" * 60)

history_all = manager2.get_alert_history()
history_c = manager2.get_alert_history(pat_c.patient_id)
check("Filter by patient works", len(history_c) <= len(history_all))
check("Filtered alerts match patient",
      all(a["patient_id"] == pat_c.patient_id for a in history_c))


print(f"\n{'=' * 60}")
print(f"RESULTS: {passed} passed, {failed} failed out of {passed + failed}")
print("=" * 60)