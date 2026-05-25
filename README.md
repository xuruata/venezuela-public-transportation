# Venezuela Public Transportation — open data

*Read this in other languages: **English** · [Español](README.es.md)*

Static public transit data for Venezuela, in formats developers can drop into a
website, GIS tool, or trip planner.

**Scope: operational only.** Venezuela has many transit projects in
indefinite-construction status. To keep the data honest, the dataset covers
only stops and lines currently in active passenger service. Planned,
under-construction, suspended, and closed segments are excluded — and called
out in each system's `sources.md`.

| City | Pop. (est.) | System | Type | Stops | Coords |
|---|---:|---|---|---:|---:|
| Maracaibo   | 2.6 M | [Metro de Maracaibo](data/maracaibo/metro/) | light rail | 6 | 6/6 |
| Caracas     | 2.2 M | [Metro de Caracas](data/caracas/metro/) | metro | 47 | 47/47 |
| Caracas     |       | [Metrocable San Agustín](data/caracas/metrocable-sanagustin/) | gondola | 3 | 3/3 |
| Caracas     |       | [Sistema Ferroviario (Caracas-Cúa)](data/caracas/sistema-ferroviario/) | commuter rail | 4 | 4/4 |
| Caracas     |       | [Teleférico Warairarepano](data/caracas/teleferico-avila/) | aerial tram | 2 | 2/2 |
| Valencia    | 1.6 M | [Metro de Valencia](data/valencia/metro/) | metro | 9 | 9/9 |
| Barquisimeto| 1.2 M | [Transbarca](data/barquisimeto/transbarca/) | BRT | 12* | 1/12 |
| Maracay     | 1.0 M | [TransMaracay](data/maracay/transmaracay/) | BRT | 2* | 0/2 |
| Los Teques  | 0.2 M | [Metro de Los Teques](data/los-teques/metro/) | metro | 3 | 3/3 |
| Mérida      | 0.3 M | [Mukumbarí (cable car)](data/merida/teleferico/) | aerial tram | 5 | 5/5 |

**Total**: 10 systems, 93 stops, 80 with coordinates (86%).

*The Barquisimeto and Maracay BRT entries are incomplete — terminal hubs plus
major named stops only. Wikipedia describes ~52 and ~13 stops respectively but
does not enumerate them; OpenStreetMap coverage is sparse. Contributions
welcome.

## What's here

```
data/<city>/<system>/
  system.json   # one system: agency, type, opening date, status
  lines.json    # lines: id, name, color, ordered list of stop ids
  stops.json    # stops: id, name, lat/lon, lines[], status
  sources.md    # provenance and caveats

exports/
  geojson/<system-id>-stops.geojson   # Point FeatureCollection
  geojson/<system-id>-lines.geojson   # LineString FeatureCollection
  gtfs/<system-id>.zip                # GTFS feed (synthetic schedule)

scripts/
  extract_from_wikidata.py   # Re-pull station coords from Wikidata SPARQL
  build_exports.py           # Regenerate exports/ from data/
  verify.py                  # Validate canonical files

raw/
  wikidata_stations.json     # Wikidata SPARQL dump used to seed coordinates
```

## Formats

**Canonical** data is hand-editable JSON in `data/`. It is the source of truth —
edit there, then run `python3 scripts/build_exports.py` to regenerate the derived
formats.

**GeoJSON** in `exports/geojson/` is suitable for Leaflet, Mapbox, QGIS, etc.
Stops are Point features; lines are LineString features drawn by connecting
each line's stops in order (so they're approximate — straight segments, not
real track geometry).

**GTFS** in `exports/gtfs/` follows the [General Transit Feed Specification][gtfs]
and can be consumed by any GTFS-aware tool (Google Maps' Transit Land import,
OpenTripPlanner, Transitland, etc.).

  > **⚠ Schedules are synthetic.** Venezuelan operators rarely publish timetables, so
  > the GTFS feeds use `frequencies.txt` with a placeholder "every N minutes
  > 05:00-23:00 weekdays". **Route topology is real; the times are not.**

[gtfs]: https://gtfs.org/

## Status field

Every stop and line carries a `status: "operational"` field. That's the only
value allowed — the dataset is operational-only by policy (see [CLAUDE.md](CLAUDE.md)
for the rationale). The field is kept so consumers can defensively check it
if the policy ever loosens.

## Coordinate provenance

| Source | Approx. stops |
|---|---:|
| Wikidata (SPARQL `wdt:P625`) | 60 |
| OpenStreetMap (Overpass) | 20 |
| Missing | 13 (all BRT stops) |

The `wikidata` field on each stop, where present, is its Wikidata QID — useful
for re-pulling future updates. See [CLAUDE.md](CLAUDE.md) for the
source-selection rules of thumb.

## Verifying and updating

```bash
python3 scripts/verify.py        # validate JSON shape, line refs, bbox sanity, status policy
python3 scripts/build_exports.py # regenerate GeoJSON + GTFS
python3 scripts/compare_osm.py   # check our coords against fresh OpenStreetMap data
```

## Contributing

Highest-value improvements:

1. **Complete the BRT stop lists** — Transbarca (Barquisimeto) and TransMaracay.
   Wikipedia describes the systems in prose; the full ordered station lists
   are not enumerated anywhere I've found and OSM coverage is sparse.
2. **Add coordinates for the 13 stops without them** — all BRT stops.
3. **Re-verify operational status periodically.** When a system or stop is
   confirmed closed/suspended, remove it from the data files; document the
   removal in the commit message and the system's `sources.md`. When a
   long-stalled "planned" line finally opens, add it.

Workflow:
1. Edit `data/<city>/<system>/{system,lines,stops}.json`.
2. Run `python3 scripts/verify.py` — must pass (it enforces the operational-only policy).
3. Run `python3 scripts/build_exports.py` to regenerate exports.
4. Open a pull request.

For deeper edits — adding a new system, refreshing from Wikidata or
OpenStreetMap — see [CLAUDE.md](CLAUDE.md).

## License

This repository — data, schema, exports, and scripts — is released under the
[Open Database License (ODbL) v1.0](LICENSE). When redistributing this dataset
or any derivative database, include the notice:

> "Contains information from the venezuela-public-transportation database,
> made available under the Open Database License (ODbL)."

ODbL was chosen because the dataset embeds coordinate data from OpenStreetMap,
whose ODbL terms require share-alike for derivative databases. Licensing the
whole repository under ODbL keeps everything internally consistent and
satisfies OSM's requirements automatically.

## Attributions

This dataset would not exist without these upstream projects. When you
redistribute data derived from them, please attribute appropriately.

### Wikipedia — system overviews, line topology, station names, opening dates
Wikipedia content is licensed under [CC BY-SA](https://creativecommons.org/licenses/by-sa/4.0/).

- [Caracas Metro](https://en.wikipedia.org/wiki/Caracas_Metro) — *Wikipedia contributors*
- [List of Caracas Metro stations](https://en.wikipedia.org/wiki/List_of_Caracas_Metro_stations) — *Wikipedia contributors*
- [Metro de Caracas](https://es.wikipedia.org/wiki/Metro_de_Caracas) — *Colaboradores de Wikipedia*
- [Línea 1 (Metro de Caracas)](https://es.wikipedia.org/wiki/L%C3%ADnea_1_(Metro_de_Caracas)) — *Colaboradores de Wikipedia*
- [Línea 3 (Metro de Caracas)](https://es.wikipedia.org/wiki/L%C3%ADnea_3_(Metro_de_Caracas)) — *Colaboradores de Wikipedia*
- [Maracaibo Metro](https://en.wikipedia.org/wiki/Maracaibo_Metro) — *Wikipedia contributors*
- [Valencia Metro (Venezuela)](https://en.wikipedia.org/wiki/Valencia_Metro_(Venezuela)) — *Wikipedia contributors*
- [Metro de Valencia (Venezuela)](https://es.wikipedia.org/wiki/Metro_de_Valencia_(Venezuela)) — *Colaboradores de Wikipedia*
- [Los Teques Metro](https://en.wikipedia.org/wiki/Los_Teques_Metro) — *Wikipedia contributors*
- [Mérida cable car](https://en.wikipedia.org/wiki/M%C3%A9rida_cable_car) — *Wikipedia contributors*
- [Teleférico de Mérida](https://es.wikipedia.org/wiki/Telef%C3%A9rico_de_M%C3%A9rida) — *Colaboradores de Wikipedia*
- [Trolleybuses in Mérida](https://en.wikipedia.org/wiki/Trolleybuses_in_M%C3%A9rida) — *Wikipedia contributors*
- [Trolmérida](https://es.wikipedia.org/wiki/Trolm%C3%A9rida) — *Colaboradores de Wikipedia*
- [Línea 1 de Trolmérida](https://es.wikipedia.org/wiki/L%C3%ADnea_1_de_Trolm%C3%A9rida) — *Colaboradores de Wikipedia*
- [Trolcable](https://es.wikipedia.org/wiki/Trolcable) — *Colaboradores de Wikipedia*
- [Transbarca](https://es.wikipedia.org/wiki/Transbarca) — *Colaboradores de Wikipedia*
- [Línea 1 de Transbarca](https://es.wikipedia.org/wiki/L%C3%ADnea_1_de_Transbarca) — *Colaboradores de Wikipedia*
- [Metrocable (Caracas)](https://en.wikipedia.org/wiki/Metrocable_(Caracas)) — *Wikipedia contributors*
- [Estación San Agustín (Metrocable de Caracas)](https://es.wikipedia.org/wiki/Estaci%C3%B3n_San_Agust%C3%ADn_(Metrocable_de_Caracas)) — *Colaboradores de Wikipedia*
- [Sistema Ferroviario Nacional (Venezuela)](https://es.wikipedia.org/wiki/Sistema_Ferroviario_Nacional_(Venezuela)) — *Colaboradores de Wikipedia*
- [List of cities in Venezuela by population](https://en.wikipedia.org/wiki/List_of_cities_in_Venezuela_by_population) — *Wikipedia contributors* (used to order the dataset)

### Wikidata — station coordinates and identifiers
Wikidata content is licensed under [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).

- [Wikidata Query Service](https://query.wikidata.org/) — SPARQL endpoint used
  to pull station coordinates and line memberships (102 stations).
- Per-stop QIDs are preserved in the `wikidata` field of `stops.json` files for
  traceability.

### OpenStreetMap — coordinates for stations not in Wikidata
Map data © OpenStreetMap contributors, licensed under
[ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/).

- [Overpass API](https://overpass-api.de/) — used to pull Valencia Metro
  stations, Mukumbarí cable car stations, and the few tagged Transbarca stops.

The whole repository inherits ODbL terms because of this OSM-derived
coordinate data. When redistributing, include the attribution
**"Map data © OpenStreetMap contributors, ODbL 1.0"** alongside the dataset's
own ODbL notice.

### Other reference sources
- [UrbanRail.Net — Maracaibo](https://www.urbanrail.net/am/mara/maracaibo.htm)
- [Metro Route Atlas — Barquisimeto](https://metrorouteatlas.net/cities/south_america/barquisimeto.html), [Maracay](https://metrorouteatlas.net/cities/south_america/maracay.html), [Mérida](https://metrorouteatlas.net/cities/south_america/merida.html)
- [BRT Data — Barquisimeto](https://brtdata.org/location/latin_america/venezuela/barquisimeto)
- [TROMERCA — official site](http://www.tromerca.gob.ve/)
- [IFE — Sistema Ferroviario](http://www.ife.gob.ve/Sistema_ferroviario/)

## Out of scope (for now)

- **Real-time data** (vehicle positions, arrival predictions).
- **Fare structures** — Venezuelan transit fares change frequently with inflation
  and are not amenable to static publication.
- **Bus routes** beyond the trunk BRT systems above. The fragmented
  por-puesto / carrito / autobús urbano networks in every Venezuelan city are
  out of scope; that would require a separate project with on-the-ground surveys.
- **Non-operational systems**, **planned extensions**, and **historical /
  closed systems**. See the **Scope: operational only** note at the top, and
  [CLAUDE.md](CLAUDE.md) for the policy.
