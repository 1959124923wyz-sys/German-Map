#!/usr/bin/env python3
"""Conservative state+name join of BASt ArcGIS county groups to German-Map shapes.

Do not label these matches official AGS. German-Map geometry only carries name,
districtType, state and vehicle licence code (kfz), not AGS. Never fuzzy auto-join.
"""
from __future__ import annotations
import collections
import difflib
import json
import pathlib
import re
import unicodedata

ROOT=pathlib.Path(__file__).resolve().parents[4]
R=ROOT/"topics/infrastructure/research"
OUT=R/"candidate_bridge_county_geometry_join.json"
STATES={"Baden-Württemberg":"DE-BW","Bayern":"DE-BY","Berlin":"DE-BE","Brandenburg":"DE-BB",
"Bremen":"DE-HB","Hamburg":"DE-HH","Hessen":"DE-HE","Mecklenburg-Vorpommern":"DE-MV",
"Niedersachsen":"DE-NI","Nordrhein-Westfalen":"DE-NW","Rheinland-Pfalz":"DE-RP",
"Saarland":"DE-SL","Sachsen":"DE-SN","Sachsen-Anhalt":"DE-ST",
"Schleswig-Holstein":"DE-SH","Thüringen":"DE-TH"}
PREFIXES=("kreisfreie stadt ","stadtkreis ","landkreis ","landkreis-","kreis ","lk ")

def canonical(s, strip_prefix=False):
    s=s.replace("ß","ss").replace("ẞ","ss")
    s=s.replace("ä","ae").replace("ö","oe").replace("ü","ue")
    s=s.replace("Ä","Ae").replace("Ö","Oe").replace("Ü","Ue")
    s=unicodedata.normalize("NFKD",s.casefold())
    s="".join(c for c in s if not unicodedata.combining(c))
    s=s.replace("&"," und ").replace("–","-").replace("—","-")
    s=re.sub(r"[\s_,.;:/()'\-]+"," ",s).strip()
    if strip_prefix:
        for p in PREFIXES:
            if s.startswith(p.replace("-"," ")):
                s=s[len(p):].strip()
                break
    return re.sub(r"\s+"," ",s)

def main():
    raw=json.loads((R/"candidate_bridge_counties_arcgis_2025.json").read_text())["counties"]
    shapes=json.loads((ROOT/"data/germany-counties.geojson").read_text())["features"]
    geometry=[]
    for i,f in enumerate(shapes):
        p=f["properties"]
        st=STATES.get(p["state"])
        if not st:raise RuntimeError("Unexpected geometry state "+str(p["state"]))
        geometry.append(dict(shape_index=i,name=p["name"],state_iso=st,
             district_type=p["districtType"],kfz=p.get("kfz")))
    indices={}
    for aggressive in (False,True):
        index=collections.defaultdict(list)
        for g in geometry:
            index[(g["state_iso"],canonical(g["name"],aggressive))].append(g)
        indices[aggressive]=index
    matched=[]
    unmatched=[]
    duplicated_shape_keys=[]
    for source in raw:
        key=(source["iso"],canonical(source["kreis_source_label"]))
        direct=indices[False].get(key,[])
        if len(direct)==1:
            possibilities=direct
            method="exact_normalized_state_and_name"
        else:
            pkey=(source["iso"],canonical(source["kreis_source_label"],True))
            loose=indices[True].get(pkey,[])
            possibilities=loose
            method="uniquely_matched_prefix_normalized" if len(loose)==1 else None
        if len(possibilities)==1:
            g=possibilities[0]
            matched.append({**source,"geometry_feature_index":g["shape_index"],
                 "geometry_name":g["name"],"geometry_state_iso":g["state_iso"],
                 "geometry_district_type":g["district_type"],"kfz_NOT_AGS":g["kfz"],
                 "join_method":method, "official_AGS":None})
        else:
            siblings=[v["name"] for v in geometry if v["state_iso"]==source["iso"]]
            hint=difflib.get_close_matches(source["kreis_source_label"],siblings,n=3,cutoff=.3)
            unmatched.append({**source,"reason":"ambiguous" if len(possibilities)>1 else "unmatched",
                "candidate_names_only_NOT_AUTOMATIC_MATCH":hint,
                "raw_norm":key[1], "possible_geometry_matches":[p["name"] for p in possibilities]})
    grouped=collections.defaultdict(list)
    for m in matched:grouped[m["geometry_feature_index"]].append(m)
    multi={geometry[i]["name"]+"|"+geometry[i]["state_iso"]:[r["kreis_source_label"] for r in members]
           for i,members in grouped.items() if len(members)>1}
    count_matched=sum(x["features"] for x in matched)
    count_unmatched=sum(x["features"] for x in unmatched)
    assert count_matched+count_unmatched==sum(x["features"] for x in raw)
    result={"source_data_year":"2025-09","created_for":"German-Map county geometry join review",
      "status":"CANDIDATE_NAME_JOIN_NOT_OFFICIAL_AGS",
      "polygon_file":"data/germany-counties.geojson",
      "polygon_has_AGS":False,"polygon_has_kfz_NOT_AGS":True,
      "join_safety":"exact state+name; unique prefix normalization only; no fuzzy auto-join",
      "geometry_count":len(geometry),"source_groups":len(raw),
      "matched_source_groups":len(matched),
      "matched_unique_county_polygons":len(grouped),
      "unmatched_source_groups":len(unmatched),
      "matched_source_features":count_matched,
      "unmatched_source_features":count_unmatched,
      "multi_source_group_geometry":multi,
      "joined":matched,"unmatched":unmatched}
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print("Polygon features",len(geometry),"source groups",len(raw),flush=True)
    print("Matched",len(matched),"distinct geometry",len(grouped),
          "unmatched",len(unmatched),"mapped bridge features",count_matched,"unmapped",count_unmatched,flush=True)
    print("Source group collisions",len(multi),flush=True)
    for x in unmatched[:20]:
        print("UNMATCHED",x["iso"],x["kreis_source_label"],x["features"],x["candidate_names_only_NOT_AUTOMATIC_MATCH"],flush=True)

if __name__=="__main__":main()
