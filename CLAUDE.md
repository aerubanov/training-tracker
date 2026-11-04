# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status

The repo has no code, build system, test suite, or lint config yet, so there are no commands to document. Update this file as those are added. The Garmin MCP server is configured in `.mcp.json` (server at `~/.local/share/garmin_mcp`, destructive tools disabled via `GARMIN_DISABLED_TOOLS`). History files live in `data/` (see below), first synced for 2026-W43 to W45.

## Purpose

A personal training tracker driven by Garmin data. Three intended capabilities:

1. **Ingest**: pull data from the user's Garmin device through an MCP integration and save it as a series of training-history files. This runs on request for a given period, usually one week.
2. **Plan**: suggest a training plan for a requested period, based on the historical files.
3. **Track progress**: high-level progress tracking over longer periods or toward a goal (for example, ski season preparation).

## Architecture notes

Garmin access goes through an MCP server, not direct API calls from project code. Sync is therefore done by Claude calling MCP tools in-session and writing the results to files. Which Garmin MCP server to use, and how it is configured (for example in `.mcp.json`), has not been decided yet.

The stored history files are the shared source of truth. Planning and long-term progress tracking should read from them rather than re-fetching from Garmin.

## Data layout

`data/` is gitignored (personal health data); it exists only on this machine.

- `data/weeks/<ISO year>-W<nn>.json`: one file per ISO week (Monday to Sunday). Re-syncing a week overwrites its file, so there are no duplicate rows.
- `data/profile.json`: slow-changing athlete settings (max HR, HR zones, lactate threshold, weight), with an `as_of` date.

Each week file has:
- `week`, `start`, `end`, `days_covered`, `complete` (false while the week is in progress), `synced` (date of the pull).
- `summary`: run distance and duration, activity training load, intensity minutes, sleep/RHR/HRV/steps averages, and the end-of-week load state. Computed from the sections below.
- `activities[]`: one per Garmin activity (id, name, type, start_time, distance_m, duration_s, avg/max HR, aerobic and anaerobic training effect, `te_label`, `training_load`, `hr_zone_s` as seconds in zones 1 to 5, `avg_pace_min_km` for runs). `start_time` is as returned by Garmin's activity list and is about 4 h later than the local times in body battery events, so treat it as GMT unless verified.
- `daily[]`: one per day (sleep, resting HR, HRV, body battery, steps and calories, Garmin acute/chronic load and ACWR). Sleep is keyed by the wake-up date. A day with `partial: true` was pulled before the day ended.
- `snapshot` (optional, only in the week of the pull): point-in-time values with no history endpoint (training readiness, load focus, race predictions, endurance score, VO2max).

Sync procedure: run `/pull-data <period>` (for example `/pull-data last week`; skill in `.claude/skills/pull-data/`). It does the following: for the requested period, call the Garmin MCP tools in-session (`get_activities_by_date`, `get_training_effect` and `get_activity_hr_in_timezones` per activity, `get_sleep_summary_range`, `get_hrv_trend`, `get_body_battery`, `get_stats_range`, `get_training_load_trend`, `get_weekly_intensity_minutes`, plus the snapshot tools), then write one file per ISO week. Re-sync the current week once it ends so `complete` becomes true.

Known quirks: Garmin load and intensity-minute figures use Garmin's own scales; weekly stress and endurance breakdowns use Thursday-start weeks and are stored in `snapshot` rather than per ISO week; `get_weigh_ins` returned nothing for the first period, so weight is only in `profile.json`.
