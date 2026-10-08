#!/usr/bin/env python3
"""Düsseldorf BV6: original 2025 four-Stadtteil PKS, eight official categories.

Polizei Düsseldorf's 10 June 2026 BV6 presentation pp.4–11, police
years 2022–2025, is joined ONLY to Düsseldorf's original 2025 Stadtteil
polygons 061–064. An independent official Stadtbezirk 6 polygon validates
the geographic coverage. This is absolute CASE COUNT, not population rates.

Any missing row, altered data, broken topology or year misalignment FAILS.
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
from build_duesseldorf_offenses_2025 import PDF_ORIGINAL,PDF_PUBLIC,KNOWN

GEO_URL="https://opendata.duesseldorf.de/sites/default/files/Stadtteile_2025_WGS84_EPSG4326_1.geojson"
PARENT_GEO=Path("artifacts/duesseldorf_district_boundaries_candidate.geojson")
PUBLIC="data/duesseldorf_bv6_local_2025.geojson"
NAMES=("Lichtenbroich","Unterrath","Rath","Mörsenbroich")
CODES=("061","062","063","064")
YEARS=(2022,2023,2024,2025)
CATEGORIES={
 "all_offenses":(3,"Gesamtkriminalität",[528,1609,1864,1096],5097),
 "street_crime":(4,"Straßenkriminalität",[157,569,384,256],1366),
 "street_robbery":(5,"Raub auf Straßen, Wegen oder Plätzen",[0,3,5,2],10),
 "street_injury":(6,"Körperverletzung auf Straßen, Wegen und Plätzen",[2,15,19,9],45),
 "vehicle_related_theft":(7,"Diebstahl an und aus Kraftfahrzeugen",[59,275,86,84],504),
 "bicycle_theft":(8,"Diebstahl von Fahrrädern",[6,44,43,33],126),
 "pickpocketing":(9,"Taschendiebstahl",[4,31,51,18],104),
 "residential_burglary":(10,"Wohnungseinbruchkriminalität",[27,43,44,71],185)
}
METRIC=Transformer.from_crs("EPSG:4326","EPSG:3035",always_xy=True).transform

def parse_source(raw):
    reader=PdfReader(io.BytesIO(raw))
    if len(reader.pages)<11:raise ValueError("Original 2025 BV6 police PDF missing source tables")
    metrics={key:{} for key in CATEGORIES}
    city_totals={}
    for key,(pdf_index,title,expected,known_total) in CATEGORIES.items():
        page=reader.pages[pdf_index].extract_text() or ""
        if title not in page or not all(name in page for name in NAMES):
            raise ValueError(f"Original PDF page {pdf_index+1} category/area heading changed")
        table={}
        for line in page.splitlines():
            match=re.fullmatch(r"\s*(202[2-5])\s+((?:[0-9.]+\s+){5}[0-9.]+)\s*",line)
            if not match:continue
            year=int(match.group(1))
            values=[int(v.replace(".","")) for v in match.group(2).split()]
            if len(values)!=6 or year in table:raise ValueError(f"Invalid PDF table {key} {year}: {values}")
            if sum(values[:4])!=values[4]:
                raise ValueError(f"Source {key} {year}: four local case counts != BV6 sum")
            table[year]=values
        if set(table)!=set(YEARS):
            raise ValueError(f"PDF source {key} expected annual 2022-25 rows; got {list(table)}")
        if table[2025][:4]!=expected or table[2025][4]!=known_total:
            raise ValueError(f"2025 original police source checksum changed: {key}={table[2025]}")
        metrics[key]={str(y):table[y][:4] for y in YEARS}
        city_totals[key]={str(y):table[y][5] for y in YEARS}
    # The 2025 all-offense counts independently agree with the 10-district source slide 2.
    for y in YEARS:
        if sum(metrics["all_offenses"][str(y)])!=KNOWN[y][5] or city_totals["all_offenses"][str(y)]!=KNOWN[y][10]:
            raise ValueError(f"BV6 all-offense 4-area and 10-district cross-check failed for {y}")
    print("[bv6-source] PASS: 8 categories × 4 neighbourhoods × 4 years, official 10-district check",flush=True)
    return metrics,city_totals

def safe_polygon(geom,name):
    old=transform(METRIC,geom).area
    if geom.is_empty:raise ValueError("Empty official Stadtteil "+name)
    if not geom.is_valid:
        repaired=make_valid(geom)
        if repaired.geom_type=="GeometryCollection":
            repaired=unary_union([g for g in repaired.geoms if g.geom_type in ("Polygon","MultiPolygon")])
        if not repaired.is_valid or repaired.geom_type not in ("Polygon","MultiPolygon"):
            raise ValueError(f"Official {name} geometrically invalid; cannot safely use")
        delta=abs(transform(METRIC,repaired).area-old)
        if delta>100:raise ValueError(f"Source {name} repair too large: {delta:.1f} m²")
        print("[bv6-geo] official minor repair",name,round(delta,3),flush=True)
        geom=repaired
    return geom

def build(out,release):
    if release and str(out)!=PUBLIC:raise ValueError("Only approved BV6 public count file may be written")
    if not release and str(out).startswith("data/"):raise ValueError("candidate cannot leak to production data")
    police,city=parse_source(download_bytes(PDF_ORIGINAL,timeout=75))
    # The exact 2025 50-Stadtteil source is immutable: persist it once and
    # reuse for the BV7/BV9 builders to avoid three simultaneous GIS fetches.
    cache=Path("data/duesseldorf_official_stadtteile_2025.geojson")
    if cache.exists():
        data=json.loads(cache.read_text(encoding="utf-8"))
    else:
        data=json.loads(download_bytes(GEO_URL,timeout=75).decode("utf-8-sig"))
        if len(data.get("features",[]))==50:
            write_geojson(cache,data)
    if len(data.get("features",[]))!=50:
        raise ValueError("Official 2025 Düsseldorf original 50 district GIS is incomplete")
    selected=[f for f in data.get("features",[]) if f.get("properties",{}).get("Name") in NAMES]
    if len(data.get("features",[]))!=50 or len(selected)!=4:
        raise ValueError("Official 2025 Düsseldorf Stadtteil geographic roster changed")
    byname={f["properties"]["Name"]:f for f in selected}
    features=[];geoms=[]
    for index,(name,code) in enumerate(zip(NAMES,CODES)):
        raw=byname[name]
        if raw["properties"].get("Nummer")!=code:
            raise ValueError(f"Official name/number code mismatch: {name} {code}")
        geom=safe_polygon(shape(raw["geometry"]),name)
        geoms.append(transform(METRIC,geom))
        metrics={key:{**{str(y):police[key][str(y)][index] for y in YEARS},"rate":None}
                 for key in CATEGORIES}
        props={"name":name,"stadtteil_code":code,"parent_stadtbezirk":"06","year":2025,
               "metric_scope":"police_published_BV6_local_cases_only","metrics":metrics}
        features.append({"type":"Feature","id":"duesseldorf-stadtteil-"+code,
          "properties":props,"geometry":mapping(geom)})
    overlap=sum(geoms[i].intersection(geoms[j]).area for i in range(4) for j in range(i))
    if overlap>5:raise ValueError(f"Four official Stadtteil polygons overlap: {overlap:.2f} m²")
    union=unary_union(geoms)
    original=json.loads(PARENT_GEO.read_text(encoding="utf-8"))
    parents=[f for f in original.get("features",[]) if f.get("properties",{}).get("district_code")=="06"]
    if len(parents)!=1:raise ValueError("Official 2025 parent Stadtbezirk 06 not found")
    parent=transform(METRIC,shape(parents[0]["geometry"]))
    diff=parent.symmetric_difference(union).area
    if diff>max(1500,parent.area*0.001):
        raise ValueError(f"4 official 2025 Stadtteile fail BV6 2025 boundary coverage: {diff:.2f}m² / parent={parent.area:.2f}m²")
    totals={key:{str(y):sum(police[key][str(y)]) for y in YEARS} for key in CATEGORIES}
    docs={"type":"FeatureCollection","meta":{
       "status":"supplementary_bv6_neighbourhood_cases_only" if release else "candidate_bv6_neighbourhood_cases_only",
       "scope":"DUESSELDORF_STADTBEZIRK_06_ONLY_NOT_CITYWIDE",
       "year":2025,"available_years":list(YEARS),"districts":4,"municipality":"Düsseldorf",
       "parent_stadtbezirk":"06","police_source":PDF_PUBLIC,"source_pages":[4,5,6,7,8,9,10,11],
       "municipal_geometry_source":GEO_URL,
       "geometry_licence":"Datenlizenz Deutschland - Zero - Version 2.0",
       "area_km2":round(union.area/1e6,4),"polygons_overlap_m2":round(overlap,3),
       "difference_parent_stadtbezirk_m2":round(diff,3),
       "mapped_categories":totals,"police_full_city_reference":city,
       "all_offense_parent_2025":5097,
       "metric_labels":{
         "all_offenses":"全部登记犯罪","street_crime":"街头犯罪","street_robbery":"道路／广场抢劫",
         "street_injury":"道路／广场伤害","vehicle_related_theft":"机动车相关盗窃",
         "bicycle_theft":"自行车盗窃","pickpocketing":"扒窃","residential_burglary":"住宅入室盗窃"},
       "limitations":"Only four Stadtteile of Stadtbezirk 6 have eight category tables. Elsewhere only 10-Stadtbezirk total crime data exist. NO 2025 neighbourhood population rates."
       },"features":features}
    write_geojson(out,docs)
    print("[bv6-join] PASS",json.dumps({"release":release,"areas":4,
       "parent_total_2025":totals["all_offenses"]["2025"],
       "categories_2025":{k:v["2025"] for k,v in totals.items()},
       "geom_sqkm":round(union.area/1e6,4),"parent_boundary_diff_m2":round(diff,2),
       "overlap_m2":round(overlap,3)},ensure_ascii=False),flush=True)
    return docs

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",default="artifacts/duesseldorf_bv6_local_candidate.geojson")
    p.add_argument("--release-count-only",action="store_true")
    a=p.parse_args()
    build(a.output,a.release_count_only)
if __name__=="__main__":main()
