#!/usr/bin/env python3
"""Archive Destatis GENESIS 22971-0080 official nationwide district homeless data.

Official GovData catalog links to a public CSV download; this bypasses API
authentication without scraping a browser session. Stage 1 only: archive the
source bytes and inspect columns; do NOT guess or join until shape is confirmed.
"""
from __future__ import annotations
import csv,hashlib,io,json,time,urllib.request
from collections import Counter
from pathlib import Path
URL="https://genesis.destatis.de/genesisWS/downloads/00/tables/22971-0080_00.csv"
CATALOG="https://data.gov.de/suche/daten/untergebrachte-wohnungslose-personen-kreise-stichtag-nationalitat-geschlecht-altersgruppen"
ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/"research/housing/raw";QA=ROOT/"research/housing/qa"
def fetch():
 for i in range(3):
  try:
   req=urllib.request.Request(URL,headers={"User-Agent":"Mozilla/5.0 (GermanMap open official data research)","Accept":"text/csv,*/*"})
   with urllib.request.urlopen(req,timeout=140) as response:
    raw=response.read(65_000_001)
    print("FETCH",response.status,len(raw),response.headers.get("Content-Type"),flush=True)
   if not (10000<len(raw)<65_000_001):raise ValueError(f"Suspicious file size {len(raw)}")
   return raw
  except Exception as e:
   print("RETRY",i,type(e).__name__,str(e)[:250],flush=True)
   if i==2:raise
   time.sleep(4*(i+1))
def inspect(raw):
 for enc in ("utf-8-sig","utf-8","cp1252"):
  try: text=raw.decode(enc);break
  except UnicodeDecodeError:pass
 else:raise ValueError("Unknown official table character encoding")
 if "Wohnung" not in text and "wohnung" not in text and "Untergeb" not in text:
  raise ValueError("Official statistical header not found")
 sep=";" if text[:2000].count(";")>=text[:2000].count("\t") else "\t"
 lines=text.splitlines()
 rows=list(csv.reader(io.StringIO("\n".join(lines[:55])),delimiter=sep))
 return {
  "source":URL,"govdata_catalog":CATALOG,
  "license":"Data Licence Germany - Attribution 2.0 (dl-de/by-2-0)",
  "statistic":"22971-0080","level":"Kreise",
  "measure":"Untergebrachte wohnungslose Personen on 31 January; not all homelessness",
  "first_55_rows":rows,"last_12_lines":lines[-12:],
  "line_count":len(lines),"delimiter":repr(sep),"encoding":enc,
  "year_markers":{y:text.count(y) for y in ("2022","2023","2024","2025","2026")},
  "notes":["The national dataset may contain disclosure suppression and 5-person rounding",
           "Use only All genders, All nationalities, All age groups totals for a map",
           "Do not sum multidimensional rows or double count subsets"]}
def main():
 RAW.mkdir(parents=True,exist_ok=True);QA.mkdir(parents=True,exist_ok=True)
 raw=fetch();audit=inspect(raw)
 audit["sha256"]=hashlib.sha256(raw).hexdigest();audit["bytes"]=len(raw)
 (RAW/"destatis_22971-0080_national_counties.csv").write_bytes(raw)
 (QA/"destatis_22971-0080_schema.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("ARCHIVED",len(raw),"bytes",audit["line_count"],"rows",audit["year_markers"],flush=True)
if __name__=="__main__":main()
