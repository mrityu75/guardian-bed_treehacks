"""
VitalGuard API Server
======================
FastAPI server with experiment mode for live dashboard demos.

Usage:
    python -m api.server                         # Default: 12 patients
    python -m api.server --experiment 1          # Exp 1: Normal->Critical
    python -m api.server --experiment 2          # Exp 2: Pressure+Posture
    python -m api.server --experiment all        # Both experiments + background
    python -m api.server --speed 2               # 2x playback speed
"""

import sys
import os
import json
import asyncio
import argparse
import random
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from api.ws_handler import ConnectionManager
from api.routes import router, set_sim_state
from config.settings import API_HOST, API_PORT, WS_BROADCAST_INTERVAL_SEC
from synthetic.scenarios import scenario_a_stable, scenario_b_gradual, scenario_c_acute
from synthetic.patient_factory import generate_patient
from synthetic.generator import SyntheticState, stream_patient_data, generate_combined_frame
from config.patient_profiles import PatientProfile
from analysis.risk_engine import RiskEngine
from analysis.pressure import compute_zone_scores
from digital_twin.twin_state import DigitalTwin
from alerts.alert_manager import AlertManager
from alerts.email_notifier import EmailNotifier
from reporting.groq_report import generate_report
from security.quantum_crypto import SecureChannel

# --- App setup ---
app = FastAPI(title="VitalGuard API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(router, prefix="/api")

ws_manager = ConnectionManager()
sim_state = {
    "twins": {}, "engines": {}, "reports": {},
    "alert_manager": None, "ws_manager": ws_manager,
    "scenario_name": "", "running": False,
}
set_sim_state(sim_state)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("action") == "get_patient":
                    pid = msg.get("id", "")
                    twin = sim_state["twins"].get(pid)
                    if twin:
                        await websocket.send_text(json.dumps({
                            "type": "patient_detail", "data": twin.to_dashboard_state(),
                        }))
            except Exception:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

dashboard_dir = os.path.join(os.path.dirname(__file__), "..", "dashboard")

@app.get("/dashboard")
async def serve_dashboard():
    html_path = os.path.join(dashboard_dir, "vitalguard.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    return {"error": "Dashboard HTML not found"}


# ============================================
# EXPERIMENT SCENARIO GENERATORS
# ============================================

def _exp1_normal_to_critical(duration_min=10):
    patient = PatientProfile(
        patient_id="EXP1-001", name="Patient Alpha",
        age=62, height_cm=170, weight_kg=78, room="ICU-301",
        surgery_type="Cardiac Bypass", post_op_day=2,
        is_diabetic=True, has_cardiovascular_risk=True, mobility_level="bed_bound",
        assigned_nurse="Nurse Kim", assigned_doctor="Dr. Han",
        surgical_history=["Appendectomy (2018)"],
        lab_results=[
            {"test": "CBC", "time": "-2h", "wbc": "7.8", "hgb": "13.1", "plt": "220", "status": "normal"},
            {"test": "BMP", "time": "-4h", "na": "141", "k": "4.0", "cr": "1.0", "glucose": "105", "status": "normal"},
        ],
        medications=["Morphine 2mg IV q4h PRN", "Cefazolin 1g IV q8h", "Enoxaparin 40mg SC daily",
                     "Metoprolol 25mg PO BID", "Insulin glargine 20u SC QHS"],
        allergies=["Penicillin (rash)"],
    )
    state = SyntheticState(patient, {
        "heart_rate": 68.0, "body_temp": 36.6, "spo2": 99.0,
        "hrv": 48.0, "resp_rate": 14.0, "movement_level": 0.4, "posture": "supine",
    })
    total = int(duration_min * 60 / 2.0)
    frames = []
    for i in range(total):
        p = i / total
        if p < 0.4:
            state.heart_rate = max(64, min(74, state.heart_rate + random.gauss(0, 0.3)))
            state.body_temp = max(36.4, min(36.8, state.body_temp + random.gauss(0, 0.01)))
            state.spo2 = max(97, min(100, state.spo2 + random.gauss(0, 0.1)))
            state.hrv = max(42, min(55, state.hrv + random.gauss(0, 0.5)))
            state.resp_rate = max(13, min(16, state.resp_rate + random.gauss(0, 0.2)))
            state.movement_level = 0.35 + random.gauss(0, 0.02)
        elif p < 0.6:
            pp = (p - 0.4) / 0.2
            for attr, s, e, n in [("heart_rate",68,95,.5),("body_temp",36.6,37.8,.02),
                ("spo2",99,94,.2),("hrv",48,28,.5),("resp_rate",14,20,.3)]:
                t = s + pp * (e - s)
                c = getattr(state, attr)
                setattr(state, attr, c + (t - c) * 0.05 + random.gauss(0, n))
            state.movement_level = max(0.1, 0.35 - pp * 0.2)
        elif p < 0.8:
            pp = (p - 0.6) / 0.2
            for attr, s, e, n in [("heart_rate",95,110,.8),("body_temp",37.8,38.5,.03),
                ("spo2",94,90,.3),("hrv",28,18,.8),("resp_rate",20,24,.4)]:
                t = s + pp * (e - s)
                c = getattr(state, attr)
                setattr(state, attr, c + (t - c) * 0.06 + random.gauss(0, n))
            state.movement_level = max(0.05, 0.15 - pp * 0.1)
        else:
            pp = (p - 0.8) / 0.2
            for attr, s, e, n in [("heart_rate",110,118,1.0),("body_temp",38.5,38.9,.03),
                ("spo2",90,88,.4),("hrv",18,13,.5),("resp_rate",24,28,.5)]:
                t = s + pp * (e - s)
                c = getattr(state, attr)
                setattr(state, attr, c + (t - c) * 0.08 + random.gauss(0, n))
            state.movement_level = max(0.02, 0.05 - pp * 0.03)
        state.heart_rate = max(55, min(130, state.heart_rate))
        state.body_temp = max(36.0, min(39.5, state.body_temp))
        state.spo2 = max(85, min(100, state.spo2))
        state.hrv = max(8, min(60, state.hrv))
        state.resp_rate = max(10, min(32, state.resp_rate))
        state.advance(2.0)
        frames.append(generate_combined_frame(state))
    return frames, patient


def _exp2_pressure_posture(duration_min=10):
    """
    Experiment 2: Pressure-driven posture rotation.
    
    Timeline (5 cycles of pressure buildup → reposition):
      Each cycle: ~20% of total time
        - Stay in position, pressure builds on contact side
        - Movement decreases (patient settles)
        - At cycle end: reposition to OPPOSITE side to relieve pressure
    
    Posture sequence: supine → right_lateral → supine → left_lateral → supine
    
    The key insight: when pressure is high on LEFT side → move to RIGHT
    When sacral pressure is high (supine too long) → move to lateral
    """
    patient = PatientProfile(
        patient_id="EXP2-001", name="Patient Beta",
        age=74, height_cm=165, weight_kg=82, room="ICU-302",
        surgery_type="Hip Replacement", post_op_day=1,
        is_diabetic=False, has_cardiovascular_risk=False, mobility_level="bed_bound",
        assigned_nurse="Nurse Park", assigned_doctor="Dr. Yoon",
        surgical_history=["Cataract surgery (2022)"],
        lab_results=[{"test":"CBC","time":"-3h","wbc":"8.1","hgb":"11.9","plt":"198","status":"normal"}],
        medications=["Morphine 2mg IV q4h PRN", "Cefazolin 1g IV q8h", "Enoxaparin 40mg SC daily"],
        allergies=["NKDA"],
    )
    state = SyntheticState(patient, {
        "heart_rate": 72.0, "body_temp": 36.7, "spo2": 98.0,
        "hrv": 42.0, "resp_rate": 15.0, "movement_level": 0.25, "posture": "supine",
    })
    total = int(duration_min * 60 / 2.0)
    frames = []

    # Posture rotation schedule:
    # supine(20%) → right_lateral(20%) → supine(20%) → left_lateral(20%) → supine(20%)
    posture_schedule = [
        (0.00, 0.20, "supine",         "Sacral pressure building"),
        (0.20, 0.40, "right_lateral",  "Right hip/shoulder pressure building"),
        (0.40, 0.60, "supine",         "Sacral pressure building again"),
        (0.60, 0.80, "left_lateral",   "Left hip/shoulder pressure building"),
        (0.80, 1.00, "supine",         "Final position"),
    ]
    last_posture = None

    for i in range(total):
        p = i / total

        # Determine current posture from schedule
        current_posture = "supine"
        for ps, pe, posture, _reason in posture_schedule:
            if ps <= p < pe:
                current_posture = posture
                break

        # Posture transition: brief movement spike
        if current_posture != last_posture and last_posture is not None:
            state.posture_duration_min = 0.0
            state.movement_level = 0.5 + random.gauss(0, 0.05)  # High movement during turn
        else:
            # Within a position: movement gradually decreases (patient settles)
            phase_progress = 0
            for ps, pe, posture, _ in posture_schedule:
                if ps <= p < pe:
                    phase_progress = (p - ps) / (pe - ps)
                    break
            state.movement_level = max(0.03, 0.3 - phase_progress * 0.25 + random.gauss(0, 0.02))

        state.posture = current_posture
        last_posture = current_posture

        # Stable vitals with slight variation based on position
        base_hr = 72
        if current_posture == "left_lateral":
            base_hr = 74  # Slightly elevated on side
        elif current_posture == "right_lateral":
            base_hr = 73
        state.heart_rate = max(65, min(85, base_hr + random.gauss(0, 1.5)))
        state.body_temp = 36.7 + random.gauss(0, 0.05)
        state.spo2 = max(95, min(100, 98 + random.gauss(0, 0.3)))
        state.hrv = 42 + random.gauss(0, 1)
        state.resp_rate = 15 + random.gauss(0, 0.5)

        state.advance(2.0)
        frames.append(generate_combined_frame(state))

    return frames, patient


# ============================================
# MAIN SIMULATION LOOP
# ============================================

async def run_simulation(scenario_key="ALL", experiment=None, speed=1.0, duration=10):
    sim_state["running"] = True
    sim_state["scenario_name"] = experiment or scenario_key
    all_frames = {}

    # Experiment patients
    if experiment:
        if experiment in ("1", "all"):
            f, pt = _exp1_normal_to_critical(duration)
            all_frames[pt.patient_id] = {"frames": f, "patient": pt}
            print(f"[EXP1] Patient Alpha: {len(f)} frames ({duration}min)")
        if experiment in ("2", "all"):
            f, pt = _exp2_pressure_posture(duration)
            all_frames[pt.patient_id] = {"frames": f, "patient": pt}
            print(f"[EXP2] Patient Beta: {len(f)} frames ({duration}min)")

    # Background patients (always add some)
    bg = [
        {"id":"BG-001","hr":68,"tp":36.5,"sp":99,"hv":48,"rr":14,"mv":0.45},
        {"id":"BG-002","hr":74,"tp":36.9,"sp":97,"hv":40,"rr":16,"mv":0.35},
        {"id":"BG-003","hr":82,"tp":37.3,"sp":96,"hv":32,"rr":17,"mv":0.28},
        {"id":"BG-004","hr":65,"tp":36.4,"sp":99,"hv":52,"rr":13,"mv":0.50},
        {"id":"BG-005","hr":70,"tp":36.6,"sp":98,"hv":44,"rr":14,"mv":0.42},
        {"id":"BG-006","hr":86,"tp":37.4,"sp":95,"hv":29,"rr":19,"mv":0.22},
    ]
    for cfg in bg:
        ep = generate_patient(patient_id=cfg["id"])
        st = SyntheticState(ep, {
            "heart_rate":cfg["hr"],"body_temp":cfg["tp"],"spo2":cfg["sp"],
            "hrv":cfg["hv"],"resp_rate":cfg["rr"],"movement_level":cfg["mv"],
            "posture": random.choice(["supine","left_lateral","right_lateral"]),
        })
        fr = list(stream_patient_data(st, duration_min=duration, interval_sec=2.0))
        all_frames[ep.patient_id] = {"frames": fr, "patient": ep}

    # Quantum encryption
    server_ch = SecureChannel()
    client_ch = SecureChannel()
    si = server_ch.init_server()
    cr = client_ch.init_client(si["public_key"])
    server_ch.complete_handshake(cr["ciphertext"])
    print(f"[SEC] Quantum channel: {si['algorithm']}")

    # Init engines
    email_notifier = EmailNotifier()
    alert_manager = AlertManager(notifiers=[email_notifier])
    sim_state["alert_manager"] = alert_manager
    for pid, data in all_frames.items():
        sim_state["engines"][pid] = RiskEngine(data["patient"])
        sim_state["twins"][pid] = DigitalTwin(data["patient"])

    max_frames = max(len(d["frames"]) for d in all_frames.values())
    interval = WS_BROADCAST_INTERVAL_SEC / speed
    print(f"[SIM] {len(all_frames)} patients | {max_frames} frames | {speed}x speed | interval={interval:.2f}s")

    # Track posture per patient for change detection
    last_postures = {}

    for fi in range(max_frames):
        if not sim_state["running"]:
            break
        bd = {"type": "update", "frame": fi, "patients": {}}

        for pid, data in all_frames.items():
            if fi >= len(data["frames"]):
                continue
            frame = data["frames"][fi]
            engine = sim_state["engines"][pid]
            twin = sim_state["twins"][pid]

            assessment = engine.assess(frame)
            bed = frame.get("bed", {})
            fsr = bed.get("fsrs", [0]*12)
            dur = frame.get("vitals_snapshot", {}).get("posture_duration_min", 0)
            zones = compute_zone_scores(fsr, dur, data["patient"].pressure_multiplier)
            twin.update_pressure_zones(zones)
            twin.update_from_assessment(assessment)

            # Detect posture change for EXP patients
            vs = frame.get("vitals_snapshot", {})
            cur_posture = vs.get("posture", "?")
            if pid.startswith("EXP"):
                prev = last_postures.get(pid)
                if prev and cur_posture != prev:
                    ts = datetime.now().strftime("%H:%M:%S")
                    # Explain why: pressure was building on previous side
                    if prev == "supine":
                        reason = "Sacral pressure overdue → relieving to lateral"
                    elif "left" in prev:
                        reason = "Left hip/shoulder pressure high → rotate to supine"
                    elif "right" in prev:
                        reason = "Right hip/shoulder pressure high → rotate to supine"
                    else:
                        reason = "Scheduled repositioning"
                    print(f"[POSTURE] {ts} | {pid} | {prev} → {cur_posture} | {reason}")
                last_postures[pid] = cur_posture

            # Alert
            ar = alert_manager.evaluate(assessment)
            if ar["should_alert"]:
                ts = datetime.now().strftime("%H:%M:%S")
                r = assessment.get("risk_score", 0)
                lv = assessment.get("risk_level", "?")
                print(f"[ALERT] {ts} | {pid} | Risk:{r:.0f} | {lv.upper()} | {ar['reason']}")

            # Report every 60 frames
            if fi % 60 == 0:
                sim_state["reports"][pid] = generate_report(assessment)

            # Encrypt
            ds = twin.to_dashboard_state()
            envelope = server_ch.encrypt_patient_data(ds)
            decrypted = client_ch.decrypt_patient_data(envelope)

            # Log encryption for EXP patients
            if pid.startswith("EXP") and fi % 15 == 0:
                vs = frame.get("vitals_snapshot", {})
                risk = assessment.get("risk_score", 0)
                enc_b = len(json.dumps(envelope))
                mac = envelope["encrypted"]["mac"][:16]
                posture = vs.get("posture", "?")
                pos_dur = vs.get("posture_duration_min", 0)
                print(f"[ENC] {pid} f#{fi:04d} | Risk:{risk:5.1f} | "
                      f"HR:{vs.get('heart_rate',0):5.1f} SpO2:{vs.get('spo2',0):5.1f} "
                      f"T:{vs.get('body_temp',0):5.2f} | {posture}/{pos_dur:.0f}m | "
                      f"{enc_b}B MAC:{mac}.. {'✓' if decrypted else '✗'}")

            bd["patients"][pid] = ds

        if ws_manager.client_count > 0:
            await ws_manager.broadcast(bd)
        await asyncio.sleep(interval)

    print(f"[SIM] Complete. {fi+1} frames processed.")
    sim_state["running"] = False


async def run_file_watch(speed=1.0):
    """
    Watch data/incoming/ for JSON files from hardware/writer.
    Reads {pid}_profile.json for patient info, {pid}.json for frames.
    """
    sim_state["running"] = True
    sim_state["scenario_name"] = "file-watch"
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "incoming")
    os.makedirs(data_dir, exist_ok=True)

    # Encryption
    server_ch = SecureChannel()
    client_ch = SecureChannel()
    si = server_ch.init_server()
    cr = client_ch.init_client(si["public_key"])
    server_ch.complete_handshake(cr["ciphertext"])
    print(f"[SEC] Quantum channel: {si['algorithm']}")

    email_notifier = EmailNotifier()
    alert_manager = AlertManager(notifiers=[email_notifier])
    sim_state["alert_manager"] = alert_manager

    interval = 0.5 / speed
    file_mtimes = {}
    patient_cache = {}  # pid -> PatientProfile
    frame_count = 0

    print(f"[WATCH] Monitoring: {os.path.abspath(data_dir)}")
    print(f"[WATCH] Poll interval: {interval:.2f}s")
    print(f"[WATCH] Waiting for data files...")

    while sim_state["running"]:
        broadcast_data = {"type": "update", "frame": frame_count, "patients": {}}
        any_update = False

        try:
            all_files = os.listdir(data_dir)
        except Exception:
            all_files = []

        # Find data files (not profiles)
        data_files = [f for f in all_files if f.endswith(".json") and not f.endswith("_profile.json")]

        for fname in data_files:
            fpath = os.path.join(data_dir, fname)
            pid = fname.replace(".json", "")

            try:
                mtime = os.path.getmtime(fpath)
                file_changed = pid not in file_mtimes or mtime != file_mtimes[pid]

                if file_changed:
                    file_mtimes[pid] = mtime

                    with open(fpath, "r") as f:
                        frame = json.load(f)

                    # Load patient profile if not cached
                    if pid not in patient_cache:
                        prof_path = os.path.join(data_dir, f"{pid}_profile.json")
                        if os.path.exists(prof_path):
                            with open(prof_path, "r") as pf:
                                pd = json.load(pf)
                            pat = PatientProfile(**pd)
                        else:
                            pat = generate_patient(patient_id=pid)
                        patient_cache[pid] = pat
                        sim_state["engines"][pid] = RiskEngine(pat)
                        sim_state["twins"][pid] = DigitalTwin(pat)
                        print(f"[WATCH] New patient: {pid} ({pat.name})")

                    engine = sim_state["engines"][pid]
                    twin = sim_state["twins"][pid]
                    pat = patient_cache[pid]

                    # Assess
                    assessment = engine.assess(frame)

                    # Pressure zones
                    bed = frame.get("bed", {})
                    fsr = bed.get("fsrs", [0]*12)
                    dur = frame.get("vitals_snapshot", {}).get("posture_duration_min", 0)
                    zones = compute_zone_scores(fsr, dur, pat.pressure_multiplier)
                    twin.update_pressure_zones(zones)
                    twin.update_from_assessment(assessment)

                    # Alert
                    ar = alert_manager.evaluate(assessment)
                    if ar["should_alert"]:
                        ts = datetime.now().strftime("%H:%M:%S")
                        r = assessment.get("risk_score", 0)
                        lv = assessment.get("risk_level", "?")
                        reason = ar.get("reason", "")
                        sent = ar.get("alerts_sent", [])
                        n_sent = len(sent) if isinstance(sent, list) else sent
                        print(f"[ALERT] {ts} | {pid} | Risk:{r:.0f} | {lv.upper()} | {reason}")
                        if n_sent:
                            print(f"[EMAIL] Sent {n_sent} email notification(s)")

                    # Report every 30 frames
                    if frame_count % 30 == 0:
                        sim_state["reports"][pid] = generate_report(assessment)

                    # Encrypt + log
                    ds = twin.to_dashboard_state()
                    envelope = server_ch.encrypt_patient_data(ds)
                    client_ch.decrypt_patient_data(envelope)

                    if pid.startswith("EXP") and frame_count % 3 == 0:
                        vs = frame.get("vitals_snapshot", {})
                        risk = assessment.get("risk_score", 0)
                        level = assessment.get("risk_level", "info")
                        enc_b = len(json.dumps(envelope))
                        mac = envelope["encrypted"]["mac"][:16]
                        posture = vs.get("posture", "?")
                        print(f"[ENC] {pid} | Risk:{risk:5.1f} ({level:8s}) | "
                              f"HR:{vs.get('heart_rate',0):5.1f} SpO2:{vs.get('spo2',0):5.1f} "
                              f"T:{vs.get('body_temp',0):5.2f} | {posture:14s} | "
                              f"{enc_b}B MAC:{mac}.. [OK]")

                    any_update = True

                # Always include in broadcast (changed or not)
                if pid in sim_state["twins"]:
                    broadcast_data["patients"][pid] = sim_state["twins"][pid].to_dashboard_state()

            except (json.JSONDecodeError, KeyError, IOError, TypeError):
                pass

        if broadcast_data["patients"] and ws_manager.client_count > 0:
            await ws_manager.broadcast(broadcast_data)

        if any_update:
            frame_count += 1

        await asyncio.sleep(interval)


@app.on_event("startup")
async def startup():
    exp = os.environ.get("VITALGUARD_EXPERIMENT", "")
    speed = float(os.environ.get("VITALGUARD_SPEED", "1"))
    dur = int(os.environ.get("VITALGUARD_DURATION", "10"))
    watch = os.environ.get("VITALGUARD_WATCH", "")
    if watch:
        asyncio.create_task(run_file_watch(speed=speed))
    else:
        asyncio.create_task(run_simulation(experiment=exp or None, speed=speed, duration=dur))


def main():
    import uvicorn
    parser = argparse.ArgumentParser(description="VitalGuard API Server")
    parser.add_argument("--host", default=API_HOST)
    parser.add_argument("--port", type=int, default=API_PORT)
    parser.add_argument("--experiment", default="", choices=["", "1", "2", "all"])
    parser.add_argument("--watch", action="store_true", help="File-watch mode: read from data/incoming/")
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--duration", type=int, default=10, help="Minutes")
    args = parser.parse_args()

    os.environ["VITALGUARD_EXPERIMENT"] = args.experiment
    os.environ["VITALGUARD_SPEED"] = str(args.speed)
    os.environ["VITALGUARD_DURATION"] = str(args.duration)
    if args.watch:
        os.environ["VITALGUARD_WATCH"] = "1"

    print(f"[VitalGuard] Dashboard: http://localhost:{args.port}/dashboard")
    if args.watch:
        print(f"[VitalGuard] FILE-WATCH MODE: reading from data/incoming/")
    elif args.experiment:
        print(f"[VitalGuard] EXPERIMENT {args.experiment} | {args.duration}min | {args.speed}x speed")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")

if __name__ == "__main__":
    main()