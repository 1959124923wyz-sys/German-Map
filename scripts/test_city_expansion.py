#!/usr/bin/env python3
"""Network-free test for independent city count and rate release gates."""
from __future__ import annotations
import copy,json
from pathlib import Path
from build_display_counties import registered_seam_sources
from validate_city_intake import validate

ROOT=Path(__file__).resolve().parents[1]


def assert_rejected(intake,live,count,needle):
    try:
        validate(intake,live,count)
    except ValueError as exc:
        if needle not in str(exc):
            raise AssertionError(f"expected {needle!r}; got {exc!s}") from exc
    else:
        raise AssertionError(f"unsafe admission passed without {needle}")


def main():
    intake=json.loads((ROOT/"data/city_candidates.json").read_text(encoding="utf-8"))
    live=json.loads((ROOT/"data/city_layers.json").read_text(encoding="utf-8"))
    counts=json.loads((ROOT/"data/city_count_layers.json").read_text(encoding="utf-8"))
    result=validate(intake,live,counts)
    sources=registered_seam_sources()
    expected=["11000","09162","02000","14713","14511","14612"]
    assert list(sources)==expected,(list(sources),expected)
    assert sources["14612"]=="data/dresden-city-boundary.geojson"
    assert result["active_rate"]==5 and result["active_count"]==2 and result["candidates"]>=10
    # Kiel is NOT a violence-rate city and can never be inserted twice.
    unauthorized=copy.deepcopy(live)
    unauthorized["cities"].append({"id":"kiel","metrics":{"violence":{"field":"crime_total"}}})
    assert_rejected(intake,unauthorized,counts,"city registered twice")
    # No repurposing an offense count as a violent crime metric.
    forged=copy.deepcopy(intake)
    next(c for c in forged["candidates"] if c["id"]=="kiel")["metric_alignment"]="incompatible"
    assert_rejected(forged,live,counts,"incompatible metrics")
    forged=copy.deepcopy(intake)
    next(c for c in forged["candidates"] if c["id"]=="kiel")["phase"]="source_probe"
    assert_rejected(forged,live,counts,"unreleased candidate")
    forged_counts=copy.deepcopy(counts)
    forged_counts["layers"][0]["metric"]="violence"
    assert_rejected(intake,live,forged_counts,"not an explicitly count-only")
    forged_bremen=copy.deepcopy(counts)
    next(x for x in forged_bremen["layers"] if x["id"]=="bremen")["metric"]="violence"
    assert_rejected(intake,live,forged_bremen,"count categories must not claim a crime rate")
    print("[city-expansion] PASS: six seams preserved, 5 rate cities, Kiel + Bremen separate count-only, no mode contamination")


if __name__=="__main__":main()
