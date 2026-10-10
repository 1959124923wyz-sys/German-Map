#!/usr/bin/env python3
"""Build nationwide Kreis 2023 *new residential building* housing completions.

Regionalstatistik CSV 31121-01-02-4 downloaded from its GovData public resource
provides ONE year (2023), not a multi-year panel. The column 'Wohnungen in
Wohngebäuden | Insgesamt | Anzahl' is the number of completed dwellings in
newly finished residential buildings, excluding other structural construction.
Do not mix with all finished dwellings (including conversions).
"""
from __future__ import annotations
import csv,io,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/"research/housing/raw/regionalstatistik_31121-01-02-4_national_counties.csv"
OUT=ROOT/"research/housing/data"
WEB=ROOT/"topics/housing/data"
QA=ROOT/"research/housing/qa"
URL="https://www.regionalstatistik.de/genesisws/downloader/00/tables/31121-01-02-4_00.csv"
def val(x):
 s=x.strip()
 if s in ("",".","-","/","x"):return None
 if not re.fullmatch(r"\d+",s):raise ValueError(f"Invalid dwelling count {x!r}")
 return int(s)
def main():
 rows=list(csv.reader(io.StringIO(RAW.read_bytes().decode("cp1252")),delimiter=";"))
 if not rows[0][0].startswith("GENESIS-Tabelle: 31121-01-02-4"):raise ValueError("Wrong official export")
 assert rows[8][7].strip()=="Insgesamt" and rows[9][7].strip()=="Anzahl",rows[8:10]
 assert rows[6][7].strip()=="Wohnungen" and rows[7][7].strip()=="in Wohngebäuden"
 reference=json.loads((WEB/"atlas-counties.json").read_text(encoding="utf-8"))
 expected={r["id"] for r in reference["counties"]}
 if len(expected)!=400:raise ValueError("Current 2024 county GIS mismatch")
 result={};excluded=[];seen_year=set();de_total=None
 for row in rows[10:]:
  if len(row)<11 or not re.fullmatch(r"\d{4}",row[0].strip()):continue
  year,key,name=row[0].strip(),row[1].strip(),row[2].strip()
  seen_year.add(year)
  if year!="2023":raise ValueError(f"Unexpected alternate completion year {year}")
  if key=="DG":
   de_total=val(row[7]);continue
  # Berlin and Hamburg each have exactly one county, geographically
  # coextensive with the federal state. The official table reports their
  # state-level values only; map those exactly to canonical 11000/02000.
  # Do NOT do this for Bremen, which comprises TWO separate county cities.
  if key in ("02","11"):
   canonical={"02":("02000","Hamburg"),"11":("11000","Berlin")}[key]
   if canonical[1].casefold() not in name.casefold():
    raise ValueError(f"Unexpected Land for singleton city-state {key}: {name}")
   key=canonical[0]
  if not re.fullmatch(r"\d{5}",key):continue
  dwellings=val(row[7]);bldgs=val(row[3])
  if key not in expected:
   excluded.append({"id":key,"name":name,"dwellings":dwellings});continue
  if key in result:raise ValueError(f"Repeated district {key}")
  subtotals=[val(row[i]) for i in (8,9,10)]
  if dwellings is not None and all(v is not None for v in subtotals):
   if sum(subtotals)!=dwellings:raise ValueError(f"Completions category total inconsistent for {key}: {subtotals} != {dwellings}")
  result[key]={"id":key,"name":name.strip(),"completed_dwellings_new_residential_buildings_2023":dwellings,
               "completed_new_residential_buildings_2023":bldgs}
 missing=sorted(expected-set(result))
 if missing:raise ValueError(f"Missing official HA26 400 GIS counties: {missing}")
 available=[d["completed_dwellings_new_residential_buildings_2023"] for d in result.values()
            if d["completed_dwellings_new_residential_buildings_2023"] is not None]
 if len(available)<385:raise ValueError(f"National completeness insufficient {len(available)}/400")
 subtotal=sum(available)
 if de_total is None or abs(subtotal-de_total)>250:raise ValueError(f"Sum of district new completed dwellings {subtotal} vs official Germany {de_total} too different")
 for p in (OUT,WEB,QA):p.mkdir(parents=True,exist_ok=True)
 payload={"meta":{"source":URL,"publisher":"Statistische Ämter des Bundes und der Länder",
   "table":"31121-01-02-4","year":2023,"districts":400,"numerical":len(available),
   "statistic":"Fertigstellungen neuer Wohngebäude und Wohnungen in Wohngebäuden nach Zahl der Wohnungen",
   "unit":"number of completed dwellings in newly completed RESIDENTIAL buildings",
   "excludes":"extensions, conversion work, and any new dwellings in non-residential buildings",
   "not_latest":"The public CSV download is dated 27 November 2024 and covers year 2023 only; do NOT label values as 2025",
   "source_credit":"© Statistische Ämter des Bundes und der Länder, 2024, dl-de/by-2-0",
   "national_table_total":de_total},"counties":[result[k] for k in sorted(result)]}
 (WEB/"germany-residential-completions-2023.json").write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
 with (OUT/"regionalstatistik_new_dwellings_counties_2023.csv").open("w",encoding="utf-8",newline="") as f:
  writer=csv.DictWriter(f,fieldnames=list(result[next(iter(result))].keys()))
  writer.writeheader();writer.writerows(payload["counties"])
 audit={"table":"31121-01-02-4","source":URL,"statistical_years":sorted(seen_year),
   "county_count":len(result),"numerical_count":len(available),
   "nation_official_total":de_total,"county_subtotal":subtotal,
   "difference":subtotal-de_total,"legacy_codes":excluded,
   "warnings":["This static CSV covers year 2023 only","Newly built residential buildings only; not all housing construction",
               "2025 NRW completed building series is newer but a separate dataset"]}
 (QA/"regionalstatistik_2023_completions_county_audit.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("PASS REGIONAL NEW HOUSING 2023",len(result),"counties",len(available),"numeric",
       subtotal,"housing units; Germany official total",de_total,flush=True)
if __name__=="__main__":main()
