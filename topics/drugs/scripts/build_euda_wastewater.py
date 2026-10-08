#!/usr/bin/env python3
"""Rebuild site-level German 2025 drug wastewater observations from EUDA CSV.

2025 observations refer to sampled WWTP catchments. Their coordinates are
published site/plant coordinates, not exact consumption locations. The units
are mg of UNCORRECTED residues per 1,000 served residents per day. Missing
("NA") is not equivalent to below-limit "0". No heroin estimates are made.
"""
from __future__ import annotations
import csv
import io
import json
import math
import sys
from pathlib import Path
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[3]
DEST=ROOT/"topics/drugs/data/euda_wastewater_2025.json"
URLBASE="https://www.euda.europa.eu/sites/default/files/data/data-nodes/33337/versions/5/"
OBS_URL=URLBASE+"ww2026-all-data_en.csv"
SITE_URL=URLBASE+"ww2026-site-info-table_en.csv"
SOURCE_PAGE="https://www.euda.europa.eu/publications/pods/waste-water-analysis_de"
SUBSTANCES={"cannabis","cocaine","methamphetamine","amphetamine","MDMA","ketamine"}

def read_csv(url):
    request=Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; GermanMapData/1.0; +https://github.com/1959124923wyz-sys/German-Map)"})
    with urlopen(request,timeout=65) as response:
        b=response.read()
    if len(b)<2000:
        raise RuntimeError(f"Unexpectedly small source: {url}")
    # EUDA's current '2026' raw export contains Western European names in CP1252
    text=b.decode("cp1252")
    return list(csv.DictReader(io.StringIO(text))),len(b)

def finite_or_none(x):
    x=str(x or "").strip()
    if not x or x.upper() in ("NA","N/A","NULL","-"):
        return None
    f=float(x)
    if not math.isfinite(f) or f<0:
        raise ValueError("Invalid EUDA numeric value: "+repr(x))
    return round(f,2)

def main():
    obs,size=read_csv(OBS_URL)
    info,site_bytes=read_csv(SITE_URL)
    site_info={r["SiteID"]:r for r in info if r.get("Country")=="DE"}
    assert len(site_info)>=8, f"Only {len(site_info)} German wastewater sites"
    sites={}
    previous={}
    rejected=0
    for row in obs:
        if row.get("Country")!="DE" or row.get("Metabolite") not in SUBSTANCES:
            continue
        year=int(row["Year"])
        if year not in (2024,2025):
            continue
        site_id=row["Site ID"]
        if site_id not in site_info:
            raise ValueError(f"No site geo for {site_id}")
        key=(site_id,row["Metabolite"])
        val=finite_or_none(row["Daily mean"])
        if year==2024:
            if key in previous:raise RuntimeError(f"Duplicate 2024 measurement {key}")
            previous[key]=val
            continue
        record=sites.get(site_id)
        if record is None:
            src=site_info[site_id]
            lat=float(src["Latitude"])
            lon=float(src["Longitude"])
            if not(47<=lat<=56 and 5<=lon<=16):
                raise ValueError(f"Coordinate outside Germany {site_id}: {lat} {lon}")
            population=src.get("Population","")
            sites[site_id]=record={
                "id":site_id,
                "city":row["City"],
                "location":src.get("Location",""),
                "lat":round(lat,6),
                "lon":round(lon,6),
                "population_served_estimate":int(population) if population.isdigit() else None,
                "observations":{},
            }
        else:
            if record["city"]!=row["City"]:
                raise RuntimeError(f"Site city mismatch {site_id}")
        if row["Metabolite"] in record["observations"]:
            raise RuntimeError(f"Duplicate 2025 measurement {key}")
        record["observations"][row["Metabolite"]]={
            "daily":val,
            "weekday":finite_or_none(row["Weekday mean"]),
            "weekend":finite_or_none(row["Weekend mean"]),
            "previous_2024":None,
        }
    for s in sites.values():
        for substance,value in s["observations"].items():
            value["previous_2024"]=previous.get((s["id"],substance))
    if not 8<=len(sites)<=120:
        raise RuntimeError(f"Unexpected German site count {len(sites)}")
    for substance in SUBSTANCES:
        n=sum(1 for s in sites.values() if s["observations"].get(substance,{}).get("daily") is not None)
        if n<4:raise RuntimeError(f"Too few 2025 values for {substance}: {n}")
    result={
        "meta":{
            "source":"European Union Drugs Agency (EUDA) and SCORE 2026 release, observations 2025",
            "study_year":2025,
            "published_year":2026,
            "source_url":SOURCE_PAGE,
            "source_data_url":OBS_URL,
            "site_table_url":SITE_URL,
            "unit":"mg/1000 inhabitants/day",
            "measurement":"population-normalised load of uncorrected drug residues in raw sewage",
            "geography_note":"Each point is a sampled wastewater treatment site, NOT the whole city or county; no interpolation",
            "zero_note":"EUDA zero means below quantification limit; missing NA is null and NOT zero",
            "heroin_note":"EUDA does not use a specific stable heroin marker in this study; heroin has no wastewater layer",
            "source_bytes":{"observations":size,"sites":site_bytes},
            "substances":sorted(SUBSTANCES),
            "site_count":len(sites),
        },
        "sites":sorted(sites.values(),key=lambda x:x["id"])
    }
    DEST.parent.mkdir(parents=True,exist_ok=True)
    content=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if DEST.exists() and DEST.read_text(encoding="utf-8")==content:
        print(f"UNCHANGED {DEST.relative_to(ROOT)} ({len(sites)} sites)")
    else:
        DEST.write_text(content,encoding="utf-8")
        print(f"BUILT {DEST.relative_to(ROOT)} ({len(sites)} sites)")
    counts={substance:sum(1 for s in sites.values() if s["observations"].get(substance,{}).get("daily") is not None) for substance in sorted(SUBSTANCES)}
    print("SUBSTANCE_VALID_SITES",counts,flush=True)
    print("SITE SAMPLE",[(s["id"],s["city"],s["lat"],s["lon"]) for s in result["sites"][:12]],flush=True)

if __name__=="__main__":
    try:main()
    except Exception as e:
        print("EUDA BUILD FAILED: "+repr(e),file=sys.stderr)
        sys.exit(1)
