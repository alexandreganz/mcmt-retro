# MCMT Sprint Retro Board — Project Context

## What this project is

A **pirate-themed sprint retrospective board** for the MCMT (Marketing Communications Management Team) at the LEGO Group. It runs as a single-page web app with real-time Firebase sync, local AI clustering via Ollama, and automatic export to Obsidian for knowledge management.

**Owner:** Alexandre Goubin (dkAleGan)  
**Live URL:** https://alexandreganz.github.io/mcmt-retro/  
**Local URL:** http://localhost:8787  
**Repo:** https://github.com/alexandreganz/mcmt-retro

---

## Architecture

```
┌──────────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   index.html         │────▶│  Firebase RTDB    │◀────│  obsidian_bridge │
│   (browser app)      │     │  (sync layer)     │     │  (Python daemon) │
│                      │     └──────────────────┘     └────────┬─────────┘
│   GitHub Pages /     │                                       │
│   localhost:8787     │     ┌──────────────────┐     ┌────────▼─────────┐
│                      │────▶│  Ollama (local)   │     │  Obsidian vault  │
└──────────────────────┘     │  localhost:11434  │     │  (Markdown/RAG)  │
                             └──────────────────┘     └──────────────────┘
```

### What runs where

| Component | Runs on | Notes |
|-----------|---------|-------|
| `index.html` | Any browser (GitHub Pages or localhost) | Single-file app, no build step |
| Firebase RTDB | Cloud (europe-west1) | Real-time sync for all users |
| Ollama AI | **Alexandre's machine only** | localhost:11434, model: `llama3.1:8b` |
| `obsidian_bridge.py` | **Alexandre's machine only** | Polls Firebase, writes to Obsidian vault |
| `setup_sprint.py` | **Alexandre's machine only** | Patches code for new sprints |

### Key constraint

AI clustering and Obsidian export only work from Alexandre's machine. Other crew members can use the retro board, vote, and drag-drop clusters — but cannot trigger clustering or export.

---

## File structure

```
jira-dashboard/
  index.html             ← Main app (HTML + CSS + JS, single file, ~65KB)
  obsidian_bridge.py     ← Firebase → Obsidian daemon (stdlib only, Python 3.9+)
  setup_sprint.py        ← Sprint lifecycle setup script
  dashboard.html         ← Legacy KPI dashboard (archived, not used)
  index_v1.html          ← Legacy v1 board (archived)
  README.md              ← User-facing docs
  CLAUDE.md              ← This file (AI context for future iterations)
  .github/workflows/     ← GitHub Pages deployment
```

---

## index.html — Single-file app anatomy

The app is one HTML file with embedded CSS and JS. No framework, no build step, no npm.

### CSS sections (top of file)

| Section | What it styles |
|---------|---------------|
| `:root` variables | Theme colors (parchment/gold/pirate palette) |
| `.board` grid | 5-column retro board layout |
| `.retro-col`, `.note` | Board columns and sticky notes |
| `.story-picker` | Custom dropdown for Jira story linking |
| `.plan-*` | Plan the Voyage view (tabs, note cards, clusters) |
| `.pn-*` | Plan note cards, votes, drag-and-drop states |
| `.modal-*` | End Voyage modal overlay |
| `.presence-*` | Online crew presence indicator |

### JS sections (in `<script>` tag)

| Section | Key functions | Purpose |
|---------|---------------|---------|
| **Data constants** | `SPRINT`, `ISSUES`, `EPICS`, `COLS` | Sprint config + Jira data (patched by setup_sprint.py) |
| **Story picker** | `buildPickerHTML()`, `togglePicker()`, `selectPickerItem()` | Custom searchable dropdown for linking notes to Jira stories |
| **Firebase data** | `load()`, `getNotes()`, `addNoteData()`, `voteNote()` | CRUD operations on Firebase notes |
| **Presence** | `setupPresence()` | Online crew tracking via Firebase |
| **Board rendering** | `renderBoard()`, `renderNotes()`, `openForm()`, `submitNote()` | Main retro board view |
| **Plan view** | `renderPlan()`, `renderNoteCard()`, `switchPlanTab()` | Plan the Voyage analysis view |
| **Drag & drop** | `setupClusterDragDrop()` | Manual cluster correction via drag-and-drop |
| **AI clustering** | `clusterNotes()`, `clusterAllNotes()`, `clearAllClusters()` | Ollama-based thematic grouping |
| **Cluster sync** | `listenClusters()` | Firebase listener for cluster changes |
| **View switching** | `switchView()` | Toggle between retro board and plan view |
| **End voyage** | `showEndVoyage()`, `lockBoard()`, `saveToObsidian()` | Export flow + board locking |

### Important variables

| Variable | Purpose |
|----------|---------|
| `_cache` | Local note cache (mirrors Firebase) |
| `_clusterCache` | AI cluster results per column |
| `_planTab` | Active tab in Plan view (default: 'fruits') |
| `_locked` | Board lock state (true after End Voyage) |
| `OLLAMA_URL` | `http://localhost:11434` |
| `OLLAMA_MODEL` | `llama3.1:8b` (was gemma4:26b, too slow) |
| `RETRO_PATH` | Firebase path, e.g. `retros/sprint-46` |

---

## obsidian_bridge.py — Firebase → Obsidian daemon

### How it works

1. Polls Firebase every 5 seconds for new export data at `/{RETRO_PATH}/export`
2. When `exportedAt` timestamp changes, calls `build_markdown(data)` to generate RAG-optimized markdown
3. Writes to Obsidian vault at `~/Library/CloudStorage/OneDrive-LEGO/LEGO-vault/LEGO/30_Projects/`
4. Writes confirmation back to Firebase so the UI shows success

### RAG-optimized markdown structure

The output is designed for future retrieval-augmented generation:

```
---
type: retro                          ← Document type for filtering
project: MCMT                       ← Project identifier
sprint: 46                          ← Sprint number
ai_themes: ["Theme 1", "Theme 2"]   ← AI cluster labels (searchable)
ai_model: "llama3.1:8b"             ← Model used for clustering
crew: [Alex, Olga, ...]             ← Participants
epics_referenced: [...]             ← Jira epic links (graph linking)
stories_referenced: [...]           ← Jira story links
tags: [retro, sprint-46, mcmt]      ← Obsidian tags
---

## Retro Notes by Category           ← Each note has inline 🏷️ theme tag
## AI-Generated Themes               ← Dedicated cluster section with notes grouped
## Action Items                       ← Checkbox tasks for next sprint
## Story Impact Map                   ← Traceability: stories → retro notes
## Sprint Health Summary              ← Quantitative health metrics
```

### Key design decisions for RAG

- **Inline theme tags per note** (`🏷️ Theme Name`) — a RAG chunk retrieves a single note and still knows its theme
- **Self-contained sections** — each H2 is a semantic chunk that stands alone
- **Rich frontmatter** — enables filtering by type, sprint, themes, model, crew
- **Dataview-compatible** — works with Obsidian Dataview queries
- **Story sentiment** — auto-derived from which retro column a story's notes appear in

### Running the bridge

```bash
# Start before retro session
nohup python3 obsidian_bridge.py &

# Check if running
ps aux | grep obsidian_bridge

# Must restart after code changes (it runs the old version otherwise!)
kill <PID> && nohup python3 obsidian_bridge.py &
```

---

## setup_sprint.py — Sprint lifecycle

Patches `index.html` and `obsidian_bridge.py` for a new sprint.

### Usage (from Copilot CLI)

Tell Copilot: _"Set up the retro board for Sprint 47"_

Copilot will:
1. Fetch active sprint data from Jira (MCMT board)
2. Generate `sprint_data.json` with issues, epics, dates, goal
3. Run `python3 setup_sprint.py sprint_data.json`
4. Script patches `SPRINT` constant, `ISSUES`, `EPICS` in index.html
5. Script patches `RETRO_PATH` and `NOTE_PATH` in obsidian_bridge.py
6. Commit + push → GitHub Pages auto-deploys

### What gets patched

| File | Constants patched |
|------|-------------------|
| `index.html` | `SPRINT`, `ISSUES`, `EPICS`, `<title>` tag |
| `obsidian_bridge.py` | `RETRO_PATH`, `NOTE_PATH` |

---

## AI clustering

### How it works

1. User clicks "🧠 Auto-Group All" in Plan the Voyage view
2. For each column with ≥2 notes, sends notes to Ollama (`POST /api/chat`)
3. Prompt asks LLM to group notes into 2-4 thematic clusters
4. Response parsed as JSON: `{clusters: [{name, noteIndexes}]}`
5. Clusters saved to Firebase at `/{RETRO_PATH}/clusters/{colId}`
6. All users see clusters in real-time via Firebase listener
7. Users can drag-and-drop notes between clusters to correct groupings
8. Drag-drop changes sync back to Firebase automatically

### Model performance (M4 Pro 32GB)

| Model | Size | Time per bucket | Verdict |
|-------|------|-----------------|---------|
| gemma4:26b | 17GB | 2+ minutes | ❌ Too slow |
| llama3.1:8b | 4.9GB | ~7 seconds | ✅ Current choice |
| qwen2.5:14b | 9GB | Untested | — |

### Cluster data shape in Firebase

```json
{
  "retros/sprint-46/clusters/fruits": {
    "clusters": [
      { "name": "Alex's Appreciation", "noteIds": ["abc123", "def456"] },
      { "name": "Process Wins", "noteIds": ["ghi789"] }
    ],
    "createdBy": "Alex",
    "createdAt": "2026-05-05T14:30:00Z",
    "model": "llama3.1:8b"
  }
}
```

---

## Firebase structure

```
mcmt-retro-default-rtdb.europe-west1.firebasedatabase.app/
  retros/
    sprint-46/
      notes/
        fruits/    ← Array of {id, text, author, votes, voters, linkedKey, ts}
        claire/
        gold/
        pirates/
        bottle/
      clusters/
        fruits/    ← {clusters: [{name, noteIds}], createdBy, createdAt, model}
        ...
      locked       ← boolean
      presence/    ← {userId: {name, lastSeen}}
      export/      ← Full payload written by saveToObsidian()
        obsidianSaved/  ← Confirmation from bridge {at, path}
```

---

## Retro flow (how a session works)

1. **Before session:** Alexandre starts `obsidian_bridge.py` and verifies Ollama is running
2. **During session:** Team opens the board, sets their pirate name, adds/votes on notes, links to Jira stories
3. **Discussion phase:** Alexandre switches to "Plan the Voyage" view, clicks "Auto-Group All" to cluster notes thematically
4. **Corrections:** Team can drag-drop notes between clusters to fix AI groupings
5. **End session:** Alexandre clicks "End the Voyage" → saves to Obsidian → board locks read-only

---

## Common tasks for future iterations

### Adding a new retro column

1. Add to `COLS` array and `COL_LABELS` in index.html
2. Add to `COLS`, `COL_LABELS`, `COL_EMOJI` in obsidian_bridge.py
3. Add column description to `col_descriptions` dict in `build_markdown()`
4. Add column color/icon CSS

### Changing the AI model

1. Update `OLLAMA_MODEL` constant in index.html (~line 1639)
2. Ensure model is pulled: `ollama pull <model-name>`
3. Test: `curl http://localhost:11434/api/tags` to verify

### Changing the Obsidian vault path

1. Update `VAULT_PATH` and `NOTE_PATH` in obsidian_bridge.py
2. Restart the bridge

### Debugging export issues

1. Check Firebase export data: `curl -s "https://mcmt-retro-default-rtdb.europe-west1.firebasedatabase.app/retros/sprint-XX/export.json" | python3 -m json.tool`
2. Test markdown generation: `python3 -c "import obsidian_bridge as ob; ..."`
3. **Always restart the bridge after code changes** — it runs the old version otherwise

### Adding new metadata to Obsidian output

1. Edit `build_markdown()` in obsidian_bridge.py
2. Add to frontmatter (YAML) for RAG filtering
3. Add inline in note lists for chunk-level context
4. Add a dedicated section (H2) for comprehensive view
5. Restart the bridge

---

## Known limitations

- **No authentication** — Firebase is in test mode, anyone with the URL can write
- **No JS framework** — everything is vanilla JS in one file (~65KB), which gets unwieldy
- **Single Ollama model** — no fallback if Ollama is down; other users just can't cluster
- **Polling bridge** — obsidian_bridge polls every 5s instead of using Firebase streaming
- **Sprint data is embedded** — ISSUES/EPICS arrays are patched into index.html (no API calls at runtime)

---

## Dependencies

| Dependency | Type | Version | Purpose |
|------------|------|---------|---------|
| Firebase Realtime DB | CDN (compat) | 9.x | Real-time data sync |
| Google Fonts | CDN | — | Pirata One + Inter fonts |
| Ollama | Local service | Latest | AI clustering (llama3.1:8b) |
| Python 3.9+ | Local | stdlib only | Bridge + setup scripts |
| GitHub Pages | Hosting | — | Static site deployment |

No npm, no node_modules, no build tools. The app is intentionally zero-dependency on the frontend.
