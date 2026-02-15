"""
Repositioning Timer & Compliance
==================================
Tracks time since last position change and generates alerts
when repositioning is overdue. Maintains compliance history.
"""

import time
from config.settings import REPOSITIONING_INTERVAL_MIN, REPOSITIONING_WARNING_MIN


class RepositioningTracker:
    """Tracks repositioning events and compliance for a single patient."""

    def __init__(self, interval_min: int = None):
        """
        Args:
            interval_min: Custom reposition interval (uses global default if None)
        """
        self.interval_min = interval_min or REPOSITIONING_INTERVAL_MIN
        self.warning_min = min(self.interval_min - 15, REPOSITIONING_WARNING_MIN)
        self.current_posture = "unknown"
        self.posture_start_min = 0.0  # elapsed minutes when posture started
        self.history = []  # list of {posture, start_min, end_min, duration_min}
        self.total_repositions = 0
        self.overdue_count = 0

    def update(self, posture: str, elapsed_min: float) -> dict:
        """
        Update tracker with current posture and elapsed time.

        Args:
            posture: Current classified posture
            elapsed_min: Total elapsed minutes since monitoring started

        Returns:
            dict with status, duration, time_remaining, alerts
        """
        alerts = []

        # Detect posture change
        if posture != self.current_posture and posture != "unknown":
            if self.current_posture != "unknown":
                # Log completed posture period
                duration = elapsed_min - self.posture_start_min
                self.history.append({
                    "posture": self.current_posture,
                    "start_min": round(self.posture_start_min, 1),
                    "end_min": round(elapsed_min, 1),
                    "duration_min": round(duration, 1),
                    "was_overdue": duration > self.interval_min,
                })
                self.total_repositions += 1
                if duration > self.interval_min:
                    self.overdue_count += 1

            self.current_posture = posture
            self.posture_start_min = elapsed_min

        # Compute current duration in position
        duration_min = elapsed_min - self.posture_start_min
        remaining_min = self.interval_min - duration_min

        # Status classification
        if remaining_min <= 0:
            status = "overdue"
            alerts.append(f"OVERDUE: Patient in {self.current_posture} for "
                         f"{duration_min:.0f} min (limit: {self.interval_min} min)")
        elif remaining_min <= (self.interval_min - self.warning_min):
            status = "warning"
            alerts.append(f"Reposition recommended in {remaining_min:.0f} min")
        else:
            status = "ok"

        return {
            "current_posture": self.current_posture,
            "duration_min": round(duration_min, 1),
            "remaining_min": round(max(0, remaining_min), 1),
            "interval_min": self.interval_min,
            "status": status,
            "alerts": alerts,
            "total_repositions": self.total_repositions,
        }

    def get_compliance(self) -> dict:
        """
        Compute repositioning compliance statistics.

        Returns:
            dict with compliance_rate, total events, overdue events
        """
        total = len(self.history)
        if total == 0:
            return {
                "compliance_rate": 1.0,
                "total_events": 0,
                "on_time": 0,
                "overdue": 0,
            }

        on_time = sum(1 for h in self.history if not h["was_overdue"])
        return {
            "compliance_rate": round(on_time / total, 4),
            "total_events": total,
            "on_time": on_time,
            "overdue": self.overdue_count,
            "avg_duration_min": round(
                sum(h["duration_min"] for h in self.history) / total, 1
            ),
        }