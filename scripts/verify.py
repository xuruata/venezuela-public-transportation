#!/usr/bin/env python3
"""Validate the canonical transit data files.

Checks:
- Every system directory has system.json, lines.json, stops.json, sources.md.
- Stop IDs in lines.json's stops_ordered exist in stops.json.
- Coordinates (when present) are inside Venezuela's bounding box.
- Each stop's `lines` list references defined line IDs.
- No duplicate stop IDs within a system.

Exit code 0 if clean, 1 otherwise.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# Generous bounding box for Venezuela (incl. islands)
VE_BBOX = {"lat_min": 0.5, "lat_max": 13.0, "lon_min": -73.5, "lon_max": -59.5}


def collect_systems():
    systems = []
    for system_json in DATA.rglob("system.json"):
        systems.append(system_json.parent)
    return sorted(systems)


def check_system(sysdir: Path, issues: list) -> dict:
    rel = sysdir.relative_to(ROOT)
    required = ["system.json", "lines.json", "stops.json", "sources.md"]
    for fname in required:
        if not (sysdir / fname).exists():
            issues.append(f"{rel}: missing {fname}")

    try:
        system = json.loads((sysdir / "system.json").read_text())
        lines = json.loads((sysdir / "lines.json").read_text())
        stops = json.loads((sysdir / "stops.json").read_text())
    except Exception as exc:
        issues.append(f"{rel}: JSON load error — {exc}")
        return {}

    stop_index = {}
    for stop in stops:
        sid = stop["id"]
        if sid in stop_index:
            issues.append(f"{rel}: duplicate stop id '{sid}'")
        stop_index[sid] = stop
        # Operational-only policy: every stop must be operational.
        if stop.get("status") != "operational":
            issues.append(
                f"{rel}: stop '{sid}' has status '{stop.get('status')}' "
                f"(only 'operational' allowed; see CLAUDE.md)")

    line_ids = {ln["id"] for ln in lines}
    for ln in lines:
        # Operational-only policy: lines must be operational (or 'partial' if the
        # system runs but with reduced stops; partial requires explicit justification).
        if ln.get("status") not in ("operational",):
            issues.append(
                f"{rel}: line '{ln['id']}' has status '{ln.get('status')}' "
                f"(only 'operational' allowed; see CLAUDE.md)")

    for ln in lines:
        for sid in ln.get("stops_ordered", []):
            if sid not in stop_index:
                issues.append(
                    f"{rel}: line {ln['id']} references missing stop '{sid}'")
        for sid in ln.get("planned_extensions", []):
            if sid not in stop_index:
                issues.append(
                    f"{rel}: line {ln['id']} planned extension references missing stop '{sid}'")

    for sid, stop in stop_index.items():
        for ln_id in stop.get("lines", []):
            if ln_id not in line_ids:
                issues.append(
                    f"{rel}: stop '{sid}' references unknown line '{ln_id}'")
        lat, lon = stop.get("lat"), stop.get("lon")
        if lat is not None and lon is not None:
            if not (VE_BBOX["lat_min"] <= lat <= VE_BBOX["lat_max"]):
                issues.append(
                    f"{rel}: stop '{sid}' latitude {lat} outside Venezuela bbox")
            if not (VE_BBOX["lon_min"] <= lon <= VE_BBOX["lon_max"]):
                issues.append(
                    f"{rel}: stop '{sid}' longitude {lon} outside Venezuela bbox")

    return {
        "system": system.get("id"),
        "n_lines": len(lines),
        "n_stops": len(stops),
        "n_stops_with_coords": sum(1 for s in stops if s.get("lat") is not None),
    }


def main():
    issues: list[str] = []
    summary = []
    for sysdir in collect_systems():
        result = check_system(sysdir, issues)
        if result:
            summary.append(result)

    print(f"{'System':40} {'Lines':>6} {'Stops':>6} {'WithCoords':>10}")
    print("-" * 64)
    for r in summary:
        print(f"{r['system']:40} {r['n_lines']:>6} {r['n_stops']:>6} "
              f"{r['n_stops_with_coords']:>10}")
    print()
    if issues:
        print(f"{len(issues)} issues:")
        for i in issues:
            print(f"  ! {i}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
