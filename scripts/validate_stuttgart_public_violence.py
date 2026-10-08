#!/usr/bin/env python3
"""Reject incorrect city-wide 2025 violence attribution/rates in Stuttgart."""
from __future__ import annotations
import json
from pathlib import Path
from shapely.geometry import shape
from shapely.ops import transform,unary_union
from pyproj import Transformer
from build_stuttgart_public_violence_2025 import URL
FILE=Path(__file__).resolve().parents[1]/"data/stuttgart_public_violence_2025.geojson"
PROJ=Transformer.from_crs("EPSG:4326","EPSG:3035",always_xy=True).transform
CITY={"public_violence":1636,"public_robbery":358,"public_serious_injury":1243}
MAPPED={"public_violence":1577,"public_robbery":350,"public_serious_injury":1194}
def main():
    d=json.loads(FILE.read_text(encoding="utf-8"));m=d["meta"];f=d["features"]
    if (m.get("status")!="supplementary_public_violence_count_only" or
        m.get("metric_scope")!="public_space_violent_crime_only_NOT_all_violence" or
        m.get("source")!=URL or m.get("year")!=2025):
        raise ValueError("Stuttgart public-space scope/source drift")
    if len(f)!=23 or len({x["id"] for x in f})!=23:raise ValueError("23 districts required")
    counts={k:0 for k in CITY};polygons=[]
    for feat in f:
        p=feat["properties"]
        if p.get("public_space_only") is not True or set(p.get("metrics",{}))!=set(CITY):
            raise ValueError("Stuttgart reporting scope is not public space")
        g=shape(feat["geometry"])
        if g.is_empty or not g.is_valid:raise ValueError("Invalid official district polygon")
        polygons.append(transform(PROJ,g))
        for k,v in p["metrics"].items():
            n=v.get("2025")
            if not isinstance(n,int) or n<0 or v.get("rate") is not None:
                raise ValueError(f"No fake rates or missing public-space cases: {feat['id']} {k}")
            counts[k]+=n
    overlap=sum(polygons[i].intersection(polygons[j]).area for i in range(23) for j in range(i))
    area=unary_union(polygons).area/1e6
    if overlap>1 or not 207.39<area<207.42:raise ValueError(f"District overlap/size failed {overlap}/{area}")
    if counts!=MAPPED or m["mapped_totals"]!=MAPPED or m["city_totals"]!=CITY:
        raise ValueError("2025 government source counts failed reconciliation")
    if any(m["unlocated_city_cases"][k]!=CITY[k]-MAPPED[k] for k in CITY):
        raise ValueError("Citywide/district differences changed")
    print("[stuttgart-public-violence-qa] PASS",json.dumps({
       "districts":23,"area_km2":round(area,3),"overlap_m2":round(overlap,2),
       "mapped":counts,"city":CITY,"unallocated_difference":m["unlocated_city_cases"],
       "crime_rates":None},ensure_ascii=False),flush=True)
if __name__=="__main__":main()
