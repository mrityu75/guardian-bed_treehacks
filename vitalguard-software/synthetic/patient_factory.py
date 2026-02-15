"""
Patient Factory
================
Generates random but realistic patient profiles for synthetic testing.
Each patient gets a unique ID, plausible demographics, and clinical info.
"""

import random
import string
from config.patient_profiles import PatientProfile, SurgeryType

# --- Name pools ---
FIRST_NAMES_M = [
    "James", "William", "Robert", "David", "Michael", "Thomas", "Daniel",
    "Andrew", "Ethan", "Lucas", "Noah", "Liam", "Benjamin", "Samuel",
    "Joseph", "Henry", "Alexander", "Christopher", "Matthew", "Nathan",
]
FIRST_NAMES_F = [
    "Eleanor", "Maria", "Sarah", "Linda", "Emma", "Olivia", "Sophia",
    "Grace", "Hannah", "Ava", "Chloe", "Isabella", "Mia", "Charlotte",
    "Emily", "Amelia", "Victoria", "Katherine", "Rachel", "Diana",
]
LAST_NAMES = [
    "Mitchell", "Sullivan", "Gonzalez", "Chen", "Thompson", "Park",
    "Patel", "Kim", "Rodriguez", "Wright", "Nakamura", "Brown",
    "Lee", "Davis", "Wilson", "Martinez", "Clark", "Moore", "Johnson",
    "Taylor", "Anderson", "Harris", "White", "Jackson", "Thomas",
    "Garcia", "Robinson", "Walker", "Young", "Allen", "King", "Scott",
]

ROOMS = [f"ICU-{i}" for i in range(201, 230)]
NURSES = ["Nurse Kim", "Nurse Park", "Nurse Lee", "Nurse Choi", "Nurse Jung",
          "Nurse Oh", "Nurse Yoon", "Nurse Hwang"]
DOCTORS = ["Dr. Han", "Dr. Yoon", "Dr. Shin", "Dr. Kwon", "Dr. Seo",
           "Dr. Lim", "Dr. Cho", "Dr. Kang"]

MEDICATIONS_POOL = [
    "Morphine 2mg IV q4h PRN", "Ketorolac 15mg IV q6h", "Cefazolin 1g IV q8h",
    "Enoxaparin 40mg SC daily", "Omeprazole 40mg IV daily", "Ondansetron 4mg IV PRN",
    "Metoclopramide 10mg IV q8h", "Acetaminophen 1g IV q6h", "Heparin 5000u SC q12h",
    "Famotidine 20mg IV q12h", "Metoprolol 25mg PO BID", "Lisinopril 10mg PO daily",
    "Insulin glargine 20u SC QHS", "Metformin 500mg PO BID", "Aspirin 81mg PO daily",
]

ALLERGIES_POOL = [
    "NKDA", "NKDA", "NKDA", "NKDA",  # Most patients have no known allergies
    "Penicillin (rash)", "Sulfa drugs (hives)", "Codeine (nausea)",
    "Latex (contact dermatitis)", "Iodine contrast (anaphylaxis)",
]

LAB_TEMPLATES = [
    {"test": "CBC", "time": "-2h", "wbc": "7.2", "hgb": "12.8", "plt": "245", "status": "normal"},
    {"test": "CBC", "time": "-2h", "wbc": "12.4", "hgb": "10.2", "plt": "180", "status": "elevated WBC"},
    {"test": "BMP", "time": "-4h", "na": "140", "k": "4.1", "cr": "0.9", "glucose": "98", "status": "normal"},
    {"test": "BMP", "time": "-4h", "na": "137", "k": "3.6", "cr": "1.4", "glucose": "186", "status": "elevated Cr/glucose"},
    {"test": "Lactate", "time": "-1h", "value": "1.2", "unit": "mmol/L", "status": "normal"},
    {"test": "Lactate", "time": "-1h", "value": "3.8", "unit": "mmol/L", "status": "elevated"},
    {"test": "CRP", "time": "-6h", "value": "5.2", "unit": "mg/L", "status": "mildly elevated"},
    {"test": "Procalcitonin", "time": "-6h", "value": "0.3", "unit": "ng/mL", "status": "normal"},
    {"test": "Coagulation", "time": "-8h", "pt": "12.5", "inr": "1.1", "aptt": "28", "status": "normal"},
]

SURGICAL_HISTORY_POOL = [
    "Appendectomy (2018)", "Cholecystectomy (2020)", "Knee arthroscopy (2019)",
    "C-section (2017)", "Hernia repair (2015)", "Tonsillectomy (childhood)",
    "Cataract surgery (2022)", "Dental extraction (2021)",
]


def generate_patient_id() -> str:
    """Generate a unique patient ID like PID-2401."""
    num = random.randint(1000, 9999)
    return f"PID-{num}"


def generate_patient(
    patient_id: str = None,
    force_elderly: bool = False,
    force_diabetic: bool = False,
    force_cardio_risk: bool = False,
    surgery_type: str = None,
) -> PatientProfile:
    """
    Create a single random patient profile.

    Args:
        patient_id: Override auto-generated ID
        force_elderly: Force age >= 65
        force_diabetic: Force diabetic flag
        force_cardio_risk: Force cardiovascular risk flag
        surgery_type: Override random surgery selection
    """
    gender = random.choice(["M", "F"])
    first = random.choice(FIRST_NAMES_M if gender == "M" else FIRST_NAMES_F)
    last = random.choice(LAST_NAMES)
    name = f"{first} {last}"

    # Age distribution: weighted toward 50-80 for ICU post-surgical
    if force_elderly:
        age = random.randint(65, 88)
    else:
        age = random.choices(
            range(25, 90),
            weights=[1]*15 + [2]*10 + [4]*15 + [3]*15 + [1]*10,
            k=1,
        )[0]

    # Height/weight with realistic BMI range
    if gender == "M":
        height = round(random.gauss(174, 7), 1)
        weight = round(random.gauss(78, 12), 1)
    else:
        height = round(random.gauss(162, 6), 1)
        weight = round(random.gauss(65, 10), 1)

    height = max(148, min(198, height))
    weight = max(42, min(130, weight))

    # Clinical attributes
    if surgery_type is None:
        surgery_type = random.choice([s.value for s in SurgeryType])

    is_diabetic = force_diabetic or (random.random() < (0.3 if age > 60 else 0.1))
    has_cardio = force_cardio_risk or (random.random() < (0.25 if age > 55 else 0.08))

    mobility_levels = ["immobile", "limited", "limited", "moderate"]
    mobility = random.choice(mobility_levels)

    post_op_day = random.randint(1, 7)

    pid = patient_id or generate_patient_id()

    patient = PatientProfile(
        patient_id=pid,
        name=name,
        age=age,
        height_cm=height,
        weight_kg=weight,
        room=random.choice(ROOMS),
        surgery_type=surgery_type,
        post_op_day=post_op_day,
        is_diabetic=is_diabetic,
        has_cardiovascular_risk=has_cardio,
        mobility_level=mobility,
        assigned_nurse=random.choice(NURSES),
        assigned_doctor=random.choice(DOCTORS),
        surgical_history=random.sample(SURGICAL_HISTORY_POOL, k=random.randint(0, 2)),
        lab_results=random.sample(LAB_TEMPLATES, k=random.randint(2, 4)),
        medications=random.sample(MEDICATIONS_POOL, k=random.randint(3, 6)),
        allergies=[random.choice(ALLERGIES_POOL)],
    )

    return patient


def generate_patient_pool(n: int = 6) -> list:
    """
    Generate a diverse pool of patients for testing.
    Ensures at least 1 elderly, 1 diabetic, 1 cardio-risk patient.
    """
    patients = []
    used_ids = set()

    # Ensure diversity
    patients.append(generate_patient(force_elderly=True))
    used_ids.add(patients[-1].patient_id)

    patients.append(generate_patient(force_diabetic=True))
    while patients[-1].patient_id in used_ids:
        patients[-1] = generate_patient(force_diabetic=True)
    used_ids.add(patients[-1].patient_id)

    patients.append(generate_patient(force_cardio_risk=True))
    while patients[-1].patient_id in used_ids:
        patients[-1] = generate_patient(force_cardio_risk=True)
    used_ids.add(patients[-1].patient_id)

    # Fill remaining
    for _ in range(n - 3):
        p = generate_patient()
        while p.patient_id in used_ids:
            p = generate_patient()
        used_ids.add(p.patient_id)
        patients.append(p)

    return patients


if __name__ == "__main__":
    # Quick test: generate and print a pool
    pool = generate_patient_pool(6)
    for p in pool:
        print(f"{p.patient_id} | {p.name:22s} | Age {p.age} | "
              f"BMI {p.bmi} | {p.surgery_type} | "
              f"Elderly={p.is_elderly} Diabetic={p.is_diabetic} "
              f"Cardio={p.has_cardiovascular_risk}")