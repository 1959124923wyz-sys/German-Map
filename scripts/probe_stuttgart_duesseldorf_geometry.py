#!/usr/bin/env python3
"""Verify exactly sourced municipal administrative polygons (candidate only).

Stuttgart source is municipal GeoPackage zipped by Stuttgart Stadtmessungsamt.
Düsseldorf official city-district boundaries are 2025 WGS84 GeoJSON.
No crime counts are attached; districts must never be shaded before an
independently verified district statistic exists.
"""
from __future__ import annotations
import io,json,sqlite3,zipfile,tempfile
from pathlib import Path
import requests

STUTTGART="https://www.stuttgart.de/medien/ibs/OpenData-KLGL-Generalsisiert.zip"
DUSSELDORF="https://opendata.duesseldorf.de/sites/default/files/Stadtbezirke_2025_WGS84_EPSG4326.geojson"
HTTP=requests.Session()
HTTP.headers.update({"User-Agent":"German-Map public geodata QA research (https://github.com/1959124923wyz-sys/German-Map)","Accept":"*/*"})

def get(url):
    r=HTTP.get(url,timeout=75)
    r.raise_for_status()
    if len(r.content)<1000:raise ValueError(f"source too short {len(r.content)}")
    return r.content

def stuttgart():
    content=get(STUTTGART)
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        files=z.namelist()
        gpkg=[name for name in files if name.lower().endswith(".gpkg")]
        out={"url":STUTTGART,"bytes":len(content),"zip_members":files[:16],"gpkg_count":len(gpkg)}
        if not gpkg:raise ValueError(f"Stuttgart official zip has no GPKG: {files[:30]}")
        with tempfile.TemporaryDirectory() as d:
            dst=Path(d)/"input.gpkg"
            with z.open(gpkg[0]) as src,dst.open("wb") as f:
                import shutil;shutil.copyfileobj(src,f)
            db=sqlite3.connect(dst)
            rows=db.execute("SELECT table_name,data_type,identifier,srs_id FROM gpkg_contents").fetchall()
            out["tables"]=[]
            for table,data_type,identifier,srs in rows:
                if data_type!="features":continue
                count=db.execute("SELECT COUNT(*) FROM '"+table.replace("'","''")+"'").fetchone()[0]
                cols=db.execute("PRAGMA table_info('"+table.replace("'","''")+"')").fetchall()
                sample=db.execute("SELECT * FROM '"+table.replace("'","''")+"' LIMIT 1").fetchone()
                out["tables"].append({"name":table,"identifier":identifier,"count":count,"srs":srs,
                    "fields":[a[1] for a in cols],"first":{a[1]:v for a,v in zip(cols,sample) if isinstance(v,(str,int,float))} if sample else {}})
            db.close()
        print("[stuttgart-geometry]",json.dumps(out,ensure_ascii=False)[:10500],flush=True)
        if not any(int(x["count"])==23 for x in out["tables"]):
            print("[stuttgart-geometry] WARNING: 23-area source layer not automatically identified; no public activation",flush=True)
        return out

def duesseldorf():
    raw=get(DUSSELDORF)
    doc=json.loads(raw.decode("utf-8-sig"))
    features=doc.get("features",[])
    result={"url":DUSSELDORF,"bytes":len(raw),"type":doc.get("type"),
      "count":len(features),"first_props":[f.get("properties") for f in features[:3]],
      "geometry_types":sorted({f.get("geometry",{}).get("type") for f in features}),
      "properties_keys":sorted({key for f in features for key in f.get("properties",{})})}
    print("[duesseldorf-geometry]",json.dumps(result,ensure_ascii=False)[:5900],flush=True)
    if len(features)!=10:
        raise RuntimeError(f"Düsseldorf official district layer expected 10 districts, got {len(features)}")
    return result

if __name__=="__main__":
    for name,func in (("stuttgart",stuttgart),("duesseldorf",duesseldorf)):
        try:func()
        except Exception as e:print("[geometry-probe] BLOCKED",name,repr(e),flush=True)
