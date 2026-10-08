#!/usr/bin/env python3
"""Fail closed: independently published Kiel all-offense count layer contract."""
from __future__ import annotations
import json
from pathlib import Path
from shapely.geometry import shape
from shapely.ops import unary_union
from pyproj import Transformer
from shapely.ops import transform

ROOT=Path(__file__).resolve().parents[1]
FILE=ROOT/"data/kiel_total_cases_2025.geojson"
MUNICIPAL=ROOT/"data/germany-counties.geojson"
to_metric=Transformer.from_crs("EPSG:4326","EPSG:3035",always_xy=True).transform

def main():
    doc=json.loads(FILE.read_text(encoding="utf-8"))
    meta=doc["meta"]
    if meta.get("status")!="supplementary_count_only" or meta.get("metric_scope")!="all_offenses_count_only_NOT_violence_or_theft":
        raise ValueError("Kiel not approved as separately labelled offense-count-only")
    fs=doc["features"]
    if len(fs)!=30 or len({x["id"] for x in fs})!=30:
        raise ValueError(f"Unexpected Kiel district count/IDs: {len(fs)}")
    counts=[]
    geom=[]
    for f in fs:
        props=f["properties"]
        annual=props["annual_cases"]
        if sorted(annual)!=list(map(str,range(2016,2026))):
            raise ValueError(f"{f['id']}: incomplete annual series")
        if props["crime_total"]["rate"] is not None:
            raise ValueError(f"{f['id']}: rate must remain null, not invented")
        n=annual["2025"]
        if n!=props["crime_total"]["cases"] or not isinstance(n,int) or n<0:
            raise ValueError(f"{f['id']}: total offense count mismatch")
        g=shape(f["geometry"])
        if not g.is_valid or g.is_empty or g.geom_type not in ("Polygon","MultiPolygon"):
            raise ValueError(f"{f['id']}: invalid official polygon")
        minx,miny,maxx,maxy=g.bounds
        if not (9.85<minx<10.45 and 9.85<maxx<10.45 and 54.1<miny<54.65 and 54.1<maxy<54.65):
            raise ValueError(f"{f['id']}: invalid Kiel geographic coordinates {g.bounds}")
        geom.append(g)
        counts.append(n)
    if sum(counts)!=24341 or meta.get("unassigned_total_2025")!=817:
        raise ValueError(f"Kiel crime totals fail reconciliation: {sum(counts)}+{meta.get('unassigned_total_2025')}")
    if sum(counts)+meta["unassigned_total_2025"]!=25158:
        raise ValueError("All official Kiel cases not accounted for")
    # District pieces are allowed to share borders but never overlap interiors.
    for i,a in enumerate(geom):
        for j,b in enumerate(geom[:i]):
            if a.intersects(b):
                overlap=a.intersection(b).area
                if overlap>1e-10:
                    raise ValueError(f"Kiel {fs[i]['id']} overlaps {fs[j]['id']} by {overlap}")
    raw=json.loads(MUNICIPAL.read_text(encoding="utf-8"))
    county=next((f for f in raw["features"] if str(f["id"])=="01002"),None)
    if not county:raise ValueError("Official national Kiel AGS 01002 is missing")
    city=shape(county["geometry"])
    union=unary_union(geom)
    km=transform(to_metric,union).area/1e6
    county_km=transform(to_metric,city).area/1e6
    if not (85<km<140 and 85<county_km<140):
        raise ValueError(f"Kiel geometry area/CRS unreasonable {km} / {county_km}")
    # Distinct map products legitimately use different cartographic scales.
    # Never stitch count-only data into the nationwide display counties here.
    print("[kiel-count-layer] PASS",json.dumps({
        "districts":len(fs),"mapped_cases":sum(counts),"unassigned_cases":meta["unassigned_total_2025"],
        "geometry_km2":round(km,2),"county_km2":round(county_km,2),
        "official_total":25158,"rate":None},ensure_ascii=False),flush=True)

if __name__=="__main__":main()
