#!/usr/bin/env python3
"""Probe the official BKG WFS for 2025 county AGS fields, without inventing them."""
from __future__ import annotations
import datetime
import json
import pathlib
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT=pathlib.Path(__file__).resolve().parents[4]
DEST=ROOT/"topics/infrastructure/research/bkg_wfs_ags_probe.json"
BASE="https://sgx.geodatenzentrum.de/wfs_vg2500"
FIELDS=["vg2500_krs","vg2500:vg2500_krs"]
def get(params):
    url=BASE+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"User-Agent":"GermanMapResearch/1.0 data attribution CC-BY-4.0"})
    with urllib.request.urlopen(req,timeout=30) as response:
        body=response.read(200_000)
        status=response.status
        ctype=response.headers.get("Content-Type")
    result={"url":url,"http_code":status,"content_type":ctype,"bytes_read_limit_200k":len(body),
            "head":body[:500].decode("utf8",errors="replace")}
    if body.strip().startswith(b"<"):
        try:
            xml=ET.fromstring(body)
            elements=[]
            for elem in xml.iter():
                local=elem.tag.rsplit("}",1)[-1]
                if local.upper() in ("AGS","GEN","BEZ","LKZ","RS","WKT","AGS_0"):
                    elements.append({"field":local,"value":(elem.text or "").strip()[:75]})
            result["key_fields_seen"]=elements[:30]
        except Exception as exc:result["xml_parse_error"]=str(exc)[:220]
    return result
def main():
    checks=[]
    for type_name in FIELDS:
        try:
            checks.append(get({"service":"WFS","version":"2.0.0","request":"GetFeature",
                "typeNames":type_name,"count":"1"}))
        except Exception as exc:
            checks.append({"type_name":type_name,"network_error":str(exc)[:300]})
    output={"published":"2026-10-10","asof_boundary":"BKG VG2500 historical 31.12.2024/2025, verify on full download",
        "publisher":"Bundesamt für Kartographie und Geodäsie (BKG)",
        "official_service_page":"https://gdz.bkg.bund.de/index.php/default/webdienste/verwaltungsgebiete/wfs-verwaltungsgebiete-1-2-500-000-stand-31-12-wfs-vg2500.html",
        "tested":checks,"assertion":"This is a probe only; AGS must be from verified WFS output before being assigned."}
    DEST.write_text(json.dumps(output,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps(checks,indent=2,ensure_ascii=False)[:3300])
if __name__=="__main__":main()
