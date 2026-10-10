#!/usr/bin/env python3
"""Acquisition of nationwide Regionaldatenbank table 42111-02-03-4.

RESEARCH RAW ONLY. The resulting CSV must NOT be mistaken for a verified
2019/latest same-scope WZ-C county employment panel. Save data and provenance
separately, leaving data/county-employment.json completely unchanged.
"""
import datetime as dt
import hashlib
import json
import pathlib
import re
import sys
import urllib.request
import urllib.error

ROOT=pathlib.Path(__file__).resolve().parents[1]
URL="https://www.regionalstatistik.de/genesisws/downloader/00/tables/42111-02-03-4_00.csv"
OUT=ROOT/"research/R8_regionalstatistik_42111-02-03-4_00_raw.csv"
META=ROOT/"research/R8_regionalstatistik_download_manifest.json"
CAP=19_000_000

def fetch():
    req=urllib.request.Request(URL,headers={"User-Agent":"German-Map-industry-research/1.0","Accept":"text/csv,*/*"})
    with urllib.request.urlopen(req,timeout=80) as r:
        status=getattr(r,"status",200)
        content_type=r.headers.get("content-type","")
        data=r.read(CAP+1)
    if status!=200 or len(data)>CAP:
        raise ValueError("Non-200 response or size above cap")
    if len(data)<500: raise ValueError("Too small for national county table")
    if b"<html" in data[:1000].lower() or b"<!doctype html" in data[:1000].lower():
        raise ValueError("Server returned HTML instead of CSV")
    try: txt=data.decode("utf-8-sig")
    except UnicodeDecodeError: txt=data.decode("iso-8859-1")
    if "42111" not in txt[:12000] and "Verarbeitendes Gewerbe" not in txt[:12000]:
        raise ValueError("No table identity or manufacturing label in CSV header")
    county_tokens=set(re.findall(r'(?<!\d)\d{5}(?!\d)',txt))
    county_tokens={s for s in county_tokens if 1<=int(s[:2])<=16}
    years=sorted(set(re.findall(r'(?<!\d)20(?:1\d|2\d)(?!\d)',txt)))
    record={
       "source_table":"42111-02-03-4","download_url":URL,
       "retrieved_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
       "bytes":len(data),"sha256":hashlib.sha256(data).hexdigest(),
       "content_type":content_type,"lines":len(txt.splitlines()),
       "candidate_5digit_tokens":len(county_tokens),
       "candidate_year_tokens":years,
       "mentions_verarbeitendes_gewerbe":"Verarbeitendes Gewerbe" in txt,
       "mentions_bergbau":"Bergbau" in txt,
       "status":"RAW_RESEARCH_ARCHIVE_NOT_APPROVED_FOR_MAP",
       "reason":"WZ-C pure manufacturing, Arbeitsort, annual period, headcount field, >=20 employee reporting threshold, 400 AGS and confidentiality NOT YET CERTIFIED",
       "no_publishing":"Never copy directly into data/county-employment.json",
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_bytes(data)
    META.write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(record,ensure_ascii=False))
if __name__=="__main__":
    try: fetch()
    except Exception as e:
        print("OFFICIAL RAW CANDIDATE NOT ACQUIRED: "+repr(e),file=sys.stderr)
        sys.exit(5)
