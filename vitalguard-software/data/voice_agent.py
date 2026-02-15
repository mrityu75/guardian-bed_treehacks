"""
Voice Summary Agent
====================
Reads accumulated voice transcripts and generates clinical summaries
using Groq LLM. Summaries are used in the patient detail panel report.

Usage:
    from data.voice_agent import VoiceSummaryAgent
    agent = VoiceSummaryAgent()
    summary = agent.summarize(voice_entries)
"""

import os
import json
import time

try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False


class VoiceSummaryAgent:
    """Summarizes patient voice transcripts into clinical notes."""

    def __init__(self):
        self.client = None
        if HAS_GROQ:
            api_key = os.environ.get("GROQ_API_KEY", "")
            if api_key:
                self.client = Groq(api_key=api_key)
        self.cache = {}
        self.last_summary = ""

    def summarize(self, voice_entries: list, patient_name: str = "the patient") -> str:
        """
        Summarize voice transcript entries into a clinical note.

        Args:
            voice_entries: List of {"text": "...", "time": "1.2m"} dicts
            patient_name: Patient name for the summary

        Returns:
            Clinical summary string
        """
        if not voice_entries:
            return "No voice data recorded during this session."

        # Build transcript
        transcript = "\n".join(
            f"[{e.get('time', '?')}] {e['text']}"
            for e in voice_entries if e.get("text")
        )

        if not transcript.strip():
            return "No voice data recorded during this session."

        # Cache key to avoid re-summarizing same content
        cache_key = hash(transcript)
        if cache_key in self.cache:
            return self.cache[cache_key]

        if self.client:
            summary = self._groq_summarize(transcript, patient_name)
        else:
            summary = self._local_summarize(voice_entries, patient_name)

        self.cache[cache_key] = summary
        self.last_summary = summary
        return summary

    def _groq_summarize(self, transcript: str, patient_name: str) -> str:
        """Use Groq LLM for clinical summary."""
        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a clinical note assistant. Summarize patient voice transcripts "
                            "into a brief clinical observation note (2-4 sentences). Focus on: "
                            "pain complaints, emotional state, requests, and any concerning statements. "
                            "Use clinical language. Do NOT invent symptoms not mentioned."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Patient: {patient_name}\n\nTranscript:\n{transcript}\n\nClinical summary:",
                    },
                ],
                max_tokens=200,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return self._local_summarize_from_text(transcript, patient_name)

    def _local_summarize(self, entries: list, patient_name: str) -> str:
        """Fallback: rule-based summary without LLM."""
        texts = [e["text"].lower() for e in entries if e.get("text")]
        if not texts:
            return "No voice data recorded."

        pain_keywords = ["pain", "hurt", "hurting", "ache", "uncomfortable", "pressure", "unbearable"]
        distress_keywords = ["help", "can't breathe", "dizzy", "fall", "wrong", "doctor", "chest"]
        request_keywords = ["water", "medication", "reposition", "nurse", "bathroom"]

        pain_mentions = sum(1 for t in texts if any(k in t for k in pain_keywords))
        distress_mentions = sum(1 for t in texts if any(k in t for k in distress_keywords))
        request_mentions = sum(1 for t in texts if any(k in t for k in request_keywords))

        parts = [f"Patient {patient_name} voice monitoring ({len(texts)} entries recorded)."]

        if distress_mentions > 0:
            parts.append(f"Patient expressed distress in {distress_mentions} instance(s) — requires immediate attention.")
        if pain_mentions > 0:
            parts.append(f"Pain complaints noted in {pain_mentions} instance(s) — review analgesic protocol.")
        if request_mentions > 0:
            parts.append(f"Patient made {request_mentions} care request(s).")
        if pain_mentions == 0 and distress_mentions == 0:
            parts.append("No significant pain or distress indicators detected in voice recordings.")

        return " ".join(parts)

    def _local_summarize_from_text(self, transcript: str, patient_name: str) -> str:
        """Fallback from transcript string."""
        entries = [{"text": line.split("] ", 1)[-1]} for line in transcript.split("\n") if "] " in line]
        return self._local_summarize(entries, patient_name)