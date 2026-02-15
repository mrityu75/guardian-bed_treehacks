"""
Sound Pattern Analysis
=======================
Analyzes microphone data to detect:
- Distress vocalizations (pain, moaning)
- Abnormal ambient noise levels
- Silence patterns (may indicate unresponsiveness)
"""

from collections import deque


# ADC thresholds (mapped from dB estimates)
AMBIENT_NORMAL_MAX = 1800     # ~45 dB
VOCALIZATION_THRESHOLD = 2400  # ~60 dB
DISTRESS_THRESHOLD = 2800      # ~70 dB
SILENCE_THRESHOLD = 600        # ~15 dB (unusually quiet)


class SoundAnalyzer:
    """Analyzes microphone data over time to detect sound patterns."""

    def __init__(self, window_size: int = 30):
        """
        Args:
            window_size: Number of recent readings to keep
        """
        self.window_size = window_size
        self.history = deque(maxlen=window_size)
        self.vocalization_count = 0
        self.distress_count = 0

    def analyze(self, mic_values: list) -> dict:
        """
        Analyze a single frame of microphone data.

        Args:
            mic_values: List of 3 microphone ADC values

        Returns:
            dict with average_level, classification, alerts
        """
        if not mic_values or len(mic_values) < 1:
            return {"average_level": 0, "classification": "no_data", "alerts": []}

        avg = sum(mic_values) / len(mic_values)
        peak = max(mic_values)
        self.history.append(avg)

        alerts = []

        # Classify current sound
        if peak >= DISTRESS_THRESHOLD:
            classification = "distress"
            self.distress_count += 1
            self.vocalization_count += 1
            alerts.append(f"Distress vocalization detected (peak ADC: {peak})")
        elif peak >= VOCALIZATION_THRESHOLD:
            classification = "vocalization"
            self.vocalization_count += 1
        elif avg < SILENCE_THRESHOLD:
            classification = "silence"
        elif avg > AMBIENT_NORMAL_MAX:
            classification = "elevated_ambient"
        else:
            classification = "normal"

        # Pattern detection over window
        if len(self.history) >= 10:
            recent = list(self.history)[-10:]
            avg_recent = sum(recent) / len(recent)

            # Sustained silence might indicate unresponsiveness
            if all(v < SILENCE_THRESHOLD for v in recent):
                alerts.append("Sustained silence detected — verify patient responsiveness")

        return {
            "average_level": round(avg, 1),
            "peak_level": peak,
            "classification": classification,
            "vocalization_count": self.vocalization_count,
            "distress_count": self.distress_count,
            "alerts": alerts,
        }