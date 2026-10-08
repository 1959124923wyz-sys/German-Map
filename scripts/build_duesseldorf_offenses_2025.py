#!/usr/bin/env python3
"""2025 Düsseldorf complete ten-Stadtbezirk TOTAL-CRIME CASES from police.

Source: Polizeipräsidium Düsseldorf, presentation to BV6, 10 June 2026,
page 2 'Gesamtkriminalität aller Stadtbezirke', covering 2022–2025.
Do not mix with nationwide violent/property rate data. The difference
between the official citywide total and 10 area totals remains unallocated.
"""
from __future__ import annotations
import argparse,io,json,re
from pathlib import Path
from pypdf import PdfReader
from city_build_common import download_bytes,write_geojson

PDF_ORIGINAL="http://ris-oparl.itk-rheinland.de/Oparl/bodies/0015/downloadfiles/00589618.pdf"
PDF_PUBLIC="https://ris-oparl.itk-rheinland.de/Oparl/bodies/0015/downloadfiles/00589618.pdf"
GEO=Path("artifacts/duesseldorf_district_boundaries_candidate.geojson")
FILE="data/duesseldorf_total_cases_2025.geojson"
KNOWN={
 2022:[21672,5091,12314,3109,3298,4475,2557,3961,5917,1594,65763],
 2023:[23029,5249,12530,3051,3810,4214,2430,3984,5694,1503,67695],
 2024:[23113,5198,13387,3286,4065,4432,2337,3904,5840,1497,68915],
 2025:[22396,5062,13314,3499,4259,5097,2490,4166,6438,1503,69522]
}
def source_table(pdf):
    reader=PdfReader(io.BytesIO(pdf))
    if len(reader.pages)<5:raise ValueError("Düsseldorf presentation PDF truncated")
    text=reader.pages[1].extract_text() or ""
    if "Gesamtkriminalität aller Stadtbezirke" not in text or "BV 10" not in text:
        raise ValueError("Not the Düsseldorf official 10-district total crime table")
    data={}
    for year in KNOWN:
        rows=re.findall(rf"(?m)^\s*{year}\s+([0-9. \t]+?)\s*$",text)
        parsed=[]
        for row in rows:
            vals=[int(x.replace(".","")) for x in re.findall(r"\d{1,3}(?:\.\d{3})+|\d+",row)]
            if len(vals)==11:parsed.append(vals)
        if len(parsed)!=1:raise ValueError(f"Official year {year} expected exactly one 11-number row, got {parsed}")
        if parsed[0]!=KNOWN[year]:
            raise ValueError(f"Official Düsseldorf {year} table changed: {parsed[0]}")
        data[year]=parsed[0]
    for i in range(10):
        if data[2025][i]-data[2024][i] != KNOWN[2025][i]-KNOWN[2024][i]:
            raise ValueError("Source 2025 vs 2024 district annual delta discrepancy")
    summary={y:{"mapped":sum(v[:10]),"city":v[10],"city_minus_district":v[10]-sum(v[:10])} for y,v in data.items()}
    if any(v["city_minus_district"]<0 for v in summary.values()):
        raise ValueError("District crime totals exceed police city report")
    print("[duesseldorf-offenses] OFFICIAL POLICE PDF PASS",json.dumps(summary,ensure_ascii=False),flush=True)
    return data,summary

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--geometry",default=str(GEO))
    ap.add_argument("--output",default="artifacts/duesseldorf_total_cases_candidate.geojson")
    ap.add_argument("--release-count-only",action="store_true")
    args=ap.parse_args()
    if args.release_count_only and args.output!=FILE:raise ValueError("Only approved Düsseldorf count path may be published")
    if not args.release_count_only and args.output.startswith("data/"):raise ValueError("research candidates cannot be published")
    data,year_stats=source_table(download_bytes(PDF_ORIGINAL,timeout=75))
    geo=json.loads(Path(args.geometry).read_text(encoding="utf-8"))
    if (geo.get("meta",{}).get("status")!="candidate_geometry_only" or
        geo["meta"].get("districts")!=10 or geo["meta"].get("overlap_m2")!=0 or
        not 217.3<geo["meta"].get("area_km2",0)<217.5):
        raise ValueError("Düsseldorf original geodata QA missing")
    features=[]
    for f in geo["features"]:
        code=f["properties"].get("district_code","")
        if not re.fullmatch(r"0[1-9]|10",code):raise ValueError("Wrong official district code "+str(code))
        n=int(code)-1
        p={**f["properties"],"year":2025,"offense_metric_scope":"all_recorded_pks_cases",
           "crime_total":{str(year):data[year][n] for year in sorted(KNOWN)}}
        p["crime_total"]["rate"]=None
        features.append({**f,"properties":p})
    if len(features)!=10 or len({f["properties"]["district_code"] for f in features})!=10:
        raise ValueError("Official 10 district geometry join incomplete")
    doc={"type":"FeatureCollection","meta":{
      "status":"supplementary_all_offense_count_only" if args.release_count_only else "candidate_all_offense_count_only",
      "city":"Düsseldorf","year":2025,"available_years":[2022,2023,2024,2025],
      "metric_scope":"all_offense_cases_by_police_stadtbezirk_NOT_violence_rates",
      "source":PDF_PUBLIC,"original_report_url":PDF_ORIGINAL,
      "source_title":"Polizeipräsidium Düsseldorf, PD Hammerschlag, BV6 presentation dated 10 June 2026, PDF p.2",
      "source_reference":"https://duesseldorf-radar.de/sitzung/2026/06/bezirksvertretung-6",
      "geometry_source":geo["meta"]["source_url"],"districts":10,
      "area_km2":geo["meta"]["area_km2"],
      "mapped_by_year":{str(y):stats["mapped"] for y,stats in year_stats.items()},
      "city_by_year":{str(y):stats["city"] for y,stats in year_stats.items()},
      "undistributed_by_year":{str(y):stats["city_minus_district"] for y,stats in year_stats.items()},
      "no_population_rates":True,
      "limitation":"The source aggregates offenses from ALL ten Düsseldorf Stadtbezirke. Crime cases are not per-capita risks. Police headquarters' totals are larger than the sum of city district counts, and the difference is NOT assigned to polygons."
    },"features":features}
    write_geojson(args.output,doc)
    print("[duesseldorf-2025] JOIN PASS",json.dumps({"districts":10,"mapped_2025":year_stats[2025]["mapped"],
        "citywide_2025":year_stats[2025]["city"],"not_distributed":year_stats[2025]["city_minus_district"],
        "published":args.release_count_only},ensure_ascii=False),flush=True)

if __name__=="__main__":main()
