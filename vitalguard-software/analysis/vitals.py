"""
Vital Signs Trend Analysis
============================
Analyzes heart rate, temperature, SpO2, HRV, and respiratory rate
to detect trends, anomalies, and threshold breaches.
Maintains a rolling window for trend detection.
"""

from collections import deque
from config.settings import VITALS


class VitalSignsAnalyzer:
    """
    Tracks and analyzes vital signs over time.
    Maintains a rolling window of recent readings for trend detection.
    """

    def __init__(self, window_size: int = 60):
        """
        Args:
            window_size: Number of recent readings to keep for trend analysis
        """
        self.window_size = window_size
        self.history = {
            "heart_rate": deque(maxlen=window_size),
            "body_temp": deque(maxlen=window_size),
            "spo2": deque(maxlen=window_size),
            "hrv": deque(maxlen=window_size),
            "resp_rate": deque(maxlen=window_size),
        }

    def add_reading(self, vitals: dict):
        """
        Add a new vitals snapshot to the history.

        Args:
            vitals: dict with heart_rate, body_temp, spo2, hrv, resp_rate
        """
        for key in self.history:
            if key in vitals:
                self.history[key].append(vitals[key])

    def classify_value(self, param: str, value: float) -> dict:
        """
        Classify a single vital sign value against thresholds.

        Args:
            param: Parameter name (e.g. 'heart_rate')
            value: Current value

        Returns:
            dict with level ('normal', 'caution', 'critical'), detail string
        """
        cfg = VITALS.get(param, {})
        unit = cfg.get("unit", "")

        # Check critical thresholds
        if "critical_max" in cfg and value > cfg["critical_max"]:
            return {"level": "critical", "detail": f"{value}{unit} exceeds critical max {cfg['critical_max']}{unit}"}
        if "critical_min" in cfg and value < cfg["critical_min"]:
            return {"level": "critical", "detail": f"{value}{unit} below critical min {cfg['critical_min']}{unit}"}

        # Check caution thresholds
        if "caution_max" in cfg and value > cfg["caution_max"]:
            return {"level": "caution", "detail": f"{value}{unit} above caution threshold {cfg['caution_max']}{unit}"}
        if "caution_min" in cfg and value < cfg["caution_min"]:
            return {"level": "caution", "detail": f"{value}{unit} below caution threshold {cfg['caution_min']}{unit}"}

        # Check normal range
        normal_min = cfg.get("normal_min", float("-inf"))
        normal_max = cfg.get("normal_max", float("inf"))
        if value < normal_min or value > normal_max:
            return {"level": "caution", "detail": f"{value}{unit} outside normal range ({normal_min}-{normal_max}{unit})"}

        return {"level": "normal", "detail": f"{value}{unit} within normal range"}

    def detect_trend(self, param: str, lookback: int = 20) -> dict:
        """
        Detect trend direction using simple linear regression over recent readings.

        Args:
            param: Parameter name
            lookback: Number of recent readings to analyze

        Returns:
            dict with direction ('rising', 'falling', 'stable'), slope, magnitude
        """
        data = list(self.history.get(param, []))
        if len(data) < max(5, lookback // 2):
            return {"direction": "insufficient_data", "slope": 0.0, "magnitude": 0.0}

        recent = data[-lookback:]
        n = len(recent)

        # Simple linear regression
        x_mean = (n - 1) / 2
        y_mean = sum(recent) / n
        numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(recent))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        slope = numerator / denominator if denominator > 0 else 0.0

        # Classify trend
        # Threshold depends on the parameter's normal range
        cfg = VITALS.get(param, {})
        normal_range = cfg.get("normal_max", 100) - cfg.get("normal_min", 0)
        threshold = normal_range * 0.005  # 0.5% of normal range per reading

        if slope > threshold:
            direction = "rising"
        elif slope < -threshold:
            direction = "falling"
        else:
            direction = "stable"

        # Magnitude: how much change over the lookback period
        magnitude = abs(recent[-1] - recent[0]) if len(recent) > 1 else 0.0

        return {
            "direction": direction,
            "slope": round(slope, 6),
            "magnitude": round(magnitude, 2),
            "readings_analyzed": n,
        }

    def analyze_all(self, current_vitals: dict) -> dict:
        """
        Perform complete vital signs analysis.

        Args:
            current_vitals: Current reading with all vital parameters

        Returns:
            Comprehensive analysis dict per parameter + overall assessment
        """
        self.add_reading(current_vitals)

        results = {}
        worst_level = "normal"
        level_priority = {"normal": 0, "caution": 1, "critical": 2}

        param_map = {
            "heart_rate": "heart_rate",
            "body_temp": "temperature",
            "spo2": "spo2",
            "hrv": "hrv",
            "resp_rate": "respiratory_rate",
        }

        for key, config_key in param_map.items():
            value = current_vitals.get(key)
            if value is None:
                continue

            classification = self.classify_value(config_key, value)
            trend = self.detect_trend(key)

            results[key] = {
                "value": value,
                "classification": classification,
                "trend": trend,
            }

            # Track worst level
            if level_priority.get(classification["level"], 0) > level_priority.get(worst_level, 0):
                worst_level = classification["level"]

        # Flag dangerous combinations
        alerts = []
        hr_cls = results.get("heart_rate", {}).get("classification", {}).get("level", "normal")
        temp_cls = results.get("body_temp", {}).get("classification", {}).get("level", "normal")
        spo2_cls = results.get("spo2", {}).get("classification", {}).get("level", "normal")

        if hr_cls == "critical" and spo2_cls in ("caution", "critical"):
            alerts.append("Tachycardia with hypoxemia — possible hemodynamic instability")
        if temp_cls in ("caution", "critical") and hr_cls in ("caution", "critical"):
            alerts.append("Fever with tachycardia — possible infection/sepsis")
        if spo2_cls == "critical":
            alerts.append("Critical hypoxemia — immediate O2 supplementation needed")

        # Trend-based warnings
        hr_trend = results.get("heart_rate", {}).get("trend", {}).get("direction", "stable")
        spo2_trend = results.get("spo2", {}).get("trend", {}).get("direction", "stable")
        if hr_trend == "rising" and spo2_trend == "falling":
            alerts.append("HR rising while SpO2 falling — deterioration pattern detected")

        return {
            "parameters": results,
            "overall_level": worst_level,
            "alerts": alerts,
            "readings_in_window": len(self.history["heart_rate"]),
        }