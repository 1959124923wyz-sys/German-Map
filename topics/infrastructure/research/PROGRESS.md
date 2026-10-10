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
