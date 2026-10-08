#!/usr/bin/env python3
"""Kiel 2025 police-neighbourhood *candidate*; never added to live map registry.

Official police annex Table 10 contains total recorded offenses, not violent
or property offense categories. This source is ONLY valid for an explicitly
named count-only local indicator, not the public violence/property modes.
"""
from __future__ import annotations

import argparse
import io
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

from pypdf import PdfReader

from city_build_common import download_bytes, download_json, write_geojson

ROOT=Path(__file__).resolve().parents[1]
PKS="https://www.schleswig-holstein.de/DE/landesregierung/ministerien-behoerden/POLIZEI/DasSindWir/PDen/Kiel/_downloads/pks/pks_pdkiel_2025.pdf?__blob=publicationFile&v=2"
GEOMETRY="https://ims.kiel.de/geodatenextern/rest/services/Stadtplan/LHKielWmsWfs/MapServer/38/query"
GEO_PARAMS={"where":"1=1","outFields":"*","outSR":"4326","f":"geojson"}
YEARS=list(range(2016,2026))
NUMBER=r"\d+(?:\.\d{3})*"
ROW=re.compile(rf"^(.+?)\s+({NUMBER}(?:\s+{NUMBER}){{9}})\s*$")


def key(name: str) -> str:
    name=unicodedata.normalize("NFKC",str(name))
    return re.sub(r"[\s\-‑‐–—]+","",name).casefold()


def police_rows(data: bytes):
    pages=PdfReader(io.BytesIO(data)).pages
    # PDF printed page labels 31–32 correspond to zero-based pages 30,31.
    text="\n".join((pages[i].extract_text() or "") for i in (30,31))
    text=re.sub(r"Neumühlen-\s*\n\s*Dietrichsdorf\s*\n",
                "Neumühlen-Dietrichsdorf ",text)
    rows={}
    for line in text.splitlines():
        match=ROW.fullmatch(line.strip())
        if not match:
            continue
        name,nums=match.groups()
        if name.strip()=="Stadtteil":
            continue
        counts=[int(x.replace(".","")) for x in nums.split()]
        if len(counts)!=10:continue
        rows[key(name)]={"name":name,"counts":dict(zip(map(str,YEARS),counts))}
    if "stadtkiel" not in rows or "tatortunbekannt" not in rows:
        raise RuntimeError("Kiel PDF annex table header or unknown-location row missing")
    # Known source layout: 31 police district rows + whole-city + unknown.
    if len(rows)<30 or len(rows)>40:
        raise RuntimeError(f"Unexpected row count {len(rows)}; PDF layout changed")
    total=rows["stadtkiel"]["counts"]["2025"]
    unknown=rows["tatortunbekannt"]["counts"]["2025"]
    return rows,total,unknown


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=None,
                        help="OPTIONAL local staging output. Never use data/city_layers.json.")
    args=parser.parse_args()
    rows,total,unknown=police_rows(download_bytes(PKS,timeout=80))
    geo=download_json(GEOMETRY,params=GEO_PARAMS,timeout=80)
    features=geo.get("features") or []
    if len(features)!=31:
        raise RuntimeError(f"Official Kiel geometry expected 31 Stadtteile, got {len(features)}")
    observed,matched,output=set(),set(),[]
    grouped={}
    # A city district can be delivered as several geographic feature parts.
    # Combine only exact same numbered official district, never neighbouring
    # names or nearby precincts.
    for feature in features:
        props=feature.get("properties") or {}
        name=str(props.get("Name","")).strip()
        code=props.get("Nummer")
        norm=key(name)
        if not name or code is None:
            raise RuntimeError(f"Missing Kiel geometry name/code: {name!r}, {code!r}")
        number=int(code)
        geom=feature.get("geometry") or {}
        if geom.get("type")=="Polygon":
            poly_parts=[geom.get("coordinates")]
        elif geom.get("type")=="MultiPolygon":
            poly_parts=geom.get("coordinates")
        else:
            raise RuntimeError(f"Invalid Kiel polygon geometry for {name}")
        old=grouped.get(norm)
        if old is None:
            grouped[norm]={"name":name,"code":number,"parts":list(poly_parts)}
        else:
            if old["code"]!=number:
                raise RuntimeError(f"Same name maps to multiple Kiel codes: {name}")
            old["parts"].extend(poly_parts)
    observed=set(grouped)
    for norm,group in grouped.items():
        police=rows.get(norm)
        if police is None:
            continue
        matched.add(norm)
        parts=group["parts"]
        geom=({"type":"Polygon","coordinates":parts[0]} if len(parts)==1
              else {"type":"MultiPolygon","coordinates":parts})
        year_counts=police["counts"]
        output.append({"type":"Feature","id":f"kiel-{group['code']:02d}","geometry":geom,
          "properties":{"city":"Kiel","state":"Schleswig-Holstein","name":group["name"],
                        "code":group["code"],"crime_total":{"cases":year_counts["2025"],"rate":None},
                        "annual_cases":year_counts}})
    exempt={"stadtkiel","tatortunbekannt"}
    missing_police=sorted((set(rows)-exempt)-matched)
    missing_geometry=sorted(observed-matched)
    city_sum=sum(x["counts"]["2025"] for k,x in rows.items() if k not in exempt)
    report={"geometry_parts":len(features),"geometry_districts":len(grouped),
            "matched":len(output),"statistic_rows":len(rows)-2,
            "city_total_2025":total,"unknown_tatort_2025":unknown,"district_sum_2025":city_sum,
            "unmatched_police":missing_police,"unmatched_geometry":missing_geometry,
            "districts_geom_names":[x["name"] for x in grouped.values()]}
    print("[kiel-staging] QA",json.dumps(report,ensure_ascii=False),flush=True)
    if missing_police or missing_geometry:
        raise RuntimeError("Official Kiel police/geography joins incomplete; do not publish")
    if city_sum+unknown!=total:
        raise RuntimeError(f"Kiel crime totals do not reconcile: {city_sum}+{unknown}!={total}")
    if len(output)!=len(grouped):
        raise RuntimeError("Kiel incomplete, not safe to stage")
    result={"type":"FeatureCollection",
      "meta":{"schema_version":1,"city":"Kiel","year":2025,"status":"candidate_only",
        "metric_scope":"all_offenses_count_only_NOT_violence_or_theft",
        "rate_status":"not_calculated_missing_verified_district_population",
        "unknown_place_cases_excluded_from_mapped_polygons":unknown,
        "crime_source":PKS,"geometry_source":GEOMETRY,
        "note":"Primary sources, NO public UI activation; these are all-offense counts, not violence/theft."},
      "features":sorted(output,key=lambda f:f["id"])}
    if args.output:
        if ROOT/"data/city_layers.json"==args.output.resolve():
            raise RuntimeError("staging may not overwrite live registry")
        write_geojson(args.output,result)
        print("[kiel-staging] candidate output",args.output,flush=True)
    print("[kiel-staging] PASS: official inputs reconcile; rate not estimated; not published",flush=True)


if __name__=="__main__":
    main()
