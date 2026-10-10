#!/usr/bin/env python3
"""2025-09 BASt geocoded bridge Teilbauwerke: conservative *spatial* district join.

Records 52,553 ArcGIS point features; assigns to a vetted candidate 400-district
geometry only when exactly ONE corrected county polygon intersects the point.
Legacy invalid polygon repairs are in-memory and audited. Unassigned records
remain explicit. This is a candidate, NEVER update live German-Map scores.
"""
from __future__ import annotations
import csv
import datetime as dt
import gzip
import json
import math
import pathlib
import urllib.parse
import urllib.request
import time
from collections import Counter, defaultdict
from shapely.geometry import Point, shape
from shapely.strtree import STRtree
from shapely.validation import make_valid

ROOT=pathlib.Path(__file__).resolve().parents[4]
RESEARCH=ROOT/"topics/infrastructure/research"
POLYGONS=RESEARCH/"germany-counties-mergers-candidate.geojson"
SOURCE_BASE=("https://services2.arcgis.com/jUpNdisbWqRpMo35/arcgis/rest/services/"
             "Br%C3%BCckenstatistik_Deutschland/FeatureServer/0")
OUT=RESEARCH/"candidate_bridge_spatial_county_400_2025.json"
RAW=RESEARCH/"bast_bridge_point_audit_2025.csv.gz"
STATE_PREFIX={"01":"DE-SH","02":"DE-HH","03":"DE-NI","04":"DE-HB",
"05":"DE-NW","06":"DE-HE","07":"DE-RP","08":"DE-BW","09":"DE-BY",
"10":"DE-SL","11":"DE-BE","12":"DE-BB","13":"DE-MV","14":"DE-SN","15":"DE-ST","16":"DE-TH"}
ARC_TO_ISO={"SH":"DE-SH","HH":"DE-HH","NI":"DE-NI","HB":"DE-HB","NW":"DE-NW",
"HE":"DE-HE","RP":"DE-RP","BW":"DE-BW","BY":"DE-BY","SL":"DE-SL",
"BE":"DE-BE","BB":"DE-BB","MV":"DE-MV","SN":"DE-SN","ST":"DE-ST","TH":"DE-TH"}
FIELDS="OBJECTID,bl,kreis,zn,flaeche"
def request(params):
    url=SOURCE_BASE+"/query?"+urllib.parse.urlencode(params)
    error=None
    for retry in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"GermanMapResearch/1.0","Accept":"application/json"}),timeout=50) as res:
                d=json.load(res)
            if "error" in d:raise RuntimeError(str(d["error"])[:250])
            return d
        except Exception as exc:
            error=exc;time.sleep(min(12,1+retry*2))
    raise RuntimeError("ArcGIS request failed: "+str(error))
def grade(value):
    if value is None: return None
    try:x=float(value)
    except Exception:return None
    if 10<=x<=40 and x.is_integer():x=x/10
    if not (1<=x<=4):raise ValueError("Unexpected DIN grade "+str(value))
    return x
def area(value):
    try:
        x=float(value)
        return x if math.isfinite(x) and 0<x<10_000_000 else None
    except Exception:return None
def main():
    src=json.loads(POLYGONS.read_text())["features"]
    assert len(src)==400
    county=[]
    shapes=[]
    repaired=[]
    for f in src:
        ags=str(f["id"]).zfill(5)
        assert len(ags)==5 and ags.isdigit() and ags[:2] in STATE_PREFIX
        g=shape(f["geometry"])
        if not g.is_valid:
            repaired.append(ags)
            g=make_valid(g)
        assert g.is_valid and not g.is_empty
        county.append({"ags":ags,"iso":STATE_PREFIX[ags[:2]],"name":f["properties"]["name"]})
        shapes.append(g)
    tree=STRtree(shapes)
    base=request({"f":"json","where":"1=1","returnCountOnly":"true"})
    total=int(base["count"])
    assert 50000<=total<=60000
    ids=request({"f":"json","where":"1=1","returnIdsOnly":"true"}).get("objectIds",[])
    assert len(ids)==len(set(ids))==total
    ids.sort()
    counters=defaultdict(lambda:dict(parts=0,poor_parts=0,valid_area_m2=0.0,poor_area_m2=0.0))
    statuses=Counter()
    cross_state=Counter()
    mismatch_examples=[]
    unmatched_examples=[]
    observed_ids=set()
    with gzip.open(RAW,"wt",newline="",encoding="utf-8") as fp:
        writer=csv.DictWriter(fp,fieldnames=["objectid","lat","lon","source_state","source_kreis",
            "ags_spatial","spatial_state","spatial_class","din_grade","area_m2"])
        writer.writeheader()
        for offset in range(0,len(ids),120):
            batch=ids[offset:offset+120]
            result=request({"f":"json","objectIds":",".join(map(str,batch)),
                 "outFields":FIELDS,"outSR":"4326","returnGeometry":"true"})
            feats=result.get("features")
            if not isinstance(feats,list) or len(feats)!=len(batch):raise RuntimeError("Partial spatial batch at "+str(offset))
            if {r["attributes"]["OBJECTID"] for r in feats}!=set(batch):raise RuntimeError("Bad response IDs")
            for feat in feats:
                attr=feat["attributes"]
                oid=attr["OBJECTID"]
                if oid in observed_ids:raise RuntimeError("Duplicate OBJECTID")
                observed_ids.add(oid)
                loc=feat.get("geometry") or {}
                lon=loc.get("x");lat=loc.get("y")
                if lon is None or lat is None or not (5<=lon<=17 and 47<=lat<=56):
                    status="no_valid_coordinate";found=None
                else:
                    p=Point(float(lon),float(lat))
                    # Predicate='intersects' retains both counties on a shared
                    # boundary as AMBIGUOUS rather than arbitrarily choosing one.
                    hits=list(tree.query(p,predicate="intersects"))
                    found=int(hits[0]) if len(hits)==1 else None
                    status="unique_polygon" if len(hits)==1 else ("overlap_or_boundary" if hits else "outside_polygons")
                state_from_source=ARC_TO_ISO.get(str(attr.get("bl") or "").strip())
                din=grade(attr.get("zn"))
                a=area(attr.get("flaeche"))
                mapped=county[found] if found is not None else None
                if mapped and state_from_source and mapped["iso"]!=state_from_source:
                    cross_state[(state_from_source,mapped["iso"])]+=1
                    if len(mismatch_examples)<55:mismatch_examples.append({"objectid":oid,"arc_state":state_from_source,
                       "point_state":mapped["iso"],"point_ags":mapped["ags"],"lat":lat,"lon":lon})
                if not mapped and len(unmatched_examples)<120:
                    unmatched_examples.append({"objectid":oid,"status":status,"lat":lat,"lon":lon,
                        "reported_state":state_from_source,"reported_kreis":attr.get("kreis")})
                if mapped:
                    x=counters[mapped["ags"]];x["parts"]+=1
                    if din>=3:x["poor_parts"]+=1
                    if a is not None:
                        x["valid_area_m2"]+=a
                        if din>=3:x["poor_area_m2"]+=a
                statuses[status]+=1
                writer.writerow({"objectid":oid,"lat":lat,"lon":lon,"source_state":state_from_source,
                    "source_kreis":attr.get("kreis"),"ags_spatial":mapped["ags"] if mapped else "",
                    "spatial_state":mapped["iso"] if mapped else "","spatial_class":status,
                    "din_grade":din,"area_m2":a})
            if offset%3600==0:print("Spatial features",len(observed_ids),"/",total,flush=True)
    assert len(observed_ids)==total
    assert sum(statuses.values())==total
    data=[]
    for item in county:
        x=counters[item["ags"]];n=x["parts"];a=x["valid_area_m2"]
        data.append({**item,"substructures":n,"poor_substructures":x["poor_parts"],
          "poor_pct_count":round(x["poor_parts"]*100/n,3) if n else None,
          "area_m2":round(a,2),"poor_area_m2":round(x["poor_area_m2"],2),
          "poor_pct_area":round(x["poor_area_m2"]*100/a,3) if a else None,
          "sample_small":n<20,"has_data":n>0})
    matched=sum(v["substructures"] for v in data)
    assert matched==statuses["unique_polygon"]
    result={"status":"CANDIDATE_GEOCODED_400_DISTRICT_NOT_OFFICIAL_BKG",
      "snapshot":"2025-09", "run_date_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
      "source_url":SOURCE_BASE,
      "source_data":"ArcGIS BASt-derived point features; no municipality/state roads, rail or municipal bridges",
      "polygon_candidate_source":str(POLYGONS.relative_to(ROOT)),
      "polygon_source_warning":"400-district derived from historic 402 shapes and two official mergers; no current BKG VG25 authentication",
      "topology_repairs_in_memory_only":repaired,
      "geojoin_rule":"unique Shapely intersects point-in-polygon match; border/overlap/outside kept unresolved, no fuzzy text fallback",
      "source_count":total,"assigned_count":matched,"unassigned_count":total-matched,
      "status_counts":dict(statuses),"cross_state_count":sum(cross_state.values()),
      "cross_state_pairs":[{"source_iso":a,"spatial_iso":b,"parts":n} for (a,b),n in sorted(cross_state.items())],
      "cross_state_examples":mismatch_examples,
      "unassigned_examples":unmatched_examples,
      "districts_total":400,
      "districts_with_data":sum(1 for v in data if v["has_data"]),
      "raw_points_file":str(RAW.relative_to(ROOT)),
      "never_use_as_official_all_bridges_quality_ranking":True,
      "data":data}
    OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print("PASS",total,"source IDs:",matched,"unique spatial county points,",total-matched,"unassigned,",
      result["districts_with_data"],"districts with data, source-state mismatches",result["cross_state_count"])
    print("Spatial assignment statuses:",dict(statuses),flush=True)

if __name__=="__main__":main()
