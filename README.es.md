# Transporte Público de Venezuela — datos abiertos

*Leer esto en otros idiomas: [English](README.md) · **Español***

Datos estáticos del transporte público de Venezuela, en formatos que cualquier
desarrollador puede usar directamente en una web, una herramienta GIS o un
planificador de viajes.

**Alcance: solo lo operativo.** Venezuela tiene muchos proyectos de transporte
en construcción indefinida. Para mantener honestos los datos, este conjunto
cubre únicamente paradas y líneas actualmente en servicio activo de pasajeros.
Los tramos planificados, en construcción, suspendidos y cerrados quedan
excluidos — y se mencionan en el `sources.md` de cada sistema.

| Ciudad | Sistema | Tipo | Paradas | Coords |
|---|---|---|---:|---:|
| Caracas     | [Metro de Caracas](data/caracas/metro/) | metro | 47 | 47/47 |
| Caracas     | [Metrobús de Caracas](data/caracas/metrobus/) | bus (alimentador) | 469 | 469/469 |
| Caracas     | [Metrocable San Agustín](data/caracas/metrocable-sanagustin/) | teleférico urbano | 3 | 3/3 |
| Caracas     | [Sistema Ferroviario (Caracas-Cúa)](data/caracas/sistema-ferroviario/) | tren de cercanías | 4 | 4/4 |
| Caracas     | [Teleférico Warairarepano](data/caracas/teleferico-avila/) | teleférico | 2 | 2/2 |
| Maracaibo   | [Metro de Maracaibo](data/maracaibo/metro/) | metro ligero | 6 | 6/6 |
| Valencia    | [Metro de Valencia](data/valencia/metro/) | metro | 9 | 9/9 |
| Barquisimeto| [Transbarca](data/barquisimeto/transbarca/) | BRT | 12* | 1/12 |
| Maracay     | [TransMaracay](data/maracay/transmaracay/) | BRT | 2* | 0/2 |
| Mérida      | [Mukumbarí (teleférico)](data/merida/teleferico/) | teleférico | 5 | 5/5 |
| Los Teques  | [Metro de Los Teques](data/los-teques/metro/) | metro | 3 | 3/3 |

**Total**: 11 sistemas, 562 paradas, 549 con coordenadas (98 %). El Metrobús
de Caracas por sí solo aporta 469 — es una red de buses alimentadores con
marca propia operada por C.A. Metro de Caracas, ubicada entre el bus urbano
convencional y el BRT pleno (vea [su sources.md](data/caracas/metrobus/sources.md)
para la salvedad de clasificación).

*Las entradas de Barquisimeto y Maracay (BRT) están incompletas — solo incluyen
los terminales y las paradas con nombre principal. Wikipedia describe ~52 y ~13
paradas respectivamente, pero no las enumera; la cobertura en OpenStreetMap es
escasa. Se aceptan contribuciones.

## Qué hay aquí

```
data/<ciudad>/<sistema>/
  system.json   # el sistema: operador, tipo, fecha de apertura, estado
  lines.json    # líneas: id, nombre, color, lista ordenada de ids de paradas
  stops.json    # paradas: id, nombre, lat/lon, lines[], estado
  sources.md    # procedencia y notas

exports/
  geojson/<id-sistema>-stops.geojson   # FeatureCollection de Point
  geojson/<id-sistema>-lines.geojson   # FeatureCollection de LineString
  gtfs/<id-sistema>.zip                # Feed GTFS (con horario sintético)

scripts/
  extract_from_wikidata.py   # Vuelve a obtener coordenadas desde Wikidata (SPARQL)
  build_exports.py           # Regenera exports/ a partir de data/
  verify.py                  # Valida los archivos canónicos

raw/
  wikidata_stations.json     # Volcado SPARQL de Wikidata usado como semilla
```

## Formatos

Los datos **canónicos** son JSON editables a mano en `data/`. Son la fuente de
verdad — edítelos ahí y luego ejecute `python3 scripts/build_exports.py` para
regenerar los formatos derivados.

El **GeoJSON** en `exports/geojson/` sirve para Leaflet, Mapbox, QGIS, etc. Las
paradas son features de tipo Point; las líneas son features de tipo LineString
trazadas conectando las paradas de cada línea en orden (así que son
aproximadas — segmentos rectos, no la geometría real de la vía;
seguimiento en [#1](https://github.com/xuruata/venezuela-public-transportation/issues/1)).

El **GTFS** en `exports/gtfs/` sigue la [General Transit Feed Specification][gtfs]
y se puede consumir con cualquier herramienta compatible con GTFS (importación
a Transit Land de Google Maps, OpenTripPlanner, Transitland, etc.).

  > **⚠ Los horarios son sintéticos.** Los operadores venezolanos rara vez
  > publican tablas de horarios, así que los feeds GTFS usan `frequencies.txt`
  > con un valor de marcador de tipo "cada N minutos, de 05:00 a 23:00, días
  > laborables". **La topología de las rutas es real; los horarios no.**

[gtfs]: https://gtfs.org/

## Campo `status`

Cada parada y línea lleva un campo `status: "operational"`. Es el único valor
permitido — el conjunto de datos es operativo-únicamente por política (ver
[CLAUDE.md](CLAUDE.md) para la justificación). El campo se mantiene para que los
consumidores puedan verificarlo defensivamente si la política llegara a
flexibilizarse.

## Procedencia de las coordenadas

| Fuente | Paradas aprox. |
|---|---:|
| OpenStreetMap (Overpass) | 489 |
| Wikidata (SPARQL `wdt:P625`) | 60 |
| Faltantes | 13 (todas son paradas BRT) |

OSM pasó a ser la fuente dominante al incorporar el Metrobús de Caracas — sus
469 paradas provienen íntegramente de OSM. Para los sistemas ferroviarios,
Wikidata sigue siendo la fuente primaria.

El campo `wikidata` en cada parada, cuando existe, es su QID de Wikidata — útil
para volver a obtener actualizaciones futuras. Ver [CLAUDE.md](CLAUDE.md) para
las reglas generales de selección de fuentes.

## Publicaciones y versionado

Las publicaciones etiquetadas usan [CalVer](https://calver.org/) —
`vAAAA.MM.DD` (por ejemplo, `v2026.05.25`). Cada publicación describe una
instantánea del transporte venezolano en esa fecha, lo cual es más
significativo que un número semver para un dataset que sigue
infraestructura del mundo real. Las republicaciones del mismo día reciben
un sufijo `.N` (`v2026.05.25.1`).

`main` siempre apunta a los datos más recientes. Las etiquetas fijan una
fecha específica si un consumidor downstream necesita una referencia
estable. La CI adjunta cada GeoJSON y GTFS a su publicación, de modo que
los consumidores pueden bajar un archivo versionado directamente:

```
https://github.com/xuruata/venezuela-public-transportation/releases/download/vAAAA.MM.DD/caracas-metro.zip
```

## Verificar y actualizar

```bash
python3 scripts/verify.py        # valida estructura JSON, referencias de líneas, bbox, política de estado
python3 scripts/build_exports.py # regenera GeoJSON + GTFS
python3 scripts/compare_osm.py   # compara nuestras coordenadas contra OpenStreetMap actualizado
```

## Cómo contribuir

Las mejoras de mayor impacto:

1. **Completar las listas de paradas de los BRT** — Transbarca (Barquisimeto) y
   TransMaracay. Wikipedia describe los sistemas en prosa; las listas completas
   y ordenadas de estaciones no están enumeradas en ningún lugar que haya
   encontrado y la cobertura de OSM es escasa.
2. **Agregar coordenadas para las 13 paradas que no las tienen** — todas son
   paradas BRT.
3. **Re-verificar el estado operativo periódicamente.** Cuando se confirme que
   un sistema o parada está cerrado o suspendido, elimínelo de los archivos de
   datos; documente la eliminación en el mensaje del commit y en el
   `sources.md` del sistema. Cuando una línea "planificada" estancada por
   mucho tiempo finalmente abra, agréguela.

Flujo de trabajo:
1. Edite `data/<ciudad>/<sistema>/{system,lines,stops}.json`.
2. Ejecute `python3 scripts/verify.py` — debe pasar (hace cumplir la política
   de solo-operativo).
3. Ejecute `python3 scripts/build_exports.py` para regenerar los exports.
4. Abra un pull request.

Para ediciones más profundas — agregar un sistema nuevo, refrescar desde
Wikidata o OpenStreetMap — vea [CLAUDE.md](CLAUDE.md).

## Licencia

Este repositorio — datos, esquema, exports y scripts — se publica bajo la
[Open Database License (ODbL) v1.0](LICENSE). Al redistribuir este conjunto
de datos o cualquier base de datos derivada, incluya el aviso:

> "Contiene información de la base de datos venezuela-public-transportation,
> disponible bajo la Open Database License (ODbL)."

Se eligió ODbL porque el conjunto de datos incorpora coordenadas provenientes
de OpenStreetMap, cuyos términos ODbL requieren compartir-igual para las bases
de datos derivadas. Licenciar todo el repositorio bajo ODbL mantiene todo
internamente consistente y satisface los requisitos de OSM automáticamente.

## Atribuciones

Este conjunto de datos no existiría sin estos proyectos previos. Al
redistribuir datos derivados de ellos, por favor atribuya apropiadamente.

### Wikipedia — descripción de sistemas, topología de líneas, nombres de estaciones, fechas de apertura
El contenido de Wikipedia está licenciado bajo [CC BY-SA](https://creativecommons.org/licenses/by-sa/4.0/).

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

### Wikidata — coordenadas e identificadores de estaciones
El contenido de Wikidata está licenciado bajo [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).

- [Wikidata Query Service](https://query.wikidata.org/) — endpoint SPARQL usado
  para obtener coordenadas de estaciones y pertenencia a líneas (102
  estaciones).
- Los QID de cada parada se conservan en el campo `wikidata` de los archivos
  `stops.json` para trazabilidad.

### OpenStreetMap — coordenadas para estaciones no presentes en Wikidata
Datos cartográficos © contribuidores de OpenStreetMap, licenciados bajo
[ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/).

- [Overpass API](https://overpass-api.de/) — usado para obtener las estaciones
  del Metro de Valencia, las estaciones del teleférico Mukumbarí, las pocas
  paradas etiquetadas de Transbarca, y la red completa del Metrobús de Caracas
  (35 rutas / 469 paradas, etiquetadas `network=Metrobus Caracas`).

Todo el repositorio hereda los términos ODbL por estos datos de coordenadas
provenientes de OSM. Al redistribuir, incluya la atribución
**"Datos cartográficos © contribuidores de OpenStreetMap, ODbL 1.0"** junto con
el aviso ODbL propio del conjunto de datos.

### Otras fuentes de referencia
- [UrbanRail.Net — Maracaibo](https://www.urbanrail.net/am/mara/maracaibo.htm)
- [Metro Route Atlas — Barquisimeto](https://metrorouteatlas.net/cities/south_america/barquisimeto.html), [Maracay](https://metrorouteatlas.net/cities/south_america/maracay.html), [Mérida](https://metrorouteatlas.net/cities/south_america/merida.html)
- [BRT Data — Barquisimeto](https://brtdata.org/location/latin_america/venezuela/barquisimeto)
- [TROMERCA — sitio oficial](http://www.tromerca.gob.ve/)
- [IFE — Sistema Ferroviario](http://www.ife.gob.ve/Sistema_ferroviario/)

## Fuera del alcance (por ahora)

- **Datos en tiempo real** (posiciones de vehículos, predicciones de llegada).
- **Estructuras tarifarias** — las tarifas del transporte venezolano cambian
  con frecuencia debido a la inflación y no son aptas para publicación
  estática.
- **Rutas de autobús** más allá de los sistemas BRT troncales y la red
  Metrobús de Caracas (operada por una agencia con marca propia) listados
  arriba. Las redes fragmentadas de por puesto / carrito / autobús urbano
  de cada ciudad venezolana están fuera del alcance; eso requeriría un
  proyecto aparte con relevamientos en el terreno.
- **Sistemas no operativos**, **extensiones planificadas** y **sistemas
  históricos / cerrados**. Vea la nota **Alcance: solo lo operativo** al
  principio, y [CLAUDE.md](CLAUDE.md) para la política.
