#!/usr/bin/env python3
"""Archive Regionaldatenbank Deutschland county housing completions, nationwide.

Source discovery: GovData publishes direct resource
https://www.regionalstatistik.de/genesisws/downloader/00/tables/31121-01-02-4_00.csv

The file may have many building-type dimensions; inspect its exact schema
before selecting dwelling totals. Do NOT sum overlapping categories.
"""
from __future__ import annotations
import csv,hashlib,io,json,time,urllib.request
from pathlib import Path
URL="https://www.regionalstatistik.de/genesisws/downloader/00/tables/31121-01-02-4_00.csv"
CATALOG="https://www.govdata.de/suche/daten/fertigstellung-neuer-wohngebaude-und-wohnungen-in-wohngebauden-nach-zahl-der-wohnungen-jahressu"
ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/"research/housing/raw";QA=ROOT/"research/housing/qa"
def fetch():
 for i in range(3):
  try:
   req=urllib.request.Request(URL,headers={"User-Agent":"Mozilla/5.0 (GermanMap official statistical research)",
     "Accept":"text/csv,*/*"})
   with urllib.request.urlopen(req,timeout=140) as r:
    b=r.read(75_000_001)
    print("FETCH",r.status,len(b),r.headers.get("Content-Type"),flush=True)
   if not 5000<len(b)<75_000_001:raise ValueError(f"Bad raw CSV length {len(b)}")
   return b
  except Exception as e:
   print("RETRY",i,type(e).__name__,str(e)[:250],flush=True)
   if i==2:raise
   time.sleep((i+1)*4)
def audit(raw):
 text=None;enc=None
 for e in ("utf-8-sig","utf-8","cp1252"):
  try:text=raw.decode(e);enc=e;break
  except UnicodeError:pass
 if text is None:raise ValueError("Unable to decode official CSV")
 if "31121" not in text[:150] and "Baufertigstellung" not in text[:1500] and "Wohngebäude" not in text[:1500]:
  raise ValueError("Unexpected regional official source/heading")
 lines=text.splitlines()
 sep=";" if text[:5000].count(";")>=text[:5000].count("\t") else "\t"
 first=list(csv.reader(io.StringIO("\n".join(lines[:55])),delimiter=sep))
 return {"source":URL,"catalog":CATALOG,"publisher":"Statistische Ämter des Bundes und der Länder",
    "license":"Datenlizenz Deutschland Attribution 2.0",
    "table":"31121-01-02-4","level":"Kreise und kreisfreie Städte","metric":"new residential buildings and dwellings, by count of dwellings",
    "bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),"encoding":enc,"delimiter":repr(sep),
    "line_count":len(lines),"first_55_rows":first,"last_12_lines":lines[-12:],
    "year_markers":{str(y):text.count(str(y)) for y in range(2018,2027)},
    "warnings":["Read full category headers before extracting a map series",
      "Completed residential buildings do not include extensions or all dwellings in nonresidential buildings",
      "New-build category splits are overlapping and MUST NOT be summed repeatedly"]}
def main():
 RAW.mkdir(parents=True,exist_ok=True);QA.mkdir(parents=True,exist_ok=True)
 raw=fetch();out=audit(raw)
 (RAW/"regionalstatistik_31121-01-02-4_national_counties.csv").write_bytes(raw)
 (QA/"regionalstatistik_31121_county_completions_schema.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("ARCHIVED NATIONAL COUNTY COMPLETIONS",out["line_count"],"lines years",out["year_markers"],flush=True)
if __name__=="__main__":main()
