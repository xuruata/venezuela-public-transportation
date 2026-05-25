#!/usr/bin/env python3
"""Compare canonical dataset against OpenStreetMap (Overpass).

Pulls every transit-ish node in Venezuela from OSM, then matches each canonical
stop against the nearest OSM neighbor. Reports:
  - per-system match coverage
  - coordinate disagreements >50 m
  - OSM stations with no canonical counterpart

Use this whenever you want to know whether OSM has discovered something we
haven't, or whether OSM disagrees with our coordinates.

Pulls live data — needs internet.
"""
import json
import math
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw" / "osm_stations.json"

OVERPASS_QUERY = """[out:json][timeout:120];
area["ISO3166-1"="VE"][admin_level=2]->.ve;
(
  node["station"~"^(subway|light_rail)$"](area.ve);
  node["railway"~"^(station|halt|tram_stop)$"](area.ve);
  node["aerialway"="station"](area.ve);
  node["trolleybus"="yes"]["public_transport"~"station|stop_position"](area.ve);
  node["public_transport"="station"]["network"~"Metro|Transbarca|TransMaracay|Trolm|Tromerca",i](area.ve);
);
out body meta;
"""


def slug(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"^(metro|estacion|estación|tromerca)\s+", "", s)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def haversine_m(a, b):
    lat1, lon1 = a
    lat2, lon2 = b
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def fetch_osm():
    url = "https://overpass-api.de/api/interpreter?" + urllib.parse.urlencode(
        {"data": OVERPASS_QUERY})
    req = urllib.request.Request(url, headers={
        "User-Agent": "venezuela-transit-data-research (compare_osm.py)",
    })
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    RAW.parent.mkdir(parents=True, exist_ok=True)
    RAW.write_bytes(data)
    return json.loads(data)


def load_canon():
    rows = []
    for sysdir in sorted((ROOT / "data").glob("*/*")):
        if not (sysdir / "system.json").exists():
            continue
        sid = json.loads((sysdir / "system.json").read_text())["id"]
        for s in json.loads((sysdir / "stops.json").read_text()):
            rows.append({
                "system": sid,
                "id": s["id"],
                "name": s["name"],
                "name_slug": slug(s["name"]),
                "lat": s.get("lat"),
                "lon": s.get("lon"),
            })
    return rows


def main():
    if "--cached" in sys.argv and RAW.exists():
        osm_raw = json.loads(RAW.read_text())
    else:
        print("Fetching OSM data via Overpass...", file=sys.stderr)
        osm_raw = fetch_osm()

    osm = [{
        "id": e["id"],
        "lat": e["lat"],
        "lon": e["lon"],
        "name": e.get("tags", {}).get("name", ""),
        "name_slug": slug(e.get("tags", {}).get("name", "")),
        "tags": e.get("tags", {}),
        "ts": e.get("timestamp", ""),
    } for e in osm_raw["elements"]]

    canon = load_canon()

    used_osm = set()
    matched = []
    unmatched_canon = []
    for c in canon:
        if c["lat"] is None:
            # name-slug match fallback
            hits = [o for o in osm if o["name_slug"] == c["name_slug"]]
            if hits:
                matched.append((c, hits[0], None))
                used_osm.add(hits[0]["id"])
            else:
                unmatched_canon.append(c)
            continue
        best, dist = None, math.inf
        for o in osm:
            d = haversine_m((c["lat"], c["lon"]), (o["lat"], o["lon"]))
            if d < dist:
                best, dist = o, d
        if dist < 500:
            matched.append((c, best, dist))
            used_osm.add(best["id"])
        else:
            unmatched_canon.append(c)

    unmatched_osm = [o for o in osm if o["id"] not in used_osm]

    by_sys = defaultdict(lambda: {"total": 0, "matched": 0, "no_coords": 0})
    for c in canon:
        by_sys[c["system"]]["total"] += 1
        if c["lat"] is None:
            by_sys[c["system"]]["no_coords"] += 1
    for c, _, _ in matched:
        by_sys[c["system"]]["matched"] += 1

    print(f"Canonical stops: {len(canon)} ({sum(1 for c in canon if c['lat'])} "
          f"with coords)")
    print(f"OSM stations:    {len(osm)}\n")
    print(f"{'system':38} {'total':>5} {'matched':>7} {'no_coords':>9}")
    for s, v in sorted(by_sys.items()):
        print(f"{s:38} {v['total']:5d} {v['matched']:7d} {v['no_coords']:9d}")

    deltas = [d for _, _, d in matched if d is not None]
    if deltas:
        ds = sorted(deltas)
        print(f"\nCoord deltas (n={len(deltas)}):  median={ds[len(ds)//2]:.0f}m  "
              f"p90={ds[int(len(ds)*0.9)]:.0f}m  max={ds[-1]:.0f}m")
        big = [(c, o, d) for c, o, d in matched if d and d > 50]
        if big:
            print(f"  >50m disagreements ({len(big)}):")
            for c, o, d in sorted(big, key=lambda x: -x[2])[:10]:
                print(f"    {d:5.0f}m  {c['system']}/{c['id']:25}  "
                      f"osm-name={o['name']!r}")

    print(f"\nOSM stations with no canonical counterpart: {len(unmatched_osm)}")
    for o in unmatched_osm:
        net = o["tags"].get("network") or o["tags"].get("operator") or "-"
        print(f"  {o['lat']:.5f},{o['lon']:.5f}  {o['name']!r:35}  net={net!r}")


if __name__ == "__main__":
    sys.exit(main())
