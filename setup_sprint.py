#!/usr/bin/env python3
"""
Sprint Retro Setup Script
Run before each retro to generate a fresh board with live Jira data.

Usage:
    python3 setup_sprint.py

What it does:
    1. Asks for sprint number (or auto-detects active sprint)
    2. Fetches issues + epics from Jira via the MCP (you run this from Copilot CLI)
    3. Patches index.html with fresh data
    4. Updates obsidian_bridge.py with the new note path
    5. Clears Firebase for the new sprint

Prerequisites:
    - Jira MCP connection (run from Copilot CLI context)
    - Firebase in test mode
"""
import json
import os
import re
import sys
import urllib.request

FIREBASE_URL = "https://mcmt-retro-default-rtdb.europe-west1.firebasedatabase.app"
DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(DIR, "index.html")
BRIDGE_PATH = os.path.join(DIR, "obsidian_bridge.py")
TEMPLATE_PATH = os.path.join(DIR, "index_template.html")


def update_html(sprint_num, sprint_id, sprint_name, sprint_goal, start_date, end_date, issues_json, epics_json):
    """Patch index.html with new sprint data."""
    with open(INDEX_PATH, "r") as f:
        content = f.read()

    # Update SPRINT constant
    old_sprint = re.search(r"const SPRINT = \{[^}]+\};", content).group(0)
    new_sprint = (
        f'const SPRINT = {{\n'
        f'  id: {sprint_id}, name: "{sprint_name}", project: "MCMT",\n'
        f'  goal: "{sprint_goal}",\n'
        f'  start: "{start_date}", end: "{end_date}",\n'
        f'  jira: "https://legogroup.atlassian.net/browse/"\n'
        f'}};'
    )
    content = content.replace(old_sprint, new_sprint)

    # Update RETRO_PATH
    content = re.sub(
        r"const RETRO_PATH = '[^']+';",
        f"const RETRO_PATH = 'retros/sprint-{sprint_num}';",
        content,
    )

    # Update ISSUES
    content = re.sub(
        r"const ISSUES = \[.*?\];",
        f"const ISSUES = {issues_json};",
        content,
        flags=re.DOTALL,
    )

    # Update EPICS
    content = re.sub(
        r"const EPICS = \{.*?\};",
        f"const EPICS = {epics_json};",
        content,
        count=1,
        flags=re.DOTALL,
    )

    # Update localStorage key
    content = re.sub(
        r"const NAME_KEY = '[^']+';",
        f"const NAME_KEY = 'mcmt-retro-pirate-name';",
        content,
    )

    # Update page title
    content = re.sub(
        r"<title>[^<]+</title>",
        f"<title>🏴‍☠️ MCMT Sprint Retro — Sprint {sprint_num}</title>",
        content,
    )

    # Update sprint bar text
    content = re.sub(
        r"🎯 <strong>[^<]+</strong>",
        f"🎯 <strong>{sprint_goal}</strong>",
        content,
        count=1,
    )

    # Update sprint dates display
    content = re.sub(
        r"\d+ \w+ – \d+ \w+ \d{4}",
        f"{_format_date(start_date)} – {_format_date(end_date)}",
        content,
    )

    # Update welcome screen sprint info
    content = re.sub(
        r"🗺️ <strong>Sprint \d+</strong>",
        f"🗺️ <strong>Sprint {sprint_num}</strong>",
        content,
    )
    content = re.sub(
        r"Captain's Orders: <strong>[^<]+</strong>",
        f"Captain's Orders: <strong>{sprint_goal}</strong>",
        content,
    )

    # Update footer
    content = re.sub(
        r"Sprint \d+ · Powered",
        f"Sprint {sprint_num} · Powered",
        content,
    )

    # Update sprint tag
    content = re.sub(
        r">Sprint \d+</span>",
        f">Sprint {sprint_num}</span>",
        content,
    )

    # Update KPI bar defaults
    total = len(json.loads(issues_json))
    content = re.sub(
        r'To Do: <strong id="bar-todo">\d+</strong>',
        f'To Do: <strong id="bar-todo">{total}</strong>',
        content,
    )

    with open(INDEX_PATH, "w") as f:
        f.write(content)

    print(f"  ✅ index.html updated for Sprint {sprint_num}")


def update_bridge(sprint_num):
    """Patch obsidian_bridge.py with new sprint path."""
    with open(BRIDGE_PATH, "r") as f:
        content = f.read()

    content = re.sub(
        r'RETRO_PATH = "[^"]+"',
        f'RETRO_PATH = "retros/sprint-{sprint_num}"',
        content,
    )
    content = re.sub(
        r'NOTE_PATH = "[^"]+"',
        f'NOTE_PATH = "30_Projects/MCMT Sprint {sprint_num} Retro.md"',
        content,
    )

    with open(BRIDGE_PATH, "w") as f:
        f.write(content)

    print(f"  ✅ obsidian_bridge.py updated → MCMT Sprint {sprint_num} Retro.md")


def clear_firebase(sprint_num):
    """Ensure the new sprint Firebase path is clean."""
    url = f"{FIREBASE_URL}/retros/sprint-{sprint_num}.json"
    try:
        req = urllib.request.Request(url, method="DELETE")
        urllib.request.urlopen(req, timeout=10)
        print(f"  ✅ Firebase retros/sprint-{sprint_num} cleared")
    except Exception as e:
        print(f"  ⚠️  Could not clear Firebase: {e}")


def _format_date(iso_date):
    """Convert 2026-05-07 to '07 May 2026'."""
    from datetime import datetime
    d = datetime.strptime(iso_date, "%Y-%m-%d")
    return d.strftime("%d %b %Y")


def main():
    print("🏴‍☠️ Sprint Retro Setup")
    print("=" * 40)
    print()
    print("This script updates the retro board for a new sprint.")
    print("It needs Jira data — run it from Copilot CLI so it can")
    print("fetch issues via the Jira MCP connection.")
    print()
    print("Provide a JSON file with sprint data:")
    print('  { "sprint_num": 47, "sprint_id": 12345,')
    print('    "sprint_name": "Sprint 47", "sprint_goal": "...",')
    print('    "start_date": "2026-05-07", "end_date": "2026-05-21",')
    print('    "issues": [...], "epics": {...} }')
    print()

    if len(sys.argv) < 2:
        print("Usage: python3 setup_sprint.py <sprint_data.json>")
        print()
        print("Generate the JSON by telling Copilot CLI:")
        print('  "set up sprint retro for sprint 47"')
        sys.exit(1)

    data_file = sys.argv[1]
    with open(data_file) as f:
        data = json.load(f)

    sprint_num = data["sprint_num"]
    sprint_id = data["sprint_id"]
    sprint_name = data.get("sprint_name", f"Sprint {sprint_num}")
    sprint_goal = data.get("sprint_goal", "")
    start_date = data["start_date"]
    end_date = data["end_date"]
    issues = data["issues"]
    epics = data["epics"]

    print(f"\n🗺️  Setting up Sprint {sprint_num}")
    print(f"    Goal: {sprint_goal}")
    print(f"    Period: {start_date} → {end_date}")
    print(f"    Issues: {len(issues)}")
    print(f"    Epics: {len(epics)}")
    print()

    update_html(
        sprint_num, sprint_id, sprint_name, sprint_goal,
        start_date, end_date,
        json.dumps(issues), json.dumps(epics),
    )
    update_bridge(sprint_num)
    clear_firebase(sprint_num)

    print()
    print(f"✅ All done! Sprint {sprint_num} retro is ready.")
    print()
    print("Next steps:")
    print("  1. Commit & push:  git add -A && git commit -m 'Sprint {0} retro' && git push".format(sprint_num))
    print("  2. Start bridge:   nohup python3 obsidian_bridge.py &")
    print("  3. Share the URL:  https://alexandreganz.github.io/mcmt-retro/")


if __name__ == "__main__":
    main()
