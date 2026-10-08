#!/usr/bin/env python3
"""Bremen supplemental PKS categories: reject missing-as-zero or invented rates."""
from __future__ import annotations
import json
from pathlib import Path
from shapely.geometry import shape
from shapely.ops import transform,unary_union
from pyproj import Transformer
from build_bremen_category_layer import EXPECTED_2025,DEFINITIONS

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/"data/bremen_local_counts_2025.geojson"
METRIC=Transformer.from_crs("EPSG:4326","EPSG:3035",always_xy=True).transform

def main():
    doc=json.loads(TARGET.read_text(encoding="utf-8"))
    meta=doc.get("meta",{})
    if meta.get("status")!="supplementary_category_counts_only" or meta.get("area_count")!=22:
        raise ValueError("not a released Bremen count-only layer")
    if meta.get("metric_scope")!="seven_official_local_categories_absolute_cases_no_rates":
        raise ValueError("Bremen metric scope incompatible with public count display")
    fs=doc.get("features",[])
    if len(fs)!=22 or len({f["id"] for f in fs})!=22:
        raise ValueError("Bremen official 22 region IDs incomplete")
    sums={key:0 for key in DEFINITIONS}
    polygons=[]
    for i,f in enumerate(fs,1):
        p=f.get("properties",{})
        if int(p.get("police_table",-1))!=i or set(p.get("metrics",{}))!=set(DEFINITIONS):
            raise ValueError(f"Missing/duplicate Bremen police categories for Table {i}")
        g=shape(f["geometry"])
        if g.is_empty or not g.is_valid or g.geom_type not in ("Polygon","MultiPolygon"):
            raise ValueError("Official Bremen geometry invalid")
        polygons.append(transform(METRIC,g))
        for key,m in p["metrics"].items():
            if m.get("rate") is not None:
                raise ValueError("No verified 2025 Bremen district population: cannot show crime rates")
            for year in ("2024","2025"):
                count=m.get(year,"__missing__")
                if count is not None and (not isinstance(count,int) or count<0):
                    raise ValueError(f"Bremen Table {i}: {key} {year} invalid {count}")
                if count=="__missing__":
                    raise ValueError(f"Bremen Table {i} {year} not documented")
            if m["2025"] is not None:sums[key]+=m["2025"]
    if sums!=EXPECTED_2025:raise ValueError(f"PKS 2025 checksum mismatch {sums}")
    overlap=sum(polygons[i].intersection(polygons[j]).area
                for i in range(22) for j in range(i))
    if overlap>100:raise ValueError(f"Bremen geometry overlap {overlap} m2")
    area=unary_union(polygons).area/1e6
    if abs(area-318.454)>.02:raise ValueError(f"Bremen official area changed: {area:.3f}")
    if meta["mapped_categories"]["all_offenses"]["2025"]!=69710:
        raise ValueError("Bremen known district total changed")
    print("[bremen-category-validate] PASS",json.dumps({
       "regions":22,"categories":len(DEFINITIONS),"area_sqkm":round(area,3),
       "overlap_m2":round(overlap,3),"mapped_2025":sums,
       "2025_missing_values":{k:meta["mapped_categories"][k]["missing_2025"] for k in sums}
    },ensure_ascii=False),flush=True)

if __name__=="__main__":main()
