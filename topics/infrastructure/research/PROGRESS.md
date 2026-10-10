# Infrastructure research handoff · R8 (2026-10-10)

## Branch & status
- Branch: `feature/infrastructure-map-phase1`; draft review: https://github.com/1959124923wyz-sys/German-Map/pull/38
- Current deployed main: **unchanged** by this research. DO NOT merge automatically.
- Saved pilot: 16-state railway (track and station)/fiber/SAIDI composite (2025/2024), known limitations as in ../README.md.
- Sourced project events: 22 across all 16 federal states; source counts and last updates in `../data/events.json`.
- Six-state TLI-IV/V motorway bridge comparison: stored separately from DIN condition scores in `../data/condition_evidence.json`.

## Reproducibility and QA
- `node topics/infrastructure/tests/validate_data.cjs`
- `node --check topics/infrastructure/topic.js`
- `python topics/infrastructure/tests/smoke_browser.py` (needs local server and Playwright)
- Confirmed GitHub Actions real-browser pass: https://github.com/1959124923wyz-sys/German-Map/actions/runs/38035609405.
- At prior checkpoint old finance/immigration smoke checks failed because nav expectations had seven links. Branch updated those tests, integration recheck pending.
- Independent bridge geodata is third-party ArcGIS geocoded subset, **not** complete BASt universe; any national-looking 16-state metrics derived from it must be marked exploratory and never silently substituted into the composite.

## Current research agenda
1. Attempt actual ArcGIS 2025-09 BASt-derived geocoded feature export; verify object ID counts, state mapping, missing condition/area, count- and area-weighted poor shares. Preserve source snapshot, API endpoint, query date, sample coverage and any extraction failure logs.
2. In parallel expand homogeneous federal-state road ZEB official primary evidence (year, road responsibility and condition threshold).
3. Enrich event archive with infrastructure-specific public sources and status updates; do not treat representative density as exhaustive incident rates.
4. Commit each independent artifact + update this handoff. Do not publish a final condition rank until official complete bridge stock and road comparison tested.

## Output contract
Every record includes `source_url`, `data_year`, `geographical_scope`, `measurement_definition`, `comparability`, `verified_status`, and explicit null for missing. Keep historical reports and live status separate.

## R9 checkpoint (2026-10-10) · verified successful GitHub writes
- **Major acquisition:** completed ArcGIS API extraction of **52,553** unique geocoded BASt-derived features (2025-09 publisher snapshot), **51,707** linked to all 16 states, **846** missing state codes. Data is committed to `research/candidate_bridge_arcgis_2025.json`, with reproduction script in `research/scripts/import_bridge_arcgis.py`; successful acquisition run: https://github.com/1959124923wyz-sys/German-Map/actions/runs/38036429551.
- **Critical caution:** only **9,969 / 51,707** state-assigned geocoded records have valid 1.0–4.0 DIN status grades (19.3%). State-level condition coverage ranges about 13%–24%; published bridge-state poor-condition rates are currently NOT representative and must not be visualized as full-state comparisons.
- Improved API request batching to 120 IDs after 350-ID requests returned HTTP 404; added strict state-code parsing and missing-state preservation. Further diagnostic run is underway to determine why grades are missing, including publisher `teil_der_bast_liste` field.
- **New confirmed source:** Saxony official Nov 2024 bridge-condition table `https://www.lasuv.sachsen.de/download/Bauwerksliste_Tabelle_Zustand_Stand_20241121.pdf` p.3; 69/952 federal B-road bridge substructures (7.25%) vs 164/1688 state-road substructures (9.72%) DIN≥3.0. Store six condition-band counts as verified originals; these are *not* municipal or motorway inventory.
- Berlin March 2026 masterplan, June 2025 baseline: 1,047 state-managed bridge structures, 19% good/very good, 175 replacements and 125 major repairs planned over 15 years, projected €1.84 billion (not disbursed). Bavaria federal-road bridge poor status in 2024 amounted to 10% of inspected bridge *area* (8.8% 3.0–3.4, 1.2% 3.5–4.0); Brandenburg 66 bridges with stress-corrosion-sensitive tendons as of Dec 2025 (not 66 structurally unsafe). Saved to `data/condition_evidence.json`.
- **Nine additional primary-source event leads** stored to `research/events_candidates_R9.json` with `map_ready:false`, exact reported-date status and source URLs. Not yet merged into selected 22 records or map; avoid double-counting.
- Current older 16-state pilot score unchanged, and main branch untouched.

### Outstanding
1. Compare ArcGIS publisher selection condition fields against official BASt full bridge table; do not compute normative 16-state bridge score using the 19.3% rated subset.
2. Discover ZEB roads in missing states; process and retain old 2020/21 inspection years where only old official data exist.
3. Ensure final bridge diagnostic GitHub Actions run succeeds and has committed updated candidate snapshot.
4. Review 9 candidate events for point precision, duplicate IDs and post-publication updates before promoting from candidate to visible event archive.

## R10 correction (2026-10-10) · ArcGIS source digit encoding fully investigated
- **Supersedes the R9 provisional “only 19.3% bridges have valid grade” finding.** All 51,707 state-assignable records actually possess a numeric condition grade. The apparent invalid/missing 41,738 grades are ArcGIS raw integer encodings of tenths (e.g. `zn=23` provisionally means official DIN `2.3`), not null inspections. A guarded `/10` decoding has run successfully across the full 52,553-feature query, with no unknown out-of-range grade value, and the decoded 16-state candidate has been committed. Provenance: https://github.com/1959124923wyz-sys/German-Map/actions/runs/38036911519.
- Candidate examples: Bavaria poor bridge **area** 10.346% vs 2024 official Bundestag **area** 10.0% (8.8+1.2); these are *independently close but not sufficient validation* because year, sample, and missing geocodes differ. Map's original composite unchanged; candidate retains `not_for_score:true`, `do_not_use_for_choropleth:true`.
- Berlin state-managed 2025 official master plan additionally reports 7% DIN≥3.0, 27% DIN 2.5–2.9, 47% DIN 2.0–2.4, 19% DIN≤1.9 among 1,047 bridge structures; added as independent source evidence. Scope differs from ArcGIS federal-road bridges.
- **Pending validation**: compare corrected `zn` numerics with ArcGIS `zustandsnotenklasse` (grade band) to establish robust encoding proof; check ArcGIS geocoded share against official BASt national stock before interpreting any cross-state bridge conditions as general bridge quality.

## R11 checkpoint (2026-10-10 16:48 Asia/Singapore) · post-timeout independently confirmed
- GitHub workflow **successful**: https://github.com/1959124923wyz-sys/German-Map/actions/runs/38037228372. The branch now contains `research/candidate_bridge_arcgis_2025.json` (16-state) and `research/candidate_bridge_counties_arcgis_2025.json` (raw county-label groupings). Confirmed live through the GitHub connector *after* the prior message-transfer timeout.
- **52,553 unique source records**, **51,707** state-assigned, **846** without state code. All state-assigned records have a decoded 1.0–4.0 condition score. Raw integers representing tenths are verified via the source-supplied `zustandsnotenklasse` six-band labels: 3,508 in 1.0–1.4, 8,392 in 1.5–1.9, 25,514 in 2.0–2.4, 12,046 in 2.5–2.9, 2,046 in 3.0–3.4 and 201 in 3.5–4.0. These total exactly 51,707.
- **County-level candidate**: 438 distinct `(state code, ArcGIS kreis source label)` groups with 51,664 features. A further 43 state-assigned features have missing county field, split NI 19, ST 3, HE 10, TH 3, NW 3 and RP 5; county and noncounty counts reconcile to 51,707. There are 53 low-denominator source-label groups (less than 20 bridge features). **438 are source label groups, NOT 438 recognized official administrative counties**. No AGS mapping or administrative polygon join has been completed. Never directly color all official counties with these labels.
- The 16-state candidate includes both count and area poor shares but still explicitly `do_not_use_for_choropleth: true`, pending checking full official BASt bridge universe, geocoded selection and source date. Pilot index remains unchanged.
- Additional primary-source research committed: Saxony 2024 bridge six-band table, Berlin 2025 1,047 state-maintained bridge plan, 2024 Bavaria official area poor share, Brandenburg sensitive tendon materials, and Mecklenburgische Seenplatte historical road/bridge tables. Nine other incident source leads are retained in `research/events_candidates_R9.json` only (not yet visible on map).
- PR #38 is OPEN DRAFT; the main branch has not been merged or modified as part of this research.
- **Next**: (1) check official BASt stock and county AGS crosswalk; (2) cautiously promote validated candidates; (3) refresh old project event statuses; (4) run cross-topic tests on up-to-date main before merge. All work should be confined to branch `feature/infrastructure-map-phase1`.
