#!/usr/bin/env python3
"""Probe official BKG-hosted Deutschlandatlas Kreise geometry endpoint.

This discovery step collects only read-only metadata and the first few AGS rows.
No geometries are published unless exact 400-county identity and boundary
provenance can be confirmed. The endpoint is the 2026 release with 2024 VG250.
"""
import json
import urllib.parse
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SRC="https://tigis.bkg.bund.de/hosting/rest/services/hh_veink_ZA2026/MapServer/5"
QA=ROOT/"research/housing/qa/bkg_geometry_endpoint_probe.json"
def get(params):
    url=SRC+"?"+urllib.parse.urlencode(params)
    q=urllib.request.Request(url,headers={"User-Agent":"GermanMapHousingResearch/1.0", "Accept":"application/json"})
    with urllib.request.urlopen(q,timeout=60) as r:
        data=json.loads(r.read())
    if not isinstance(data,dict) or "error" in data:raise ValueError(f"Service error {data}")
    return data

def main():
    meta=get({"f":"pjson"})
    query_url=SRC+"/query?"+urllib.parse.urlencode({"where":"1=1","outFields":"*",
               "returnGeometry":"false","resultRecordCount":"5","f":"json"})
    with urllib.request.urlopen(query_url,timeout=60) as r:
        sample=json.loads(r.read())
    if "error" in sample:raise ValueError(sample)
    count_url=SRC+"/query?"+urllib.parse.urlencode({"where":"1=1","returnCountOnly":"true","f":"json"})
    with urllib.request.urlopen(count_url,timeout=60) as r:
        count=json.loads(r.read())
    if "error" in count:raise ValueError(count)
    out={"source_layer":SRC,"count":count.get("count"),
         "service_name":meta.get("name"),"service_description":meta.get("description"),
         "copyright_text":meta.get("copyrightText"),
         "spatial_reference":meta.get("spatialReference"),
         "geometry_type":meta.get("geometryType"),
         "fields":meta.get("fields"),
         "sample_features":sample.get("features",[])[:5],
         "source_notice":"BKG official 2024 VG250 geographic boundary; copyright must be fully attributed for republishing."
         }
    QA.parent.mkdir(parents=True,exist_ok=True)
    QA.write_text(json.dumps(out,ensure_ascii=False,indent=2,default=str)+"\n",encoding="utf-8")
    print("BKG COUNTY SERVICE",out["count"],"NAME",out["service_name"])
    print("FIELDS",[(f["name"],f.get("type")) for f in meta.get("fields",[])])
    print("SAMPLES",out["sample_features"][:3])
if __name__=="__main__":main()
