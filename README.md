# 🏴‍☠️ MCMT Sprint Retro Board

An interactive pirate-themed sprint retrospective board with real-time sync (Firebase), Jira integration, and auto-save to Obsidian.

## Quick Start

```bash
cd jira-dashboard
python3 -m http.server 8787
```

Open: http://localhost:8787  
Live: https://alexandreganz.github.io/mcmt-retro/

## New Sprint Setup

When a new sprint starts, run from Copilot CLI:

```
"Set up the retro board for Sprint 47"
```

Copilot will:
1. Fetch active sprint data from Jira (issues, epics, dates, goal)
2. Generate a `sprint_data.json` file
3. Run `python3 setup_sprint.py sprint_data.json`
4. This patches `index.html` and `obsidian_bridge.py` with fresh data
5. Commit + push → GitHub Pages auto-deploys

Each sprint gets:
- Its own Firebase path (`retros/sprint-47/`)
- Its own Obsidian note (`MCMT Sprint 47 Retro.md`)

## Obsidian Bridge

The bridge daemon watches Firebase and auto-saves to Obsidian when the retro ends:

```bash
nohup python3 obsidian_bridge.py &
```

Start it before the retro session.

## Features

- **5 retro columns**: Sweet Fruits, Discuss with Claire, Hidden Gold, Pirates on the Shore, Message in a Bottle
- **Real-time sync**: Firebase Realtime DB — multiple crew members at once
- **Online crew**: See who's on the ship
- **Story linking**: Link notes to Jira user stories, grouped by epic
- **Vote on notes**: 👍 to surface important topics
- **End the Voyage**: Save retro → auto-push to Obsidian → board locks read-only
- **Sprint lifecycle**: `setup_sprint.py` configures everything for a new sprint

## File Structure

```
jira-dashboard/
  index.html           ← Retro board (single-file app)
  obsidian_bridge.py   ← Firebase → Obsidian daemon
  setup_sprint.py      ← New sprint setup script
  dashboard.html       ← Old KPI dashboard (archived)
  README.md            ← This file
```
