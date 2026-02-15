from __future__ import annotations

from typing import List
from .schemas import Utterance, Chunk

def segment_utterances(utterances: List[Utterance], max_turns: int = 8) -> List[Chunk]:
    chunks: List[Chunk] = []
    buf: List[Utterance] = []
    cid = 0

    SOCIAL_BREAK_CUES = ["bestie", "gossip", "dude", "bro", "tiktok", "instagram"]
    CLINICAL_BREAK_CUES = ["nurse", "doctor", "pain", "nausea", "shortness of breath", "med", "discharge"]

    def flush() -> None:
        nonlocal cid, buf
        if not buf:
            return
        chunks.append(
            Chunk(
                chunk_id=f"c{cid:04d}",
                start_t=buf[0].t,
                end_t=buf[-1].t,
                utterances=buf,
            )
        )
        cid += 1
        buf = []

    for u in utterances:
        txt = u.text.lower()

        # If we already have clinical content and we hit obvious social talk, split
        if buf:
            buf_text = " ".join(x.text.lower() for x in buf)
            already_clinical = any(c in buf_text for c in CLINICAL_BREAK_CUES)
            entering_social = any(c in txt for c in SOCIAL_BREAK_CUES)
            if already_clinical and entering_social:
                flush()

        buf.append(u)

        if len(buf) >= max_turns:
            flush()

    flush()
    return chunks