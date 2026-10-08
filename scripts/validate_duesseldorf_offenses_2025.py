#!/usr/bin/env python3
"""Düsseldorf 2025 official 10-area PKS total cases: strict QA and topology."""
from __future__ import annotations
import json
from pathlib import Path
from shapely.geometry import shape
from shapely.ops import unary_union,transform
from pyproj import Transformer
from build_duesseldorf_offenses_2025 import KNOWN,PDF_PUBLIC
FILE=Path(__file__).resolve().parents[1]/"data/duesseldorf_total_cases_2025.geojson"
PROJECT=Transformer.from_crs("EPSG:4326","EPSG:3035",always_xy=True).transform

def main():
    data=json.loads(FILE.read_text(encoding="utf-8"))
    meta=data.get("meta",{});items=data.get("features",[])
    if meta.get("status")!="supplementary_all_offense_count_only" or meta.get("metric_scope")!="all_offense_cases_by_police_stadtbezirk_NOT_violence_rates":
        raise ValueError("Düsseldorf official source must be all-offense cases, not violence rate")
    if meta.get("source")!=PDF_PUBLIC or len(items)!=10 or meta.get("districts")!=10:
        raise ValueError("Düsseldorf official source/ten districts changed")
    mapped={str(year):0 for year in KNOWN}
    shapes=[]
    seen=set()
    for f in items:
        p=f["properties"];code=p.get("district_code");n=int(code)-1 if str(code).isdigit() else -1
        if not(0<=n<10) or code in seen or p.get("offense_metric_scope")!="all_recorded_pks_cases":
            raise ValueError("Official Düsseldorf district ID incomplete or duplicated")
        seen.add(code)
        g=shape(f["geometry"])
        if g.is_empty or not g.is_valid or g.geom_type not in ("Polygon","MultiPolygon"):
            raise ValueError(f"Düsseldorf city district polygon invalid: {code}")
        shapes.append(transform(PROJECT,g))
        c=p.get("crime_total",{})
        if c.get("rate") is not None:raise ValueError("Düsseldorf district population unavailable: NO fake rates")
        for year,checks in KNOWN.items():
            count=c.get(str(year))
            if not isinstance(count,int) or count!=checks[n]:
                raise ValueError(f"Düsseldorf official district {code}, {year}: count mismatched {count}")
            mapped[str(year)]+=count
    overlap=sum(shapes[i].intersection(shapes[j]).area for i in range(10) for j in range(i))
    area=unary_union(shapes).area/1e6
    if overlap>1 or not 217.39<area<217.43:
        raise ValueError(f"Düsseldorf official area/seams changed: {area} km² overlap {overlap}")
    for year,checks in KNOWN.items():
        y=str(year)
        if (mapped[y]!=meta["mapped_by_year"][y] or checks[-1]!=meta["city_by_year"][y] or
            checks[-1]-mapped[y]!=meta["undistributed_by_year"][y]):
            raise ValueError("Unlocated citywide offenses must be preserved, not redistributed")
    print("[duesseldorf-offense-qa] PASS",json.dumps({
       "districts":10,"years":list(KNOWN),"2025_mapped":mapped["2025"],
       "2025_citywide":meta["city_by_year"]["2025"],
       "unallocated":meta["undistributed_by_year"]["2025"],
       "area_km2":round(area,3),"overlap_m2":round(overlap,2),"per_capita_rate":None},ensure_ascii=False),flush=True)

if __name__=="__main__":main()
