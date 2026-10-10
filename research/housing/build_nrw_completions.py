#!/usr/bin/env python3
"""Extract county/year NRW 31121-06i NEW residential building completions.

NE: Wohnungen in Wohngebäuden (new-build residential structures). The figures
are NOT all completed housing units: later conversion/expansion and housing in
nonresidential buildings may be excluded from this published category.
"""
from __future__ import annotations
import csv,json,re
from collections import Counter,defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/"research/housing/raw/nrw_baufertigstellungen_31121_06i.csv"
OUT=ROOT/"research/housing/data"
QA=ROOT/"research/housing/qa"
WEB=ROOT/"topics/housing/data"
URL="https://www.landesdatenbank.nrw.de/ldbnrwws/downloader/00/tables/31121-06i_00.csv"
FIELDS=("new_residential_buildings","new_dwellings_in_residential_buildings",
        "rooms_in_new_residential_buildings","floor_area_new_residential_sqm",
        "nonliving_area_new_residential_sqm")

def count(s):
    s=str(s or "").strip()
    if s in ("","-",".","/","x","…"):return None
    cleaned=s.replace(".","").replace(" ","")
    if not re.fullmatch(r"-?\d+",cleaned):raise ValueError(f"Invalid numeric field {s!r}")
    return int(cleaned)

def main():
    raw=RAW.read_bytes();txt=raw.decode("cp1252")
    latest=2025
    years={};names={};states={};categories=Counter()
    for line,row in enumerate(csv.reader(txt.splitlines(),delimiter=";"),start=1):
        if len(row)!=9 or not re.fullmatch(r"20\d\d",row[0].strip()):
            continue
        y=int(row[0]);key=row[1].strip();category=row[3].strip()
        if y>latest:raise ValueError(f"Newer year {y} exists in source, update release labels")
        if category!="Wohngebäude insgesamt":
            categories[category]+=1
            continue
        if key=="05":
            states[y]=dict(zip(FIELDS,(count(x) for x in row[4:9])))
        if not re.fullmatch(r"05\d{3}",key):continue
        d=dict(zip(FIELDS,(count(x) for x in row[4:9])))
        rec=(key,y)
        if rec in years:raise ValueError(f"Duplicate county-year row {rec}")
        years[rec]=d;names[key]=row[2].strip()
    all_ids=sorted({key for key,y in years if y==latest})
    discontinued=sorted(k for k in all_ids if years[(k,latest)]["new_dwellings_in_residential_buildings"] is None)
    # NRW still includes Aachen City/County (superseded by Städteregion Aachen,
    # 05334) as two historical empty series. They are NOT two extra Kreise.
    if discontinued!=["05313","05354"]:
        raise ValueError(f"Unexpected 2025 suppressed/obsolete regions: {discontinued}")
    ids=[k for k in all_ids if k not in discontinued]
    if len(ids)!=53:raise ValueError(f"NRW active county count expected 53, got {len(ids)}")
    assert states[latest]["new_dwellings_in_residential_buildings"]==31237
    sum_dwellings=sum(years[(key,latest)]["new_dwellings_in_residential_buildings"] for key in ids)
    if sum_dwellings!=31237:raise ValueError(f"County sum {sum_dwellings} not equal state 31237")
    atlas=json.loads((WEB/"atlas-counties.json").read_text(encoding="utf-8"))
    atlas_ids={r["id"] for r in atlas["counties"]}
    assert all(i in atlas_ids for i in ids)
    rows=[]
    for key in ids:
        rec={"id":key,"name":names[key],"values_by_year":{}}
        for yr in range(2015,latest+1):
            d=years.get((key,yr))
            if d is not None:
                rec["values_by_year"][str(yr)]=d
        rec["new_dwellings_2025"]=years[(key,latest)]["new_dwellings_in_residential_buildings"]
        rec["new_buildings_2025"]=years[(key,latest)]["new_residential_buildings"]
        rows.append(rec)
    OUT.mkdir(parents=True,exist_ok=True);QA.mkdir(parents=True,exist_ok=True);WEB.mkdir(parents=True,exist_ok=True)
    with (OUT/"nrw_new_residential_completions_2015_2025.csv").open("w",encoding="utf-8",newline="") as f:
        writer=csv.writer(f)
        writer.writerow(["ags","county","year",*FIELDS])
        for row in rows:
            for year,d in sorted(row["values_by_year"].items()):
                writer.writerow([row["id"],row["name"],year,*[d.get(x) for x in FIELDS]])
    payload={"meta":{
      "publisher":"IT.NRW / Landesdatenbank Nordrhein-Westfalen",
      "source":URL,"last_updated":"2026-09-21",
      "scope":"North Rhine-Westphalia ONLY; 53 counties, 2015-2025 series",
      "metric":"NE: Wohnungen in Wohngebäuden - dwellings in NEW completed residential buildings",
      "counting_unit":"number of dwellings; NOT number of building permits, nor all completions including building modifications",
      "state_2025_dwellings_in_new_residential_buildings":31237,
      "limitations":"Only NRW; selection of one residential new-construction category; does not include conversions/extensions or new dwellings in nonresidential buildings."},
      "counties":rows}
    (WEB/"nrw-new-home-completions.json").write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    qa={"source":URL,"counties_2025":len(ids),"observations":len(years),
        "year_span":[min(y for _,y in years),max(y for _,y in years)],
        "state_2025":states[latest],"sum_county_2025":sum_dwellings,
        "retired_aachen_rows_omitted":discontinued,"nrw_counties":ids,"2015_2025_row_count":sum(len(x["values_by_year"]) for x in rows),
        "category_examples":dict(categories.most_common(9)),
        "matched_current_map":len([i for i in ids if i in atlas_ids]),
        "warnings":[payload["meta"]["metric"],payload["meta"]["limitations"]]}
    (QA/"nrw_new_residential_completions_audit.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("SUCCESS NRW",len(ids),"counties with",sum_dwellings,"new residential dwellings completed in 2025")
    print("YEAR SPAN",qa["year_span"],"OBS",len(years))
if __name__=="__main__":main()
