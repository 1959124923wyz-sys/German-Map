#!/usr/bin/env python3
"""Join cached 52,553 BASt ArcGIS 2025-09 point records to official BKG VG250 2025-12-31 counties.

Uses the already committed raw-point evidence archive; no repeat BASt API call.
Always preserves uncertain boundary/outside/overlap cases and 2025-vintage
date mismatch, never touches production main maps or composite scores.
"""
from __future__ import annotations
from collections import defaultdict, Counter
from pathlib import Path
import csv
import gzip
import json
import math
import re
from shapely.geometry import Point,shape
from shapely.strtree import STRtree
from shapely.validation import make_valid

ROOT=Path(__file__).resolve().parents[4]
BASE=ROOT/"topics/infrastructure/research"
SOURCE=BASE/"bast_bridge_point_audit_2025.csv.gz"
GEO=BASE/"germany-counties-bkg-official-2025.geojson"
OLD=BASE/"candidate_bridge_spatial_county_400_2025.json"
DEST=BASE/"candidate_bridge_official_bkg_counties_2025.json"
POINT_DEST=BASE/"bast_bridge_point_bkg2025_audit.csv.gz"
PREFIX={"01":"DE-SH","02":"DE-HH","03":"DE-NI","04":"DE-HB","05":"DE-NW",
"06":"DE-HE","07":"DE-RP","08":"DE-BW","09":"DE-BY","10":"DE-SL","11":"DE-BE",
"12":"DE-BB","13":"DE-MV","14":"DE-SN","15":"DE-ST","16":"DE-TH"}

def finite_num(x):
    try:
        y=float(x)
        return y if math.isfinite(y) else None
    except (TypeError,ValueError):
        return None

def main():
    official=json.loads(GEO.read_text())
    fs=official["features"]
    assert len(fs)==400
    geos=[];lookup=[];repaired=[]
    for f in fs:
        ags=str(f["id"])
        assert re.fullmatch(r"\d{5}",ags)
        g=shape(f["geometry"])
        if not g.is_valid:
            repaired.append(ags)
            g=make_valid(g)
        if not g.is_valid or g.is_empty:raise RuntimeError("Invalid BKG geometry "+ags)
        assert f["properties"]["iso"]==PREFIX[ags[:2]]
        geos.append(g)
        lookup.append({"ags":ags,"iso":PREFIX[ags[:2]],"name":f["properties"]["name"]})
    assert not repaired,("Unexpected repair to official BKG geometry",repaired)
    tree=STRtree(geos)
    count=Counter();source_state_mismatch=Counter()
    totals=defaultdict(lambda:{"parts":0,"poor":0,"area":0.0,"bad_area":0.0})
    old_counties={}
    missing_coords_examples=[];mismatch_examples=[];assigned_ids=set();old_assigned=0;changed=0
    status_detail=Counter()
    with gzip.open(SOURCE,"rt",encoding="utf-8",newline="") as f, \
         gzip.open(POINT_DEST,"wt",encoding="utf-8",newline="") as w:
        reader=csv.DictReader(f)
        writer=csv.DictWriter(w,fieldnames=reader.fieldnames+["bkg_ags","bkg_state","bkg_join_status","boundary_changed","state_mismatch"])
        writer.writeheader()
        for rec in reader:
            oid=int(rec["objectid"])
            if oid in assigned_ids:raise RuntimeError("Duplicate OBJECTID")
            assigned_ids.add(oid)
            old_ags=rec.get("ags_spatial") or ""
            if old_ags:old_assigned+=1
            x=finite_num(rec.get("lon"));y=finite_num(rec.get("lat"))
            if x is None or y is None or not (5<=x<=17 and 47<=y<=56):
                status="no_valid_coordinate";hit=None
            else:
                matches=list(tree.query(Point(x,y),predicate="intersects"))
                hit=int(matches[0]) if len(matches)==1 else None
                status="unique_polygon" if len(matches)==1 else ("border_overlap" if matches else "outside_official_boundary")
            mapped=lookup[hit] if hit is not None else None
            ags=mapped["ags"] if mapped else ""
            iso=mapped["iso"] if mapped else ""
            change=(ags!=old_ags)
            if change:changed+=1
            mismatched=bool(mapped and rec["source_state"] and rec["source_state"]!=iso)
            if mismatched:
                source_state_mismatch[(rec["source_state"],iso)]+=1
                if len(mismatch_examples)<130:
                    mismatch_examples.append({"objectid":oid,"source_iso":rec["source_state"],"bkg_iso":iso,
                      "bkg_ags":ags,"old_ags":old_ags,"lat":y,"lon":x,"source_kreis":rec["source_kreis"]})
            if status!="unique_polygon" and len(missing_coords_examples)<170:
                missing_coords_examples.append({"objectid":oid,"status":status,"lat":y,"lon":x,"source_iso":rec["source_state"]})
            if mapped:
                t=totals[ags];t["parts"]+=1
                z=finite_num(rec.get("din_grade"));area=finite_num(rec.get("area_m2"))
                if z is not None and z>=3:t["poor"]+=1
                if area is not None and area>0:
                    t["area"]+=area
                    if z is not None and z>=3:t["bad_area"]+=area
            count[status]+=1
            status_detail[(bool(old_ags),bool(ags))]+=1
            writer.writerow({**rec,"bkg_ags":ags,"bkg_state":iso,"bkg_join_status":status,
                "boundary_changed":"true" if change else "false","state_mismatch":"true" if mismatched else "false"})
    assert len(assigned_ids)==52553, len(assigned_ids)
    assert sum(count.values())==52553
    items=[]
    for site in lookup:
        t=totals[site["ags"]]
        n=t["parts"];a=t["area"]
        items.append({**site,"parts":n,"poor_parts":t["poor"],
            "poor_pct_count":round(100*t["poor"]/n,3) if n else None,
            "area_m2":round(a,2),"bad_area_m2":round(t["bad_area"],2),
            "poor_pct_area":round(100*t["bad_area"]/a,3) if a else None,
            "low_sample":n<20,"has_data":n>0})
    assigned=sum(x["parts"] for x in items)
    assert assigned==count["unique_polygon"]
    result={
      "status":"OFFICIAL_BKG_BOUNDARY_CANDIDATE_WITH_BAST_2025_POINTS",
      "bridge_snapshot":"2025-09",
      "county_boundary_snapshot":"2025-12-31",
      "county_boundary_authority":"BKG VG250, dl-de/by-2-0 attribution",
      "county_geometry":"topics/infrastructure/research/germany-counties-bkg-official-2025.geojson",
      "point_source":"topics/infrastructure/research/bast_bridge_point_audit_2025.csv.gz",
      "point_audit":"topics/infrastructure/research/bast_bridge_point_bkg2025_audit.csv.gz",
      "scope":"Only federal motorways and Bundesstrassen bridges (Teilbauwerke) in 2025-09 ArcGIS derivative",
      "exclude":"State roads, district roads, municipal bridges, Deutsche Bahn railway bridges",
      "bkg_not_replacing_main":True,
      "not_in_existing_composite":True,
      "source_bridge_parts":52553,
      "assigned":assigned,"unassigned":52553-assigned,
      "status_counts":dict(count),
      "historical_polygon_assigned":old_assigned,
      "changed_ags_from_historical_join":changed,
      "transition_summary":[{"old_assigned":oldflag,"new_assigned":newflag,"n":n}
         for (oldflag,newflag),n in sorted(status_detail.items())],
      "reported_state_vs_spatial_mismatches":sum(source_state_mismatch.values()),
      "reported_state_mismatch_pairs":[{"source_iso":a,"bkg_iso":b,"n":v} for (a,b),v in sorted(source_state_mismatch.items())],
      "mismatch_examples":mismatch_examples,
      "unassigned_examples":missing_coords_examples,
      "districts":400,
      "districts_with_data":sum(x["has_data"] for x in items),
      "small_sample_districts":sum(x["low_sample"] for x in items),
      "data":items}
    DEST.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    assert len(result["data"])==400
    print("PASS official BKG 2025 districts:",result["districts_with_data"],"with data",
          assigned,"of 52553 point features; changed historical county assignments",
          changed,"state mismatch",result["reported_state_vs_spatial_mismatches"],flush=True)
    print("Official BKG statuses:",dict(count),flush=True)

if __name__=="__main__":main()
