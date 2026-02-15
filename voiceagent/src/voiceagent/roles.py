from __future__ import annotations

from typing import Dict, List
from .schemas import Chunk, RoleTag

# Simple cue lists (you’ll refine over time)
NURSE_CUES = [
    "i'm your nurse", "i am your nurse", "rn", "nurse",
    "pain scale", "vitals", "call light", "iv", "discharge",
    "meds", "medications", "bp", "spo2", "oxygen"
]

DOCTOR_CUES = [
    "i'm dr", "i am dr", "i'm doctor", "i am doctor", "physician",
    "surgeon", "rounds", "orders", "assessment", "plan",
    "procedure", "post-op", "post op"
]

VISITOR_CUES = [
    "bestie", "friend", "girlfriend", "boyfriend",
    "mom", "dad", "sister", "brother", "visitor"
]

PATIENT_SYMPTOM_CUES = [
    "i feel", "my pain", "hurts", "nausea", "nauseous",
    "dizzy", "lightheaded", "vomit", "throw up",
    "shortness of breath", "can't breathe", "can’t breathe",
    "chest pain", "incision", "wound"
]


def infer_roles_rule_based(chunk: Chunk) -> List[RoleTag]:
    """
    Infer role per speaker using only the text in the chunk.
    This is intentionally simple and deterministic.
    """
    speaker_text: Dict[str, str] = {}
    for u in chunk.utterances:
        speaker_text.setdefault(u.speaker, "")
        speaker_text[u.speaker] += " " + u.text.lower()

    tags: List[RoleTag] = []
    for spk, txt in speaker_text.items():
        role = "UNKNOWN"
        conf = 0.55

        if any(cue in txt for cue in DOCTOR_CUES):
            role, conf = "DOCTOR", 0.85
        elif any(cue in txt for cue in NURSE_CUES):
            role, conf = "NURSE", 0.85
        elif any(cue in txt for cue in VISITOR_CUES):
            role, conf = "VISITOR", 0.75
        else:
            # default guess: patient if symptom language appears
            if any(cue in txt for cue in PATIENT_SYMPTOM_CUES):
                role, conf = "PATIENT", 0.70

        tags.append(RoleTag(speaker=spk, role=role, confidence=conf))

    return tags