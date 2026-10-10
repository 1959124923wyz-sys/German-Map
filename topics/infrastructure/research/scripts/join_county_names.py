#!/usr/bin/env python3
"""Conservative join of 2025 BASt source county labels to German-Map's 402 polygons.

Important: the existing geometry has county names, district types, state and
car licence codes but NO official AGS. DO NOT fake AGS, confuse an independent
urban city with similarly named Landkreis, or join out-of-state records.
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
STATES={"Baden-Württemberg":"DE-BW","Bayern":"DE-BY","Berlin":"DE-BE",
"Brandenburg":"DE-BB","Bremen":"DE-HB","Hamburg":"DE-HH","Hessen":"DE-HE",
"Mecklenburg-Vorpommern":"DE-MV","Niedersachsen":"DE-NI","Nordrhein-Westfalen":"DE-NW",
"Rheinland-Pfalz":"DE-RP","Saarland":"DE-SL","Sachsen":"DE-SN","Sachsen-Anhalt":"DE-ST",
"Schleswig-Holstein":"DE-SH","Thüringen":"DE-TH"}
AGS_STATE_PREFIX={"DE-SH":"01","DE-HH":"02","DE-NI":"03","DE-HB":"04","DE-NW":"05","DE-HE":"06","DE-RP":"07","DE-BW":"08","DE-BY":"09","DE-SL":"10","DE-BE":"11","DE-BB":"12","DE-MV":"13","DE-SN":"14","DE-ST":"15","DE-TH":"16"}
PREFIXES=("kreisfreie stadt ","kfr stadt ","kfr. stadt ","stadtkreis ",
"landeshauptstadt ","hansestadt ","stadt ","landkreis ","landkr ","landkr. ","lk ","kreis ")
SUFFIXES=(", kreisfreie stadt",", hansestadt",", landeshauptstadt",", stadt")
# Disambiguating aliases are explicit and still require an *exact* unique
# name + administrative TYPE match in the SAME federal state.
ALIASES={
 ("DE-BW","ostalb"):"ostalbkreis",
 ("DE-BW","freiburg"):"freiburg im breisgau",
 ("DE-BY","neumarkt i d opf"):"neumarkt in der oberpfalz",
 ("DE-BY","neustadt a d waldnaab"):"neustadt an der waldnaab",
 ("DE-BY","pfaffenhofen a d ilm"):"pfaffenhofen an der ilm",
 ("DE-BY","muehldorf a inn"):"muehldorf am inn",
 ("DE-BY","wunsiedel i fichtelgebirge"):"wunsiedel im fichtelgebirge",
 ("DE-BY","dillingen a d donau"):"dillingen an der donau",
 ("DE-BY","weiden i d opf"):"weiden in der oberpfalz",
 ("DE-BY","neustadt a d aisch bad windsheim"):"neustadt an der aisch bad windsheim",
 ("DE-HE","frankfurt main"):"frankfurt am main",
 ("DE-RP","neustadt weinstrasse"):"neustadt an der weinstrasse",
 ("DE-RP","altenkirchen"):"altenkirchen westerwald",
 ("DE-TH","altenburg"):"altenburger land"
}

def simplify(s):
    s=s.replace("ß","ss").replace("ẞ","ss")
    for a,b in (("ä","ae"),("ö","oe"),("ü","ue"),
                ("Ä","Ae"),("Ö","Oe"),("Ü","Ue")):s=s.replace(a,b)
    s=unicodedata.normalize("NFKD",s.casefold())
    s="".join(c for c in s if not unicodedata.combining(c))
    s=s.replace("&"," und ").replace("–","-").replace("—","-")
    s=re.sub(r"[\s_,.;:/()'\-]+"," ",s).strip()
    return re.sub(r"\s+"," ",s)

def classify_source(raw):
    s=simplify(raw)
    if re.search(r"(^| )kreisfreie stadt |^kfr stadt |^stadt | stadt$|^landeshauptstadt |^hansestadt | hansestadt$| landeshauptstadt$|^stadtkreis ",s):
        return "urban"
    if re.search(r"^landkreis |^landkr |^lk |^kreis ",s):return "rural"
    return None

def classify_shape(district_type):
    s=simplify(district_type)
    if "kreisfrei" in s or "stadtkreis" in s:return "urban"
    if "landkreis" in s or s=="kreis":return "rural"
    return None

def strip_titles(raw):
    s=simplify(raw)
    for prefix in PREFIXES:
        p=simplify(prefix)
        if s.startswith(p+" "):s=s[len(p)+1:].strip();break
    for suffix in SUFFIXES:
        q=simplify(suffix)
        if s.endswith(" "+q):s=s[:-len(q)-1].strip();break
    return s

def main():
    raw=json.loads((R/"candidate_bridge_counties_arcgis_2025.json").read_text())["counties"]
    source_total=sum(x["features"] for x in raw)
    shapes=json.loads((ROOT/"data/germany-counties.geojson").read_text())["features"]
    geometry=[]
    seen_ags=set()
    for i,f in enumerate(shapes):
        p=f["properties"];st=STATES.get(p["state"])
        if not st:raise RuntimeError("Unexpected geometry state "+str(p["state"]))
        # AGS is a top-level GeoJSON Feature.id, NOT properties.AGS.
        source_ags=str(f.get("id") or "").strip()
        ags=source_ags.zfill(5) if source_ags.isdigit() and len(source_ags) in (4,5) else source_ags
        if not re.fullmatch(r"\d{5}",ags):
            raise RuntimeError("County geometry missing verifiable 5-digit AGS at index "+str(i)+": "+repr(source_ags))
        if ags[:2]!=AGS_STATE_PREFIX[st]:raise RuntimeError("AGS/state mismatch: "+ags+" "+st)
        if ags in seen_ags:raise RuntimeError("Duplicate AGS "+ags)
        seen_ags.add(ags)
        geometry.append(dict(shape_index=i,name=p["name"],state_iso=st,
            district_type=p["districtType"],kfz=p.get("kfz"),ags=ags,
            class_=classify_shape(p["districtType"])))
    by_name=collections.defaultdict(list)
    for g in geometry:by_name[(g["state_iso"],simplify(g["name"]))].append(g)
    matched=[];unmatched=[]
    for source in raw:
        state=source["iso"]; rawlabel=source["kreis_source_label"]
        sname=strip_titles(rawlabel)
        aliased=ALIASES.get((state,sname),sname)
        expected_type=classify_source(rawlabel)
        options=by_name.get((state,aliased),[])
        options=[o for o in options if expected_type is None or o["class_"]==expected_type]
        if len(options)==1:
            g=options[0]
            matched.append({**source,"geometry_feature_index":g["shape_index"],
                "geometry_name":g["name"],"geometry_state_iso":g["state_iso"],
                "geometry_district_type":g["district_type"],"kfz_NOT_AGS":g["kfz"],
                "join_method":"explicit_same_state_type_and_alias" if aliased!=sname
                    else "same_state_exact_normalized_name_type",
                "source_implied_type":expected_type,"official_AGS":g["ags"],
                "AGS_from_historical_geometry_not_revalidated_current":True})
        else:
            siblings=[v["name"] for v in geometry if v["state_iso"]==state]
            suggestions=difflib.get_close_matches(rawlabel,siblings,n=3,cutoff=.34)
            unmatched.append({**source,"reason":"same_name_type_collision" if len(options)>1 else
                "unmatched_name_or_admin_type",
                "implied_admin_type":expected_type,
                "normalized_name":aliased,
                "suggestions_ONLY_no_autojoin":suggestions,
                "actual_exact_name_geometry_types":[g["district_type"] for g in by_name.get((state,aliased),[])]})
    grouped=collections.defaultdict(list)
    for m in matched:grouped[m["geometry_feature_index"]].append(m)
    multi={}
    for i,items in grouped.items():
        if len(items)>1:multi[geometry[i]["name"]+"|"+geometry[i]["state_iso"]]=[x["kreis_source_label"] for x in items]
    matched_count=sum(x["features"] for x in matched)
    unmatched_count=sum(x["features"] for x in unmatched)
    assert matched_count+unmatched_count==source_total
    assert not any(x["source_implied_type"] and
      x["source_implied_type"]!=classify_shape(x["geometry_district_type"]) for x in matched)
    assert all(re.fullmatch(r"\d{5}",x["official_AGS"]) for x in matched)
    result={"source_data_year":"2025-09",
        "status":"CANDIDATE_TYPE_SAFE_NAME_JOIN_NOT_OFFICIAL_AGS",
        "polygon_file":"data/germany-counties.geojson",
        "polygon_has_AGS":True,
        "ags_verified_by":"GeoJSON top-level Feature.id, checked 402 codes unique and 16 state numeric prefixes",
        "geometry_blob_sha":"d4fb08f16444b40b462ba26beb4d4c97cf236888",
        "matching_upstream":"https://github.com/m-ad/geofeatures-ags-germany/blob/master/geojson/counties.json",
        "upstream_same_blob_sha_confirmed":True,
        "ags_2026_currency":"UNVERIFIED: historical AGS source may predate 2025 boundary changes; current BKG WFS probe timed out",
        "join_safety":"same state + exact normalized name + administrative type; AGS from the exact same historic GeoJSON Feature.id; 2025 administrative validity not yet certified",
        "geometry_count":len(geometry),"source_groups":len(raw),
        "matched_source_groups":len(matched),
        "matched_unique_county_polygons":len(grouped),
        "unmatched_source_groups":len(unmatched),
        "matched_source_features":matched_count,
        "unmatched_source_features":unmatched_count,
        "multi_source_group_geometry":multi,
        "joined":matched,"unmatched":unmatched}
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print("Matched",len(matched),"groups covering",len(grouped),"polygons,",
        matched_count,"bridge substructures; unmatched",len(unmatched),"groups/",unmatched_count,"parts",flush=True)
    print("Multiple source names for one shape",multi,flush=True)
    for x in sorted(unmatched,key=lambda x:-x["features"])[:24]:
        print("UNMATCHED",x["iso"],x["kreis_source_label"],x["features"],x["normalized_name"],flush=True)

if __name__=="__main__":main()
