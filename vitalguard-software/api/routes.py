"""
API Routes
===========
REST endpoints for patient data, reports, and system status.
"""

from fastapi import APIRouter

router = APIRouter()

# These will be populated by server.py with references to the simulation state
_sim_state = {}


def set_sim_state(state: dict):
    """Called by server.py to share simulation state with routes."""
    global _sim_state
    _sim_state = state


@router.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "VitalGuard API"}


@router.get("/patients")
async def get_patients():
    """Get list of all patients with current risk status."""
    twins = _sim_state.get("twins", {})
    patients = []
    for pid, twin in twins.items():
        state = twin.to_dashboard_state()
        patients.append({
            "patient_id": state["patient_id"],
            "patient_name": state["patient_name"],
            "room": state["room"],
            "risk_score": state["risk_score"],
            "risk_level": state["risk_level"],
            "vitals": state["vitals"],
            "posture": state["posture"]["current"],
        })
    # Sort by risk (critical first)
    level_order = {"critical": 0, "warning": 1, "caution": 2, "info": 3}
    patients.sort(key=lambda p: (level_order.get(p["risk_level"], 9), -p["risk_score"]))
    return {"patients": patients, "count": len(patients)}


@router.get("/patients/{patient_id}")
async def get_patient_detail(patient_id: str):
    """Get full digital twin state for a specific patient."""
    twins = _sim_state.get("twins", {})
    twin = twins.get(patient_id)
    if not twin:
        return {"error": f"Patient {patient_id} not found"}
    return twin.to_dashboard_state()


@router.get("/patients/{patient_id}/report")
async def get_patient_report(patient_id: str):
    """Get the latest generated report for a patient."""
    reports = _sim_state.get("reports", {})
    report = reports.get(patient_id)
    if not report:
        return {"error": f"No report available for {patient_id}"}
    return report


@router.get("/alerts")
async def get_alerts():
    """Get recent alerts across all patients."""
    alert_mgr = _sim_state.get("alert_manager")
    if not alert_mgr:
        return {"alerts": []}
    history = alert_mgr.get_alert_history()
    # Return last 50 alerts, newest first
    return {"alerts": history[-50:][::-1], "total": len(history)}


@router.get("/status")
async def get_system_status():
    """Get system status and simulation info."""
    twins = _sim_state.get("twins", {})
    ws_mgr = _sim_state.get("ws_manager")
    return {
        "status": "running",
        "patients_monitored": len(twins),
        "ws_clients": ws_mgr.client_count if ws_mgr else 0,
        "scenario": _sim_state.get("scenario_name", "unknown"),
    }