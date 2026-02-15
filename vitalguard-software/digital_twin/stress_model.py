"""
Stress Model
==============
Computes physiological stress level from heart rate and HRV data.
Used by the digital twin to drive visual stress indicators
(body glow color, breathing rate, etc.)
"""

from collections import deque


class StressModel:
    """
    Computes a stress index (0-1) from cardiovascular parameters.

    Stress indicators:
    - Low HRV → high stress (autonomic nervous system under strain)
    - High HR → high stress (sympathetic activation)
    - HR variability trend → stress trajectory
    """

    def __init__(self, window_size: int = 30):
        self.hr_history = deque(maxlen=window_size)
        self.hrv_history = deque(maxlen=window_size)

    def update(self, heart_rate: float, hrv: float) -> dict:
        """
        Update stress model with new readings.

        Args:
            heart_rate: Current HR in bpm
            hrv: Current HRV in ms

        Returns:
            dict with stress_index (0-1), components, visual parameters
        """
        self.hr_history.append(heart_rate)
        self.hrv_history.append(hrv)

        # HRV component: lower HRV = higher stress
        # Normal HRV ~40-60ms, stressed <25ms
        hrv_stress = max(0, min(1, (50 - hrv) / 40))

        # HR component: higher HR = higher stress
        # Normal 60-80, stressed >95
        hr_stress = max(0, min(1, (heart_rate - 75) / 35))

        # Combined (HRV is more reliable indicator)
        stress_index = hrv_stress * 0.65 + hr_stress * 0.35

        # Trend: is stress increasing?
        trend = "stable"
        if len(self.hrv_history) >= 10:
            recent_hrv = list(self.hrv_history)[-10:]
            older_hrv = list(self.hrv_history)[-20:-10] if len(self.hrv_history) >= 20 else recent_hrv
            if sum(recent_hrv) / len(recent_hrv) < sum(older_hrv) / len(older_hrv) - 2:
                trend = "increasing"
            elif sum(recent_hrv) / len(recent_hrv) > sum(older_hrv) / len(older_hrv) + 2:
                trend = "decreasing"

        # Visual parameters for 3D rendering
        # Breathing rate correlates with stress
        breathing_rate = 0.8 + stress_index * 1.2  # 0.8-2.0 Hz
        # Body glow: green → yellow → red
        if stress_index < 0.3:
            glow_color = [0.2, 0.8, 0.4]  # Green
        elif stress_index < 0.6:
            glow_color = [0.9, 0.8, 0.2]  # Yellow
        else:
            glow_color = [0.9, 0.2, 0.2]  # Red
        glow_intensity = 0.1 + stress_index * 0.4

        return {
            "stress_index": round(stress_index, 4),
            "components": {
                "hrv_stress": round(hrv_stress, 4),
                "hr_stress": round(hr_stress, 4),
            },
            "trend": trend,
            "visual": {
                "breathing_rate_hz": round(breathing_rate, 2),
                "glow_color": [round(c, 3) for c in glow_color],
                "glow_intensity": round(glow_intensity, 3),
            },
        }