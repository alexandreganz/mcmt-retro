#!/usr/bin/env python3
"""
Firebase → Obsidian Bridge
Watches Firebase Realtime DB for retro export data.
When the 'Save to Captain's Log' button is clicked, this daemon
picks up the data and writes it to the Obsidian vault automatically.

Usage:
    python3 obsidian_bridge.py          # run in foreground
    nohup python3 obsidian_bridge.py &  # run as background daemon
"""
import json
import os
import sys
import time
import datetime
import urllib.request

FIREBASE_URL = "https://mcmt-retro-default-rtdb.europe-west1.firebasedatabase.app"
RETRO_PATH = "retros/sprint-46"  # updated by setup_sprint.py
POLL_INTERVAL = 5  # seconds

VAULT_PATH = os.path.expanduser(
    "~/Library/CloudStorage/OneDrive-LEGO/LEGO-vault/LEGO"
)
NOTE_PATH = "30_Projects/MCMT Sprint 46 Retro.md"  # updated by setup_sprint.py

COL_LABELS = {
    "fruits": "🍎 Sweet Fruits",
    "claire": "💬 Discuss with Claire",
    "gold": "🏆 Hidden Gold",
    "pirates": "🏴\u200d☠️ Pirates on the Shore",
    "bottle": "📜 Message in a Bottle",
}
COL_EMOJI = {
    "fruits": "🍎", "claire": "💬", "gold": "🏆",
    "pirates": "🏴\u200d☠️", "bottle": "📜",
}
COLS = ["fruits", "claire", "gold", "pirates", "bottle"]

last_export_time = None


def fetch_export():
    """Read the export node from Firebase."""
    url = f"{FIREBASE_URL}/{RETRO_PATH}/export.json"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data
    except Exception as e:
        print(f"  ⚠️  Firebase read error: {e}")
        return None


def confirm_saved(timestamp):
    """Write a confirmation back to Firebase so the UI can show success."""
    url = f"{FIREBASE_URL}/{RETRO_PATH}/export/obsidianSaved.json"
    payload = json.dumps({"at": timestamp, "path": NOTE_PATH}).encode()
    try:
        req = urllib.request.Request(url, data=payload, method="PUT")
        req.add_header("Content-Type", "application/json")
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"  ⚠️  Could not write confirmation: {e}")


def build_markdown(data):
    """Convert export payload to RAG-optimized Obsidian markdown.

    Structure designed for retrieval-augmented generation:
    - Rich frontmatter with typed metadata for filtering
    - Each section is a self-contained semantic chunk
    - Consistent heading hierarchy (H2 = category, H3 = topic, H4 = detail)
    - Inline metadata (author, votes, links) for context preservation
    - Dataview-compatible fields for Obsidian queries
    """
    sprint = data.get("sprint", {})
    notes = data.get("notes", {})
    epics = data.get("epics", {})
    issues = data.get("issues", [])
    clusters = data.get("clusters", {})
    today = datetime.date.today().isoformat()

    all_notes = []
    for col in COLS:
        for n in (notes.get(col) or []):
            if n:
                all_notes.append({**n, "col": col})

    authors = sorted(set(n.get("author", "?") for n in all_notes))
    total_votes = sum(n.get("votes", 0) for n in all_notes)
    linked_count = sum(1 for n in all_notes if n.get("linkedKey"))

    sprint_name = sprint.get("name", "Sprint")
    sprint_num = "".join(c for c in sprint_name.split()[-1] if c.isdigit()) or "?"
    sprint_tag = f"sprint-{sprint_num}"
    sprint_goal = sprint.get("goal", "")

    # ── Frontmatter (rich metadata for RAG filtering) ──
    md = "---\n"
    md += f"type: retro\n"
    md += f"project: MCMT\n"
    md += f"sprint: {sprint_num}\n"
    md += f'sprint_name: "{sprint_name}"\n'
    md += f'sprint_goal: "{sprint_goal}"\n'
    md += f'start_date: {sprint.get("start", "")}\n'
    md += f'end_date: {sprint.get("end", "")}\n'
    md += f"date: {today}\n"
    md += f"status: completed\n"
    md += f"tags:\n  - retro\n  - {sprint_tag}\n  - mcmt\n"
    md += f"crew:\n"
    for a in authors:
        md += f"  - {a}\n"
    md += f"total_notes: {len(all_notes)}\n"
    md += f"total_votes: {total_votes}\n"
    md += f"linked_notes: {linked_count}\n"
    md += f"unlinked_notes: {len(all_notes) - linked_count}\n"

    # Collect all referenced epic/story keys for graph linking
    epic_keys_used = set()
    story_keys_used = set()
    for n in all_notes:
        if n.get("linkedKey"):
            story_keys_used.add(n["linkedKey"])
            issue = next((i for i in issues if i["key"] == n["linkedKey"]), None)
            if issue and issue.get("epicKey"):
                epic_keys_used.add(issue["epicKey"])

    if epic_keys_used:
        md += "epics_referenced:\n"
        for ek in sorted(epic_keys_used):
            md += f'  - key: {ek}\n    name: "{epics.get(ek, "Unknown")}"\n'
    if story_keys_used:
        md += "stories_referenced:\n"
        for sk in sorted(story_keys_used):
            md += f"  - {sk}\n"

    # Collect AI theme names for RAG filtering
    all_theme_names = []
    for col in COLS:
        col_clusters = clusters.get(col, {}).get("clusters", [])
        for c in col_clusters:
            if c.get("name"):
                all_theme_names.append(c["name"])
    if all_theme_names:
        md += "ai_themes:\n"
        for t in all_theme_names:
            md += f'  - "{t}"\n'
        md += f'ai_model: "{clusters.get(COLS[0], {}).get("model", "unknown")}"\n'

    md += "---\n\n"

    # ── Header ──
    md += f"# {sprint_name} Retrospective\n\n"
    md += f"| Field | Value |\n"
    md += f"|-------|-------|\n"
    md += f"| **Sprint Goal** | {sprint_goal} |\n"
    md += f"| **Period** | {sprint.get('start', '')} → {sprint.get('end', '')} |\n"
    md += f"| **Crew** | {', '.join(authors)} |\n"
    md += f"| **Notes** | {len(all_notes)} total, {linked_count} linked, {total_votes} votes |\n\n"

    # ── Section 1: Retro Categories (semantic chunks per column) ──
    md += "---\n\n## Retro Notes by Category\n\n"

    col_descriptions = {
        "fruits": "Things that went well this sprint — celebrate these",
        "claire": "Topics to escalate or discuss with leadership",
        "gold": "Hidden improvements or discoveries worth noting",
        "pirates": "Risks, blockers, or threats to the team",
        "bottle": "Action items and commitments for the next sprint",
    }

    for col in COLS:
        col_notes = sorted(
            [n for n in all_notes if n["col"] == col],
            key=lambda n: n.get("votes", 0),
            reverse=True,
        )
        md += f"### {COL_LABELS[col]}\n\n"
        md += f"> {col_descriptions[col]}\n\n"

        # Build note→theme lookup for RAG (inline cluster label per note)
        note_theme = {}
        col_clusters = clusters.get(col, {}).get("clusters", [])
        for c in col_clusters:
            for nid in c.get("noteIds", []):
                note_theme[nid] = c.get("name", "")

        if not col_notes:
            md += "_No notes in this category._\n\n"
        else:
            for n in col_notes:
                votes = f" `👍 {n['votes']}`" if n.get("votes", 0) > 0 else ""
                link = ""
                if n.get("linkedKey"):
                    issue = next(
                        (i for i in issues if i["key"] == n["linkedKey"]), None
                    )
                    summary = issue["summary"] if issue else n["linkedKey"]
                    link = f" → **{n['linkedKey']}** _{summary}_"
                theme_tag = f" `🏷️ {note_theme[n['id']]}`" if n.get("id") and note_theme.get(n.get("id")) else ""
                md += f"- {n['text']}{votes}{theme_tag}{link}\n"
                md += f"  - _Author: {n.get('author', '?')}_\n"
            md += "\n"

    # ── Section 2: AI Clusters (if available) ──
    has_clusters = False
    for col in COLS:
        if clusters.get(col) and clusters[col].get("clusters"):
            has_clusters = True
            break

    if has_clusters:
        md += "---\n\n## AI-Generated Themes\n\n"
        md += "> Thematic groupings generated by local AI model during the retro session.\n\n"

        for col in COLS:
            col_clusters = clusters.get(col, {}).get("clusters", [])
            if not col_clusters:
                continue
            col_notes_map = {
                n.get("id"): n for n in all_notes if n["col"] == col
            }
            model = clusters.get(col, {}).get("model", "unknown")
            md += f"### {COL_LABELS[col]} — Themes\n\n"
            md += f"_Clustered by: {model}_\n\n"

            for cluster in col_clusters:
                c_notes = [
                    col_notes_map[nid]
                    for nid in cluster.get("noteIds", [])
                    if nid in col_notes_map
                ]
                if not c_notes:
                    continue
                c_votes = sum(n.get("votes", 0) for n in c_notes)
                md += f"#### 🏷️ {cluster['name']}"
                if c_votes > 0:
                    md += f" `{c_votes} votes`"
                md += f" ({len(c_notes)} notes)\n\n"
                for n in sorted(c_notes, key=lambda x: x.get("votes", 0), reverse=True):
                    votes = f" `👍 {n['votes']}`" if n.get("votes", 0) > 0 else ""
                    link = ""
                    if n.get("linkedKey"):
                        link = f" → **{n['linkedKey']}**"
                    md += f"- {n['text']}{votes}{link} _({n.get('author', '?')})_\n"
                md += "\n"

    # ── Section 3: Action Items (standalone chunk for task extraction) ──
    actions = sorted(
        [n for n in all_notes if n["col"] == "bottle"],
        key=lambda n: n.get("votes", 0),
        reverse=True,
    )
    if actions:
        md += "---\n\n## Action Items\n\n"
        md += "> Commitments for the next sprint. Track completion status here.\n\n"
        for n in actions:
            link = ""
            if n.get("linkedKey"):
                link = f" → **{n['linkedKey']}**"
            votes = f" `👍 {n['votes']}`" if n.get("votes", 0) > 0 else ""
            md += f"- [ ] {n['text']}{link}{votes} — _{n.get('author', '?')}_\n"
        md += "\n"

    # ── Section 4: Story Impact Map (traceability for RAG) ──
    linked = [n for n in all_notes if n.get("linkedKey")]
    if linked:
        md += "---\n\n## Story Impact Map\n\n"
        md += "> Which user stories generated retro discussion? Grouped by epic for traceability.\n\n"

        by_epic = {}
        for n in linked:
            issue = next((i for i in issues if i["key"] == n["linkedKey"]), None)
            ek = (issue.get("epicKey") or "__none__") if issue else "__none__"
            if ek not in by_epic:
                by_epic[ek] = {}
            key = n["linkedKey"]
            if key not in by_epic[ek]:
                by_epic[ek][key] = []
            by_epic[ek][key].append(n)

        for ek in sorted(by_epic.keys()):
            epic_name = epics.get(ek, "No Epic")
            stories = by_epic[ek]
            total_story_notes = sum(len(v) for v in stories.values())
            md += f"### {epic_name}\n\n"

            for key in sorted(stories.keys()):
                issue = next((i for i in issues if i["key"] == key), None)
                status = issue["status"] if issue else "?"
                summary = issue["summary"] if issue else key
                story_notes = stories[key]
                sentiment = _story_sentiment(story_notes)
                md += f"#### {key} — {summary}\n\n"
                md += f"| Status | Notes | Sentiment |\n"
                md += f"|--------|-------|-----------|\n"
                md += f"| `{status}` | {len(story_notes)} | {sentiment} |\n\n"
                for sn in story_notes:
                    md += f"- {COL_EMOJI[sn['col']]} {sn['text']} _({sn.get('author', '?')})_\n"
                md += "\n"

    # ── Section 5: Sprint Health Summary (high-level RAG chunk) ──
    md += "---\n\n## Sprint Health Summary\n\n"

    col_counts = {}
    col_votes = {}
    for col in COLS:
        col_notes = [n for n in all_notes if n["col"] == col]
        col_counts[col] = len(col_notes)
        col_votes[col] = sum(n.get("votes", 0) for n in col_notes)

    md += "| Category | Notes | Votes | Signal |\n"
    md += "|----------|-------|-------|--------|\n"
    for col in COLS:
        signal = "🟢" if col in ("fruits", "gold") else "🔴" if col in ("pirates",) else "🟡"
        md += f"| {COL_LABELS[col]} | {col_counts[col]} | {col_votes[col]} | {signal} |\n"
    md += f"| **Total** | **{len(all_notes)}** | **{total_votes}** | |\n\n"

    # Insight ratios
    positive = col_counts.get("fruits", 0) + col_counts.get("gold", 0)
    negative = col_counts.get("pirates", 0)
    if positive + negative > 0:
        ratio = positive / (positive + negative)
        mood = "🟢 Positive" if ratio > 0.6 else "🔴 Concerning" if ratio < 0.4 else "🟡 Mixed"
        md += f"> **Team mood:** {mood} ({positive} positive vs {negative} concern notes)\n\n"

    return md


def _story_sentiment(notes):
    """Derive a simple sentiment indicator from the columns of linked notes."""
    cols = [n["col"] for n in notes]
    if all(c in ("fruits", "gold") for c in cols):
        return "🟢 Positive"
    elif all(c in ("pirates",) for c in cols):
        return "🔴 Concern"
    elif "pirates" in cols:
        return "🟡 Mixed"
    else:
        return "🟢 Positive"



def save_to_obsidian(data):
    """Write the retro markdown to the Obsidian vault."""
    md = build_markdown(data)
    full_path = os.path.join(VAULT_PATH, NOTE_PATH)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(md)
    return full_path


def main():
    global last_export_time
    print("🪨  Obsidian Bridge — Firebase → Obsidian vault")
    print(f"    Watching: {FIREBASE_URL}/{RETRO_PATH}/export")
    print(f"    Writing:  {VAULT_PATH}/{NOTE_PATH}")
    print(f"    Polling every {POLL_INTERVAL}s — Ctrl+C to stop\n")

    while True:
        try:
            data = fetch_export()
            if data and isinstance(data, dict) and data.get("exportedAt"):
                export_time = data["exportedAt"]

                # Skip if already processed this export
                already_saved = data.get("obsidianSaved")
                if already_saved and already_saved.get("at") == export_time:
                    time.sleep(POLL_INTERVAL)
                    continue

                if export_time != last_export_time:
                    print(f"📥 New export detected! ({export_time})")
                    print(f"   By: {data.get('exportedBy', '?')}")
                    path = save_to_obsidian(data)
                    print(f"   ✅ Saved to: {path}")
                    confirm_saved(export_time)
                    print(f"   📡 Confirmation sent to Firebase")
                    last_export_time = export_time

        except KeyboardInterrupt:
            print("\n⚓ Bridge stopped. Fair winds, Captain!")
            sys.exit(0)
        except Exception as e:
            print(f"  ❌ Error: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
