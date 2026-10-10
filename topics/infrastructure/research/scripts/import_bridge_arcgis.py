#!/usr/bin/env python3
"""Candidate ONLY: aggregate geocoded BASt-derived 2025-09 ArcGIS point inventory.

The public ArcGIS publisher explicitly drops non-geocoded BASt records. The
result cannot be called a complete official 16-state bridge census and MUST
NOT modify state_scores_2025.json.
"""
from __future__ import annotations
import datetime as dt
import json
import os
import pathlib
import time
import unicodedata
import urllib.parse
import urllib.request
from collections import defaultdict

BASE = ("https://services2.arcgis.com/jUpNdisbWqRpMo35/arcgis/rest/services/"
        "Br%C3%BCckenstatistik_Deutschland/FeatureServer/0")
DEST = pathlib.Path(__file__).resolve().parents[1] / "candidate_bridge_arcgis_2025.json"
STATE_MAP = {
 "BADEN-WURTTEMBERG":"DE-BW", "BAYERN":"DE-BY", "BERLIN":"DE-BE",
 "BRANDENBURG":"DE-BB", "BREMEN":"DE-HB", "HAMBURG":"DE-HH",
 "HESSEN":"DE-HE", "MECKLENBURG-VORPOMMERN":"DE-MV",
 "NIEDERSACHSEN":"DE-NI", "NORDRHEIN-WESTFALEN":"DE-NW",
 "RHEINLAND-PFALZ":"DE-RP", "SAARLAND":"DE-SL",
 "SACHSEN":"DE-SN", "SACHSEN-ANHALT":"DE-ST",
 "SCHLESWIG-HOLSTEIN":"DE-SH", "THURINGEN":"DE-TH",
}
FIELDS = "OBJECTID,id_nr,bl,kreis,zn,zustandsnotenklasse,flaeche,trag_l_idx,jahr_letzte_hauptpruefung,baujahr,teil_der_bast_liste,status_der_nr,teil_bw_stadium"
def http_json(params):
    url = BASE + "/query?" + urllib.parse.urlencode(params)
    last = None
    for retry in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent":"GermanMapResearch/2026-10-10","Accept":"application/json"})
            with urllib.request.urlopen(req, timeout=50) as response:
                data = json.load(response)
            if isinstance(data,dict) and "error" in data:
                raise RuntimeError(str(data["error"])[:400])
            return data
        except Exception as exc:
            last = exc
            time.sleep(min(8, 1+2*retry))
    raise RuntimeError("ArcGIS endpoint inaccessible after retries: " + str(last))

def iso(value):
    raw = str(value or "").strip().replace("ß","ss")
    raw = unicodedata.normalize("NFKD",raw)
    raw = "".join(c for c in raw if not unicodedata.combining(c)).upper()
    return STATE_MAP.get(raw) or (("DE-"+raw) if len(raw)==2 and ("DE-"+raw) in STATE_MAP.values() else (raw if raw in STATE_MAP.values() else None))

def num(value):
    try:
        x = float(value)
        return x if x == x else None
    except (TypeError, ValueError):
        return None

def summarize(rows, expected):
    stats = defaultdict(lambda:dict(features=0,condition_valid=0,condition_bad=0,
      area_condition_valid_m2=0.0,area_condition_bad_m2=0.0,
      condition_missing=0,area_missing_or_invalid=0,tli_valid=0,tli_bad=0,raw_tenths_grade_count=0,
      inspections_year_present=0,county_present=0))
    unknown = defaultdict(int)
    missing_state = 0
    missing_grade_reason = defaultdict(int)
    listed_grade_present = defaultdict(lambda: [0,0])
    invalid_zn_values = defaultdict(int)
    source_grade_class_crosscheck = defaultdict(lambda: {"total":0,"decoded_min":None,"decoded_max":None,"poor":0})
    county_stats = defaultdict(lambda:{"features":0,"poor_features":0,"valid_area_m2":0.0,"poor_area_m2":0.0})
    county_missing_by_state = defaultdict(int)
    ids = set()
    for record in rows:
        a=record["attributes"]
        rid=a.get("OBJECTID")
        if rid in ids:raise RuntimeError("duplicate ArcGIS OBJECTID")
        ids.add(rid)
        key=iso(a.get("bl"))
        if not key:
            if a.get("bl") in (None,"", "None"):
                missing_state+=1
            else:
                unknown[str(a.get("bl"))]+=1
            continue
        t=stats[key]
        t["features"]+=1
        district_name=str(a.get("kreis") or "").strip()
        if district_name:t["county_present"]+=1
        else:county_missing_by_state[key]+=1
        if num(a.get("jahr_letzte_hauptpruefung")) is not None:t["inspections_year_present"]+=1
        raw_grade=num(a.get("zn"))
        # ArcGIS numeric field appears to drop decimal point for non-whole values:
        # 11 -> 1.1, 23 -> 2.3. Hypothesis only until BASt original is matched.
        z=raw_grade
        if raw_grade is not None and 10<=raw_grade<=40 and raw_grade.is_integer():
            z=raw_grade/10
            t["raw_tenths_grade_count"]+=1
        elif raw_grade is not None and raw_grade>4:
            raise RuntimeError("Unrecognized condition-grade encoding "+repr(raw_grade))

        listing=str(a.get("teil_der_bast_liste") or "NULL")[:80]
        listed_grade_present[listing][0]+=1
        if z is not None and 1<=z<=4:listed_grade_present[listing][1]+=1
        if z is None:missing_grade_reason["null_or_non_numeric"]+=1
        elif z<1:missing_grade_reason["below_1"]+=1
        elif z>4:
            missing_grade_reason["above_4"]+=1
            invalid_zn_values[str(a.get("zn"))]+=1
        source_class=str(a.get("zustandsnotenklasse") or "UNSPECIFIED").strip()[:90]
        cross=source_grade_class_crosscheck[source_class]
        cross["total"]+=1
        cross["decoded_min"]=min(cross["decoded_min"],z) if cross["decoded_min"] is not None else z
        cross["decoded_max"]=max(cross["decoded_max"],z) if cross["decoded_max"] is not None else z
        if z>=3:cross["poor"]+=1
        area=num(a.get("flaeche"))
        valid_area = area is not None and 0 < area < 10000000
        if district_name:
            c=county_stats[(key,district_name)]
            c["features"]+=1
            if z>=3:c["poor_features"]+=1
            if valid_area:
                c["valid_area_m2"]+=area
                if z>=3:c["poor_area_m2"]+=area
        if not valid_area:t["area_missing_or_invalid"]+=1
        if z is None or not 1<=z<=4:
            t["condition_missing"]+=1
        else:
            t["condition_valid"]+=1
            if z>=3:t["condition_bad"]+=1
            if valid_area:
                t["area_condition_valid_m2"]+=area
                if z>=3:t["area_condition_bad_m2"]+=area
        tv=str(a.get("trag_l_idx") or "").upper().strip()
        if tv in {"I","II","III","IV","V"}:
            t["tli_valid"]+=1
            if tv in {"IV","V"}:t["tli_bad"]+=1
    if unknown:
        raise RuntimeError("Unknown/missing state labels - do not silently discard: "+json.dumps(unknown,ensure_ascii=False))
    if len(rows)!=expected or len(ids)!=expected:raise RuntimeError("incomplete source ID list")
    if len(stats)!=16:raise RuntimeError("Expected 16 geocoded states, got "+str(len(stats)))
    results=[]
    for key in sorted(stats):
        v=stats[key].copy()
        def ratio(a,b):return round(100*v[a]/v[b],3) if v[b] else None
        for k in ["area_condition_valid_m2","area_condition_bad_m2"]:
            v[k]=round(v[k],2)
        v.update(iso=key, condition_bad_pct_count=ratio("condition_bad","condition_valid"),
             condition_bad_pct_area=ratio("area_condition_bad_m2","area_condition_valid_m2"),
             tli_iv_v_pct_count=ratio("tli_bad","tli_valid"),
             condition_valid_pct_of_geocoded=ratio("condition_valid","features"))
        results.append(v)
    if sum(x["features"] for x in results)+missing_state!=expected:raise RuntimeError("state totals + missing attribution fail")
    county_rows=[]
    for (state_id,district_name),v in sorted(county_stats.items()):
        county_rows.append(dict(iso=state_id,kreis_source_label=district_name,
            features=v["features"],poor_features=v["poor_features"],
            poor_pct_count=round(100*v["poor_features"]/v["features"],3),
            valid_area_m2=round(v["valid_area_m2"],2),
            poor_area_m2=round(v["poor_area_m2"],2),
            poor_pct_area=round(100*v["poor_area_m2"]/v["valid_area_m2"],3) if v["valid_area_m2"] else None,
            small_denominator_warning=v["features"]<20))
    if sum(r["features"] for r in county_rows)+sum(county_missing_by_state.values())!=expected-missing_state:
        raise RuntimeError("county names and missing county counts do not reconcile with known state count")
    return results,missing_state,dict(missing_grade_reason),dict(listed_grade_present),dict(sorted(invalid_zn_values.items(),key=lambda x:-x[1])[:15]),dict(source_grade_class_crosscheck),county_rows,dict(county_missing_by_state)

def main():
    count=http_json({"f":"json","where":"1=1","returnCountOnly":"true"})
    expected=int(count.get("count",0))
    print("ArcGIS reported feature count",expected,flush=True)
    if not 10000 <= expected <= 100000:raise RuntimeError("Unexpected ArcGIS feature count "+str(expected))
    data=http_json({"f":"json","where":"1=1","returnIdsOnly":"true"})
    ids=data.get("objectIds")
    if not isinstance(ids,list) or len(set(ids))!=expected:raise RuntimeError("ID listing inconsistent with count")
    ids=sorted(ids)
    rows=[]
    for offset in range(0,len(ids),120):
        batch=ids[offset:offset+120]
        response=http_json({"f":"json","objectIds":",".join(map(str,batch)),"outFields":FIELDS,
                "returnGeometry":"false"})
        records=response.get("features")
        if not isinstance(records,list) or len(records)!=len(batch):
            raise RuntimeError("Partial response "+str(offset)+": expected "+str(len(batch))+" got "+str(len(records) if isinstance(records,list) else None))
        retrieved={x["attributes"]["OBJECTID"] for x in records}
        if retrieved!=set(batch):raise RuntimeError("ArcGIS returned wrong ID set")
        rows.extend(records)
        if offset%3600==0:print("Downloaded",len(rows),"/",expected,flush=True)
    results,unattributed,grade_gaps,listing_coverage,invalid_zn,class_crosscheck,county_rows,county_missing=summarize(rows,expected)
    output={
      "status":"candidate_geocoded_subset_not_full_BASt",
      "snapshot_claim":"2025-09",
      "retrieved_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
      "origin":"Third-party ArcGIS republishing of BASt federal-road bridge data",
      "source_url":BASE,
      "official_bast_source":"https://www.govdata.de/suche/daten/bruckenstatistik",
      "raw_feature_count":expected,
      "raw_grade_diagnostics":grade_gaps,
      "invalid_grade_top_values":invalid_zn,
      "official_grade_class_crosscheck":class_crosscheck,
      "source_list_membership_grade_coverage":listing_coverage,
      "quality_verdict":"ArcGIS integer-tenths encoding provisionally corrected; source calibration and full BASt coverage not yet proven",
      "do_not_use_for_choropleth":True,
      "grade_decoding_hypothesis":"ArcGIS raw 11 treated provisionally as DIN 1.1, 23 as DIN 2.3; must cross-check official BASt export",
      "attributed_state_feature_count":expected-unattributed,
      "missing_state_feature_count":unattributed,
      "attributed_state_feature_pct":round(100*(expected-unattributed)/expected,3),
      "states":results,
      "excluded_records":"Original BASt records with no coordinates are omitted by ArcGIS publisher; exclusion counts UNKNOWN",
      "geometry_scope":"Federal motorway and Bundesstraße bridge point features; NOT states' road bridges, municipal, or railway bridges",
      "measurement":"DIN 1076 inspection condition poor if >=3.0; TLI IV/V is a SEPARATE capacity measure",
      "weight":"bridge area m2 among records with valid condition and valid area",
      "not_for_score":True
    }
    county_output={
      "status":"candidate_source_labels_not_geographical_polygon_join",
      "snapshot_claim":"2025-09",
      "retrieved_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
      "source_url":BASE,
      "district_label_meaning":"Unvalidated literal ArcGIS kreis field, not official AGS; no administrative geometry association was performed",
      "missing_county_name_by_state":county_missing,
      "small_denominator_flag_below":20,
      "do_not_use_for_choropleth":True,
      "not_for_score":True,
      "counties":county_rows
    }
    county_file=DEST.parent / "candidate_bridge_counties_arcgis_2025.json"
    DEST.parent.mkdir(parents=True,exist_ok=True)
    county_file.write_text(json.dumps(county_output,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("County source-label groups:",len(county_rows),"no county:",sum(county_missing.values()),flush=True)
    DEST.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("SUCCESS candidate bridge metrics:",str(DEST),"features:",expected,"states:",len(results),flush=True)
    for a in sorted(results,key=lambda x:x["condition_bad_pct_area"] or -1,reverse=True):
        print(a["iso"],a["condition_bad_pct_count"],a["condition_bad_pct_area"],a["features"],flush=True)

if __name__=="__main__":
    main()
