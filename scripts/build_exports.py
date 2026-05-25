#!/usr/bin/env python3
"""Generate GeoJSON and GTFS exports from canonical JSON.

For each system in data/<city>/<system>/:
- Emits exports/geojson/<system_id>-stops.geojson (Point FeatureCollection)
- Emits exports/geojson/<system_id>-lines.geojson (LineString FeatureCollection,
  one feature per line, drawn by connecting that line's stops in order)
- Emits exports/gtfs/<system_id>.zip with the standard GTFS files. Times are
  synthetic — frequencies-based, 5am-11pm, every 5-15 minutes depending on the
  mode. Mark this clearly in agency.txt.

Stops without coordinates are skipped from GeoJSON output and emitted with a
warning. They still appear in GTFS stops.txt with NaN coords flagged.
"""
import csv
import io
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT_GEO = ROOT / "exports" / "geojson"
OUT_GTFS = ROOT / "exports" / "gtfs"

# GTFS route_type values
GTFS_ROUTE_TYPE = {
    "metro": 1,
    "light_rail": 0,
    "commuter_rail": 2,
    "bus_rapid_transit": 3,
    "trolleybus_brt": 11,
    "gondola_lift": 6,
    "aerial_tramway": 6,
    "tram": 0,
}

DEFAULT_HEADWAY = {
    "metro": 300,
    "light_rail": 480,
    "commuter_rail": 1800,
    "bus_rapid_transit": 360,
    "trolleybus_brt": 600,
    "gondola_lift": 60,
    "aerial_tramway": 900,
}


def collect_systems():
    for system_json in sorted(DATA.rglob("system.json")):
        yield system_json.parent


def load_system(sysdir: Path):
    system = json.loads((sysdir / "system.json").read_text())
    lines = json.loads((sysdir / "lines.json").read_text())
    stops = {s["id"]: s for s in json.loads((sysdir / "stops.json").read_text())}
    return system, lines, stops


def build_stops_geojson(system, stops) -> dict:
    feats = []
    for sid, s in stops.items():
        if s.get("lat") is None or s.get("lon") is None:
            continue
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [s["lon"], s["lat"]]},
            "properties": {
                "id": f"{system['id']}:{sid}",
                "name": s["name"],
                "system": system["id"],
                "lines": s.get("lines", []),
                "status": s.get("status", "unknown"),
                "altitude_m": s.get("altitude_m"),
                "wikidata": s.get("wikidata"),
            },
        })
    return {"type": "FeatureCollection", "features": feats}


def build_lines_geojson(system, lines, stops) -> dict:
    feats = []
    for ln in lines:
        coords = []
        for sid in ln.get("stops_ordered", []):
            s = stops.get(sid)
            if not s or s.get("lat") is None or s.get("lon") is None:
                continue
            coords.append([s["lon"], s["lat"]])
        if len(coords) < 2:
            continue
        feats.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {
                "id": f"{system['id']}:{ln['id']}",
                "system": system["id"],
                "line": ln["id"],
                "short_name": ln.get("short_name"),
                "long_name": ln.get("long_name"),
                "color": ln.get("color"),
                "status": ln.get("status"),
                "type": ln.get("type"),
                "alignment_note":
                    "Approximate alignment — straight segments between station "
                    "coordinates. Not the actual track geometry.",
            },
        })
    return {"type": "FeatureCollection", "features": feats}


def gtfs_color(hexc: str | None) -> str:
    if not hexc:
        return ""
    return hexc.lstrip("#").upper()


def build_gtfs(system, lines, stops) -> bytes:
    """Build a minimal but valid GTFS feed.

    Schedules are synthetic frequencies-based service every weekday 05:00-23:00.
    """
    sid = system["id"]
    rows = {}

    rows["agency.txt"] = [
        ["agency_id", "agency_name", "agency_url", "agency_timezone", "agency_lang"],
        [
            sid,
            system["agency"]["name"],
            system["agency"].get("url") or "https://example.invalid/",
            system["agency"]["timezone"],
            system["agency"].get("lang", "es"),
        ],
    ]

    # stops.txt — coord-less stops get 0,0 with a note in stop_desc
    stops_rows = [["stop_id", "stop_name", "stop_lat", "stop_lon", "stop_desc"]]
    for stop_id, s in stops.items():
        lat = s.get("lat")
        lon = s.get("lon")
        desc = s.get("notes") or ""
        if lat is None or lon is None:
            desc = ("[COORDINATES MISSING] " + desc).strip()
            lat, lon = 0, 0
        stops_rows.append([stop_id, s["name"], f"{lat}", f"{lon}", desc])
    rows["stops.txt"] = stops_rows

    # routes.txt
    routes_rows = [["route_id", "agency_id", "route_short_name", "route_long_name",
                    "route_type", "route_color", "route_text_color"]]
    # trips.txt + frequencies.txt + stop_times.txt
    trips_rows = [["route_id", "service_id", "trip_id", "trip_headsign", "direction_id"]]
    freq_rows = [["trip_id", "start_time", "end_time", "headway_secs"]]
    st_rows = [["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"]]

    for ln in lines:
        route_id = f"{sid}:{ln['id']}"
        routes_rows.append([
            route_id, sid, ln.get("short_name", ""), ln.get("long_name", ""),
            GTFS_ROUTE_TYPE.get(ln.get("type", system["type"]), 3),
            gtfs_color(ln.get("color")), gtfs_color(ln.get("text_color")),
        ])

        seq = ln.get("stops_ordered", [])
        if len(seq) < 2:
            continue

        # Build a single trip in each direction for the route. A per-line
        # `headway_secs` field in lines.json wins over the mode default — use
        # it only when an authoritative source confirms (see CLAUDE.md).
        headway = ln.get("headway_secs") or DEFAULT_HEADWAY.get(
            ln.get("type", system["type"]), 600)
        for direction, ordered in enumerate([seq, list(reversed(seq))]):
            trip_id = f"{route_id}:dir{direction}"
            headsign = stops[ordered[-1]]["name"] if ordered[-1] in stops else ordered[-1]
            trips_rows.append([route_id, "weekday", trip_id, headsign, direction])
            freq_rows.append([trip_id, "05:00:00", "23:00:00", headway])
            # Assign rough stop times spaced 90s apart (template trip used only
            # to anchor the frequencies block).
            for i, stop_id in enumerate(ordered):
                if stop_id not in stops:
                    continue
                offset = i * 90
                h, rem = divmod(offset, 3600)
                m, sec = divmod(rem, 60)
                tstr = f"{5 + h:02d}:{m:02d}:{sec:02d}"
                st_rows.append([trip_id, tstr, tstr, stop_id, i + 1])

    rows["routes.txt"] = routes_rows
    rows["trips.txt"] = trips_rows
    rows["frequencies.txt"] = freq_rows
    rows["stop_times.txt"] = st_rows

    rows["calendar.txt"] = [
        ["service_id", "monday", "tuesday", "wednesday", "thursday",
         "friday", "saturday", "sunday", "start_date", "end_date"],
        ["weekday", 1, 1, 1, 1, 1, 1, 1, "20260101", "20300101"],
    ]

    # Pack to zip. Use a fixed date_time on every entry so that successive
    # builds with identical inputs produce byte-identical zip files — this
    # is what lets CI verify "exports/ is up to date" with a simple git diff.
    def _put(zf, fname, data):
        info = zipfile.ZipInfo(fname, date_time=(2026, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        zf.writestr(info, data)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for fname, rs in rows.items():
            out = io.StringIO()
            writer = csv.writer(out)
            writer.writerows(rs)
            _put(zf, fname, out.getvalue())
        _put(zf, "README.txt",
            "Synthetic frequencies-based feed. The route topology is real, but\n"
            "the schedule is approximate (every N minutes 05:00-23:00 weekdays).\n"
            "Do not use for trip-planning. See sources.md in the upstream repo.\n")
    return buf.getvalue()


def main():
    OUT_GEO.mkdir(parents=True, exist_ok=True)
    OUT_GTFS.mkdir(parents=True, exist_ok=True)
    skipped_total = 0
    for sysdir in collect_systems():
        system, lines, stops = load_system(sysdir)
        sid = system["id"]

        stops_geo = build_stops_geojson(system, stops)
        lines_geo = build_lines_geojson(system, lines, stops)
        (OUT_GEO / f"{sid}-stops.geojson").write_text(
            json.dumps(stops_geo, ensure_ascii=False, indent=2) + "\n")
        (OUT_GEO / f"{sid}-lines.geojson").write_text(
            json.dumps(lines_geo, ensure_ascii=False, indent=2) + "\n")

        gtfs_bytes = build_gtfs(system, lines, stops)
        (OUT_GTFS / f"{sid}.zip").write_bytes(gtfs_bytes)

        n_stops_with_coords = sum(1 for s in stops.values() if s.get("lat"))
        n_skipped = len(stops) - n_stops_with_coords
        skipped_total += n_skipped
        print(f"  {sid:40}  stops={len(stops):3}  geojson_pts={n_stops_with_coords:3}"
              f"  gtfs_zip={len(gtfs_bytes)//1024}KB  skipped_no_coords={n_skipped}")
    print(f"\nTotal stops without coords (omitted from GeoJSON): {skipped_total}")


if __name__ == "__main__":
    sys.exit(main())
