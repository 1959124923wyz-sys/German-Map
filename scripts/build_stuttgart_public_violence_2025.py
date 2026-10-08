#!/usr/bin/env python3
"""Build Stuttgart 2025 PUBLIC-SPACE violence CASE COUNTS (not general PKS violence).

Official source: Baden-Württemberg Landtag DS 17/10292 pages 3-5;
data are not a per-100k rate nor the city's overall violent-crime series.
Municipal polygons from Stuttgart's original 23-Stadtbezirk GeoPackage.
Never substitute unspecified citywide cases into districts.
"""
from __future__ import annotations
import argparse,io,json,re,unicodedata
from pathlib import Path
from pypdf import PdfReader
from city_build_common import download_bytes,write_geojson

URL="https://www.landtag-bw.de/resource/blob/620460/1a5fd7fcd9c3aea2600f92f0fca27952/17_10292_D.pdf"
GEO="artifacts/stuttgart_district_boundaries_candidate.geojson"
DEST="data/stuttgart_public_violence_2025.geojson"
# Source table order (not municipality polygon/GPKG feature order).
ORDER=[
 "Nord","Mitte","Ost","West","Süd","Bad Cannstatt","Birkach","Botnang",
 "Degerloch","Feuerbach","Hedelfingen","Möhringen","Mühlhausen","Münster",
 "Obertürkheim","Plieningen","Sillenbuch","Stammheim","Untertürkheim",
 "Vaihingen","Wangen","Weilimdorf","Zuffenhausen"
]
CASE_ROW=re.compile(r"(?m)^[^\n]*?\bGewaltkriminalität[ \t]+(\d[\d.]*)[ \t]+(\d{1,3},\d)")
SUBGROUP={
    "public_robbery":re.compile(r"(?m)^[^\n]*?\bRaub/räub\.[^\n]*?[ \t]+(\d[\d.]*)[ \t]+\d{1,3},\d"),
    "public_serious_injury":re.compile(r"(?m)^[^\n]*?\bgefährliche/schwere Körperverletzung[ \t]+(\d[\d.]*)[ \t]+\d{1,3},\d")
}
def norm(value):
    txt=unicodedata.normalize("NFKC",str(value)).casefold().replace("ß","ss")
    return re.sub(r"[^a-z0-9äöü]+","",txt)
def intval(s):
    return int(s.replace(".",""))

def police_rows(data):
    r=PdfReader(io.BytesIO(data))
    if len(r.pages)<5:raise ValueError("official Landtag PDF truncated")
    t="\n".join((r.pages[i].extract_text(extraction_mode="layout") or "") for i in (2,3,4))
    match=list(CASE_ROW.finditer(t))
    if len(match)!=24:
        raise ValueError(f"Landtag official table changed: expected 1 city+23 districts, found {len(match)} rows")
    result=[]
    for ix,m in enumerate(match):
        sub=t[m.end():match[ix+1].start() if ix+1<len(match) else len(t)]
        values={"public_violence":intval(m.group(1))}
        for metric,pattern in SUBGROUP.items():
            hits=list(pattern.finditer(sub))
            if len(hits)!=1:
                raise ValueError(f"Landtag row {ix} has {len(hits)} values for {metric}")
            values[metric]=intval(hits[0].group(1))
        if values["public_serious_injury"]>values["public_violence"] or values["public_robbery"]>values["public_violence"]:
            raise ValueError(f"Landtag bad category counts: {ix}, {values}")
        if ix>0:
            name=ORDER[ix-1]
            # In this PDF the left geographic label is often printed AFTER
            # the numeric Gewaltkriminalität row, in the same statistical
            # block as that district's detailed offences.
            context=sub
            if any(norm(part) not in norm(context) for part in name.split()):
                raise ValueError(f"Landtag district name mismatch at {ix}: expected {name}; excerpt={context[:620]!r}")
            result.append({"name":name,"metrics":values})
        else:
            if values!={"public_violence":1636,"public_robbery":358,"public_serious_injury":1243}:
                raise ValueError(f"Landtag Stuttgart city total changed: {values}")
    assert len(result)==23
    totals={metric:sum(row["metrics"][metric] for row in result) for metric in ("public_violence","public_robbery","public_serious_injury")}
    city={"public_violence":1636,"public_robbery":358,"public_serious_injury":1243}
    if any(totals[k]>city[k] for k in city):raise ValueError(f"districts exceed city total {totals}")
    print("[stuttgart-2025] source table parsed",json.dumps({
        "districts":23,"citywide":city,"assigned":totals,
        "not_assigned":{k:city[k]-totals[k] for k in city},
        "sample":result[:3]},ensure_ascii=False),flush=True)
    return result,city

def build(path,release):
    data=download_bytes(URL,timeout=65)
    assert data.startswith(b"%PDF-")
    rows,city=police_rows(data)
    geo=json.loads(Path(GEO).read_text(encoding="utf-8"))
    if geo["meta"].get("status")!="candidate_geometry_only" or geo["meta"].get("districts")!=23 or geo["meta"].get("overlap_m2")!=0:
        raise ValueError("Stuttgart municipality geometry QA missing")
    byname={norm(row["name"]):row for row in rows}
    features=[]
    seen=set()
    for f in geo["features"]:
        p=f["properties"]
        key=norm(p["name"])
        if key not in byname or key in seen:
            raise ValueError(f"Missing/duplicate police district match: {p['name']}")
        seen.add(key)
        entry=byname[key]
        props={**p,"year":2025,"public_space_only":True,"metrics":{
            k:{"2025":v,"rate":None} for k,v in entry["metrics"].items()}}
        features.append({**f,"properties":props})
    if len(seen)!=23:raise ValueError("Not all 23 police districts matched")
    district_totals={k:sum(f["properties"]["metrics"][k]["2025"] for f in features) for k in city}
    result={"type":"FeatureCollection",
      "meta":{
       "status":"supplementary_public_violence_count_only" if release else "candidate_public_violence_count_only",
       "year":2025,"city":"Stuttgart","metric_scope":"public_space_violent_crime_only_NOT_all_violence",
       "metric_names":{"public_violence":"公共场所暴力犯罪（PKS Gewaltkriminalität im öffentlichen Raum）",
          "public_robbery":"公共场所抢劫及暴力勒索","public_serious_injury":"公共场所危险及严重伤害"},
       "source":URL,"official_geometry_source":geo["meta"]["source_url"],
       "source_coverage":"Baden-Württemberg Landtag DS 17/10292 printed pages 3-5",
       "districts":23,"area_km2":geo["meta"]["area_km2"],
       "city_totals":city,"mapped_totals":district_totals,
       "unlocated_city_cases":{k:city[k]-district_totals[k] for k in city},
       "no_population_rates":True,
       "limitation":"Counts of crimes in PUBLIC SPACE only; they are not the PKS all-settings Gewaltkriminalität category. Unallocated city cases do not map to districts."
      },
      "features":features}
    if release and str(path)!=DEST:raise ValueError("only exact supplemental public file is permitted")
    if not release and str(path).startswith("data/"):raise ValueError("research draft cannot activate public map")
    write_geojson(path,result)
    print("[stuttgart-2025] joined official 23-area data",json.dumps({"public":release,
        "mapped":district_totals,"unlocated":result["meta"]["unlocated_city_cases"]},ensure_ascii=False),flush=True)
    return result

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--output",default="artifacts/stuttgart_violence_candidate.geojson")
    a.add_argument("--release-count-only",action="store_true")
    args=a.parse_args()
    build(args.output,args.release_count_only)
