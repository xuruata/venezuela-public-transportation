#!/usr/bin/env python3
"""Extract Caracas Metrobús lines + stops from OSM Overpass dump.

Reads raw/osm_caracas_metrobus.json (a Overpass dump of route relations
tagged network="Metrobus Caracas" together with their member nodes/ways)
and writes data/caracas/metrobus/{lines,stops}.json.

Routes with multiple OSM relations (bi-directional or branched) collapse
to the longest relation; the other variants are noted in
`stops_ordered_note` so the information isn't lost.

Stops are deduplicated by OSM node id across routes — a stop served by
multiple routes lives once in stops.json with all its `lines` listed.
"""
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "raw" / "osm_caracas_metrobus.json"
OUT_DIR = ROOT / "data" / "caracas" / "metrobus"


def slugify(name: str) -> str:
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"^estacion\s+", "", s)
    s = re.sub(r"\s*\(.*?\)\s*", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def ref_sort_key(ref: str):
    m = re.match(r"P-(\d+)", ref)
    if m:
        return (1, int(m.group(1)), ref)
    m = re.match(r"(\d+)", ref)
    if m:
        return (0, int(m.group(1)), ref)
    return (2, 0, ref)


def stop_member_count(rel) -> int:
    return sum(1 for m in rel["members"]
               if m["type"] == "node" and "stop" in m.get("role", ""))


def clean_long_name(name: str, ref: str) -> str:
    # "Metrobus 001: Macaracuay" -> "Macaracuay"
    # "Ruta Preferencial 681: Bello Monte - Chuao" -> "Bello Monte - Chuao"
    s = re.sub(r"^(Metrobus|Ruta Preferencial)\s+\S+:\s*", "", name).strip()
    return s or ref


def main():
    d = json.loads(SRC.read_text())
    els = d["elements"]
    nodes = {e["id"]: e for e in els if e["type"] == "node"}
    rels = [e for e in els if e["type"] == "relation"]

    # Pick the longest relation per ref; remember the rest as variants.
    by_ref = defaultdict(list)
    for r in rels:
        by_ref[r["tags"].get("ref", "")].append(r)

    chosen = {}
    variants = {}
    for ref, rels_list in by_ref.items():
        rels_list.sort(key=lambda r: -stop_member_count(r))
        chosen[ref] = rels_list[0]
        if len(rels_list) > 1:
            variants[ref] = [
                (r["tags"].get("name", ""), stop_member_count(r))
                for r in rels_list[1:]
            ]

    # Build dedup-by-OSM-id stop table while walking each route in order.
    stops_by_id = {}    # slug -> stop record (with _osm_id)
    osm_to_slug = {}    # osm node id -> slug
    used_slugs = set()

    def get_or_create_stop(node_id):
        if node_id in osm_to_slug:
            return osm_to_slug[node_id]
        n = nodes.get(node_id)
        if not n:
            return None
        tags = n.get("tags", {})
        name = tags.get("name") or tags.get("ref") or f"Stop {node_id}"
        base = slugify(name) or f"stop-{node_id}"
        slug = base
        i = 2
        while slug in used_slugs:
            slug = f"{base}-{i}"
            i += 1
        used_slugs.add(slug)
        stops_by_id[slug] = {
            "id": slug,
            "name": name,
            "lat": n["lat"],
            "lon": n["lon"],
            "lines": [],
            "status": "operational",
            "_osm_id": node_id,
        }
        osm_to_slug[node_id] = slug
        return slug

    lines_out = []
    for ref in sorted(chosen.keys(), key=ref_sort_key):
        rel = chosen[ref]
        tags = rel["tags"]
        ordered = []
        seen_in_route = set()
        for m in rel["members"]:
            if m["type"] != "node":
                continue
            if "stop" not in m.get("role", ""):
                continue
            slug = get_or_create_stop(m["ref"])
            if not slug or slug in seen_in_route:
                continue
            ordered.append(slug)
            seen_in_route.add(slug)
            if ref not in stops_by_id[slug]["lines"]:
                stops_by_id[slug]["lines"].append(ref)

        line = {
            "id": ref,
            "short_name": ref,
            "long_name": clean_long_name(tags.get("name", ""), ref),
            "color": tags.get("colour", "#FF8800"),
            "text_color": "#FFFFFF",
            "type": "bus",
            "status": "operational",
            "stops_ordered": ordered,
            "osm_relation": rel["id"],
        }
        if ref.startswith("P-"):
            line["notes"] = "Ruta Preferencial — premium express variant."
        if ref in variants:
            extra = "; ".join(f"{n} ({c} stops)" for n, c in variants[ref])
            line["stops_ordered_note"] = (
                f"OSM has {len(variants[ref]) + 1} relations for this route; "
                f"this entry uses the longest. Other variant(s): {extra}."
            )
        lines_out.append(line)

    stops_out = []
    for slug in sorted(stops_by_id.keys()):
        s = stops_by_id[slug]
        stops_out.append({
            "id": s["id"],
            "name": s["name"],
            "lat": s["lat"],
            "lon": s["lon"],
            "lines": sorted(s["lines"], key=ref_sort_key),
            "status": s["status"],
            "osm_node": s["_osm_id"],
        })

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "lines.json").write_text(
        json.dumps(lines_out, indent=2, ensure_ascii=False) + "\n")
    (OUT_DIR / "stops.json").write_text(
        json.dumps(stops_out, indent=2, ensure_ascii=False) + "\n")

    print(f"wrote {len(lines_out)} lines, {len(stops_out)} stops")


if __name__ == "__main__":
    sys.exit(main())
