#!/usr/bin/env python3
"""Acquire BKG official 31 Dec 2025 VG250 county boundary and AGS registry.

Does not touch production data. Reads BKG freely licensed (dl-de/by-2-0)
geopackage from official direct ZIP and produces county-only GeoJSON with
provenance, optional topology-preserving display generalization (separate),
AGS keys, names, and a comprehensive shape validation audit.
"""
from __future__ import annotations
import datetime
import json
import os
import pathlib
import tempfile
import urllib.request
import zipfile
from collections import Counter
import geopandas as gpd
import pyogrio
from shapely.geometry import mapping, shape
from shapely.ops import unary_union
from shapely.validation import make_valid

ROOT=pathlib.Path(__file__).resolve().parents[4]
R=ROOT/"topics/infrastructure/research"
SOURCE_URL="https://daten.gdz.bkg.bund.de/produkte/vg/vg250_ebenen_1231/aktuell/vg250_12-31.utm32s.gpkg.ebenen.zip"
OUT=R/"germany-counties-bkg-official-2025.geojson"
AUDIT=R/"germany-counties-bkg-official-2025-audit.json"
STATE_MAP={"01":"DE-SH","02":"DE-HH","03":"DE-NI","04":"DE-HB",
"05":"DE-NW","06":"DE-HE","07":"DE-RP","08":"DE-BW","09":"DE-BY","10":"DE-SL",
"11":"DE-BE","12":"DE-BB","13":"DE-MV","14":"DE-SN","15":"DE-ST","16":"DE-TH"}

def val(row,k):
    v=row.get(k)
    if v is None:return None
    s=str(v).strip()
    if s.lower() in ("none","nan","null",""):return None
    return s

def main():
    with tempfile.TemporaryDirectory() as d:
        d=pathlib.Path(d)
        archive=d/"bkg_vg250.zip"
        req=urllib.request.Request(SOURCE_URL,headers={"User-Agent":"GermanMapResearch/2026-10-10 BKG official data attribution","Accept":"application/zip"})
        with urllib.request.urlopen(req,timeout=180) as reply,archive.open("wb") as fp:
            import shutil
            shutil.copyfileobj(reply,fp)
        with zipfile.ZipFile(archive) as z:
            names=z.namelist()
            gpkg_files=[x for x in names if x.lower().endswith(".gpkg")]
            if len(gpkg_files)!=1:raise RuntimeError("Expected single BKG GeoPackage: "+str(names[:45]))
            entry=gpkg_files[0]
            z.extract(entry,d)
        gpkg=d/entry
        available=pyogrio.list_layers(str(gpkg))
        print("Official BKG GeoPackage layers:",available.tolist(),flush=True)
        layers=[x[0] for x in available if "krs" in str(x[0]).lower()]
        if not layers:raise RuntimeError("No county KRS layer found")
        layer=layers[0]
        county=gpd.read_file(gpkg,layer=layer)
        print("KRS source features",len(county),"CRS",county.crs,"columns",county.columns.tolist(),flush=True)
        if not 390<=len(county)<=550:raise RuntimeError("Unexpected count of county features")
        assert county.crs is not None
        county=county.to_crs("EPSG:4326")
        keys={x.lower():x for x in county.columns}
        ags_col=keys.get("ags")
        if ags_col is None:raise RuntimeError("BKG AGS column not found: "+str(county.columns.tolist()))
        name_col=keys.get("gen")
        kind_col=keys.get("bez")
        if not name_col or not kind_col:raise RuntimeError("Missing official BKG GEN / BEZ fields")
        groups={}
        repairs=[]
        skipped=[]
        for _,r in county.iterrows():
            a=val(r,ags_col)
            if not a:skipped.append("null AGS");continue
            if a.endswith(".0") and a[:-2].isdigit():a=a[:-2]
            a=a.zfill(5)
            if len(a)!=5 or not a.isdigit() or a[:2] not in STATE_MAP:
                raise RuntimeError("Unexpected BKG AGS "+repr(a))
            g=r.geometry
            if g is None or g.is_empty:skipped.append(a+" null geometry");continue
            if not g.is_valid:
                repairs.append(a)
                g=make_valid(g)
            if not g.is_valid:raise RuntimeError("BKG make_valid did not fix "+a)
            if a not in groups:
                groups[a]={"AGS":a,"name":val(r,name_col),"districtType":val(r,kind_col),
                           "iso":STATE_MAP[a[:2]],"geometries":[g]}
            else:
                groups[a]["geometries"].append(g)
        if skipped:raise RuntimeError("Official BKG records skipped: "+repr(skipped[:30]))
        if len(groups)!=400:raise RuntimeError("Expected 400 county AGS, found "+str(len(groups)))
        assert all(len(a)==5 and a[:2] in STATE_MAP for a in groups)
        features=[]
        generalization_delta=[]
        for a,item in sorted(groups.items()):
            geo=unary_union(item["geometries"])
            if not geo.is_valid:geo=make_valid(geo)
            if geo.is_empty or not geo.is_valid:raise RuntimeError("Bad county geometry "+a)
            features.append({"type":"Feature","id":a,
                "properties":{"ags":a,"name":item["name"],"districtType":item["districtType"],"iso":item["iso"],
                    "source_layer":layer,"source_date":"2025-12-31"},
                "geometry":mapping(geo)})
        # No simplification: preserves the official geometry in the separate research dataset.
        output={"type":"FeatureCollection","metadata":{
            "status":"BKG_OFFICIAL_VG250_2025_COUNTY_RESEARCH_COPY_NOT_YET_PRODUCTION",
            "publisher":"Bundesamt für Kartographie und Geodäsie (BKG)",
            "snapshot":"2025-12-31",
            "source_download":SOURCE_URL,
            "official_product_page":"https://gdz.bkg.bund.de/index.php/default/digitale-geodaten/verwaltungsgebiete/verwaltungsgebiete-1-250-000-stand-31-12-vg250-31-12.html",
            "required_attribution":"© BKG (2026) dl-de/by-2-0; see original BKG product attribution and providers",
            "source_crs":str(gpd.read_file(gpkg,layer=layer,rows=1).crs),
            "display_crs":"EPSG:4326",
            "site_main_boundary_replaced":False},
            "features":features}
        OUT.write_text(json.dumps(output,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
        by_state=dict(Counter(v["iso"] for v in groups.values()))
        AUDIT.write_text(json.dumps({
            "status":"OFFICIAL_2025_12_31_BKG_COUNTY_GEOMETRY_VERIFIED",
            "source_zip":SOURCE_URL,"source_layer":layer,
            "source_columns":county.columns.tolist(),"source_rows":len(county),
            "unique_AGS_count":len(groups),"merged_duplicate_AGS_source_rows":len(county)-len(groups),
            "invalid_source_features_repaired":repairs,
            "AGS_state_prefix_distribution":by_state,
            "file_bytes":OUT.stat().st_size,
            "license":"dl-de/by-2-0 attribution with BKG and data providers",
            "note":"BKG official 1:250,000 generalized administrative boundaries, not cadastral precision",
            "output":str(OUT.relative_to(ROOT))
        },indent=2,ensure_ascii=False)+"\n")
        print("BKG 2025 county AGS",len(groups),"bad source geometry",len(repairs),
              "GeoJSON bytes",OUT.stat().st_size,flush=True)

if __name__=="__main__":main()
