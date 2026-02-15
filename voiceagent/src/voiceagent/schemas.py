from __future__ import annotations
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

Role = Literal["DOCTOR", "NURSE", "PATIENT", "VISITOR", "UNKNOWN"]
Priority = Literal["P0", "P1", "P2", "P3"]


class Utterance(BaseModel):
    t: Optional[float] = None
    speaker: str
    text: str


class Chunk(BaseModel):
    chunk_id: str
    start_t: Optional[float] = None
    end_t: Optional[float] = None
    utterances: List[Utterance]


class RoleTag(BaseModel):
    speaker: str
    role: Role
    confidence: float = Field(ge=0.0, le=1.0)


class ChunkAnalysis(BaseModel):
    chunk_id: str
    roles: List[RoleTag]
    clinical_relevance: int = Field(ge=0, le=5)
    safety_flags: List[str] = []
    priority: Priority
    score: int
    reasons: List[str]
    summary: str
    med_events: List[MedicationEvent] = []


Route = Literal["PO", "IV", "IM", "SC", "TOPICAL", "UNKNOWN"]
EventType = Literal["ADMINISTERED", "OFFERED", "ORDERED", "REQUESTED", "DECLINED", "UNKNOWN"]

class MedicationEvent(BaseModel):
    t: Optional[float] = None            # timestamp seconds (from transcript)
    speaker: str                         # e.g., S1
    event_type: EventType
    med_name: str                        # normalized if possible
    dose: Optional[str] = None           # e.g., "5 mg"
    route: Route = "UNKNOWN"
    raw_text: str                        # original utterance text
    next_eligible_t: Optional[float] = None  # computed
    interval_minutes: Optional[int] = None   # what rule used
    confidence: float = Field(ge=0.0, le=1.0, default=0.6)