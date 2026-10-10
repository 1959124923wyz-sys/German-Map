#!/usr/bin/env python3
"""Extract the complete 400 county rows of the nationwide official 2022 Zensus
regional building and dwelling census from the machine-readable XLSX sheets.

Never aggregate Gemeinde rows with Kreis rows, as those overlap; only select
5-digit _RS and the literal county territorial level. Raw source value tokens
are retained, so suppressed data is not misread as zero. 2022 administrative
vintage is stored explicitly even when displayed on a 2024 BKG geometry.
"""
from __future__ import annotations
import csv,json,re,hashlib
from collections import Counter
from pathlib import Path
from openpyxl import load_workbook

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/"research/housing/raw/destatis_zensus_2022_regional_housing_national.xlsx"
OUT=ROOT/"research/housing/data";WEB=ROOT/"topics/housing/data";QA=ROOT/"research/housing/qa"
SHEETS={"dwellings":"CSV-Wohnungen","buildings":"CSV-Gebäude"}
URL="https://www.destatis.de/static/DE/zensus/gitterdaten/Regionaltabelle_Gebaeude_Wohnungen.xlsx"

def collect(sh,expected):
    itr=sh.iter_rows(values_only=True);header=[str(x or "").strip() for x in next(itr)]
    if header[:4]!=["Berichtszeitpunkt","_RS","Name","Regionalebene"]:
        raise ValueError(f"Unrecognized Zensus machine CSV sheet structure: {header[:4]}")
    if any(not k for k in header) or len(header)!=len(set(header)):
        raise ValueError("Blank or repeated Zensus county column codes")
    data={};levels=Counter();excluded=[];suppressed=Counter()
    for row in itr:
        key=str(row[1]).strip() if row[1] is not None else ""
        name=str(row[2]).strip() if row[2] is not None else ""
        lev=str(row[3]).strip() if row[3] is not None else ""
        levels[lev]+=1
        if not re.fullmatch(r"\\d{5}",key) or lev!="Stadtkreis/kreisfreie Stadt/Landkreis":
            continue
        if row[0] != 20220515 and str(row[0])!="20220515":
            raise ValueError(f"Unexpected Zensus reference date {_id}, {row[0]}")
        if key in data:raise ValueError(f"Duplicate census county {key}")
        vals={}
        for col,v in zip(header[4:],row[4:]):
            if v is None or str(v).strip() in ("","-","/","x",".","…","X"):
                vals[col]=None
                suppressed[col]+=1
            elif isinstance(v,(int,float)):
                vals[col]=v
            else:
                v=str(v).strip()
                if re.fullmatch(r"-?\\d+(?:[,.]\\d+)?",v):
                    vals[col]=float(v.replace(",",".")) if "," in v or "." in v else int(v)
                else:
                    vals[col]=v
                    if len(suppressed)<1000: suppressed["non_numeric:"+col]+=1
        data[key]={"id":key,"name":name,"values":vals}
    if len(data)!=400:raise ValueError(f"Need exactly 400 national Zensus Kreise, found {len(data)}")
    missing=set(expected)-set(data);excess=set(data)-set(expected)
    if missing or excess:raise ValueError(f"Zensus 2022 and HA26 IDs differ. missing={sorted(missing)}, excess={sorted(excess)}")
    print("EXTRACTED",sh.title,"400 Kreise",len(header)-4,"data columns",flush=True)
    return {"columns":header[4:],"items":[data[k] for k in sorted(data)],
            "audit":{"count":len(data),"columns":len(header)-4,
                "levels":dict(levels),"null_counts":dict(suppressed),
                "geo_difference_2022_vs_2024":[],
                "sample_ids":sorted(data)[:7]}}

def main():
    atlas=json.loads((WEB/"atlas-counties.json").read_text(encoding="utf-8"))
    expected={d["id"] for d in atlas["counties"]}
    if len(expected)!=400:raise ValueError("Need official 400 district county reference")
    if not SRC.exists():raise ValueError("Download official Zensus 2022 national workbook first")
    wb=load_workbook(SRC,data_only=True,read_only=True)
    payload={"meta":{"publisher":"Statistische Ämter des Bundes und der Länder",
              "dataset":"Zensus 2022, Gebäude- und Wohnungszählung, national regional XLSX",
              "year":"2022","census_reference_day":"2022-05-15",
              "countrywide_counties":400,
              "source":URL,
              "license":"Datenlizenz Deutschland – Namensnennung 2.0",
              "warning":"2022 census county figures, not 2025 new construction; do not sum nested municipality/association/county records",
              "column_codes":"All machine-readable official source column codes retained; interpretation requires original XLSX methodology tab."},
             "sheets":{}}
    audit={"source":URL,"expected_2024_AGS_count":400,"sheets":{}}
    for dest,name in SHEETS.items():
        v=collect(wb[name],expected);audit["sheets"][dest]=v["audit"]
        payload["sheets"][dest]={"columns":v["columns"],"counties":v["items"]}
        OUT.mkdir(parents=True,exist_ok=True)
        csvpath=OUT/f"zensus2022_official_400_counties_{dest}.csv"
        with csvpath.open("w",newline="",encoding="utf-8") as f:
            w=csv.writer(f);w.writerow(["AGS","Name",*v["columns"]])
            for d in v["items"]:
                w.writerow([d["id"],d["name"],*[d["values"][k] if d["values"][k] is not None else "" for k in v["columns"]]])
    wb.close()
    WEB.mkdir(parents=True,exist_ok=True);QA.mkdir(parents=True,exist_ok=True)
    (WEB/"zensus2022-county-archive.json").write_text(
      json.dumps(payload,ensure_ascii=False,separators=(",",":"),default=str)+"\\n",encoding="utf-8")
    (QA/"zensus2022_official_county_extract_audit.json").write_text(
      json.dumps(audit,ensure_ascii=False,indent=2)+"\\n",encoding="utf-8")
    print("SUCCESS national Zensus: 400 current AGS building+dwellings, full source columns",flush=True)
if __name__=="__main__":main()
