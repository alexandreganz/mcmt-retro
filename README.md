# 🏴‍☠️ MCMT Sprint Retro Board

An interactive pirate-themed sprint retrospective board connected to Jira.

## Run locally

```bash
cd jira-dashboard
python3 -m http.server 8787
```

Then open: http://localhost:8787

## Features

- **5 retro columns**: Sweet Fruits, Discuss with Claire, Hidden Gold, Pirates on the Shore, Message in a Bottle
- **Interactive notes**: Team adds sticky notes in-browser, stored in localStorage
- **Sprint data from Jira**: Live issue list, KPIs, and backlog reference
- **Export notes**: Download retro notes as JSON for post-retro review
- **Vote on notes**: 👍 to surface important topics
- **Action items → Jira**: Post-retro, ask Copilot to create Jira stories from exported action items

## Refresh sprint data

To regenerate with the latest Jira sprint data, ask Copilot:
> "Regenerate the retro board with fresh sprint data"

## Post-retro: create Jira stories from action items

1. Export notes (📥 button)
2. Ask Copilot: "Create Jira stories from Message in a Bottle items in this export"

## File structure

```
jira-dashboard/
  index.html       ← Retro board (interactive, pirate-themed)
  dashboard.html   ← Old KPI dashboard (archived)
  README.md        ← This file
```
