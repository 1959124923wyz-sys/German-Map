#!/usr/bin/env python3
"""Official Düsseldorf BV7/BV9 2025 Stadtteil CASE-COUNT source GIS join.

BV7 PP Düsseldorf 26 May 2026 pages 4–11: 5 Stadtteile × 8 police
crime categories × 2022–2025.
BV9 PI Süd 3 July 2026 pages 8 and 16: 8 Stadtteile × STREET CRIME
and RESIDENTIAL BURGLARY × 2021–2025 (IGVP/VIVA Eingangsstatistik).

All values are police-registered absolute cases, not rates. Never fill
unreported BV9 categories by estimation. No official PDF is republished.
"""
from __future__ import annotations
import argparse,io,json,re
from pathlib import Path
from pypdf import PdfReader
from shapely import make_valid
from shapely.geometry import shape,mapping
from shapely.ops import unary_union,transform
from pyproj import Transformer
from city_build_common import download_bytes,write_geojson
from build_duesseldorf_offenses_2025 import KNOWN as DISTRICT_TOTALS
from build_duesseldorf_bv6_local import GEO_URL

PDFS={
 "07":"http://ris-oparl.itk-rheinland.de/Oparl/bodies/0015/downloadfiles/00588348.pdf",
 "09":"http://ris-oparl.itk-rheinland.de/Oparl/bodies/0015/downloadfiles/00592935.pdf"
}
GEO_PARENT="artifacts/duesseldorf_district_boundaries_candidate.geojson"
NAMES={
 "07":("Gerresheim","Grafenberg","Ludenberg","Hubbelrath","Knittkuhl"),
 "09":("Hassels","Wersten","Holthausen","Benrath","Urdenbach","Reisholz","Himmelgeist","Itter")
}
CODES={
 "07":("071","072","073","074","075"),
 "09":("097","091","093","095","096","094","092","098")
}
CONFIG={
 "07":{
   "years":(2022,2023,2024,2025),
   "scope":"BV7_EIGHT_POLICE_OFFENSE_CLASSES",
   "source_type":"Police Stadtteil 2025 presentation to Bezirksvertretung 7, 26 May 2026",
   "metrics":{
     "all_offenses":(3,"Gesamtkriminalität",[1623,323,395,110,39],2490),
     "street_crime":(4,"Straßenkriminalität",[397,99,84,11,9],600),
     "street_robbery":(5,"Raub auf Straßen, Wegen oder Plätzen",[6,1,0,0,0],7),
     "street_injury":(6,"Körperverletzung auf Straßen, Wegen und Plätzen",[10,1,3,0,0],14),
     "vehicle_related_theft":(7,"Diebstahl an / aus Kraftfahrzeugen",[97,35,17,5,5],159),
     "bicycle_theft":(8,"Diebstahl von Fahrrädern",[46,21,16,1,0],84),
     "pickpocketing":(9,"Taschendiebstahl",[96,11,9,1,0],117),
     "residential_burglary":(10,"Wohnungseinbruchkriminalität",[41,20,27,10,4],102)
   }
 },
 "09":{
   "years":(2021,2022,2023,2024,2025),
   "scope":"BV9_ONLY_STREET_CRIME_AND_RESIDENTIAL_BURGLARY",
   "source_type":"PI Süd Düsseldorf 2025 Sicherheitslagebild 3 July 2026; IGVP/ViVa Eingangsstatistik",
   "metrics":{
     "street_crime":(7,"Entwicklung Straßenkriminalität in den Stadtteilen",[269,409,269,459,104,93,38,18],1659),
     "residential_burglary":(15,"Entwicklung Wohnungseinbruchskriminalität in den Stadtteilen",[44,59,32,16,13,15,2,3],184)
   }
 }
}
METER=Transformer.from_crs("EPSG:4326","EPSG:3035",always_xy=True).transform

def read_pdf(bv):
    raw=download_bytes(PDFS[bv],timeout=85)
    if not raw.startswith(b"%PDF-"):raise ValueError("Not an original police PDF for BV"+bv)
    pdf=PdfReader(io.BytesIO(raw))
    config=CONFIG[bv];names=NAMES[bv];years=config["years"]
    data={};pp_total={}
    for metric,(idx,title,known,total_2025) in config["metrics"].items():
        if len(pdf.pages)<=idx:raise ValueError(f"BV{bv} missing original PDF page {idx+1}")
        text=pdf.pages[idx].extract_text() or ""
        if title not in text or any(name not in text for name in names):
            raise ValueError(f"BV{bv} category or names changed for {metric}, page {idx+1}")
        table={}
        if bv=="07":
            for line in text.splitlines():
                matched=re.fullmatch(r"\s*(202[2-5])\s+((?:[0-9.]+\s+){6}[0-9.]+)\s*",line)
                if not matched:continue
                year=int(matched.group(1))
                numbers=[int(t.replace(".","")) for t in matched.group(2).split()]
                if len(numbers)!=7 or year in table:
                    raise ValueError(f"BV7 invalid police row for {metric}: {line}")
                if sum(numbers[:5])!=numbers[5]:
                    raise ValueError(f"BV7 police five-neighbourhood cases do not sum {metric}/{year}: {numbers}")
                table[year]=numbers
        else:
            # German police PI Süd table: each named row stores
            # 2021 2022 2023 2024 2025 followed by 2024→25 delta/%.
            per_year={int(year):[] for year in years}
            for name in names:
                lines=[line.strip() for line in text.splitlines()
                       if re.match(r"^"+re.escape(name)+r"\s+",line.strip())]
                parsed=[]
                for line in lines:
                    toks=line.split()
                    if len(toks)<7:continue
                    try:
                        nums=[int(v.replace(".","")) for v in toks[1:6]]
                    except ValueError:continue
                    if len(nums)==5:parsed.append(nums)
                if len(parsed)!=1:
                    raise ValueError(f"BV9 police 5-year named row missing/duplicate for {metric}/{name}: {lines}")
                for year,n in zip(years,parsed[0]):
                    per_year[year].append(n)
            parent_lines=[line.strip() for line in text.splitlines()
                         if re.match(r"^Stadtbezirk 9\s+",line.strip())]
            parent=[]
            for line in parent_lines:
                tokens=line.split()
                try:nums=[int(v.replace(".","")) for v in tokens[2:7]]
                except (ValueError,IndexError):continue
                if len(nums)==5:parent.append(nums)
            if len(parent)!=1:raise ValueError(f"BV9 main Stadtbezirk 9 row missing for {metric}")
            for j,year in enumerate(years):
                nums=per_year[year]
                subtotal=sum(nums)
                if subtotal!=parent[0][j]:
                    raise ValueError(f"BV9 locality checksum mismatch {metric}/{year}: {subtotal} != {parent[0][j]}")
                table[year]=nums+[subtotal,None]
        if set(table)!=set(years):
            raise ValueError(f"BV{bv} {metric}: required {years}, got {sorted(table)}")
        if table[2025][:len(names)]!=known or table[2025][len(names)]!=total_2025:
            raise ValueError(f"BV{bv} original 2025 police category drift: {metric}={table[2025]}")
        data[metric]={str(y):table[y][:len(names)] for y in years}
        if bv=="07":pp_total[metric]={str(y):table[y][-1] for y in years}
    if bv=="07":
        for year in years:
            if sum(data["all_offenses"][str(year)])!=DISTRICT_TOTALS[year][6]:
                raise ValueError(f"BV7 official 5-area all-offense counts do not match independent 10-district source {year}")
    print("[duesseldorf-more-source] PASS",json.dumps({
       "district":bv,"source_pdf":PDFS[bv],"area_count":len(names),
       "metrics":len(data),"years":list(years),
       "2025_sum":{k:sum(v["2025"]) for k,v in data.items()}},ensure_ascii=False),flush=True)
    return data,pp_total

def valid_polygon(g,name):
    if g.is_empty:raise ValueError("Empty municipal district polygon "+name)
    if not g.is_valid:
        repaired=make_valid(g)
        if repaired.geom_type=="GeometryCollection":
            repaired=unary_union([x for x in repaired.geoms if x.geom_type in ("Polygon","MultiPolygon")])
        if repaired.is_empty or repaired.geom_type not in ("Polygon","MultiPolygon") or not repaired.is_valid:
            raise ValueError(f"Unrepairable official Stadtteil polygon {name}")
        change=abs(transform(METER,g).area-transform(METER,repaired).area)
        if change>100:raise ValueError(f"{name} municipal polygon repair exceeded 100m²")
        print("[duesseldorf-more] official minor shape repair",name,round(change,3),flush=True)
        g=repaired
    return g

def build(bv,output,release):
    if bv not in CONFIG:raise ValueError("Only independently verified source district 07 or 09")
    official_out=f"data/duesseldorf_bv{int(bv)}_local_2025.geojson"
    if release and output!=official_out:raise ValueError(f"Wrong public BV{bv} path")
    if not release and output.startswith("data/"):raise ValueError("Cannot publish candidate without explicit approval")
    metrics,police_full_city=read_pdf(bv)
    original=json.loads(download_bytes(GEO_URL,timeout=75).decode("utf-8-sig"))
    if len(original.get("features",[]))!=50:raise ValueError("Original Düsseldorf 2025 city has not got 50 Stadtteil polygons")
    index={f.get("properties",{}).get("Nummer"):f for f in original["features"]}
    names=NAMES[bv];codes=CODES[bv];years=CONFIG[bv]["years"]
    features=[];projected=[]
    for i,(name,code) in enumerate(zip(names,codes)):
        source=index.get(code)
        if not source or source.get("properties",{}).get("Name")!=name:
            raise ValueError(f"BV{bv} official Stadtteil code/name mismatched: {code} expected {name}, got {source and source.get('properties')}")
        g=valid_polygon(shape(source["geometry"]),name)
        projected.append(transform(METER,g))
        props={"name":name,"stadtteil_code":code,"parent_stadtbezirk":bv,
         "year":2025,"metric_scope":CONFIG[bv]["scope"],
         "metrics":{metric:{**{str(year):values[str(year)][i] for year in years},"rate":None}
           for metric,values in metrics.items()}}
        features.append({"type":"Feature","id":f"duesseldorf-stadtteil-{code}",
                         "properties":props,"geometry":mapping(g)})
    overlap=sum(projected[i].intersection(projected[j]).area for i in range(len(projected)) for j in range(i))
    if overlap>5:raise ValueError(f"Official BV{bv} Stadtteile polygons overlap {overlap:.2f}m²")
    parent=json.loads(Path(GEO_PARENT).read_text(encoding="utf-8"))
    parents=[f for f in parent["features"] if f["properties"]["district_code"]==bv]
    if len(parents)!=1:raise ValueError(f"Missing official Düsseldorf parent Stadtbezirk {bv}")
    parent_g=transform(METER,valid_polygon(shape(parents[0]["geometry"]),bv))
    united=unary_union(projected)
    diff=united.symmetric_difference(parent_g).area
    if diff>max(1500,parent_g.area*0.001):
        raise ValueError(f"BV{bv} children cannot cover official parent (difference {diff:.2f}m²)")
    sums={metric:{str(y):sum(data[str(y)]) for y in years} for metric,data in metrics.items()}
    if bv=="07" and sums["all_offenses"]["2025"]!=2490:
        raise ValueError("BV7 source category cannot match official 10 district all offense sum")
    if bv=="09" and (sums["street_crime"]["2025"]!=1659 or sums["residential_burglary"]["2025"]!=184):
        raise ValueError("BV9 two independent original category totals changed")
    doc={"type":"FeatureCollection","meta":{
       "status":"supplementary_bv_additional_neighbourhood_cases_only" if release else "candidate_bv_additional_neighbourhood_cases_only",
       "city":"Düsseldorf","source_statistical_year":2025,"parent_stadtbezirk":bv,
       "scope":CONFIG[bv]["scope"],"source_type":CONFIG[bv]["source_type"],
       "police_source":"https:"+PDFS[bv][5:],"source_years":list(years),
       "police_source_pages":[v[0]+1 for v in CONFIG[bv]["metrics"].values()],
       "municipal_geometry_source":GEO_URL,
       "municipal_geometry_licence":"Datenlizenz Deutschland – Zero – Version 2.0",
       "neighbourhoods":len(names),"categories":list(metrics),
       "area_km2":round(united.area/1e6,4),
       "parent_outline_diff_m2":round(diff,3),"internal_overlap_m2":round(overlap,3),
       "mapped_by_category":sums,"offense_rates":None,
       "all_offenses_parent_count_2025":2490 if bv=="07" else None,
       "scope_warning":"BV7 has 8 PKS presentation categories for five Stadtteile; BV9 has ONLY street crime and burglary IGVP/VIVA incoming-case statistics for eight Stadtteile. Do NOT extrapolate BV9 missing six categories or compare absolute cases as per capita safety rates.",
       "police_citywide_category_totals":police_full_city
     },"features":features}
    write_geojson(output,doc)
    print("[duesseldorf-more-join] PASS",json.dumps({
       "bv":bv,"public":release,"features":len(features),"metrics":len(metrics),
       "mapped_2025":{k:v["2025"] for k,v in sums.items()},
       "parent_outline_diff_m2":round(diff,2),"overlap_m2":round(overlap,2),
       "area_km2":round(united.area/1e6,3)},ensure_ascii=False),flush=True)
    return doc

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--district",required=True,choices=("07","09"))
    p.add_argument("--output",required=True)
    p.add_argument("--release-count-only",action="store_true")
    a=p.parse_args()
    build(a.district,a.output,a.release_count_only)
if __name__=="__main__":main()
