"""
Quick Email Test
=================
Run this to verify email sending works.
Usage: python scripts/test_email.py
"""

import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from alerts.email_notifier import EmailNotifier, _load_smtp_config

# Step 1: Check config
print("=" * 50)
print("CHECKING SMTP CONFIG...")
print("=" * 50)
config = _load_smtp_config()
print(f"  Host: {config['host'] or '(empty)'}")
print(f"  Port: {config['port']}")
print(f"  User: {config['user'] or '(empty)'}")
print(f"  Pass: {'*' * len(config['password']) if config['password'] else '(empty)'}")
print(f"  To:   {config['recipient'] or '(empty)'}")

if not config["host"] or not config["user"] or not config["password"]:
    print("\n❌ SMTP not configured!")
    print("Make sure .env file is in the project root (vitalguard-software/.env)")
    print("With these values:")
    print("  SMTP_HOST=smtp.gmail.com")
    print("  SMTP_PORT=587")
    print("  SMTP_USER=ksh727301@gmail.com")
    print("  SMTP_PASSWORD=your_app_password_here")
    print("  ALERT_RECIPIENT=ilksh0530@gmail.com")
    sys.exit(1)

# Step 2: Send test email
print(f"\n{'=' * 50}")
print("SENDING TEST EMAIL...")
print("=" * 50)

notifier = EmailNotifier(config)
print(f"  Configured: {notifier.is_configured()}")

test_alert = {
    "patient_id": "PID-TEST",
    "patient_name": "Test Patient (VitalGuard)",
    "risk_score": 82.5,
    "risk_level": "critical",
    "reason": "This is a test alert from VitalGuard",
    "alerts": ["Heart rate elevated to 110 bpm", "SpO2 dropped to 91%", "Repositioning overdue (95 min)"],
    "timestamp": time.time(),
    "posture": {"current": "supine", "duration_min": 95},
    "sub_scores": {"vitals": 85, "pressure": 70, "repositioning": 80, "movement": 75, "sound": 30},
}

result = notifier.send(test_alert)

if result["success"] and "console" not in result.get("detail", ""):
    print(f"\n✅ Email sent successfully!")
    print(f"  Detail: {result['detail']}")
    print(f"  Check {config['recipient']} inbox (and spam folder)")
else:
    print(f"\n❌ Email failed!")
    print(f"  Detail: {result.get('detail', 'unknown')}")
    if "Authentication" in str(result.get("detail", "")):
        print("\n  → This usually means you need an App Password, not your regular Gmail password")
        print("  → Go to: https://myaccount.google.com/apppasswords")