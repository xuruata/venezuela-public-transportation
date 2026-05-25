#!/usr/bin/env python3
"""Cut a CalVer release: vYYYY.MM.DD (with .N suffix for same-day re-cuts).

Runs pre-flight checks (clean tree, in sync with origin, no export drift),
generates a stats-filled release-notes template, lets you edit it in
$EDITOR, then creates the GitHub release via `gh`. The CI workflow
(.github/workflows/build.yml) attaches every GeoJSON + GTFS export as a
release asset on the resulting `release: published` event.

Usage:
    python3 scripts/release.py                # interactive
    python3 scripts/release.py --dry-run      # show the plan, don't push
    python3 scripts/release.py --tag v2026.05.25.1
    python3 scripts/release.py --notes-file path/to/notes.md
    python3 scripts/release.py --no-edit      # use generated notes verbatim
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def sh(cmd, *, check=True, capture=True):
    r = subprocess.run(cmd, capture_output=capture, text=True)
    if check and r.returncode != 0:
        sys.stderr.write(f"$ {' '.join(cmd)}\n{r.stdout}{r.stderr}")
        sys.exit(r.returncode)
    return r


def preflight():
    r = sh(["git", "status", "--porcelain"])
    if r.stdout.strip():
        sys.exit("✗ working tree is dirty — commit or stash before cutting a release")

    sh(["git", "fetch", "origin", "main"], capture=False)
    behind = sh(["git", "rev-list", "HEAD..origin/main", "--count"]).stdout.strip()
    ahead = sh(["git", "rev-list", "origin/main..HEAD", "--count"]).stdout.strip()
    if behind != "0":
        sys.exit(f"✗ HEAD is {behind} commit(s) behind origin/main — pull first")
    if ahead != "0":
        sys.exit(f"✗ HEAD is {ahead} commit(s) ahead of origin/main — push first")

    sh(["python3", str(ROOT / "scripts" / "verify.py")], capture=False)
    sh(["python3", str(ROOT / "scripts" / "build_exports.py")], capture=False)
    drift = sh(["git", "diff", "--quiet", "--exit-code", "exports/"], check=False)
    if drift.returncode != 0:
        sys.exit("✗ exports/ would drift after rebuilding — regenerate and push first")


def next_tag():
    base = "v" + datetime.date.today().strftime("%Y.%m.%d")
    tags = set(sh(["git", "tag", "--list", base + "*"]).stdout.split())
    if base not in tags:
        return base
    n = 1
    while f"{base}.{n}" in tags:
        n += 1
    return f"{base}.{n}"


def gather_stats():
    rows, n_systems, n_stops, n_with = [], 0, 0, 0
    for sys_json in sorted(DATA.rglob("system.json")):
        sysdir = sys_json.parent
        system = json.loads(sys_json.read_text())
        stops = json.loads((sysdir / "stops.json").read_text())
        with_coords = sum(1 for s in stops if s.get("lat") is not None)
        rows.append({
            "city": system["city"],
            "name": system["name"],
            "type": system["type"],
            "stops": len(stops),
            "with_coords": with_coords,
        })
        n_systems += 1
        n_stops += len(stops)
        n_with += with_coords
    return {"n_systems": n_systems, "n_stops": n_stops,
            "n_with": n_with, "rows": rows}


def previous_tag():
    r = sh(["git", "describe", "--tags", "--abbrev=0", "--match", "v*"],
           check=False)
    return r.stdout.strip() or None


def commit_log(since_tag):
    if not since_tag:
        return ""
    r = sh(["git", "log", "--oneline", f"{since_tag}..HEAD"])
    return r.stdout.strip()


def default_notes(tag, stats, prev_tag, log):
    date_str = tag.lstrip("v").split(".")
    date_str = f"{date_str[0]}-{date_str[1]}-{date_str[2]}"
    pct = round(100 * stats["n_with"] / stats["n_stops"]) if stats["n_stops"] else 0

    out = []
    out.append(f"Snapshot of `venezuela-public-transportation` as of {date_str}.")
    out.append("")
    out.append("## Contents")
    out.append("")
    out.append(f"{stats['n_systems']} operational transit systems, "
               f"{stats['n_stops']} stops, "
               f"{stats['n_with']} with coordinates ({pct}%).")
    out.append("")
    out.append("| City | System | Type | Stops |")
    out.append("|---|---|---|---:|")
    for row in stats["rows"]:
        out.append(f"| {row['city']} | {row['name']} | {row['type']} | {row['stops']} |")
    out.append("")
    out.append("## What's changed")
    out.append("")
    if log:
        out.append(f"Since [{prev_tag}](../../releases/tag/{prev_tag}):")
        out.append("")
        out.append("```")
        out.append(log)
        out.append("```")
    else:
        out.append("_describe the meaningful changes vs the previous snapshot_")
    out.append("")
    out.append("## Assets")
    out.append("")
    out.append("Every system ships two GeoJSON files (stops + lines) and a "
               "GTFS zip, attached below. GTFS schedules are **synthetic "
               "frequencies** — route topology is real, but timetables are "
               "placeholders. See the README for the rationale.")
    out.append("")
    out.append("## Licensing")
    out.append("")
    out.append("Released under the [Open Database License (ODbL) v1.0]"
               "(https://opendatacommons.org/licenses/odbl/1-0/). Includes "
               "data derived from OpenStreetMap; redistribute with attribution.")
    return "\n".join(out) + "\n"


def edit_in_editor(initial):
    editor = os.environ.get("EDITOR", "vi")
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w+", delete=False,
                                     encoding="utf-8") as f:
        f.write(initial)
        path = f.name
    try:
        subprocess.run([editor, path])
        return Path(path).read_text()
    finally:
        os.unlink(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", help="release tag (default: today's CalVer)")
    ap.add_argument("--notes-file", help="use these notes verbatim")
    ap.add_argument("--no-edit", action="store_true",
                    help="skip the editor; use generated notes as-is")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan and exit; don't create the release")
    args = ap.parse_args()

    tag = args.tag or next_tag()
    print(f"tag:    {tag}")

    if not args.dry_run:
        preflight()

    stats = gather_stats()
    prev = previous_tag()
    log = commit_log(prev) if prev else ""

    if args.notes_file:
        notes = Path(args.notes_file).read_text()
    else:
        notes = default_notes(tag, stats, prev, log)
        if not args.no_edit and not args.dry_run:
            notes = edit_in_editor(notes)

    date_str = tag.lstrip("v").split(".")
    title = f"Snapshot {date_str[0]}-{date_str[1]}-{date_str[2]}"
    print(f"title:  {title}")

    if args.dry_run:
        print("--- notes ---")
        print(notes)
        return

    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False,
                                     encoding="utf-8") as f:
        f.write(notes)
        notes_path = f.name
    try:
        subprocess.run(
            ["gh", "release", "create", tag,
             "--title", title, "--notes-file", notes_path],
            check=True)
    finally:
        os.unlink(notes_path)


if __name__ == "__main__":
    main()
