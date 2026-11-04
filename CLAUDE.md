# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status

The repo is at the very start: it contains only a `README.md` with the project title. There is no code, build system, test suite, or lint config yet, so there are no commands to document. Update this file as those are added.

## Purpose

A personal training tracker driven by Garmin data. Three intended capabilities:

1. **Ingest**: pull data from the user's Garmin device through an MCP integration and save it as a series of training-history files. This runs on request for a given period, usually one week.
2. **Plan**: suggest a training plan for a requested period, based on the historical files.
3. **Track progress**: high-level progress tracking over longer periods or toward a goal (for example, ski season preparation).

## Architecture notes

Garmin access goes through an MCP server, not direct API calls from project code. Sync is therefore done by Claude calling MCP tools in-session and writing the results to files. Which Garmin MCP server to use, and how it is configured (for example in `.mcp.json`), has not been decided yet.

The stored history files are the shared source of truth. Planning and long-term progress tracking should read from them rather than re-fetching from Garmin. When the file layout, naming scheme, and format are chosen, document them here, since all three capabilities depend on them.
