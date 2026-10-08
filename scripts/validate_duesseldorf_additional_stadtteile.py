#!/usr/bin/env python3
"""Strict 2025 police and municipal GIS checks for Düsseldorf BV7 / BV9."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from shapely.geometry import shape
from shapely.ops import transform,unary_union
from pyproj import Transformer
from build_duesseldorf_additional_stadtteile import CONFIG,NAMES,CODES,GEO_URL,PDFS
from build_duesseldorf_offenses_2025 import KNOWN
METRIC=Transformer.from_crs("EPSG:4326","EPSG:3035",always_xy=True).transform
ROOT=Path(__file__).resolve().parents[1]

def validate(bv):
    doc=json.loads((ROOT/f"data/duesseldorf_bv{int(bv)}_local_2025.geojson").read_text(encoding="utf-8"))
    m=doc.get("meta",{});fs=doc.get("features",[]);cfg=CONFIG[bv]
    if (m.get("status")!="supplementary_bv_additional_neighbourhood_cases_only" or
        m.get("scope")!=cfg["scope"] or m.get("parent_stadtbezirk")!=bv or
        m.get("police_source")!="https:"+PDFS[bv][5:] or
        m.get("municipal_geometry_source")!=GEO_URL or
        m.get("source_years")!=list(cfg["years"]) or
        m.get("categories")!=list(cfg["metrics"]) or len(fs)!=len(NAMES[bv])):
        raise ValueError(f"BV{bv} original evidence, year, or geography scope mismatched")
    projected=[]
    totals={metric:{str(y):0 for y in cfg["years"]} for metric in cfg["metrics"]}
    for i,(name,code) in enumerate(zip(NAMES[bv],CODES[bv])):
        feature=fs[i];p=feature.get("properties",{})
        if (p.get("name")!=name or p.get("stadtteil_code")!=code or
            p.get("parent_stadtbezirk")!=bv or p.get("metric_scope")!=cfg["scope"] or
            set(p.get("metrics",{}))!=set(cfg["metrics"])):
            raise ValueError(f"BV{bv} official {name} metadata out of place")
        g=shape(feature["geometry"])
        if g.is_empty or not g.is_valid or g.geom_type not in ("Polygon","MultiPolygon"):
            raise ValueError(f"BV{bv} official {name} polygon invalid")
        projected.append(transform(METRIC,g))
        for metric,values in p["metrics"].items():
            if values.get("rate") is not None:raise ValueError("No BV7/BV9 population denominator; no fake crime rate")
            for y in cfg["years"]:
                n=values.get(str(y))
                if type(n) is not int or n<0:raise ValueError(f"BV{bv} police data {name}/{metric}/{y} missing/negative")
                totals[metric][str(y)]+=n
    for k,(_,_,official_2025,total_2025) in cfg["metrics"].items():
        if [f["properties"]["metrics"][k]["2025"] for f in fs]!=official_2025 or totals[k]["2025"]!=total_2025:
            raise ValueError(f"BV{bv} primary police {k}/2025 count mismatch")
        if totals[k]!=m["mapped_by_category"][k]:
            raise ValueError(f"BV{bv} history checksum drift for {k}")
    if bv=="07":
        for year in cfg["years"]:
            if totals["all_offenses"][str(year)]!=KNOWN[year][6]:
                raise ValueError("BV7 5-Stadtteil all offenses do not match independently sourced 10 district counts")
    else:
        if set(totals)!={"street_crime","residential_burglary"}:
            raise ValueError("BV9 police did NOT publish other neighborhood categories")
    overlap=sum(projected[i].intersection(projected[j]).area for i in range(len(projected)) for j in range(i))
    area=unary_union(projected).area/1e6
    if (overlap>5 or not 2<area<100 or
        abs(area-m["area_km2"])>.0002 or m["parent_outline_diff_m2"]>1500):
        raise ValueError(f"BV{bv} source municipal geometry seams/area invalid: {area}, {overlap}")
    print("[duesseldorf-more-qa] PASS",json.dumps({
       "bv":bv,"areas":len(fs),"categories":len(totals),"years":list(cfg["years"]),
       "2025_counts":{k:t["2025"] for k,t in totals.items()},
       "area_km2":round(area,3),"parent_outline_difference_m2":m["parent_outline_diff_m2"],
       "overlap_m2":round(overlap,2),"fake_rates":False},ensure_ascii=False),flush=True)
    return True
if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--district",required=True,choices=("07","09"))
    validate(ap.parse_args().district)
