#!/usr/bin/env python3
"""Probe official Regionaldatenbank GENESIS REST via POST, recording diagnostics.
Non-authoritative candidate only: never writes production county-employment.json.
"""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import urllib.parse
import urllib.request
import urllib.error

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"research/R8_GENESIS_API_PROBE.json"
TABLE="42111-02-03-4"
BASE="https://www.regionalstatistik.de/genesisws/rest/2020"
ENDPOINTS=["metadata/table","data/tablefile","data/table"]
MAX_BYTES=18_000_000

def attempt(endpoint):
    fields={"name":TABLE,"area":"free","language":"de"}
    if endpoint.startswith("data/"):
        fields.update({"startyear":"2019","endyear":"2025","compress":"false","job":"false"})
        if endpoint.endswith("tablefile"): fields["format"]="datencsv"
    body=urllib.parse.urlencode(fields).encode("utf-8")
    headers={"username":os.environ.get("REGSTAT_USER","GAST"),
             "password":os.environ.get("REGSTAT_PASSWORD","GAST"),
             "Content-Type":"application/x-www-form-urlencoded; charset=UTF-8",
             "Accept":"application/json, text/csv, */*",
             "User-Agent":"German-Map industrial research 1.0",
             "Content-Length":str(len(body))}
    req=urllib.request.Request(BASE+"/"+endpoint,data=body,headers=headers,method="POST")
    out={"endpoint":BASE+"/"+endpoint,"method":"POST","fields":fields}
    try:
        with urllib.request.urlopen(req,timeout=50) as response:
            out["http"]=response.status
            out["content_type"]=response.headers.get("Content-Type","")
            bs=response.read(MAX_BYTES+1)
    except urllib.error.HTTPError as ex:
        out["http"]=ex.code
        bs=ex.read(10000)
        out["http_error_excerpt"]=bs.decode("utf-8","replace")[:1500]
    except Exception as ex:
        out["network_error"]=str(ex)
        return out
    out["bytes"]=len(bs)
    out["sha256"]=hashlib.sha256(bs).hexdigest()
    if len(bs)>MAX_BYTES:
        out["status"]="response_above_size_limit"
        return out
    txt=bs.decode("utf-8-sig","replace")
    out["excerpt"]=txt[:2200]
    try:
        obj=json.loads(txt)
        if isinstance(obj,dict):
            out["json_keys"]=list(obj.keys())[:30]
            out["Status"]=str(obj.get("Status", ""))[:1000]
            result=obj.get("Object")
            if isinstance(result,dict):out["ObjectKeys"]=list(result.keys())[:40]
    except Exception: pass
    out["status"]="diagnostic_only_no_county_employment_import"
    return out

def main():
    results=[]
    for endpoint in ENDPOINTS:
        results.append(attempt(endpoint))
    document={"created_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
      "table":TABLE,"authentication":"guest or supplied GitHub Actions secret, no secret printed",
      "source_openapi":"https://www.regionalstatistik.de/genesisws/rest/2020/GOJsonApi.json",
      "status":"RAW_API_DIAGNOSTIC_NEVER_PRODUCTION", "attempts":results,
      "caution":"An API HTTP 200, JSON metadata, or partial table is not a verified nationwide WZ-C employment panel; never convert to county-employment.json."}
    OUTPUT.parent.mkdir(exist_ok=True,parents=True)
    OUTPUT.write_text(json.dumps(document,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"file":str(OUTPUT),"results":[{"endpoint":x["endpoint"],"http":x.get("http"),"status":x.get("Status",""),"bytes":x.get("bytes"),"error":x.get("network_error")} for x in results]},ensure_ascii=False))
if __name__=="__main__":main()
