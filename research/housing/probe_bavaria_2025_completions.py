#!/usr/bin/env python3
"""Discover official Bavaria county 2025 construction report spreadsheet.

Bayerisches Landesamt für Statistik lists F2200C 202500 on
https://www.statistik.bayern.de/statistik/bauen_wohnen/bautaetigkeit/
Try only plausible official static download forms; save candidate ONLY after
valid XLSX structure. Inventory sheets first, don't infer district columns.
"""
from __future__ import annotations
import hashlib,json,urllib.error,urllib.request
from pathlib import Path
from openpyxl import load_workbook
ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/"research/housing/raw";QA=ROOT/"research/housing/qa"
BASE="https://www.statistik.bayern.de/mam/produkte/veroffentlichungen/statistische_berichte/"
CANDIDATES=[
 BASE+"f2200c_202500.xlsx",
 BASE+"f2200c_202500.xls",
 BASE+"f2200c_202500.xlsm",
 "https://www.statistik.bayern.de/mam/produkte/veroffentlichungen/statistische_berichte/f2200c_202500tab.xlsx",
]
LANDING="https://www.statistik.bayern.de/statistik/bauen_wohnen/bautaetigkeit/"
def main():
 RAW.mkdir(parents=True,exist_ok=True);QA.mkdir(parents=True,exist_ok=True)
 audit={"publisher":"Bayerisches Landesamt für Statistik","report":"F2200C 202500","reference_year":2025,
 "landing":LANDING,"tried":[],"status":"not_obtained","notes":"Do not claim archived/parsed if all official candidate URLs fail"}
 for url in CANDIDATES:
  rec={"url":url}
  try:
   req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 GermanMap open data archival research"})
   with urllib.request.urlopen(req,timeout=40) as f:
    b=f.read(26_000_000)
    rec["http_status"]=f.status
    rec["bytes"]=len(b)
   if not b.startswith(b"PK") or len(b)<20000:raise ValueError("Not substantial XLSX ZIP workbook")
   path=RAW/"bavaria_f2200c_202500_official.xlsx";path.write_bytes(b)
   wb=load_workbook(path,read_only=True,data_only=True)
   out={}
   for sh in wb:
    rows=[]
    for row in sh.iter_rows(min_row=1,max_row=min(sh.max_row,20),
                             max_col=min(sh.max_column,20),values_only=True):
     rows.append([str(v)[:130] if v is not None else None for v in row])
    out[sh.title]={"rows":sh.max_row,"columns":sh.max_column,"first20":rows}
   wb.close()
   rec["sha256"]=hashlib.sha256(b).hexdigest()
   audit["workbook"]=out
   audit["status"]="obtained_workbook"
   audit["download"]=url
   audit["tried"].append(rec)
   print("FOUND Bavaria official 2025 XLSX",url,len(b),"sheets",list(out),flush=True)
   break
  except Exception as e:
   rec["error"]=type(e).__name__+": "+str(e)[:160]
   audit["tried"].append(rec)
   print("UNAVAILABLE",url,rec["error"],flush=True)
 (QA/"bavaria_2025_completions_xlsx_discovery.json").write_text(
  json.dumps(audit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("PROBE RESULT",audit["status"],flush=True)
if __name__=="__main__":main()
