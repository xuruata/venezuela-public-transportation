# CLAUDE.md — working on this repo

Static public transit data for Venezuela. Edit canonical JSON in `data/`,
then regenerate the GeoJSON + GTFS exports.

## Layout (mental model)

```
data/<city>/<system>/        ← canonical source of truth (hand-edited)
  system.json   lines.json   stops.json   sources.md

exports/geojson/             ← generated; never edit by hand
exports/gtfs/                ← generated; never edit by hand

scripts/
  extract_from_wikidata.py   ← seed coords from Wikidata SPARQL
  build_exports.py           ← canonical → GeoJSON + GTFS
  verify.py                  ← validate canonical files

raw/wikidata_stations.json   ← cached SPARQL dump (re-pull as needed)
```

**The canonical files are the source of truth.** Always edit `data/`, never the
files under `exports/`. After any edit, run:

```bash
python3 scripts/verify.py        # must pass — exit 0
python3 scripts/build_exports.py # regenerates exports/
```

Don't commit until both succeed.

## Adding a new transit system

1. `mkdir -p data/<city>/<system>/`
2. Create the four files (use any existing system as a template — e.g.
   `data/maracaibo/metro/` is the simplest):
   - `system.json` — agency, type, opened, status
   - `lines.json` — one entry per line, including `stops_ordered` (array of stop ids)
   - `stops.json` — every stop the lines reference, with `id`, `name`, `lat`,
     `lon`, `lines`, `status`
   - `sources.md` — where the data came from, plus any caveats
3. Run `verify.py` to confirm shape, then `build_exports.py`.

## Adding / updating stops

- Stop `id` is a kebab-case slug derived from the Spanish name (strip accents,
  lowercase, replace spaces with hyphens). Match the convention in existing
  files. See `scripts/extract_from_wikidata.py::slugify` for the canonical rule.
- A stop on multiple lines lives once in `stops.json` with `lines: ["L1", "L3"]`.
- If you don't have coordinates, set `lat: null, lon: null` — that's better than
  guessing. Verify ignores nulls; build skips them from GeoJSON and writes 0,0
  with a `[COORDINATES MISSING]` flag in GTFS `stop_desc`.
- Lines reference stops by id in `stops_ordered`. If a stop_id in `stops_ordered`
  isn't in `stops.json`, verify fails.

## Line id conventions

- Numbered metro lines: `L1`, `L2`, ... `L6`.
- Named lines (commuter rail, cable systems): meaningful prefix — e.g. `TL1`
  for Tren Caracas-Cúa.
- Whatever id you pick in `lines.json`, every stop on that line must list the
  *same* id in its `lines` array. Verify checks this.

## Scope: operational-only

**Every stop and line in this dataset must currently be in active passenger
service.** Venezuela has a long history of transit projects that announce,
break ground, and then sit for years without finishing. Including those would
mislead consumers, so we exclude them.

| value | usage |
|---|---|
| `operational` | **The only value `status` should take** on a stop or line. Verify enforces this. |
| `under_construction`, `planned`, `suspended`, `closed`, `partial` | Document in `sources.md` if relevant. Do not put in the data files — verify will fail. |

If a system has both operating and non-operating segments (e.g. Maracaibo Metro
phase 1 vs phase 2 extension):
- Include only the operational segment in `lines.json` / `stops.json`.
- Mention the excluded segment in `system.json:notes` and in `sources.md` with
  the phrase "excluded per the operational-only policy".

If a system flips out of operational service (suspended or closed entirely),
**remove the system directory** — don't downgrade its status. Document the
removal in a commit message. Trolmérida is the precedent: it was removed
from the dataset when its service was confirmed suspended.

Why this matters: the Wikidata SPARQL query in `scripts/extract_from_wikidata.py`
will pull planned/under-construction stations because Wikidata catalogs them.
After re-extracting, **diff against canonical and discard any non-operational
stops** before merging.

## Refreshing coordinates from Wikidata

For systems where stations have Wikidata QIDs (Caracas Metro, Maracaibo Metro,
Los Teques Metro, Sistema Ferroviario, Teleférico Ávila):

```bash
# Re-pull the SPARQL dump
curl -sS -A "venezuela-transit-data-research" -G "https://query.wikidata.org/sparql" \
  --data-urlencode 'format=json' \
  --data-urlencode "@docs/sparql/stations.rq" \
  -o raw/wikidata_stations.json

# Re-extract into staging files
python3 scripts/extract_from_wikidata.py
```

That writes `data/<system>/stops.wikidata.json` next to each system's existing
`stops.json`. **Diff against the canonical** `stops.json` and merge updates
manually — don't overwrite, because hand-curated fields (status, notes,
alt_names, planned-extension stops not in Wikidata) live only in the canonical
file.

The Wikidata query (from memory — `stations.rq` doesn't exist yet, create it
if/when needed):

```sparql
SELECT ?station ?stationLabel ?coord ?line ?lineLabel WHERE {
  ?station wdt:P17 wd:Q717 .                # country: Venezuela
  ?station wdt:P31/wdt:P279* wd:Q55488 .    # subclass of train station
  OPTIONAL { ?station wdt:P625 ?coord }     # coordinate location
  OPTIONAL { ?station wdt:P81 ?line }       # part of line
  SERVICE wikibase:label { bd:serviceParam wikibase:language "es" }
}
```

## Geocoding gaps (OSM via Overpass)

For BRT / trolleybus systems Wikidata doesn't cover well (Transbarca,
TransMaracay) and for cable cars (where Wikidata is sparse but OSM mappers are
thorough):

```bash
curl -sS -A "venezuela-transit-data-research" --get "https://overpass-api.de/api/interpreter" \
  --data-urlencode 'data=[out:json][timeout:30];node["station"="subway"](BBOX);out;'
```

A descriptive `User-Agent` is required — Overpass returns 406 to generic UAs.
Pace requests; one bbox query at a time is fine.

## When OSM disagrees with our data

`scripts/compare_osm.py` pulls every transit node in Venezuela from Overpass
and matches it against canonical stops. Use it whenever you want to:
- Check if OSM has discovered a new station we don't have.
- Find coordinate disagreements (anything >50 m is worth a look).
- Verify a refresh hasn't introduced regressions.

```bash
python3 scripts/compare_osm.py           # fresh pull
python3 scripts/compare_osm.py --cached  # reuse raw/osm_stations.json
```

When OSM and Wikidata disagree on a coordinate, prefer OSM if its element was
edited recently (timestamp in tags). OSM mappers update from on-the-ground
knowledge; Wikidata coordinates can be old. The Mukumbarí precedent: OSM's
Feb 2025 edits gave us coords accurate to ~10 m, while Wikidata-style
interpolated coords were off by up to 4.7 km.

## Source-selection rule of thumb

- **Numbered metro lines, commuter rail**: Wikidata is best. Each station has a
  QID, line membership is explicit, and operational stations are well-covered.
- **Cable cars, aerial trams**: OSM is best. Wikidata has only the most famous
  stations; OSM has full chains with surveyed coordinates.
- **BRT and trolleybus**: Both are weak. Document what you find in
  `sources.md`. On-the-ground surveys are the gold standard here.

## Adding or correcting timetables / schedules

The GTFS feeds use synthetic `frequencies.txt` schedules — every N minutes,
05:00–23:00 weekdays, where N depends on the mode (see
`DEFAULT_HEADWAY` in `scripts/build_exports.py`). **Do not** add real
schedules unless an authoritative source confirms them. Per-line overrides
are supported via an optional `headway_secs` field in `lines.json` — set it
only when you have a source; the mode default applies otherwise.

## Cross-checking before committing

```bash
python3 scripts/verify.py                  # JSON shape, line refs, bbox sanity
python3 scripts/build_exports.py           # regenerate exports
git diff --stat data/ exports/             # sanity-check change scope
```

Also a useful manual count check against Wikipedia: total operational stops per
line should match the upstream sources cited in each system's `sources.md`.
The validation snippet lives at the end of the agent's conversation log if you
need a copy.

## What NOT to do

- Don't put coordinates you're not confident in. Null is fine.
- Don't invent stop names. If a source uses two names for the same stop (e.g.
  Valencia L2 "Negra Hipólita" / "Los Sauces"), put the formal one in `name`
  and the other in `alt_names`.
- Don't add bus routes outside the trunk BRT systems and branded
  operator-run networks already documented (Transbarca, TransMaracay, and
  the Caracas Metrobús — the latter is a feeder network with numbered
  routes, signed stops, and a single agency, so it shares the same data
  shape as a BRT even though it lacks dedicated lanes). The fragmented
  por-puesto / carrito / autobús urbano networks are explicitly out of
  scope — they'd require on-the-ground surveys and would dilute the
  dataset.
- Don't edit `exports/` directly. Regenerate.
- Don't strip the `wikidata` field from existing stops — it's the key to
  re-pulling future coordinate updates.
