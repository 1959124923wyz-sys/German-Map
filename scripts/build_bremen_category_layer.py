#!/usr/bin/env python3
"""Bremen 2024/2025 official PKS categorized case COUNTS by 22 reporting areas.

Input geometry has to pass build_bremen_geometry_staging.py topology gates.
Never compute rates without matched official populations. A dash in the PKS
report remains null, not an inferred 0.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from audit_bremen_district_joins import PKS
from city_build_common import download_bytes,write_geojson
from extract_bremen_offenses import read_tables, CODES

EXPECTED_2025={"all_offenses":69710,"sexual":960,"robbery":959,
               "bodily_injury":7138,"burglary":1000,"theft":33720,"drug":2379}
DEFINITIONS={
 "all_offenses":{"zh":"全部登记犯罪","code":"------"},
 "sexual":{"zh":"性犯罪","code":"100000"},
 "robbery":{"zh":"抢劫与暴力勒索","code":"210000"},
 "bodily_injury":{"zh":"伤害犯罪","code":"220000"},
 "burglary":{"zh":"住宅入室盗窃","code":"435*00"},
 "theft":{"zh":"盗窃总体","code":"****00"},
 "drug":{"zh":"毒品犯罪","code":"730000"}
}


def combine(geom:dict, police:list[dict], release:bool):
    if len(geom.get("features",[]))!=22 or len(police)!=22:
        raise ValueError("Bremen polygons/PDF tables must both cover 22 areas")
    by_num={x["table"]:x for x in police}
    assert len(by_num)==22
    new_features=[]
    for raw in geom["features"]:
        row=int(raw["properties"]["police_table"])
        rec=by_num.get(row)
        if rec is None or rec["label"]!=raw["properties"]["name"]:
            raise ValueError(f"Bremen PKS title mismatch at police table {row}")
        p=dict(raw["properties"])
        p["metrics"]={k:{**rec["metrics"][k],"rate":None}
                      for k in DEFINITIONS}
        p["year"]=2025
        new_features.append({**raw,"properties":p})
    result={}
    for key in DEFINITIONS:
        result[key]={str(year):sum(
            f["properties"]["metrics"][key][str(year)] or 0 for f in new_features)
            for year in (2024,2025)}
        result[key]["missing_2025"]=sum(
            f["properties"]["metrics"][key]["2025"] is None for f in new_features)
        if result[key]["2025"]!=EXPECTED_2025[key]:
            raise ValueError(f"Bremen checksum changed for {key}: {result[key]['2025']}")
    # All categories are separate: total offenses is NOT their mathematical sum.
    if any(result[k]["2025"]>result["all_offenses"]["2025"] for k in result):
        raise ValueError("category greater than all recorded police offenses")
    combined={"type":"FeatureCollection",
      "meta":{
       "schema_version":1,
       "status":"supplementary_category_counts_only" if release else "candidate_category_counts_only",
       "city":"Bremen","year":2025,"comparison_year":2024,
       "metric_scope":"seven_official_local_categories_absolute_cases_no_rates",
       "police_source":PKS,
       "geometry_source":geom["meta"]["source"],
       "geometry_area_km2":geom["meta"]["mapped_area_km2"],
       "official_area_km2":geom["meta"]["official_area_km2"],
       "area_count":22,
       "category_definitions":DEFINITIONS,
       "mapped_categories":result,
       "year_rate_status":"not_calculated_no_verified_matching_2025_population",
       "no_zero_imputation":"Official dash in source is encoded as JSON null, never zero.",
       "unlocated_warning":"2024/2025 PKS city totals may contain cases not assigned to these 22 areas. Local sums are not complete city totals.",
       "license_note":"Official parliamentary publication is linked for source verification; numbers are independently transcribed public statistics, PDF is not redistributed."
      },
      "features":new_features}
    print("[bremen-category] PASS",json.dumps({
        "area_count":len(new_features),"geometry_km2":combined["meta"]["geometry_area_km2"],
        "2025_mapped_categories":result,
        "no_population_rates":True,"public_mode":release
        },ensure_ascii=False),flush=True)
    return combined


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--geometry",default="artifacts/bremen_areas_staging.geojson")
    ap.add_argument("--output",default="artifacts/bremen_offenses_staging.geojson")
    ap.add_argument("--release-count-only",action="store_true")
    a=ap.parse_args()
    if a.release_count_only and a.output!="data/bremen_local_counts_2025.geojson":
        raise ValueError("only approved count-only public artifact allowed")
    if not a.release_count_only and a.output.startswith("data/"):
        raise ValueError("candidates must remain under artifacts/")
    geom=json.loads(Path(a.geometry).read_text(encoding="utf-8"))
    if geom["meta"].get("status")!="candidate_geometry_only" or geom["meta"].get("reporting_areas")!=22:
        raise ValueError("Bremen source geometry is not an audited candidate")
    for key in ("uncovered_km2","outside_official_km2","internal_overlap_m2"):
        if geom["meta"].get(key,999)!=0:
            raise ValueError(f"Bremen candidate topology unapproved: {key}")
    rows=read_tables(download_bytes(PKS,timeout=80))
    result=combine(geom,rows,a.release_count_only)
    write_geojson(a.output,result)

if __name__=="__main__":main()
