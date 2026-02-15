from __future__ import annotations

import os
from groq import Groq
from .schemas import Chunk, Priority


def _fallback_summary(chunk: Chunk, priority: Priority) -> str:
    """Deterministic fallback if GROQ_API_KEY is missing."""
    text = " ".join(u.text for u in chunk.utterances)
    if len(text) > 220:
        text = text[:220] + "..."
    return f"(LLM disabled) Priority {priority}. Snippet: {text}"


def _build_prompt(chunk: Chunk, priority: Priority) -> str:
    """Build prompt without triple-quoted f-strings."""
    transcript = "\n".join(f"{u.speaker}: {u.text}" for u in chunk.utterances)
    style = "CLINICAL HANDOFF" if priority in ("P0", "P1") else "BRIEF NOTE"

    lines = [
        "You are an assistant for post-op hospital room monitoring.",
        "",
        "Goal:",
        "- Summarize medically relevant information first.",
        '- If the chunk is mostly social, explicitly say: "No clinically relevant info."',
        "",
        "Output format (STRICT):",
        f"Style: {style}",
        "Summary:",
        "- (2 to 6 bullets)",
        "Action items:",
        '- (bullets) OR "None"',
        "Safety concerns:",
        '- (bullets) OR "None"',
        "",
        "Chunk transcript:",
        transcript,
    ]
    return "\n".join(lines)


def summarize_chunk(chunk: Chunk, priority: Priority) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    if not api_key:
        return _fallback_summary(chunk, priority)

    client = Groq(api_key=api_key)
    prompt = _build_prompt(chunk, priority)

    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()