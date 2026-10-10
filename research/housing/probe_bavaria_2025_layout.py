#!/usr/bin/env python3
"""Forensic inventory of 2025 Bavarian official F2200C district report layout.

The XLSX has four paginated 'Kreisübersicht Tab4' sheets, 177 columns of
heavily merged presentation structure. Record sparse cell addresses, no
imputation or guessed placement of numbers. Keep partial QA reviewable.
"""
from __future__ import annotations
import json
from pathlib import Path
from openpyxl import load_workbook
ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/"research/housing/raw/bavaria_f2200c_202500_official.xlsx"
QA=ROOT/"research/housing/qa"
def main():
 wb=load_workbook(SRC,read_only=True,data_only=True)
 result={"source":"https://www.statistik.bayern.de/mam/produkte/veroffentlichungen/statistische_berichte/f2200c_202500.xlsx",
         "tables":{}}
 for sh in wb:
  if not sh.title.startswith("Kreisübersicht Tab4"):continue
  examples=[]
  for i,row in enumerate(sh.iter_rows(min_row=1,max_row=min(sh.max_row,53),max_col=min(sh.max_column,100),values_only=True),start=1):
   nonempty=[{"c":j+1,"v":str(x)[:140]} for j,x in enumerate(row) if x is not None and str(x).strip()]
   examples.append({"r":i,"values":nonempty[:46]})
  result["tables"][sh.title]={"rows":sh.max_row,"cols":sh.max_column,"samples":examples}
  print("BAVARIA SHEET",sh.title,"ROWS",sh.max_row,flush=True)
 wb.close()
 QA.mkdir(parents=True,exist_ok=True)
 (QA/"bavaria_2025_construction_district_table_layout.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("Saved Bavaria 2025 exact table row/col positions",flush=True)
if __name__=="__main__":main()
