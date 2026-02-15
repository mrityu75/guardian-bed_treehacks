"""
Digital Twin State Model
=========================
Maintains a real-time virtual replica of the patient's condition.
Not just visualization — this is the complete digital representation
that combines all sensor data into a unified patient model.

The twin state feeds:
- 3D mannequin visualization (posture, pressure heatmap, stress glow)
- Dashboard status indicators
- Risk engine (provides computed features)
"""

import time
from dataclasses import dataclass, field
from typing import Optional
from config.patient_profiles import PatientProfile


@dataclass
class BodyZoneState:
    """State of a single body pressure zone."""
    zone_name: str
    pressure: float = 0.0       # 0-1 normalized
    risk: float = 0.0           # 0-1 risk score
    level: str = "low"          # low/moderate/elevated/high
    duration_min: float = 0.0   # time under current pressure
    color: list = field(default_factory=lambda: [0.2, 0.8, 0.2])  # RGB for visualization


@dataclass
class VitalsState:
    """Current vital signs with classification."""
    heart_rate: float = 72.0
    heart_rate_level: str = "normal"
    body_temp: float = 36.7
    body_temp_level: str = "normal"
    spo2: float = 98.0
    spo2_level: str = "normal"
    hrv: float = 42.0
    hrv_level: str = "normal"
    resp_rate: float = 16.0
    resp_rate_level: str = "normal"
    blood_pressure: str = "120/80"


def _risk_to_color(risk: float) -> list:
    """
    Convert risk score (0-1) to RGB color for visualization.
    Green (safe) -> Yellow (caution) -> Red (danger)
    """
    if risk < 0.3:
        # Green to yellow
        t = risk / 0.3
        return [t, 0.85, 0.2 * (1 - t)]
    elif risk < 0.7:
        # Yellow to orange
        t = (risk - 0.3) / 0.4
        return [0.95, 0.85 - t * 0.5, 0.0]
    else:
        # Orange to red
        t = (risk - 0.7) / 0.3
        return [0.95, 0.35 - t * 0.35, 0.0]


class DigitalTwin:
    """
    Complete digital twin of a patient.
    Aggregates all sensor analysis into a single state model
    that can be serialized for the dashboard.
    """

    def __init__(self, patient: PatientProfile):
        self.patient = patient
        self.last_update = 0.0

        # Posture state
        self.posture = "supine"
        self.posture_confidence = 0.0
        self.posture_duration_min = 0.0
        self.reposition_status = "ok"
        self.reposition_remaining_min = 90.0

        # Vitals
        self.vitals = VitalsState()

        # Pressure zones (12 FSR sensors)
        self.body_zones = {}
        zone_names = [
            "head", "left_shoulder", "right_shoulder",
            "upper_back_left", "upper_back_right",
            "mid_back_left", "mid_back_right",
            "sacrum_left", "sacrum_right",
            "left_thigh", "right_thigh", "heels",
        ]
        for name in zone_names:
            self.body_zones[name] = BodyZoneState(zone_name=name)

        # Overall state
        self.risk_score = 0.0
        self.risk_level = "info"
        self.stress_level = 0.0  # 0-1, derived from HRV + HR
        self.movement_level = 0.3
        self.consciousness = "responsive"  # responsive/reduced/unresponsive
        self.alerts = []

        # History for sparkline charts
        self.history_length = 120
        self.hr_history = []
        self.temp_history = []
        self.spo2_history = []
        self.risk_history = []

    def update_from_assessment(self, assessment: dict):
        """
        Update the digital twin from a risk engine assessment.
        This is the main update method called every data frame.

        Args:
            assessment: Output from RiskEngine.assess()
        """
        self.last_update = time.time()

        # --- Posture ---
        posture_data = assessment.get("posture", {})
        self.posture = posture_data.get("current", self.posture)
        self.posture_confidence = posture_data.get("confidence", 0)
        self.posture_duration_min = posture_data.get("duration_min", 0)

        repo = assessment.get("repositioning", {})
        self.reposition_status = repo.get("status", "ok")
        self.reposition_remaining_min = repo.get("remaining_min", 90)

        # --- Vitals ---
        vitals_params = assessment.get("vitals_analysis", {}).get("parameters", {})

        if "heart_rate" in vitals_params:
            self.vitals.heart_rate = vitals_params["heart_rate"]["value"]
            self.vitals.heart_rate_level = vitals_params["heart_rate"]["classification"]["level"]

        if "body_temp" in vitals_params:
            self.vitals.body_temp = vitals_params["body_temp"]["value"]
            self.vitals.body_temp_level = vitals_params["body_temp"]["classification"]["level"]

        if "spo2" in vitals_params:
            self.vitals.spo2 = vitals_params["spo2"]["value"]
            self.vitals.spo2_level = vitals_params["spo2"]["classification"]["level"]

        if "hrv" in vitals_params:
            self.vitals.hrv = vitals_params["hrv"]["value"]
            self.vitals.hrv_level = vitals_params["hrv"]["classification"]["level"]

        if "resp_rate" in vitals_params:
            self.vitals.resp_rate = vitals_params["resp_rate"]["value"]
            self.vitals.resp_rate_level = vitals_params["resp_rate"]["classification"]["level"]

        # --- Pressure zones ---
        pressure_data = assessment.get("pressure_analysis", {})
        # If full zone data is available (from extended assessment)
        overall = pressure_data.get("overall", {})

        # --- Risk ---
        self.risk_score = assessment.get("risk_score", 0)
        self.risk_level = assessment.get("risk_level", "info")
        self.movement_level = assessment.get("movement_level", 0.3)
        self.alerts = assessment.get("alerts", [])

        # --- Computed: stress level ---
        # Stress derived from HRV (low HRV = high stress) and HR (high HR = high stress)
        hrv_stress = max(0, 1 - (self.vitals.hrv / 50))  # HRV < 50 = some stress
        hr_stress = max(0, (self.vitals.heart_rate - 80) / 40)  # HR > 80 = some stress
        self.stress_level = min(1.0, (hrv_stress * 0.6 + hr_stress * 0.4))

        # --- Computed: consciousness estimate ---
        if self.movement_level < 0.05:
            sound = assessment.get("sound", {})
            if sound.get("classification") == "silence":
                self.consciousness = "unresponsive"
            else:
                self.consciousness = "reduced"
        elif self.movement_level < 0.15:
            self.consciousness = "reduced"
        else:
            self.consciousness = "responsive"

        # --- History ---
        self.hr_history.append(self.vitals.heart_rate)
        self.temp_history.append(self.vitals.body_temp)
        self.spo2_history.append(self.vitals.spo2)
        self.risk_history.append(self.risk_score)

        # Trim history
        for hist in [self.hr_history, self.temp_history, self.spo2_history, self.risk_history]:
            if len(hist) > self.history_length:
                hist.pop(0)

    def update_pressure_zones(self, zone_scores: dict):
        """
        Update pressure zone data from detailed pressure analysis.

        Args:
            zone_scores: Output from pressure.compute_zone_scores()
        """
        for name, data in zone_scores.items():
            if name in self.body_zones:
                zone = self.body_zones[name]
                zone.pressure = data.get("pressure", 0)
                zone.risk = data.get("risk", 0)
                zone.level = data.get("level", "low")
                zone.color = _risk_to_color(zone.risk)

    def to_dashboard_state(self) -> dict:
        """
        Serialize the twin state for the dashboard WebSocket feed.
        This is what gets sent to the frontend every update.
        """
        return {
            "patient_id": self.patient.patient_id,
            "patient_name": self.patient.name,
            "room": self.patient.room,
            "surgery_type": self.patient.surgery_type,
            "post_op_day": self.patient.post_op_day,
            "last_update": self.last_update,

            # Overall
            "risk_score": round(self.risk_score, 1),
            "risk_level": self.risk_level,
            "stress_level": round(self.stress_level, 3),
            "consciousness": self.consciousness,

            # Posture
            "posture": {
                "current": self.posture,
                "confidence": round(self.posture_confidence, 3),
                "duration_min": round(self.posture_duration_min, 1),
                "reposition_status": self.reposition_status,
                "remaining_min": round(self.reposition_remaining_min, 1),
            },

            # Vitals
            "vitals": {
                "heart_rate": {"value": round(self.vitals.heart_rate, 1), "level": self.vitals.heart_rate_level},
                "body_temp": {"value": round(self.vitals.body_temp, 2), "level": self.vitals.body_temp_level},
                "spo2": {"value": round(self.vitals.spo2, 1), "level": self.vitals.spo2_level},
                "hrv": {"value": round(self.vitals.hrv, 1), "level": self.vitals.hrv_level},
                "resp_rate": {"value": round(self.vitals.resp_rate, 1), "level": self.vitals.resp_rate_level},
            },

            # Pressure heatmap
            "pressure_zones": {
                name: {
                    "pressure": round(z.pressure, 4),
                    "risk": round(z.risk, 4),
                    "level": z.level,
                    "color": [round(c, 3) for c in z.color],
                }
                for name, z in self.body_zones.items()
            },

            # Movement
            "movement_level": round(self.movement_level, 3),

            # Alerts
            "alerts": self.alerts[:10],
            "alert_count": len(self.alerts),

            # Sparkline data (last N readings)
            "history": {
                "heart_rate": [round(v, 1) for v in self.hr_history[-60:]],
                "body_temp": [round(v, 2) for v in self.temp_history[-60:]],
                "spo2": [round(v, 1) for v in self.spo2_history[-60:]],
                "risk_score": [round(v, 1) for v in self.risk_history[-60:]],
            },

            # Patient profile summary
            "profile": {
                "age": self.patient.age,
                "bmi": self.patient.bmi,
                "is_elderly": self.patient.is_elderly,
                "is_diabetic": self.patient.is_diabetic,
                "mobility_level": self.patient.mobility_level,
                "assigned_nurse": self.patient.assigned_nurse,
                "assigned_doctor": self.patient.assigned_doctor,
                "allergies": getattr(self.patient, 'allergies', []),
                "medications": getattr(self.patient, 'medications', []),
                "lab_results": getattr(self.patient, 'lab_results', []),
                "surgical_history": getattr(self.patient, 'surgical_history', []),
                "has_cardiovascular_risk": getattr(self.patient, 'has_cardiovascular_risk', False),
            },

            # Voice & Fall risk (populated by server from hw_adapter)
            "voice_summary": getattr(self, '_voice_summary', ''),
            "fall_risk": getattr(self, '_fall_risk', {"score": 0, "level": "low", "indicators": []}),
            "_voiceLog": getattr(self, '_voice_log', []),
        }