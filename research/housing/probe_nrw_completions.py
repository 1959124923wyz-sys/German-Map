#!/usr/bin/env python3
"""Archive NRW state official county building completions table 31121-06i.

Source is the Landesdatenbank NRW CSV export (GovData resource, 2026-09-21).
Do not interpret columns before schema inspection; preserve entire source.
"""
from __future__ import annotations
import csv,hashlib,io,json,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/"research/housing/raw"
QA=ROOT/"research/housing/qa"
URL="https://www.landesdatenbank.nrw.de/ldbnrwws/downloader/00/tables/31121-06i_00.csv"
PAGE="https://www.govdata.de/suche/daten/baufertigstellungen-neubau-wohngebaude-nach-anzahl-derwohnungen-sowie-fertigteilbau-und-eigentu"

def main():
    req=urllib.request.Request(URL,headers={"User-Agent":"GermanMap Housing Research (public data aggregation)"})
    with urllib.request.urlopen(req,timeout=85) as resp:
        raw=resp.read()
        print("HTTP",resp.status,"bytes",len(raw),"content-type",resp.headers.get("Content-Type"))
    if len(raw)<4000 or b"<html" in raw[:500].lower():
        raise ValueError("Official NRW CSV cannot be verified")
    txt=None;enc=None
    for e in ("utf-8-sig","cp1252","iso-8859-1"):
        try:
            trial=raw.decode(e)
            if "Baufertig" in trial or "Wohngeb" in trial:
                txt=trial;enc=e;break
        except UnicodeError:pass
    if txt is None:raise ValueError("No building completion heading in downloaded source")
    RAW.mkdir(parents=True,exist_ok=True);QA.mkdir(parents=True,exist_ok=True)
    (RAW/"nrw_baufertigstellungen_31121_06i.csv").write_bytes(raw)
    first=txt.splitlines()[:45]
    report={
     "source":URL,"source_landing":PAGE,"publication_last_modified":"2026-09-21 (GovData resource)",
     "publisher":"Information und Technik Nordrhein-Westfalen / Landesdatenbank NRW",
     "sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw),"encoding":enc,
     "line_count":len(txt.splitlines()),"first_45_lines":first,
     "warning":"NRW only; includes all building categories, years and county groups; isolate exact housing unit completions from new residential construction and distinguish rebuilt/modified structures."
    }
    (QA/"nrw_baufertigstellungen_schema.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("NRW RAW ARCHIVED","lines",report["line_count"],"first",first[:10])

if __name__=="__main__":main()
