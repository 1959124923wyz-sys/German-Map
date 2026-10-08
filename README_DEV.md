# Germany Crime Map – Developer Guide

This directory powers the public Germany crime map. The current goal is to keep the map visually simple while the implementation remains modular enough to add or replace official data sources without editing unrelated code.

## Runtime architecture

```text
index.html                      thin page shell
css/map.css                     all map UI styling
js/app.js                       startup, orchestration and UI event wiring
js/core/config.js               metric labels, categories and palettes
js/core/geo-stats.js            shared geometry / quantile helpers
js/core/data-model.js           aggregation and case-matching logic
js/panels/state-panel.js        state drawer rendering / selection state
js/panels/area-panel.js         area data and national summary cards
js/panels/drawer-drag.js        reusable draggable panel behavior
js/layers/berlin-detail.js      Berlin-specific annual + rolling local layers
js/layers/county-layer.js       national county boundaries and choropleth
js/layers/state-layer.js        federal state borders and selection
js/layers/city-detail.js        generic registry-driven city detail loader
js/layers/recent-events.js      recent police-publication markers
js/layers/recent-events.js      rolling report markers and list rendering
data/city_layers.json           city layer + builder registry
data/*.geojson / *.json         generated runtime datasets
scripts/build_city_layers.py    registry-driven annual city build orchestrator
scripts/city_build_common.py    shared HTTP download and atomic deterministic GeoJSON I/O
scripts/*.py                    source adapters, updaters and validators
```

The public page should not contain large inline CSS or JavaScript blocks. New city detail layers should normally be added through `data/city_layers.json` and a generated GeoJSON file, not by adding city-specific branches to `index.html`.

## City/county seam topology (October 2026)

Annual city and county boundaries are both official, but they use different
cartographic scales. Overlaying them directly produces visible slivers and
overlapping colors around municipal borders.

- **Do not modify** `data/germany-counties.geojson`, official city GeoJSON,
  district IDs, crime statistics, or derived rates to cosmetically hide strips.
- `scripts/build_display_counties.py` constructs
  `data/germany-counties-display.geojson` as a **display-only** nationwide
  geometry. The high-resolution city union (or Dresden's official full-city polygon) becomes the canonical outer border,
  and the older coarse-county fringe is reallocated to the adjacent county.
- The map reads `germany-counties-display.geojson`, while the raw county
  source remains available for auditing or rebuilding.
- Current harmonized cities: **Berlin, München Stadt (AGS 09162), Hamburg,
  Leipzig, Chemnitz, Dresden**. Dresden's 61 police-atlas Stadtteile cover
  only part of the city (~267 km²) and must NOT be used as the outer municipal
  limit. Its full city boundary comes from the Landeshauptstadt Dresden official
  **KUEK5 Stadtgrenze** cadastral WFS (1:5,000, NodeId 111 / cls:L84);
  `scripts/build_dresden_city_boundary.py` stores it separately.
  The uncovered outer territory retains a subdued city-wide annual PKS fill,
  never a fabricated neighbourhood crime rate.
- City `county_ags` in `data/city_layers.json` is required for
  unambiguous county suppression. Name matching is unsafe for München Stadt
  versus Landkreis München.
- `scripts/validate_display_counties.py` checks that all 402 county IDs
  and properties remain unchanged, and the fine city geometry has no visible
  gaps/overlaps with neighbouring display counties. EPSG transformation and
  GeoJSON serialization allow only a very small area-relative tolerance.
- Build order: build/refresh official city data -> build display county
  geometry -> validate both layers -> run browser smoke -> deploy. Do not
  silently replace unsupported city boundaries in production.

This geometric harmonisation is a **cartographic rendering layer**, not a
change to police administrative districts or reported crime rates.

## Leaflet rendering and pointer-event invariant

The app sets `preferCanvas: true` for dense county/heatmap layers. However,
`newsPane` is stacked above states/counties, and a Canvas renderer in that
pane leaves a full-viewport pointer target EVEN AFTER markerGroup.clearLayers().
That canvas swallowed ordinary clicks on all 16 states after the first detail
drawer interaction. The permanent fix is one reusable `L.svg({pane:'newsPane'})`
renderer for all report circle markers, and a reusable SVG renderer for state
selection. Only actual marker SVG paths may intercept pointer events; blank
space must hit the state polygon below. The browser smoke test asserts the
topmost real `document.elementsFromPoint()` element is a state path and then
clicks several states with real mouse events. Do not return the report markers
to the default full-viewport Canvas renderer.

## State overview interaction invariant

Clicking a state at nationwide/state zoom opens its movable overview without
automatic pan/zoom. As long as state outlines render (below zoom 7.5), they
are interactive, including fractional zoom levels. Switching to a different
state must update an already-open drawer in place; closing the drawer must not
hide state hit targets or trigger animated map restoration when the map has not
moved. The Playwright smoke test exercises *real pointer clicks* through
open-switch-close-reopen cycles, not just synthetic Leaflet event dispatch.

## Data-layer hierarchy

The map deliberately separates spatial/data levels:

1. **National** – BKA PKS 2025, Kreis / kreisfreie Stadt.
2. **State** – state outline and aggregate view; used for hover/click navigation.
3. **City detail** – official Stadtteil / Stadtbezirk / Planungsraum data where a current compatible source exists.
4. **Recent reports** – rolling public police/news reports; supplemental only and never treated as total crime.

When a city detail layer is active, the underlying national polygon for that city should visually retreat so boundaries and fills never compete.

## Metric rules

Public metric keys are stable UI concepts:

```text
violence
serious_injury
robbery
sexual
homicide

property_total
burglary
bicycle_theft
vehicle_theft
theft_from_vehicle
```

A city may expose only the subset supported by its official source. If a local source uses a proxy rather than the same BKA definition, put the explanation in that metric's `note` field. Never silently present a proxy as an identical definition.

## Adding a city detail layer

1. Create a deterministic builder such as `scripts/build_<city>_local_2025.py`. Annual builders must not embed the current wall-clock time in output; identical source data should produce identical files. Use `city_build_common.py` for official downloads and atomic output writing; do not duplicate HTTP and JSON publishing boilerplate.
2. Generate a GeoJSON FeatureCollection into `data/<city>_local_2025.geojson`.
3. Each feature should have a stable `id`, Polygon/MultiPolygon geometry, `properties.name`, and metric objects such as:
   ```json
   "property_total": {
     "cases": 1234,
     "rate": 2456.7
   }
   ```
4. Register the layer in `data/city_layers.json` with:
   - `builder`
   - bounds
   - minimum zoom
   - source label
   - public metric → GeoJSON field mapping
5. Run:
   ```bash
   python scripts/build_city_layers.py --city <city-id>
   python scripts/validate_city_layers.py
   node --check js/app.js
   node --check js/layers/city-detail.js
   ```

The generic city loader will create the jump button, detect the city by map extent, render the choropleth, show tooltips, and populate the existing side panel.

## Files that should remain stable

- `index.html`: HTML structure only.
- `js/app.js`: orchestration only; map layers and area UI should stay in their own modules.
- `js/layers/county-layer.js`: nationwide geography and click/hover selection.
- `js/layers/state-layer.js`: federal state boundaries and selection.
- `js/panels/area-panel.js`: current-area and national-aggregate card.
- `js/layers/berlin-detail.js`: Berlin-only behavior.
- `js/layers/city-detail.js`: generic city detail behavior.
- `data/city_layers.json`: declarative city/data-builder registry.

Avoid putting source-specific scraping/parsing logic in browser JavaScript.

## Build and update responsibilities

- `build_*.py`: annual or reproducible official baseline datasets.
- `update_*.py`: rolling/recent datasets.
- `validate_*.py`: invariants and schema/data checks.
- one-off probes should not have permanent push-triggered workflows once the production builder exists.

The main workflow runs one registry-driven city build step, validates JavaScript and registry/data consistency, runs rolling-data validators/updaters, commits only changed generated data, and deploys Pages. Static annual builders are deterministic so a no-change rebuild does not create a new commit. A Playwright smoke workflow also tests national hover/click, state close/reopen, Berlin mode switching and Hamburg lazy detail loading.

## Data integrity principles

- Do not mix annual PKS data with rolling 90-day reports as if they have one denominator.
- `0` public reports does not mean `0` crimes.
- Crime counts are cases unless a source explicitly supplies victims.
- Prefer rates per 100,000 for national/city structural comparisons.
- Use official local geometry for city detail layers; do not approximate a district boundary from point density.
- If a source fails, preserve the last known good generated file rather than replacing it with empty data.

## Current city-detail sources

The registry is authoritative for Hamburg, Munich and the supported Saxony cities. Berlin remains the only dedicated city path because it combines two different local datasets: an annual violence layer and a rolling 90-day property layer with its own Planungsraum mapping.

## City expansion programme (batch-based)

**Do not put a researched candidate into `data/city_layers.json` prematurely.**
The expansion queue lives in `data/city_candidates.json` and is never
loaded by browser JavaScript. `scripts/validate_city_intake.py` guards
against unfinished candidates becoming live layers and checks legal/source
signoff before new publication. `scripts/test_city_expansion.py` tests
legacy layers and ordering without network access.

City release gates:

| Gate | What is required | Output |
| --- | --- | --- |
| G0 discovery | official statistical source and official geometry candidate identified | research queue |
| G1 source proof | reproducible primary URLs, year, statistical unit, source license, endpoint response | `source_probe` record |
| G2 semantics | each proposed metric maps to an *actual* official category, or an explicitly labeled proxy; official cases and appropriate population reference for published per-100,000 rates | documented mapping |
| G3 geometry | administrative keys/name join; valid WGS84 polygons; non-overlap/coverage; compare against raw municipality, resolve official boundary differences | candidate GeoJSON + QA |
| G4 validation | no fabricated rates, no unverified missing-as-zero, schema + geometry checks + real browser tests | approved candidate |
| G5 publication | change candidate phase to `published`, record `qa_passed` and `source_license_reviewed`, add exact builder/metrics to the live registry and choose stable seam priority | city appears on map |
| G6 monitoring | keep deterministic build, last-known-good fallback, license/source drift and regular checks | maintenance |

When a new city is approved, mark its live registry entry
`seam_enabled: true` and `seam_priority: <unique positive integer>`.
The county display seam builder reads *only approved live entries* from this
registry; candidates cannot alter the 402-county display geometry.
Partial coverage requires a **complete official municipality boundary** in
`boundary_file`; never union incomplete neighbourhoods and pretend it is
the city border. `data/germany-counties.geojson` and official city source
geometries remain immutable.

**Kiel first pilot — audited 2026-10-08:** The official 2025 PKS
Annex Table 10 contains all-offense counts by police reporting district.
The GovData example WFS call returns 0 rows, but the municipal **ArcGIS
REST MapServer layer 38** returns **31 polygon pieces for 30 distinct
official Stadtteile**. `scripts/build_kiel_staging.py` performs source
joins and validates all annual values without adding a live city layer.

2025 police **25,158 cases = 24,341 spatially assigned + 817 unassigned**
(762 'Tatort unbekannt' + 20 Hammer + 35 Kroog). The official geographic
district 'Gaarden-Süd und Kronsburg' is explicitly composed of those
two separately tabulated police reporting units; they are summed only
because the municipal polygon's own title identifies both subareas.
Unmapped cases remain outside the choropleth rather than guessed.

**Kiel count-only layer is now published (2026-10-08).** It is independent
of the existing violence/property-rate controls: `data/city_count_layers.json`
registers an explicitly titled absolute-case-count overlay, and
`js/layers/city-count-detail.js` implements a separate 2025 choropleth,
district 2016–2025 history popups, source attribution and a visible
817-case unlocated remainder. No population denominator or rate is invented;
the latest city open-data population CSV ends in 2023. Official municipal
GeoJSON is CC BY 4.0, with attribution in the map and source links.
The separate `scripts/validate_kiel_count_layer.py` validates source
cases, 30 district polygons and geometry; the full Playwright smoke
checks map load, legend, exit and switching back to Hamburg.
The national BKA rate dataset and its 402 Kreis polygons remain unchanged.
The `published` candidate phase must be paired with
`public_scope=supplementary_count_only` and never appears in the main
`city_layers.json` violence/theft registry.

Next source-probe priorities: **Bremen** has 2025 official tables for
22 local districts including robbery, injury, burglary, sexual offenses and
theft (Senat reply 2026-06-23), but note missing small-area assignment
and licensing. **Stuttgart** has an official CC BY 4.0 CSV for
city-district street/violent crime since 2008 and should be checked for
2025 field definitions, official district geometry and population.
Neither is promoted to a public polygon layer until its own data QA passes.


Run acceptance locally:

```bash
python scripts/validate_city_intake.py
python scripts/test_city_expansion.py
python scripts/build_display_counties.py
python scripts/validate_display_counties.py
python scripts/validate_city_layers.py
```

## Bremen 2025 official district categories: published as case COUNTS

Bremen Police/Senate 2025 district facts in Bürgerschaft Drucksache 21/1866
(22 tables, seven PKS offence-category rows each, calendar years 2024–2025).
Official GeoInformation Bremen WFS GML is joined from **19 Stadtteile and
87 Ortsteile**. Some PDF reporting areas combine one Stadtteil and multiple
harbor Ortsteile; preserve their official composite shapes. Source geometry
union is **318.454 km², no overlap or gaps**. Detailed category counts
were extracted with 2024→2025 delta verification. Published district
totals for 2025 include **69,710 recorded all offenses**, **33,720 thefts**,
**959 robberies**, **7,138 injuries**, **1,000 apartment burglaries**,
**960 sexual offences** and **2,379 narcotics cases**, with nulls excluded.
**These are mapped-area case counts, not complete citywide PKS totals or rates.**
A `-` token in official PDF is represented by null, not 0.
No demographic denominator is invented; official categories are kept separate
from BKA national violence/property-rate map.

Public read path: `data/city_count_layers.json` +
`data/bremen_local_counts_2025.geojson`.
Builder `scripts/build_bremen_geometry_staging.py` then
`scripts/build_bremen_category_layer.py --release-count-only`.
Validation `scripts/validate_bremen_category_layer.py` and browser smoke
check the count semantics, toggle, category selector, map hover and close.
The PDF itself is never republished; official facts are independently
re-expressed, with link to original parliamentary source.

## Stuttgart 2025 public-space violent crime district map

Primary source: Baden-Württemberg Landtag official Interior Ministry
reply `Drucksache 17/10292` pp.3–5, reporting **Gewaltkriminalität im
öffentlichen Raum** (not all-settings violent crime) and its robbery /
dangerous-or-serious injury subcategories, all 23 Stuttgart Stadtbezirke.
The independently verified official city counts are **1636** public-space
violence, **358** robbery and **1243** serious injury; exact sum of district
counts **1577 / 350 / 1194**. City minus district residual
**59 / 8 / 49** is deliberately NOT drawn on a polygon. No per-capita rate
is computed and the nationwide violence/property modes are never changed.
Stuttgart's original municipal Stadtmessungsamt GPKG polygons cover the
whole 207.403 km² city with zero overlap and the official municipal
outline. The map credits the city government (CC BY 4.0) and links to
the Landtag original.

Only this pipeline writes the public feature collection:
```sh
python scripts/build_stuttgart_duesseldorf_geometry.py
python scripts/build_stuttgart_public_violence_2025.py --output data/stuttgart_public_violence_2025.geojson --release-count-only
python scripts/validate_stuttgart_public_violence.py
```
The separate city intake gate and browser smoke test verify scientific
scope, original district totals, strict null rates, real popup interaction
and navigation among Stuttgart/Bremen/Kiel without cross-layer collisions.

## Düsseldorf 2025 ten-Stadtbezirk total criminal case counts

Official Düsseldorf Police presentation to Bezirksvertretung 6 on
2026-06-10, **slide 2 `Gesamtkriminalität aller Stadtbezirke`**.
Original official OParl PDF:
https://ris-oparl.itk-rheinland.de/Oparl/bodies/0015/downloadfiles/00589618.pdf
(HTTP server also accessible). The source includes all **10** Stadtbezirk
columns and citywide PP total for calendar years **2022–2025**, so a
genuine geographic ten-district map is possible. For 2025, the
district case counts are:
22,396 / 5,062 / 13,314 / 3,499 / 4,259 /
5,097 / 2,490 / 4,166 / 6,438 / 1,503.
**Sum 68,224; PP city total 69,522; official city/district
difference 1,298.** That difference is unlocated and never assigned to
district shapes. These are all-offense **absolute cases** (not rates, not
violence/robbery subset), independent of the nationwide rate display.

Official City of Düsseldorf 2025 administrative WGS84 GeoJSON has
10 Stadtbezirk shapes and 217.407 km², zero overlap after documented
zero-area self-intersection repair. Candidate geometry produced by
`scripts/build_stuttgart_duesseldorf_geometry.py`.
Public builder:
```sh
python scripts/build_stuttgart_duesseldorf_geometry.py
python scripts/build_duesseldorf_offenses_2025.py --output data/duesseldorf_total_cases_2025.geojson --release-count-only
python scripts/validate_duesseldorf_offenses_2025.py
```
Metadata identifies 2022–2025 original counts and municipality-minus-area
differences each year. Page links to source and official boundaries.
Dedicated browser tests cover popups, no fake rate, other city overlays,
state/county map and all previously fixed click interactions.

## Düsseldorf BV6 local drill-down, 2025 eight categories

Original Düsseldorf Polizeipräsidium `BV 6` PKS presentation,
10 June 2026, **PDF pp.4–11**, contains the original 2022–2025
individual crime case tables for *Lichtenbroich (061), Unterrath (062),
Rath (063), Mörsenbroich (064)*. The eight local metrics are
total offenses, street crime, street robbery, street injury,
theft on/from motor vehicles, bicycle theft, pickpocketing and
residential burglary. The **2025 four-Stadtteil total 5,097 cases**
is crosschecked *independently* against the existing official
ten-Stadtbezirk PKS table (Stadtbezirk 6 = 5,097) for **all four years**.

Official City of Düsseldorf 26 March 2025 WGS84 Stadtteil polygons (50)
are published by Amt für Statistik und Wahlen under **Datenlizenz
Deutschland Zero 2.0**. Four geometries together cover 19.678 km²
with zero internal overlap and only 405.3 m² symmetric difference from
the official 2025 Stadtbezirk-6 geography (0.0021% of its area).
All local values are absolute cases, **never per-capita rates**.
Criminal category counts from BV6 must NOT be projected into
Düsseldorf's other nine districts. Source PDF pages and true spatial
coverage are cited directly in the panel.

The drill-down is nested under the existing public
`杜塞尔多夫·全部案件` panel: switch 10 administrative districts
to 4 officially reported Stadtteile, select 8 original crime classes,
and return to 10 districts. Scripts:
```sh
python scripts/build_stuttgart_duesseldorf_geometry.py
python scripts/build_duesseldorf_bv6_local.py --output data/duesseldorf_bv6_local_2025.geojson --release-count-only
python scripts/validate_duesseldorf_bv6_local.py
```
Existing nationwide rates and city overlays remain entirely separate.
