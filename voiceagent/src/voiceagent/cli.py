from __future__ import annotations

import argparse
import json
from typing import Any, Optional

from .pipeline import run


def _fmt_time(sec: Optional[float]) -> str:
    if sec is None:
        return "?"
    m = int(sec // 60)
    s = sec - m * 60
    return f"{m:02d}:{s:04.1f}"


def _print_med_events(med_events: list[dict[str, Any]]) -> None:
    if not med_events:
        return

    print("Medication events:")
    for e in med_events:
        t = _fmt_time(e.get("t"))
        nxt = _fmt_time(e.get("next_eligible_t"))
        med = e.get("med_name", "unknown")
        evtype = e.get("event_type", "UNKNOWN")
        dose = e.get("dose")
        route = e.get("route", "UNKNOWN")
        interval = e.get("interval_minutes")

        dose_str = f" {dose}" if dose else ""
        route_str = f" ({route})" if route and route != "UNKNOWN" else ""
        interval_str = f", interval={interval}m" if interval is not None else ""

        print(f"- t={t}: {evtype} {med}{dose_str}{route_str}{interval_str}; next eligible ~ {nxt}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to transcript JSON")
    parser.add_argument("--out", default="", help="Optional output JSON path")
    args = parser.parse_args()

    results = run(args.input)
    payload = [r.model_dump() for r in results]

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    # Print top chunks
    for r in payload[:6]:
        print("=" * 60)
        print(r["chunk_id"], r["priority"], "score=", r["score"])
        print("reasons:", "; ".join(r["reasons"]))
        print(r["summary"])

        # ✅ NEW: print meds timeline if present
        _print_med_events(r.get("med_events", []))


if __name__ == "__main__":
    main()