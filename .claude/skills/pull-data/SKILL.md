---
name: pull-data
description: Pull training, recovery and load data from Garmin (via the garmin MCP) for a period such as "last week" and store it as per-ISO-week JSON files in data/weeks/. Use when the user asks to sync, pull, load or update Garmin training history.
argument-hint: "[period, e.g. last week | this week | last 3 weeks | 2026-10-19..2026-11-01]"
---

# pull-data

Sync Garmin data for the period in `$ARGUMENTS` into `data/weeks/<ISO year>-W<nn>.json`, then give a short analysis. If no period is given, ask for one.

Garmin is read only through the `garmin` MCP tools, called in-session. Never call tools that create, edit, schedule or delete anything. Planning and progress tracking read the stored files, so the files must be accurate.

## 1. Resolve the period

Use today's date from the environment. Weeks are ISO weeks, Monday to Sunday.

- "last week": the previous full ISO week.
- "this week": this week's Monday through today (partial).
- "last N weeks": the N previous full weeks. Add "and this week" only if the user says so.
- "current and two previous weeks": this week plus the two before it.
- Explicit dates: expand to whole ISO weeks, but only pull dates that exist (never future dates).

Print the resolved weeks and date range before pulling. If `data/weeks/<week>.json` already exists with `complete: true`, say so and skip it unless the user asked to refresh.

## 2. Pull

Run independent calls in parallel. Use the full resolved range as `start_date` / `end_date` unless a tool limits the range (noted below).

Activities:
- `get_activities_by_date` (paginate with `page` while `has_more`).
- For every activity: `get_training_effect` and `get_activity_hr_in_timezones`.

Daily:
- `get_sleep_summary_range`: sleep score, stages, resting HR, overnight HRV, sleep stress. Keyed by wake-up date.
- `get_hrv_trend` (max 30 days): weekly average and 5-minute high.
- `get_body_battery`: charged, drained, level.
- `get_stats_range` (max 28 days): steps, total and active calories.
- `get_training_load_trend` (max 90 days): Garmin acute load, chronic load, ACWR and status, training status.

Weekly:
- `get_weekly_intensity_minutes` with `end_date` = last date and `weeks` = number of weeks. It may return an extra earlier week. Match by `week_start` (Monday).

Snapshot (point-in-time, only when the period includes today; otherwise omit, as there is no history endpoint):
- `get_training_status`, `get_training_readiness`, `get_training_load_balance`, `get_vo2max_trend`, `get_endurance_score`, `get_race_predictions`.
- Weekly stress (`get_weekly_stress`) uses Thursday-start weeks, so store it in `snapshot`, not per ISO week.

Profile (refresh `data/profile.json` when the period includes today): `get_lactate_threshold`, `get_heart_rate_zones`, `get_weigh_ins`. If there are no weigh-ins, keep the weight from the threshold profile and say so in `weight_note`.

A failed or empty call is not a reason to invent a value: leave the field out and mention it in the report.

## 3. Store

Write one file per ISO week, overwriting any existing file for that week. `data/` is gitignored personal data: never commit it, and never put it in an artifact or share it.

```
{
  "week": "2026-W44", "start": "2026-10-26", "end": "2026-11-01",
  "days_covered": 7, "complete": true, "synced": "2026-11-04",
  "summary": { ... },              // recomputed by the script in step 4
  "activities": [ {
      "id", "name", "type", "start_time", "distance_m", "duration_s",
      "calories", "avg_hr", "max_hr", "steps", "elev_gain_m", "elev_loss_m",
      "aerobic_te", "anaerobic_te", "te_label", "training_load",
      "hr_zone_s": [z1, z2, z3, z4, z5],      // seconds in each zone
      "avg_pace_min_km"                         // runs only, added by the script
  } ],
  "daily": [ {
      "date", "partial",
      "sleep": {"score", "hours", "deep_s", "light_s", "rem_s", "awake_s", "avg_stress"},
      "resting_hr",
      "hrv": {"overnight_avg_ms", "weekly_avg_ms", "last_night_5min_high_ms", "status"},
      "body_battery": {"charged", "drained", "level"},
      "activity": {"steps", "total_kcal", "active_kcal"},
      "load": {"acute", "chronic", "acwr", "acwr_status", "training_status"}
  } ],
  "snapshot": { ... }              // optional, only for the week containing today
}
```

Rules:
- Copy values exactly as the tools return them. Do not round or estimate, except `sleep.hours` (seconds / 3600, 2 decimals) and round training load and elevations to 1 decimal.
- `complete` is true only if the week's last day is before the sync date. The sync-date day has `partial: true` (its calories and steps are incomplete).
- Keep activity names as Garmin returns them (they may not be English).
- `start_time` is as returned by the activity list. It appeared about 4 h later than the local times in body battery events, so treat it as GMT until verified.
- `summary.intensity_minutes` is `{"moderate", "vigorous", "total_weighted", "goal"}` taken from `get_weekly_intensity_minutes`. Put it in the file before running the script, which keeps it.
- If you write several week files from one set of tool results, do it carefully and verify (step 4), because values pass through your context, not a pipeline.

## 4. Verify

Run the bundled script on every written file. It adds run paces, recomputes `days_covered` and `complete`, and recomputes `summary` (run distance and duration, activity training load, sleep, resting HR, HRV and step averages, end-of-week load) from the file's own data:

```
python3 -I .claude/skills/pull-data/summarize_week.py data/weeks/<week>.json [...]
```

Then check: activity count equals what `get_activities_by_date` returned, `daily` has one entry per covered day, and spot-check two or three values per file against the tool output. Report any mismatch.

## 5. Analyze and report

Compare the pulled weeks with the two weeks before them from `data/weeks/` when available. Keep it short: a small week-by-week table and a handful of observations. Cover:

- Volume: runs, distance, duration, activity training load, intensity minutes against the 150 goal.
- Load: acute vs chronic load and ACWR. ACWR above 1.5 or a jump in acute load of more than about 50% in a few days is a spike; below 0.8 sustained is detraining.
- Intensity distribution: use `hr_zone_s` and `te_label`. Check whether runs labeled easy or "Base" are really in zone 1 to 2. Zone 4 starts at the `profile.json` zone floor. Compare with `snapshot.load_focus_28d` (aerobic low/high/anaerobic vs target).
- Recovery: overnight HRV against its weekly average (a drop of more than 10 ms from baseline is a warning), resting HR trend, sleep score and hours, body battery, training readiness.
- Fitness: VO2max, endurance score, threshold pace and HR across comparable sessions (same workout name).
- Data gaps: anything not available (weigh-ins, goals, scheduled workouts) and any partial week or day.

State facts from the files; label any inference. Do not prescribe a training plan here, that is a separate task.

Finish by listing the files written and whether each week is complete. Do not commit.
