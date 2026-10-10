#!/usr/bin/env python3
"""Fetch independent exact-2024 official BKG county geometry for housing map.

Keep the existing German-Map 402 historical polygons UNTOUCHED. This self-owned
GeoJSON uses the Bundesamt für Kartographie und Geodäsie's Deutschlandatlas
2024 county map layer. Require the official 400 county IDs to match the
Deutschlandatlas 2026 CSV exactly or publish NOTHING.
"""
from __future__ import annotations
import csv
import gzip
import hashlib
import json
import math
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from shapely.geometry import shape

ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/"research/housing/raw"
QA=ROOT/"research/housing/qa"
OUT=ROOT/"topics/housing/data"
SERVICE="https://tigis.bkg.bund.de/hosting/rest/services/hh_veink_ZA2026/MapServer/5"
SOURCE_PAGE="https://deutschlandatlas.bund.de/karten/wie-wir-arbeiten/verfuegbares-einkommen"
LICENSE="https://www.govdata.de/dl-de/by-2-0"
DATA_SOURCES="https://sgx.geodatenzentrum.de/web_public/gdz/datenquellen/datenquellen_vg_nuts.pdf"
CSV_SOURCE=RAW/"deutschlandatlas_krs2024_ha26.csv"

def json_request(q):
    url=SERVICE+"/query?"+urllib.parse.urlencode(q)
    req=urllib.request.Request(url,headers={"User-Agent":"GermanMapHousingResearch/1.0 (official public map data)"})
    with urllib.request.urlopen(req,timeout=110) as r:
        data=r.read()
        print("FETCH",r.status,len(data),"bytes from official GIS source",flush=True)
    if len(data)<50_000:raise ValueError("Unreasonably small 400-feature polygon response")
    obj=json.loads(data)
    if not isinstance(obj,dict) or obj.get("error"):
        raise ValueError(f"GeoJSON service error {str(obj)[:2000]}")
    return obj,data

def ags_csv():
    if not CSV_SOURCE.exists():raise FileNotFoundError("Run official HA26 intake before geometry generation")
    txt=CSV_SOURCE.read_bytes().decode("cp1252")
    rows=csv.reader(txt.splitlines(),delimiter=";")
    header=next(rows)
    if header[0].lower().strip()!="regionalschlüssel":
        raise ValueError("Wrong official county CSV schema")
    ids=set()
    for row in rows:
        if row and row[0].isdigit():
            s=row[0].zfill(8)[:5]
            if s in ids:raise ValueError(f"Duplicated HA26 official county {s}")
            ids.add(s)
    if len(ids)!=400:raise ValueError(f"Expected 400 HA26 county IDs; got {len(ids)}")
    return ids

def main():
    expected=ags_csv()
    geo,raw=json_request({"where":"1=1","outFields":"Gebietskennziffer,GEN,BEZ,name",
               "returnGeometry":"true","outSR":4326,"f":"geojson",
               "geometryPrecision":5})
    if geo.get("type")!="FeatureCollection":
        raise ValueError(f"BKG endpoint did not return GeoJSON: {str(geo)[:400]}")
    features=geo.get("features",[])
    if len(features)!=400:
        raise ValueError(f"BKG geometry did not deliver 400 regions: {len(features)}")
    seen=set();bad=[];bytype=Counter()
    for f in features:
        props=f.get("properties") or {}
        code=props.get("Gebietskennziffer")
        if code is None:raise ValueError(f"BKG geometry missing Gebietsschlüssel; {props}")
        code=str(int(code)).zfill(5)
        if code in seen:raise ValueError(f"Repeated Landkreis {code}")
        seen.add(code)
        name=props.get("name") or props.get("GEN") or code
        geom=f.get("geometry")
        if not geom or geom.get("type") not in ("Polygon","MultiPolygon"):
            raise ValueError(f"Unsupported geometry at {code}: {geom and geom.get('type')}")
        g=shape(geom)
        if g.is_empty or not g.is_valid or g.area<1e-7:
            bad.append({"id":code,"reason":"invalid or empty geometry","bounds":g.bounds})
        xmin,ymin,xmax,ymax=g.bounds
        if not (5<=xmin<=16 and 5<=xmax<=16 and 47<=ymin<=56 and 47<=ymax<=56):
            raise ValueError(f"Bad WGS84 bounds for {code}: {g.bounds}")
        bytype[geom["type"]]+=1
        f["id"]=code
        f["properties"]={"id":code,"name":name,"district_type":props.get("BEZ"),
                         "source_code":code}
    if bad:raise ValueError(f"BKG invalid geo features: {bad[:6]}")
    if seen!=expected:
        raise ValueError(f"County geometry != official 2024 districts: +{sorted(seen-expected)} -{sorted(expected-seen)}")
    features.sort(key=lambda f:f["id"])
    product={"type":"FeatureCollection","meta":{
         "publisher":"Bundesamt für Kartographie und Geodäsie (BKG)",
         "dataset":"VG250 administrative districts, county status 2024-12-31 via Deutschlandatlas BKG-hosted ArcGIS",
         "source":SERVICE,
         "atlas_indicator_page":SOURCE_PAGE,
         "license":"dl-de/by-2-0","license_url":LICENSE,
         "attribution":"© BKG (2026) dl-de/by-2-0, Datenquellen: "+DATA_SOURCES,
         "licensing_note":"For publishing hyperlink BKG https://www.bkg.bund.de and dl-de/by-2-0; show modification notice: derived simplification precision rounded to 5 decimal places, attributes reduced.",
         "geometry_changed":"Reduced coordinate precision to 5 decimals via official query, nonspatial attributes selected; no county polygons manually stretched or patched.",
         "administrative_vintage":"2024-12-31",
         "counties":400,
         "territorial_match":"Exact 400/400 five-digit AGS identity with Deutschlandatlas KRS1224 HA26 official CSV"},
       "features":features}
    compact=json.dumps(product,ensure_ascii=False,separators=(",",":"))
    if len(compact)>18_000_000:raise ValueError("Unexpectedly large housing map geometry")
    RAW.mkdir(parents=True,exist_ok=True);QA.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    (RAW/"bkg_counties_2024_arcgis_response.geojson.gz").write_bytes(gzip.compress(raw,compresslevel=9,mtime=0))
    (OUT/"germany-counties-2024.geojson").write_text(compact+"\n",encoding="utf-8")
    report={"source":SERVICE,"sha256_official_download":hashlib.sha256(raw).hexdigest(),
      "download_bytes":len(raw),"on_disk_output_bytes":len(compact.encode()),
      "districts":len(features),"match":len(seen & expected),"missing":sorted(expected-seen),
      "unexpected":sorted(seen-expected),"geometry_types":dict(bytype),
      "old_project_map_count":402,
      "old_project_map_unmatched":["03152","03156","16056"],
      "new_official_county_present":"03159" in seen,
      "attribution":product["meta"]["attribution"],
      "license_url":LICENSE,
      "notes":["Maps can now show all 400 official HA26 counties, versus only 399 of 402 older polygons",
        "Independent geometry is housing-specific and does not alter existing crime/finance maps",
        "The year 2022 indicators can be shown on 2024 county polygons with disclosure of geographic vintage"]}
    (QA/"bkg_2024_400_county_geometries.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("BKG 2024 COUNTY GEOMETRY PASS",len(features),"polygon identities match all HA26 districts; types",bytype)

if __name__=="__main__":main()
