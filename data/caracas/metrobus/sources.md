# Sources — Metrobús de Caracas

## Primary source

**OpenStreetMap** — every route, stop, and coordinate in this system was
extracted from OSM relations tagged `network=Metrobus Caracas` and
`operator=C.A. Metro de Caracas`. Pulled via Overpass on 2026-05-25 and
cached to `raw/osm_caracas_metrobus.json` for reproducibility.

To re-pull:

```bash
curl -sS -A "venezuela-transit-data-research" --get "https://overpass-api.de/api/interpreter" \
  --data-urlencode 'data=[out:json][timeout:120];
relation["type"="route"]["route"="bus"]["network"="Metrobus Caracas"](10.35,-67.10,10.65,-66.65);
(._;>;);
out body;' -o raw/osm_caracas_metrobus.json

python3 scripts/extract_caracas_metrobus.py
```

The extractor (`scripts/extract_caracas_metrobus.py`) walks each relation's
ordered `stop` members, deduplicates by OSM node id, and emits `lines.json`
and `stops.json`. Each stop carries its OSM node id in the `osm_node`
field for traceability.

## Background

- [Wikipedia EN — Caracas Metro, Metrobús section](https://en.wikipedia.org/wiki/Caracas_Metro)
  — describes the system as a 20-urban + 4-suburban-route feeder network
  connecting metro stations to outlying neighborhoods (Guarenas, La Guaira,
  La Rosa, San Antonio, Los Teques). The OSM mapping is more current and
  enumerates more routes than the Wikipedia summary.

## Classification caveat

Whether Metrobús counts as BRT is debatable. Arguments for: branded
vehicles, fixed numbered routes, built stops with route signage, single
agency operating to a published map. Arguments against: most of the
network lacks dedicated bus lanes, so vehicles run in mixed traffic in a
densely congested city. The BRT Standard scores systems on a spectrum
rather than binary classification; we record `type: "bus"` in `lines.json`
to be conservative about that distinction, but include the network here
alongside the formally-BRT Transbarca and TransMaracay because the data
shape (numbered routes, ordered named stops, single operator) is the
same.

## Route variants

A handful of OSM refs (601, 605, 603) have multiple relations because
the route is bidirectional or branches mid-corridor. Where multiple
relations exist, we keep the relation with the longest stop chain and
record the variant(s) we dropped in each line's `stops_ordered_note`.
Future contributions can split those into separate line entries
(`601a`, `601b`) if desired.

## Completeness caveat

OSM coverage of Metrobús appears to be substantial but not authoritative:
- 35 routes mapped here, versus the ~24 mentioned by Wikipedia. The
  delta is probably real (newer routes, or routes Wikipedia
  underreports) but we cannot independently verify each.
- Stop names occasionally fall back to OSM node ids when the underlying
  node has no `name` tag.
- We have not cross-checked against an operator-published route map; an
  authoritative source from C.A. Metro de Caracas would be the gold
  standard.

## Suspensions

The Metrobús has been suspended on multiple occasions during the
2017–present period of political and economic crisis (general strikes,
fuel rationing). The system has resumed each time, so we mark routes as
`operational` per the project's policy. If the system is confirmed
suspended for the long term, remove it entirely per the
operational-only policy in CLAUDE.md.
