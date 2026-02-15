"""
Email Notifier
===============
Sends alert emails via SMTP when risk events occur.
Supports Gmail and other SMTP providers.
Falls back to logging if SMTP is not configured.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


def _load_smtp_config() -> dict:
    """Load SMTP config from environment or .env file."""
    config = {
        "host": os.environ.get("SMTP_HOST", ""),
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "user": os.environ.get("SMTP_USER", ""),
        "password": os.environ.get("SMTP_PASSWORD", ""),
        "recipient": os.environ.get("ALERT_RECIPIENT", ""),
    }

    # Try .env file
    if not config["host"]:
        env_paths = [
            os.path.join(os.path.dirname(__file__), "..", ".env"),
            ".env",
        ]
        for path in env_paths:
            try:
                with open(path) as f:
                    for line in f:
                        line = line.strip()
                        if "=" in line and not line.startswith("#"):
                            key, val = line.split("=", 1)
                            key = key.strip()
                            val = val.strip()
                            if key == "SMTP_HOST":
                                config["host"] = val
                            elif key == "SMTP_PORT":
                                config["port"] = int(val)
                            elif key == "SMTP_USER":
                                config["user"] = val
                            elif key == "SMTP_PASSWORD":
                                config["password"] = val
                            elif key == "ALERT_RECIPIENT":
                                config["recipient"] = val
            except (FileNotFoundError, ValueError):
                continue

    return config


def _format_alert_email(alert: dict) -> tuple:
    """
    Format alert data into email subject and HTML body.

    Returns:
        (subject, html_body) tuple
    """
    level = alert.get("risk_level", "info").upper()
    name = alert.get("patient_name", "Unknown")
    pid = alert.get("patient_id", "")
    score = alert.get("risk_score", 0)
    reason = alert.get("reason", "")
    alerts = alert.get("alerts", [])
    posture = alert.get("posture", {})
    sub = alert.get("sub_scores", {})
    ts = datetime.fromtimestamp(alert.get("timestamp", 0)).strftime("%Y-%m-%d %H:%M:%S")

    # Color by level
    color = {
        "CRITICAL": "#f05050",
        "WARNING": "#f0a030",
        "CAUTION": "#e0c040",
    }.get(level, "#4a7dff")

    alerts_html = "".join(f"<li>{a}</li>" for a in alerts) if alerts else "<li>None</li>"

    subject = f"[VitalGuard {level}] {name} ({pid}) — Risk Score {score:.0f}/100"

    body = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
    <div style="background:{color};color:white;padding:16px 24px;border-radius:8px 8px 0 0;">
        <h2 style="margin:0;">⚠ VitalGuard Alert — {level}</h2>
        <p style="margin:4px 0 0;opacity:0.9;">{ts}</p>
    </div>
    <div style="background:#f8f9fa;padding:20px 24px;border:1px solid #e0e0e0;border-top:none;border-radius:0 0 8px 8px;">
        <h3 style="margin:0 0 8px;">{name} ({pid})</h3>
        <p style="margin:0 0 16px;"><strong>Risk Score: {score:.0f}/100</strong> — {reason}</p>

        <table style="width:100%;border-collapse:collapse;margin-bottom:16px;">
            <tr style="background:#e8e8e8;">
                <th style="padding:8px;text-align:left;">Sub-Score</th>
                <th style="padding:8px;text-align:right;">Value</th>
            </tr>
            <tr><td style="padding:6px 8px;">Vitals</td><td style="padding:6px 8px;text-align:right;">{sub.get('vitals',0):.0f}/100</td></tr>
            <tr style="background:#f0f0f0;"><td style="padding:6px 8px;">Pressure</td><td style="padding:6px 8px;text-align:right;">{sub.get('pressure',0):.0f}/100</td></tr>
            <tr><td style="padding:6px 8px;">Repositioning</td><td style="padding:6px 8px;text-align:right;">{sub.get('repositioning',0):.0f}/100</td></tr>
            <tr style="background:#f0f0f0;"><td style="padding:6px 8px;">Movement</td><td style="padding:6px 8px;text-align:right;">{sub.get('movement',0):.0f}/100</td></tr>
            <tr><td style="padding:6px 8px;">Sound</td><td style="padding:6px 8px;text-align:right;">{sub.get('sound',0):.0f}/100</td></tr>
        </table>

        <p><strong>Position:</strong> {posture.get('current','N/A')} ({posture.get('duration_min',0):.0f} min)</p>

        <h4 style="margin:16px 0 8px;">Active Alerts:</h4>
        <ul style="margin:0;padding-left:20px;">{alerts_html}</ul>

        <p style="margin-top:20px;font-size:12px;color:#888;">
            This is an automated alert from VitalGuard Patient Monitoring System.
            Do not reply to this email.
        </p>
    </div>
    </body></html>
    """

    return subject, body


class EmailNotifier:
    """Sends alert emails via SMTP."""

    def __init__(self, config: dict = None):
        """
        Args:
            config: SMTP config dict. Auto-loads from env if None.
        """
        self.config = config or _load_smtp_config()
        self.sent_count = 0
        self.send_log = []

    def is_configured(self) -> bool:
        """Check if SMTP is properly configured."""
        return bool(
            self.config.get("host")
            and self.config.get("user")
            and self.config.get("password")
            and self.config.get("recipient")
        )

    def send(self, alert: dict) -> dict:
        """
        Send an alert email.
        Falls back to console logging if SMTP is not configured.

        Args:
            alert: Alert payload from AlertManager

        Returns:
            dict with success, detail
        """
        subject, body = _format_alert_email(alert)

        if not self.is_configured():
            # Fallback: log to console
            log_entry = {
                "type": "email_log",
                "subject": subject,
                "to": "console (SMTP not configured)",
                "level": alert.get("risk_level", "info"),
                "patient": alert.get("patient_name", ""),
                "score": alert.get("risk_score", 0),
            }
            self.send_log.append(log_entry)
            self.sent_count += 1
            return {
                "success": True,
                "detail": "Logged to console (SMTP not configured)",
                "subject": subject,
            }

        # Send via SMTP
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.config["user"]
            msg["To"] = self.config["recipient"]
            msg.attach(MIMEText(body, "html"))

            with smtplib.SMTP(self.config["host"], self.config["port"]) as server:
                server.starttls()
                server.login(self.config["user"], self.config["password"])
                server.send_message(msg)

            self.sent_count += 1
            self.send_log.append({"type": "email_sent", "subject": subject})
            return {"success": True, "detail": f"Sent to {self.config['recipient']}"}

        except Exception as e:
            self.send_log.append({"type": "email_error", "error": str(e)})
            return {"success": False, "detail": str(e)}