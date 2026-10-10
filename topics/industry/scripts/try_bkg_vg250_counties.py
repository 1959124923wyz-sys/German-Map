#!/usr/bin/env python3
"""Fetch and validate BKG VG250 county geometry as a RESEARCH CANDIDATE only.

Never publishes over main/shared data/germany-counties.geojson.
ArcGIS layer based on BKG 2025 data. 400 canonical Kreis AGS must match the
research crosswalk. Fail closed on any short/long/suppressed response.
"""
import argparse
import datetime as dt
import json
import pathlib
import sys
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
API = "https://tigis.bkg.bund.de/hosting/rest/services/VG250_KREISE25_Punkte_Grenzen/MapServer/0/query"
META = "https://gdz.bkg.bund.de/index.php/default/wfs-verwaltungsgebiete-1-250-000-stand-01-01-wfs-vg250.html"
STATES = {
 "01":"Schleswig-Holstein","02":"Hamburg","03":"Niedersachsen",
 "04":"Bremen","05":"Nordrhein-Westfalen","06":"Hessen",
 "07":"Rheinland-Pfalz","08":"Baden-Württemberg","09":"Bayern",
 "10":"Saarland","11":"Berlin","12":"Brandenburg",
 "13":"Mecklenburg-Vorpommern","14":"Sachsen",
 "15":"Sachsen-Anhalt","16":"Thüringen",
}

def run(out):
    params = {
       "where": "1=1", "outFields": "AGS,GEN,BEZ,GF",
       "returnGeometry": "true", "outSR": "4326",
       "f": "geojson", "geometryPrecision": "5",
       "maxAllowableOffset": "0.001",
    }
    url=API+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"User-Agent":"German-Map-industry-research/1.0 (public statistical geography)","Accept":"application/geo+json,application/json"})
    with urllib.request.urlopen(req, timeout=65) as handle:
        data=handle.read(22_000_000)
        if handle.read(1): raise ValueError("Response >22MB; do not silently truncate")
    obj=json.loads(data)
    if obj.get("error"): raise ValueError("ArcGIS returned error: "+json.dumps(obj["error"],ensure_ascii=False))
    features=obj.get("features", [])
    crosswalk=json.loads((ROOT/"data/ags-crosswalk-402-to-400.json").read_text(encoding="utf-8"))
    canonical={e["canonical_ags"] for e in crosswalk["features"]}
    if len(canonical)!=400: raise ValueError("Reference modern AGS count is not 400")
    seen=set()
    cleaned=[]
    for feat in features:
        p=feat.get("properties") or {}
        ags=str(p.get("AGS","")).strip()
        if len(ags)!=5 or not ags.isdigit(): raise ValueError(f"Bad AGS: {ags!r} {p}")
        if ags in seen: raise ValueError("Duplicate canonical AGS "+ags)
        seen.add(ags)
        name=p.get("GEN")
        if not name or not str(name).strip(): raise ValueError("Empty county name for "+ags)
        if (feat.get("geometry") or {}).get("type") not in {"Polygon","MultiPolygon"}: raise ValueError("Missing polygon for "+ags)
        if ags[:2] not in STATES: raise ValueError("Bad state code "+ags)
        # Same minimal properties as site static old geometries.
        cleaned.append({"type":"Feature","id":ags,"properties":{
          "name":name,"state":STATES[ags[:2]],"districtType":p.get("BEZ") or "Kreis",
          "ags":ags,"official_source":"BKG VG250 Kreise 01.01.2025"
        },"geometry":feat["geometry"]})
    if len(cleaned)!=400 or seen!=canonical:
        raise ValueError("BKG geometries not safely usable. count="+str(len(cleaned))+
                         " missing="+str(sorted(canonical-seen)[:15])+
                         " extra="+str(sorted(seen-canonical)[:15]))
    cleaned.sort(key=lambda x:x["id"])
    record={"type":"FeatureCollection","_provenance":{
      "publisher":"Bundesamt für Kartographie und Geodäsie","product":"VG250 Kreise",
      "effective_date":"2025-01-01","obtained_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
      "source_api":API,"source_metadata":META,"query":params,
      "geometry_note":"ArcGIS query maxAllowableOffset 0.001° for map rendering; no exact surveyed boundaries promised",
      "license":"Data licence Germany attribution 2.0 dl-de/by-2-0",
      "credit":"© BKG (2026) dl-de/by-2-0; https://www.bkg.bund.de; https://www.govdata.de/dl-de/by-2-0",
      "status":"candidate_only_no_website_swap",
      "validated":True,"feature_count":400},"features":cleaned}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(record,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    print(json.dumps({"source":"BKG VG250 Kreis 2025","status":"validated_candidate","districts":400,"output":str(out),"bytes":out.stat().st_size}))
    return 0

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=pathlib.Path,default=ROOT/"data/bkg_vg250_counties_2025_candidate.geojson")
    a=parser.parse_args()
    try: sys.exit(run(a.out))
    except Exception as exc:
        print("BKG research candidate failed; NO geojson published: "+str(exc),file=sys.stderr)
        sys.exit(4)
