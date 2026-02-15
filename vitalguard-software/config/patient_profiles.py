"""
Patient Profile Definitions
============================
Schema for patient metadata and personalized risk parameters.
Used by both synthetic generator and the adaptive risk engine.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class RiskCategory(Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class SurgeryType(Enum):
    SPINAL_FUSION = "Spinal Fusion"
    HIP_REPLACEMENT = "Hip Replacement"
    CARDIAC_BYPASS = "Cardiac Bypass"
    CRANIOTOMY = "Craniotomy"
    APPENDECTOMY = "Appendectomy"
    KNEE_ARTHROPLASTY = "Knee Arthroplasty"
    CHOLECYSTECTOMY = "Cholecystectomy"
    COLECTOMY = "Colectomy"
    THORACOTOMY = "Thoracotomy"
    HYSTERECTOMY = "Hysterectomy"
    CABG = "CABG"


@dataclass
class PatientProfile:
    """Complete patient profile with metadata and risk parameters."""

    # --- Core metadata ---
    patient_id: str              # e.g. "PID-2401"
    name: str                    # Full name
    age: int
    height_cm: float             # cm
    weight_kg: float             # kg
    room: str                    # e.g. "ICU-204"

    # --- Clinical info ---
    surgery_type: str
    post_op_day: int             # days since surgery
    is_diabetic: bool = False
    is_elderly: bool = False     # auto-set based on age
    has_cardiovascular_risk: bool = False
    mobility_level: str = "limited"  # "immobile", "limited", "moderate", "independent"

    # --- Personalized thresholds (overrides from risk engine) ---
    pressure_multiplier: float = 1.0
    reposition_interval_min: int = 90
    hr_upper_threshold: int = 90
    temp_upper_threshold: float = 37.5

    # --- Runtime state ---
    current_risk_category: RiskCategory = RiskCategory.LOW
    assigned_nurse: Optional[str] = None
    assigned_doctor: Optional[str] = None

    # --- Clinical history ---
    surgical_history: list = field(default_factory=list)
    lab_results: list = field(default_factory=list)
    medications: list = field(default_factory=list)
    allergies: list = field(default_factory=list)

    def __post_init__(self):
        """Auto-compute derived fields."""
        self.is_elderly = self.age >= 65
        self.bmi = round(self.weight_kg / (self.height_cm / 100) ** 2, 1)

        # Personalized adjustments
        if self.is_elderly:
            self.pressure_multiplier *= 1.2
            self.reposition_interval_min = 75
        if self.is_diabetic:
            self.pressure_multiplier *= 1.3
            self.reposition_interval_min = min(self.reposition_interval_min, 60)
        if self.has_cardiovascular_risk:
            self.hr_upper_threshold = 85

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON/API output."""
        return {
            "patient_id": self.patient_id,
            "name": self.name,
            "age": self.age,
            "height_cm": self.height_cm,
            "weight_kg": self.weight_kg,
            "bmi": self.bmi,
            "room": self.room,
            "surgery_type": self.surgery_type,
            "post_op_day": self.post_op_day,
            "is_diabetic": self.is_diabetic,
            "is_elderly": self.is_elderly,
            "has_cardiovascular_risk": self.has_cardiovascular_risk,
            "mobility_level": self.mobility_level,
            "pressure_multiplier": self.pressure_multiplier,
            "reposition_interval_min": self.reposition_interval_min,
            "hr_upper_threshold": self.hr_upper_threshold,
            "temp_upper_threshold": self.temp_upper_threshold,
            "current_risk_category": self.current_risk_category.value,
            "assigned_nurse": self.assigned_nurse,
            "assigned_doctor": self.assigned_doctor,
            "surgical_history": self.surgical_history,
            "lab_results": self.lab_results,
            "medications": self.medications,
            "allergies": self.allergies,
        }