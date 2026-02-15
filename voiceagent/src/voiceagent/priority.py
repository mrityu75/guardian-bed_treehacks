from __future__ import annotations

from typing import List, Tuple
from .schemas import Chunk, RoleTag, Priority

# ---------
# URGENCY TRIGGERS
# ---------
# P0 = truly urgent / emergent
P0_TRIGGERS = [
    "can't breathe", "can’t breathe",
    "shortness of breath", "difficulty breathing",
    "chest pain", "pressure in chest",
    "passed out", "unresponsive",
    "won't stop bleeding", "won’t stop bleeding",
    "heavy bleeding",
    "throat swelling", "swelling of lips",
]

# P1 = clinically important but not always emergent
P1_TRIGGERS = [
    "fell", "fall",
    "worst pain", "severe pain",
    "confused", "not making sense", "new confusion",
]

# General clinical cues
CLINICAL_CUES = [
    "pain", "pain scale",
    "nausea", "vomit", "nauseous",
    "dizzy", "lightheaded",
    "incision", "wound", "bandage", "drain",
    "blood pressure", "bp", "heart rate", "hr",
    "oxygen", "spo2", "temperature", "fever",
    "med", "meds", "medication", "dose", "iv",
    "pt", "physical therapy", "walk", "ambulate",
    "discharge", "instructions", "follow-up", "follow up",
    "lab", "labs", "scan", "x-ray", "ct", "mri",
]

# Negation cues
NEGATION_CUES = [
    "no", "not",
    "denies", "deny", "denied",
    "without",
    "negative for",
    "doesn't", "doesnt",
    "didn't", "didnt",
]


def _is_negated(text: str, phrase: str, window: int = 40) -> bool:
    idx = text.find(phrase)
    if idx == -1:
        return False
    left = text[max(0, idx - window): idx]
    return any(cue in left for cue in NEGATION_CUES)


def _match_triggers_in_non_questions(chunk: Chunk, triggers: List[str]) -> List[str]:
    hits: List[str] = []
    for tr in triggers:
        for u in chunk.utterances:
            txt = u.text.lower()
            if tr in txt:
                if "?" in txt:
                    continue  # ignore screening questions
                if _is_negated(txt, tr):
                    continue
                hits.append(tr)
                break
    return hits


def _role_pair_score(roles: List[RoleTag]) -> Tuple[int, List[str]]:
    rs = [r.role for r in roles]
    reasons: List[str] = []
    s = 0

    def has(a: str, b: str) -> bool:
        return (a in rs) and (b in rs)

    if has("DOCTOR", "NURSE"):
        s += 3
        reasons.append("Role pair doctor↔nurse")
    if has("NURSE", "PATIENT"):
        s += 3
        reasons.append("Role pair nurse↔patient")
    if has("DOCTOR", "PATIENT"):
        s += 3
        reasons.append("Role pair doctor↔patient")
    if has("PATIENT", "VISITOR"):
        s -= 1
        reasons.append("Role pair patient↔visitor (likely social)")

    return s, reasons


def _clinical_relevance_and_flags(chunk: Chunk) -> Tuple[int, List[str], List[str], List[str]]:
    full_text = " ".join(u.text.lower() for u in chunk.utterances)

    flags_p0 = _match_triggers_in_non_questions(chunk, P0_TRIGGERS)
    flags_p1 = _match_triggers_in_non_questions(chunk, P1_TRIGGERS)

    hits = sum(1 for c in CLINICAL_CUES if c in full_text)

    if hits == 0:
        clinical_relevance = 0
    elif hits <= 2:
        clinical_relevance = 2
    elif hits <= 5:
        clinical_relevance = 3
    elif hits <= 8:
        clinical_relevance = 4
    else:
        clinical_relevance = 5

    reasons: List[str] = []
    if hits > 0:
        reasons.append(f"Clinical cues present ({hits} hits)")
    if flags_p0:
        reasons.append(f"P0 triggers: {', '.join(flags_p0)}")
    if flags_p1:
        reasons.append(f"P1 triggers: {', '.join(flags_p1)}")

    return clinical_relevance, reasons, flags_p0, flags_p1


def _to_priority(score: int, flags_p0: List[str], flags_p1: List[str], clinical_relevance: int) -> Priority:
    if flags_p0:
        return "P0"
    if flags_p1:
        return "P1"

    # 🔥 Clinical floor: any real symptom should not be P3
    if clinical_relevance >= 2 and score < 3:
        return "P2"

    if score >= 9:
        return "P0"
    if score >= 6:
        return "P1"
    if score >= 3:
        return "P2"
    return "P3"


def score_chunk(chunk: Chunk, roles: List[RoleTag]) -> Tuple[Priority, int, List[str], int, List[str]]:
    rp_score, rp_reasons = _role_pair_score(roles)
    clinical_rel, clinical_reasons, flags_p0, flags_p1 = _clinical_relevance_and_flags(chunk)

    total = rp_score + clinical_rel
    reasons = rp_reasons + clinical_reasons
    priority = _to_priority(total, flags_p0, flags_p1, clinical_rel)

    safety_flags = flags_p0 + flags_p1
    return priority, total, reasons, clinical_rel, safety_flags