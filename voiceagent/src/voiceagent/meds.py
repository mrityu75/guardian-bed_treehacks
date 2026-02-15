from __future__ import annotations
import re
from typing import Dict, List, Optional, Tuple
from .schemas import Chunk, MedicationEvent

# A starter lexicon. Expand as you go.
MED_ALIASES: Dict[str, str] = {
    "dilaudid": "hydromorphone",
    "hydromorphone": "hydromorphone",
    "morphine": "morphine",
    "oxycodone": "oxycodone",
    "hydrocodone": "hydrocodone",
    "tylenol": "acetaminophen",
    "acetaminophen": "acetaminophen",
    "advil": "ibuprofen",
    "ibuprofen": "ibuprofen",
    "toradol": "ketorolac",
    "ketorolac": "ketorolac",
    "gabapentin": "gabapentin",
}

# Default interval rules (minutes). Make these configurable later.
DEFAULT_INTERVAL_MIN: Dict[str, int] = {
    "oxycodone": 360,        # 4–6h -> choose conservative 6h by default, or set 240
    "hydrocodone": 360,
    "morphine": 240,         # 2–4h -> choose 4h
    "hydromorphone": 360,    # 3–6h -> choose 6h
    "acetaminophen": 360,    # 4–6h -> choose 6h
    "ibuprofen": 480,        # 6–8h -> choose 8h
    "ketorolac": 360,        # 6h
    "gabapentin": 720,       # 8–12h -> choose 12h
}

ADMIN_PATTERNS = [
    r"\b(i'?m|i am)\s+(giving|administering|pushing)\b",
    r"\b(i'?ll|i will)\s+give\b",
    r"\bhere('?s| is)\s+(some|your)\b",
    r"\bwe('?re| are)\s+going to give\b",
]

ROUTE_HINTS = [
    (r"\biv\b|\bintravenous\b|\bthrough your iv\b", "IV"),
    (r"\bpo\b|\bby mouth\b|\boral\b|\bpill\b|\btablet\b", "PO"),
    (r"\binjection\b|\bshot\b", "IM"),
]

DOSE_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s?(mg|mcg|g|ml)\b", re.IGNORECASE)


def _normalize_med(text: str) -> Optional[str]:
    t = text.lower()
    for alias, canonical in MED_ALIASES.items():
        if re.search(rf"\b{re.escape(alias)}\b", t):
            return canonical
    return None


def _infer_route(text: str) -> str:
    t = text.lower()
    for pat, route in ROUTE_HINTS:
        if re.search(pat, t):
            return route
    return "UNKNOWN"


def _infer_event_type(text: str) -> str:
    t = text.lower()
    if any(re.search(p, t) for p in ADMIN_PATTERNS):
        # "I'll give you" is often OFFERED/ADMINISTERED; we’ll call it OFFERED unless "now"/"just gave"
        if "now" in t or "just" in t or "i gave" in t or "i'm giving" in t or "administering" in t or "pushing" in t:
            return "ADMINISTERED"
        return "OFFERED"
    return "UNKNOWN"


def extract_med_events(chunk: Chunk) -> List[MedicationEvent]:
    events: List[MedicationEvent] = []
    for u in chunk.utterances:
        med = _normalize_med(u.text)
        if not med:
            continue

        event_type = _infer_event_type(u.text)
        if event_type == "UNKNOWN":
            # still log it, but lower confidence, because med mention may be casual
            conf = 0.4
        else:
            conf = 0.75

        dose_m = DOSE_RE.search(u.text)
        dose = f"{dose_m.group(1)} {dose_m.group(2)}" if dose_m else None

        route = _infer_route(u.text)

        events.append(
            MedicationEvent(
                t=u.t,
                speaker=u.speaker,
                event_type=event_type,
                med_name=med,
                dose=dose,
                route=route,
                raw_text=u.text,
                confidence=conf,
            )
        )
    return events


def apply_next_eligible(events: List[MedicationEvent], interval_min: Dict[str, int] = DEFAULT_INTERVAL_MIN) -> None:
    for e in events:
        mins = interval_min.get(e.med_name)
        if e.t is not None and mins is not None:
            e.interval_minutes = mins
            e.next_eligible_t = e.t + mins * 60