# VitalGuard — Test Scenarios (S1, S2, S3)

These are short test scenarios to verify individual features.
Each one takes about 3 minutes and stops automatically.

All scenarios require two terminals open at the same time.

---

## Common Setup (same for all 3)

Terminal 1 — Start the server:
```bash
cd vitalguard-software
python -m api.server --hybrid --speed 4 --duration 10
```

Browser:
```
http://localhost:8000/dashboard
```

Then run one of the scenarios below in Terminal 2.

---

## S1: Risk Escalation — Card Sorting

Purpose: Verify that when a patient's risk score rises, their card moves to the top of the dashboard automatically.

Terminal 2:
```bash
cd vitalguard-software
python data/hw_simulator.py --scenario 1 --speed 4
```

What to watch: The TESTER card starts at the bottom (green, Risk ~15). Over 3 minutes it moves to the middle (orange, ~40), then to the very top (red, ~65). Cards are sorted by risk score in real time.

---

## S2: Voice Conversation — AI Summary

Purpose: Verify that patient speech is captured and summarized correctly by the AI voice agent.

Terminal 2:
```bash
cd vitalguard-software
python data/hw_simulator.py --scenario 2 --speed 4
```

What to watch: Click the TESTER card. Look for "Voice Monitoring Summary" — it should mention pain complaints and distress. Below it, "Recent Patient Speech" shows the latest conversation with pain keywords highlighted.

---

## S3: Fall Risk Detection — Sidebar Alert

Purpose: Verify that when fall risk is detected, a warning card appears on the right sidebar.

Terminal 2:
```bash
cd vitalguard-software
python data/hw_simulator.py --scenario 3 --speed 4
```

What to watch: The right sidebar starts empty. After about 1.5 minutes, a fall risk card appears (WARNING), then escalates to CRITICAL with indicators like "patient moving", "near bed edge", "bed tilt detected".

How fall detection works: mmWave radar detects the patient near the bed edge (< 50cm) and moving, the bed gyroscope detects sudden tilting (> 2.0 rad/s), and the wrist accelerometer detects impact or flailing (> 15g). These combine into a 0-1 risk score.