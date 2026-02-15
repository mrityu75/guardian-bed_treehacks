"""
Alert Manager
==============
Central dispatcher that decides when to send alerts based on
risk level changes, cooldown periods, and escalation rules.
"""

import time
from config.settings import ALERT_LEVELS, EMAIL_COOLDOWN_SEC


class AlertManager:
    """
    Manages alert dispatching for all patients.
    Tracks alert history to prevent spam (cooldown) and
    handles escalation logic.
    """

    def __init__(self, notifiers: list = None):
        """
        Args:
            notifiers: List of notifier objects with .send(alert) method
                       (e.g., EmailNotifier instances)
        """
        self.notifiers = notifiers or []
        self.last_alert_time = {}  # patient_id -> timestamp
        self.last_alert_level = {}  # patient_id -> level
        self.alert_log = []  # all dispatched alerts

    def evaluate(self, assessment: dict) -> dict:
        """
        Evaluate a risk assessment and decide if alerts should be sent.

        Rules:
        1. Always alert on transition TO critical
        2. Alert on transition from info/caution TO warning
        3. Respect cooldown period (no repeat alerts within window)
        4. Escalate: if level worsens, always alert regardless of cooldown

        Args:
            assessment: Output from RiskEngine.assess()

        Returns:
            dict with should_alert, reason, alerts_sent
        """
        pid = assessment.get("patient_id", "unknown")
        risk_level = assessment.get("risk_level", "info")
        risk_score = assessment.get("risk_score", 0)
        now = time.time()

        prev_level = self.last_alert_level.get(pid, "info")
        last_time = self.last_alert_time.get(pid, 0)
        elapsed = now - last_time

        level_order = {"info": 0, "caution": 1, "warning": 2, "critical": 3}
        current_severity = level_order.get(risk_level, 0)
        prev_severity = level_order.get(prev_level, 0)

        should_alert = False
        reason = ""

        # Rule 1: Always alert on critical
        if risk_level == "critical" and prev_level != "critical":
            should_alert = True
            reason = f"Escalated to CRITICAL (score: {risk_score:.0f})"

        # Rule 2: Alert on escalation to warning
        elif risk_level == "warning" and prev_severity < level_order["warning"]:
            should_alert = True
            reason = f"Escalated to WARNING (score: {risk_score:.0f})"

        # Rule 3: Re-alert if still critical and cooldown expired
        elif risk_level == "critical" and elapsed >= EMAIL_COOLDOWN_SEC:
            should_alert = True
            reason = f"Sustained CRITICAL — re-alert (score: {risk_score:.0f})"

        # Rule 4: Escalation always overrides cooldown
        elif current_severity > prev_severity and current_severity >= 2:
            should_alert = True
            reason = f"Risk escalated: {prev_level} -> {risk_level}"

        # Build alert payload
        alerts_sent = []
        if should_alert:
            alert_payload = {
                "patient_id": pid,
                "patient_name": assessment.get("patient_name", "Unknown"),
                "risk_score": risk_score,
                "risk_level": risk_level,
                "reason": reason,
                "alerts": assessment.get("alerts", [])[:5],
                "timestamp": now,
                "posture": assessment.get("posture", {}),
                "sub_scores": assessment.get("sub_scores", {}),
            }

            # Dispatch to all notifiers
            for notifier in self.notifiers:
                try:
                    result = notifier.send(alert_payload)
                    alerts_sent.append({
                        "notifier": notifier.__class__.__name__,
                        "success": result.get("success", False),
                        "detail": result.get("detail", ""),
                    })
                except Exception as e:
                    alerts_sent.append({
                        "notifier": notifier.__class__.__name__,
                        "success": False,
                        "detail": str(e),
                    })

            # Update tracking
            self.last_alert_time[pid] = now
            self.last_alert_level[pid] = risk_level
            self.alert_log.append(alert_payload)
        else:
            self.last_alert_level[pid] = risk_level

        return {
            "should_alert": should_alert,
            "reason": reason,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "alerts_sent": alerts_sent,
            "cooldown_remaining": max(0, EMAIL_COOLDOWN_SEC - elapsed),
        }

    def get_alert_history(self, patient_id: str = None) -> list:
        """Get alert history, optionally filtered by patient."""
        if patient_id:
            return [a for a in self.alert_log if a["patient_id"] == patient_id]
        return self.alert_log