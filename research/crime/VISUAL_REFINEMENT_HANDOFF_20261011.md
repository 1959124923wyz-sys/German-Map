# Main atlas visual and interaction handoff — 2026-10-11

## Goal and preservation
The nationwide front page should feel like a restrained mapping application, while state and county selections should reveal genuinely useful preexisting data without visual clutter. This is a **presentation/interaction** batch: no crime sources, numeric facts, PKS semantic definitions, city atlas manifests, or EUDA results are changed.

## UX delivered
- One restrained on-map label hints at state/county interaction without blocking Leaflet pointer events. The label disappears whenever the state drawer opens, leaving maximum room for the primary map and already-visible choropleth legend.
- Typography, surfaces, spacing, focus outlines, nav buttons, cards, legend, and map caption adjusted in `css/visual-refinement.css`. An isolated stylesheet avoids compounding scattered append-only rules in the 200+ line crime stylesheet.
- State drawer design places the selected rate/case count in the visual hierarchy. Real 16 state geometries populate a native “快速切换州” select; explicit selecting a different state pans/zooms with bounds and refreshes existing PKS statistics. Ordinary state polygon clicks remain nonzooming.
- State city source archive remains autoexpanded only where real manifests provide a city, while statewide top five county stats and latest police reports are hidden behind separate disclosures. Switching states resets expanded supplementary drawers rather than displaying another state's stale scrolled content. Closing the state drawer restores prior map view under existing rules.
- County source dossier stays available after an explicit pinned county selection but is represented by a slim summary until the user chooses to reveal 10 original rate/case count/change metrics. Reopening or switching counties clears stale expanded content, and the original accessible two-tab component continues to work.

## Validation
- `scripts/smoke_test_ui.py` asserts all 16 source-state dropdown options, state-jump navigation, no autozoom on ordinary state clicks, and that secondary drawers reset.
- `tests/smoke_county_dossier.py` runs Chromium desktop and 390px mobile, checks that the county dossier is initially closed, expands it and exercises original 10 metrics, then checks mode switching/national resets.
- Do not merge until the full crime map UI workflow and unrelated topic browser checks pass; preserve map screenshots for regressions.

## Known limits
- The data is still 2025 police-recorded crime, with time-windowed news and separate city-local count-only layers; the refinement does not resolve differences in those statistical denominators.
- Native dropdown is scoped to the main national crime atlas, not intended to replace topic-specific region controls.
