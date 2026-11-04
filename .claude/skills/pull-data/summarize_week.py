"""Recompute derived fields of data/weeks/*.json from the file's own activities and daily data.

Usage: python3 -I summarize_week.py data/weeks/2026-W44.json [...]
"""
import json
import sys


def pace(distance_m, duration_s):
    if not distance_m:
        return None
    s = duration_s / (distance_m / 1000)
    return f"{int(s // 60)}:{int(round(s % 60)):02d}"


def avg(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 1) if xs else None


def summarize(path):
    with open(path) as f:
        week = json.load(f)

    acts = week.get("activities", [])
    daily = week.get("daily", [])
    full_days = [d for d in daily if not d.get("partial")]
    runs = [a for a in acts if a["type"] == "running"]

    for a in runs:
        a["avg_pace_min_km"] = pace(a["distance_m"], a["duration_s"])

    week["days_covered"] = len(daily)
    week["complete"] = week["end"] < week["synced"]

    prev = week.get("summary", {})
    week["summary"] = {
        "activities": len(acts),
        "runs": len(runs),
        "run_distance_km": round(sum(a["distance_m"] for a in runs) / 1000, 2),
        "run_duration_min": round(sum(a["duration_s"] for a in runs) / 60, 1),
        "activity_training_load": round(sum(a["training_load"] for a in acts), 1),
        "intensity_minutes": prev.get("intensity_minutes"),
        "avg_sleep_score": avg([d["sleep"]["score"] for d in daily]),
        "avg_sleep_hours": avg([d["sleep"]["hours"] for d in daily]),
        "avg_resting_hr": avg([d.get("resting_hr") for d in daily]),
        "avg_overnight_hrv_ms": avg([d["hrv"]["overnight_avg_ms"] for d in daily]),
        "avg_steps": round(sum(d["activity"]["steps"] for d in full_days) / len(full_days)) if full_days else None,
        "end_of_week_load": daily[-1]["load"] if daily else None,
    }

    with open(path, "w") as f:
        json.dump(week, f, indent=2, ensure_ascii=False)
        f.write("\n")
    s = week["summary"]
    print(f'{week["week"]}: complete={week["complete"]} days={week["days_covered"]} '
          f'activities={s["activities"]} load={s["activity_training_load"]} hrv={s["avg_overnight_hrv_ms"]}')


if __name__ == "__main__":
    for p in sys.argv[1:]:
        summarize(p)
