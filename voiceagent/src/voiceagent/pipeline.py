from __future__ import annotations
from .meds import extract_med_events, apply_next_eligible
import json
from pathlib import Path
from typing import List

from dotenv import load_dotenv

from .schemas import Utterance, ChunkAnalysis
from .segment import segment_utterances
from .roles import infer_roles_rule_based
from .priority import score_chunk
from .summarize import summarize_chunk


def load_transcript(path: str) -> List[Utterance]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Utterance(**u) for u in data["utterances"]]


def run(path: str) -> List[ChunkAnalysis]:
    # loads voiceagent/.env if present
    load_dotenv()

    utterances = load_transcript(path)
    chunks = segment_utterances(utterances, max_turns=8)

    results: List[ChunkAnalysis] = []
    for ch in chunks:
        roles = infer_roles_rule_based(ch)
        pr, score, reasons, cr, flags = score_chunk(ch, roles)
        # ✅ NEW: extract medication events
        med_events = extract_med_events(ch)
        apply_next_eligible(med_events)
        summary = summarize_chunk(ch, pr)

        results.append(
            ChunkAnalysis(
                chunk_id=ch.chunk_id,
                roles=roles,
                clinical_relevance=cr,
                safety_flags=flags,
                priority=pr,
                score=score,
                reasons=reasons,
                summary=summary,
                med_events=med_events,
            )
        )

    order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    results.sort(key=lambda r: (order[r.priority], -r.score))
    return results