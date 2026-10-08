#!/usr/bin/env python3
"""Fail closed: public city layers require audited data and metric-specific admission.

Two deliberately separate publication tracks:
- annual BKA-compatible violence/property RATE city layers (main registry)
- named city-specific counts with NO invented rates (supplementary registry)
Research candidates never directly enter either public registry.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CANDIDATES=ROOT/"data/city_candidates.json"
LIVE=ROOT/"data/city_layers.json"
COUNT=ROOT/"data/city_count_layers.json"
PHASES={"research","source_probe","join_ready","published","blocked"}
METRIC={"unverified","incompatible","compatible","independent_count_only"}
PUBLIC_METRICS={"violence","serious_injury","robbery","sexual","homicide",
                "property_total","burglary","bicycle_theft","vehicle_theft","theft_from_vehicle"}


def validate(intake:dict,live:dict,supplementary:dict|None=None)->dict:
    if intake.get("schema_version")!=1:
        raise ValueError("unsupported city_candidates schema")
    candidates=intake.get("candidates")
    if not isinstance(candidates,list):
        raise ValueError("candidate list missing")
    active={c["id"]:c for c in live.get("cities",[])}
    count_layers=(supplementary or {}).get("layers",[])
    supplements={c["id"]:c for c in count_layers}
    if len(supplements)!=len(count_layers):
        raise ValueError("duplicate supplemental city count layer")
    baseline=set(intake.get("baseline_published_ids",[]))
    if not baseline.issubset(active):
        raise ValueError("baseline active cities removed without migration")
    if set(active)&set(supplements):
        raise ValueError(f"city registered twice (rate+count): {sorted(set(active)&set(supplements))}")
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
                raise ValueError(f"{cid}: {kind} requires original HTTPS source")
        if phase=="published":
            for key in ("crime_source","geometry_source"):
                if not c.get(key):
                    raise ValueError(f"{cid}: published source requires {key}")
            if not c.get("qa_passed") or not c.get("source_license_reviewed"):
                raise ValueError(f"{cid}: missing QA and license review")
            if cid in active:
                if c.get("metric_alignment")!="compatible":
                    raise ValueError(f"{cid}: incompatible metrics cannot publish")
                declared=set(active[cid].get("metrics",{}))
                if not declared or not declared.issubset(PUBLIC_METRICS):
                    raise ValueError(f"{cid}: invalid published rate metrics")
            elif cid in supplements:
                item=supplements[cid]
                if c.get("metric_alignment")!="independent_count_only":
                    raise ValueError(f"{cid}: incompatible metrics cannot publish")
                if item.get("source_url","")!=c["crime_source"]["url"]:
                    raise ValueError(f"{cid}: live count layer source does not match approved police PDF")
                if c.get("public_scope")=="supplementary_count_only":
                    if item.get("metric")!="all_offenses_cases" or "非每10万人率" not in str(item.get("unit","")):
                        raise ValueError(f"{cid}: not an explicitly count-only metric")
                    if not (0<item.get("mapped_total",0)<item.get("reported_total",0) and
                            item["mapped_total"]+item["unassigned_total"]==item["reported_total"]):
                        raise ValueError(f"{cid}: count reconciliation invalid")
                elif c.get("public_scope")=="supplementary_category_counts_only":
                    expected={"all_offenses","theft","robbery","bodily_injury","burglary","sexual","drug"}
                    if item.get("metric")!="local_category_cases" or "非每10万人率" not in str(item.get("unit","")):
                        raise ValueError(f"{cid}: count categories must not claim a crime rate")
                    if item.get("region_count")!=22 or set(item.get("categories",[]))!=expected:
                        raise ValueError(f"{cid}: category names or number of official PKS regions drifted")
                elif c.get("public_scope")=="supplementary_public_violence_count_only":
                    expected={"public_violence","public_robbery","public_serious_injury"}
                    if item.get("metric")!="public_space_violence_cases" or "非每10万人率" not in str(item.get("unit","")):
                        raise ValueError(f"{cid}: public-space category cannot claim all-scene crime rate")
                    if item.get("region_count")!=23 or set(item.get("categories",[]))!=expected:
                        raise ValueError(f"{cid}: published Stuttgart 23 areas/3 categories changed")
                    if item.get("official_city_count")!=1636 or item.get("assigned_to_districts")!=1577 or item.get("unmatched_remainder")!=59:
                        raise ValueError(f"{cid}: Stuttgart official 2025 city/district totals changed")
                else:
                    raise ValueError(f"{cid}: unsupported supplementary publication scope")
            else:
                raise ValueError(f"{cid}: published candidate not in approved public city registry")
        elif cid in active or cid in supplements:
            raise ValueError(f"{cid}: unreleased candidate leaked into public map")
        phases[phase]=phases.get(phase,0)+1
    allowed={c["id"] for c in candidates if c["phase"]=="published"}
    unknown_rate=set(active)-baseline-allowed
    unknown_count=set(supplements)-allowed
    if unknown_rate or unknown_count:
        raise ValueError(f"unreviewed public city entries: rate={sorted(unknown_rate)}, count={sorted(unknown_count)}")
    return {"active_rate":len(active),"active_count":len(supplements),"candidates":len(candidates),"by_phase":phases}


def main():
    result=validate(json.loads(CANDIDATES.read_text(encoding="utf-8")),
                    json.loads(LIVE.read_text(encoding="utf-8")),
                    json.loads(COUNT.read_text(encoding="utf-8")))
    print("[city-intake] PASS",json.dumps(result,ensure_ascii=False))


if __name__=="__main__":main()
