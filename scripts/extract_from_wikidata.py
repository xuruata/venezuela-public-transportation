#!/usr/bin/env python3
"""Extract per-system station data from raw Wikidata SPARQL dump.

Reads raw/wikidata_stations.json and writes per-system stops.json files.
Also prints a diff against existing files so manual edits are preserved.
"""
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LINE_MAP = {
    "Q6515333":   ("caracas/metro",                "L1"),
    "Q5986160":   ("caracas/metro",                "L2"),
    "Q21346332":  ("caracas/metro",                "L3"),
    "Q21659772":  ("caracas/metro",                "L4"),
    "Q55411476":  ("caracas/metro",                "L5"),
    "Q109123589": ("caracas/metro",                "L6"),
    "Q57555433":  ("maracaibo/metro",              "L1"),
    "Q56168307":  ("los-teques/metro",             "L1"),
    "Q56347950":  ("los-teques/metro",             "L2"),
    "Q6129604":   ("caracas/sistema-ferroviario",  "L1"),
    "Q1280714":   ("caracas/teleferico-avila",     "L1"),
}


def slugify(name: str) -> str:
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"^metro\s+", "", s)
    s = re.sub(r"^estacion\s+", "", s)
    s = re.sub(r"\s*\(.*?\)\s*", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def parse_point(wkt: str):
    m = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", wkt or "")
    if not m:
        return None, None
    return float(m.group(2)), float(m.group(1))


def load_wikidata():
    p = ROOT / "raw" / "wikidata_stations.json"
    return json.load(p.open())["results"]["bindings"]


def main():
    rows = load_wikidata()

    by_system = defaultdict(dict)  # system -> {stop_id: stop_record}

    for b in rows:
        suri = b.get("station", {}).get("value", "").split("/")[-1]
        name = (b.get("stationLabel", {}).get("value")
                or b.get("stationLabelEn", {}).get("value")
                or suri)
        line_qid = b.get("line", {}).get("value", "").split("/")[-1]
        coord = b.get("coord", {}).get("value", "")

        mapping = LINE_MAP.get(line_qid)
        if not mapping:
            continue

        system, line_id = mapping
        clean_name = re.sub(r"^Metro\s+", "", name)
        clean_name = re.sub(r"\s*\([^)]*\)\s*", "", clean_name).strip()
        stop_id = slugify(clean_name)

        lat, lon = parse_point(coord)
        rec = by_system[system].setdefault(stop_id, {
            "id": stop_id,
            "name": clean_name,
            "lat": lat,
            "lon": lon,
            "lines": [],
            "wikidata": suri,
        })
        if line_id not in rec["lines"]:
            rec["lines"].append(line_id)

    # Sort lines and emit
    for system, stops in by_system.items():
        out = sorted(stops.values(), key=lambda r: (r["lines"][0], r["id"]))
        for r in out:
            r["lines"].sort()
        target = ROOT / "data" / system / "stops.wikidata.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
        print(f"wrote {target.relative_to(ROOT)}  ({len(out)} stops)")


if __name__ == "__main__":
    sys.exit(main())
