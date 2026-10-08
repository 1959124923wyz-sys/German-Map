#!/usr/bin/env python3
"""Network-free regression of the declarative seam and city-admission gates."""
from __future__ import annotations
import copy
import json
from pathlib import Path

from build_display_counties import registered_seam_sources
from validate_city_intake import validate

ROOT=Path(__file__).resolve().parents[1]


def main():
    intake=json.loads((ROOT/"data/city_candidates.json").read_text(encoding="utf-8"))
    live=json.loads((ROOT/"data/city_layers.json").read_text(encoding="utf-8"))
    result=validate(intake,live)
    expected=["11000","09162","02000","14713","14511","14612"]
    sources=registered_seam_sources()
    assert list(sources)==expected,(list(sources),expected)
    assert sources["14612"]=="data/dresden-city-boundary.geojson"
    assert result["active"]==5 and result["candidates"]>=10
    # Fail closed when a candidate is added to the LIVE registry prematurely.
    unauthorized=copy.deepcopy(live)
    unauthorized["cities"].append({"id":"kiel","metrics":{"violence":{"field":"crime_total"}}})
    try:
        validate(intake,unauthorized)
        raise AssertionError("unapproved Kiel crime_total leaked into the live map")
    except ValueError as exc:
        assert "unreleased candidate" in str(exc),str(exc)
    # A generic total-offense metric is never a substitute for violent crime.
    forged=copy.deepcopy(intake)
    kiel=next(c for c in forged["candidates"] if c["id"]=="kiel")
    kiel["phase"]="published"
    kiel["metric_alignment"]="incompatible"
    try:
        validate(forged,unauthorized)
        raise AssertionError("incompatible Kiel source was published")
    except ValueError as exc:
        assert "incompatible metrics" in str(exc),str(exc)
    print("[city-expansion] PASS: deterministic seam order, five existing cities, unpublished candidate isolation, category gate")


if __name__=="__main__":
    main()
