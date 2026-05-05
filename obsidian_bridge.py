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
RETRO_PATH = "retros/sprint-46"
POLL_INTERVAL = 5  # seconds

VAULT_PATH = os.path.expanduser(
    "~/Library/CloudStorage/OneDrive-LEGO/LEGO-vault/LEGO"
)
NOTE_PATH = "30_Projects/MCMT Sprint 46 Retro.md"

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
    """Convert export payload to Obsidian-ready markdown."""
    sprint = data.get("sprint", {})
    notes = data.get("notes", {})
    epics = data.get("epics", {})
    issues = data.get("issues", [])
    today = datetime.date.today().isoformat()

    all_notes = []
    for col in COLS:
        for n in (notes.get(col) or []):
            if n:
                all_notes.append({**n, "col": col})

    authors = sorted(set(n.get("author", "?") for n in all_notes))

    md = "---\n"
    md += "tags: [retro, sprint-46, mcmt]\n"
    md += f"date: {today}\n"
    md += 'sprint: "Sprint 46"\n'
    md += f'sprint_goal: "{sprint.get("goal", "")}"\n'
    md += "status: completed\n"
    md += f'crew: [{", ".join(authors)}]\n'
    md += "---\n\n"

    md += f"# 🏴\u200d☠️ Sprint 46 Retro — {sprint.get('name', 'Sprint 46')}\n\n"
    md += f"> **Sprint Goal:** {sprint.get('goal', '')}\n"
    md += f"> **Period:** {sprint.get('start', '')} to {sprint.get('end', '')}\n"
    md += f"> **Crew:** {', '.join(authors)}\n\n---\n\n"

    for col in COLS:
        col_notes = [n for n in all_notes if n["col"] == col]
        md += f"## {COL_LABELS[col]}\n\n"
        if not col_notes:
            md += "_No notes_\n\n"
        else:
            for n in col_notes:
                link = f' → [[{n["linkedKey"]}]]' if n.get("linkedKey") else ""
                votes = f' 👍×{n["votes"]}' if n.get("votes", 0) > 0 else ""
                md += f'- {n["text"]} _({n.get("author","?")})_{link}{votes}\n'
            md += "\n"

    actions = [n for n in all_notes if n["col"] == "bottle"]
    if actions:
        md += "---\n\n## ⚓ Action Items\n\n"
        for n in actions:
            link = f' → [[{n["linkedKey"]}]]' if n.get("linkedKey") else ""
            md += f'- [ ] {n["text"]}{link} _({n.get("author","?")})_\n'
        md += "\n"

    linked = [n for n in all_notes if n.get("linkedKey")]
    if linked:
        md += "---\n\n## 🔗 Linked User Stories\n\n"
        by_epic = {}
        for n in linked:
            issue = next((i for i in issues if i["key"] == n["linkedKey"]), None)
            ek = (issue.get("epicKey") or "__none__") if issue else "__none__"
            if ek not in by_epic:
                by_epic[ek] = set()
            by_epic[ek].add(n["linkedKey"])

        for ek, keys in by_epic.items():
            epic_name = epics.get(ek, "No Epic")
            md += f"### 🎯 {epic_name}\n\n"
            for key in keys:
                issue = next((i for i in issues if i["key"] == key), None)
                story_notes = [n for n in linked if n.get("linkedKey") == key]
                status = issue["status"] if issue else "?"
                summary = issue["summary"] if issue else key
                md += f"- **{key}** — {summary} `{status}`\n"
                for sn in story_notes:
                    md += f'  - {COL_EMOJI[sn["col"]]} {sn["text"]} _({sn.get("author","?")})_\n'
            md += "\n"

    return md


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
