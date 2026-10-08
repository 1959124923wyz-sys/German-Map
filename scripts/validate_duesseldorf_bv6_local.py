#!/usr/bin/env python3
"""Release QA: Düsseldorf BV6 4 official Stadtteile, 8 police categories × 4 years.

Requires the original 2025 official district-6 geography and PKS facts;
neither crime rates nor borough-wide imputation may be invented.
"""
from __future__ import annotations
import json
from pathlib import Path
from shapely.geometry import shape
from shapely.ops import transform,unary_union
from pyproj import Transformer
from build_duesseldorf_bv6_local import CATEGORIES, NAMES, CODES, YEARS, GEO_URL, PDF_PUBLIC
from build_duesseldorf_offenses_2025 import KNOWN
FILE=Path(__file__).resolve().parents[1]/"data/duesseldorf_bv6_local_2025.geojson"
TRANSFORM=Transformer.from_crs("EPSG:4326","EPSG:3035",always_xy=True).transform

def validate(doc):
    meta=doc.get("meta",{});features=doc.get("features",[])
    if (meta.get("status")!="supplementary_bv6_neighbourhood_cases_only" or
        meta.get("scope")!="DUESSELDORF_STADTBEZIRK_06_ONLY_NOT_CITYWIDE" or
        meta.get("municipal_geometry_source")!=GEO_URL or meta.get("police_source")!=PDF_PUBLIC or
        meta.get("year")!=2025 or meta.get("available_years")!=list(YEARS) or len(features)!=4):
        raise ValueError("BV6 source provenance/strict locality approval failed")
    geom=[];totals={k:{str(y):0 for y in YEARS} for k in CATEGORIES}
    for i,(name,code) in enumerate(zip(NAMES,CODES)):
        f=features[i];p=f.get("properties",{})
        if (p.get("name")!=name or p.get("stadtteil_code")!=code or
            p.get("parent_stadtbezirk")!="06" or
            p.get("metric_scope")!="police_published_BV6_local_cases_only" or
            set(p.get("metrics",{}))!=set(CATEGORIES)):
            raise ValueError(f"BV6 Stadtteil {code} wrongly attributed")
        g=shape(f["geometry"])
        if g.is_empty or not g.is_valid or g.geom_type not in ("Polygon","MultiPolygon"):
            raise ValueError(f"Invalid official polygon {name}")
        geom.append(transform(TRANSFORM,g))
        for metric,entry in p["metrics"].items():
            if entry.get("rate") is not None:
                raise ValueError("No matched 2025 neighbourhood population: refuse fake crime rate")
            for year in YEARS:
                val=entry.get(str(year))
                if not isinstance(val,int) or val<0:
                    raise ValueError(f"Missing/unverified {metric}/{year}/{name}")
                totals[metric][str(year)]+=val
    for metric,(_,_,known,source_total) in CATEGORIES.items():
        if [features[i]["properties"]["metrics"][metric]["2025"] for i in range(4)]!=known:
            raise ValueError(f"Official police 2025 district values changed for {metric}")
        if totals[metric]["2025"]!=source_total:
            raise ValueError(f"Official 2025 police source total mismatched for {metric}")
        if totals[metric]!=meta.get("mapped_categories",{}).get(metric):
            raise ValueError(f"BV6 historical source category drift for {metric}")
    for year in YEARS:
        if totals["all_offenses"][str(year)]!=KNOWN[year][5]:
            raise ValueError(f"BV6 neighbourhood counts do not equal official police ten-district table in {year}")
    overlap=sum(geom[i].intersection(geom[j]).area for i in range(4) for j in range(i))
    union=unary_union(geom)
    if (overlap>5 or not 19.65<union.area/1e6<19.71 or
        meta.get("difference_parent_stadtbezirk_m2",1e9)>1000):
        raise ValueError(f"Official BV6 geography changed: {union.area/1e6:.4f} km², {overlap:.2f}m² overlap")
    print("[duesseldorf-bv6-qa] PASS",json.dumps({
        "areas":len(geom),"categories":len(CATEGORIES),"years":list(YEARS),
        "mapped_2025":{k:v["2025"] for k,v in totals.items()},
        "area_km2":round(union.area/1e6,3),
        "parent_boundary_diff_m2":meta["difference_parent_stadtbezirk_m2"],
        "overlap_m2":round(overlap,2),"rates":None},ensure_ascii=False),flush=True)
    return True
if __name__=="__main__":
    validate(json.loads(FILE.read_text(encoding="utf-8")))
