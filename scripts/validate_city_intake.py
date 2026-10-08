#!/usr/bin/env python3
"""Prevent unverified city candidates from accidentally becoming live map layers.

Candidate research is NOT a publication authorisation. Only a documented
source->metric->geometry reconciliation can promote a new city.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CANDIDATES=ROOT/"data/city_candidates.json"
LIVE=ROOT/"data/city_layers.json"
PHASES={"research","source_probe","join_ready","published","blocked"}
METRIC={"unverified","incompatible","compatible"}
PUBLIC_METRICS={"violence","serious_injury","robbery","sexual","homicide",
                "property_total","burglary","bicycle_theft","vehicle_theft","theft_from_vehicle"}


def validate(intake:dict,live:dict)->dict:
    if intake.get("schema_version")!=1:
        raise ValueError("unsupported city_candidates schema")
    candidates=intake.get("candidates")
    if not isinstance(candidates,list):
        raise ValueError("candidate list missing")
    active={c["id"]:c for c in live.get("cities",[])}
    baseline=set(intake.get("baseline_published_ids",[]))
    if not baseline.issubset(active):
        raise ValueError("baseline active cities were removed without migration")
    seen=set()
    phases={}
    for c in candidates:
        cid=c.get("id")
        if not isinstance(cid,str) or not cid or cid in seen:
            raise ValueError(f"invalid/duplicate candidate {cid!r}")
        seen.add(cid)
        phase=c.get("phase")
        if phase not in PHASES:
            raise ValueError(f"{cid}: unsupported phase {phase!r}")
        if c.get("metric_alignment") not in METRIC:
            raise ValueError(f"{cid}: metric_alignment missing or invalid")
        priority=c.get("priority")
        if not isinstance(priority,int) or priority<1:
            raise ValueError(f"{cid}: positive integer priority required")
        for kind in ("crime_source","geometry_source"):
            source=c.get(kind)
            if source and (not isinstance(source,dict) or
                not str(source.get("url","")).startswith("https://")):
                raise ValueError(f"{cid}: {kind} must have an HTTPS evidence URL")
        if phase=="published":
            if cid not in active:
                raise ValueError(f"{cid}: published candidate not in live city registry")
            if c.get("metric_alignment")!="compatible":
                raise ValueError(f"{cid}: incompatible metrics cannot publish")
            for key in ("crime_source","geometry_source"):
                if not c.get(key):
                    raise ValueError(f"{cid}: published city requires {key}")
            if not c.get("qa_passed") or not c.get("source_license_reviewed"):
                raise ValueError(f"{cid}: missing QA and license signoff")
            declared=set(active[cid].get("metrics",{}))
            if not declared or not declared.issubset(PUBLIC_METRICS):
                raise ValueError(f"{cid}: invalid published metric keys")
        elif cid in active:
            raise ValueError(f"{cid}: unreleased candidate leaked into live map")
        phases[phase]=phases.get(phase,0)+1
    unknown=set(active)-baseline-{c["id"] for c in candidates if c["phase"]=="published"}
    if unknown:
        raise ValueError(f"unreviewed active cities: {sorted(unknown)}")
    return {"active":len(active),"candidates":len(candidates),"by_phase":phases}


def main():
    result=validate(json.loads(CANDIDATES.read_text(encoding="utf-8")),
                    json.loads(LIVE.read_text(encoding="utf-8")))
    print("[city-intake] PASS",json.dumps(result,ensure_ascii=False))


if __name__=="__main__":
    main()
