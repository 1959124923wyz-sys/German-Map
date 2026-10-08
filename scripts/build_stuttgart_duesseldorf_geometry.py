#!/usr/bin/env python3
"""Prepare source-verifiable Stuttgart/Düsseldorf OFFLINE staging geometries.

Never publish these candidate geographies to production map before official
district-matched crime values are independently verified. No rate imputation.
"""
from __future__ import annotations
import io,json,sqlite3,tempfile,zipfile,shutil
from pathlib import Path
import requests
from shapely import wkb
from shapely.geometry import shape,mapping
from shapely.ops import transform,unary_union
from shapely.validation import explain_validity
from shapely import make_valid
from pyproj import Transformer

STUTTGART="https://www.stuttgart.de/medien/ibs/OpenData-KLGL-Generalsisiert.zip"
DUSSELDORF="https://opendata.duesseldorf.de/sites/default/files/Stadtbezirke_2025_WGS84_EPSG4326.geojson"
TO_GPS=Transformer.from_crs("EPSG:25832","EPSG:4326",always_xy=True).transform
TO_METRIC=Transformer.from_crs("EPSG:4326","EPSG:3035",always_xy=True).transform
HTTP=requests.Session()
HTTP.headers["User-Agent"]="German-Map geographic data validation (https://github.com/1959124923wyz-sys/German-Map)"
TARGET=Path("artifacts")

def download(url):
    response=HTTP.get(url,timeout=75)
    response.raise_for_status()
    if len(response.content)<1000:raise ValueError(f"source unexpectedly short {url}")
    return response.content

def from_gpkg(blob):
    if not blob or blob[:2]!=b"GP":raise ValueError("Invalid GPKG geometry BLOB")
    # GeoPackage WKB prefix: GP/version/flags/4-byte srs_id/envelope (0|32|48|48|64 bytes).
    env_type=(blob[3]>>1)&7
    size={0:0,1:32,2:48,3:48,4:64}.get(env_type)
    if size is None:raise ValueError(f"Unknown GPKG envelope type {env_type}")
    geom=wkb.loads(blob[8+size:])
    if geom.is_empty or not geom.is_valid or geom.geom_type not in ("Polygon","MultiPolygon"):
        raise ValueError("Invalid Stuttgart source polygon")
    return transform(TO_GPS,geom)

def save(city,source,features,audit):
    if len(features)!=len({f["id"] for f in features}):
        raise ValueError(city+" duplicate official district codes")
    valid=[]
    repair_audit=[]
    for f in features:
        source=shape(f["geometry"])
        if source.is_empty:raise ValueError(city+": empty official polygon")
        if not source.is_valid:
            diagnosis=explain_validity(source)
            fixed=make_valid(source)
            # Closed invalid polygons can have stray collapsed lines. Retain
            # only polygonal components; do NOT smooth, buffer or interpolate.
            if fixed.geom_type=="GeometryCollection":
                from shapely.geometry import Polygon,MultiPolygon
                polygons=[g for g in fixed.geoms if g.geom_type in ("Polygon","MultiPolygon")]
                fixed=unary_union(polygons)
            if not fixed.is_valid or fixed.geom_type not in ("Polygon","MultiPolygon"):
                raise ValueError(f"{city} {f['id']}: cannot safely repair {diagnosis}")
            old_km2=transform(TO_METRIC,source).area/1e6
            new_km2=transform(TO_METRIC,fixed).area/1e6
            delta_m2=abs(new_km2-old_km2)*1e6
            print("[city-geography] official invalid polygon",json.dumps({
               "city":city,"feature":f["id"],"reason":diagnosis,
               "area_change_m2":round(delta_m2,3)},ensure_ascii=False),flush=True)
            if delta_m2>100:
                raise ValueError(f"{city} {f['id']} repair exceeded 100m²; manual source review needed")
            repair_audit.append({"id":f["id"],"diagnosis":diagnosis,"area_change_m2":round(delta_m2,3)})
            f["geometry"]=mapping(fixed)
            source=fixed
        valid.append(source)
    geoms=[transform(TO_METRIC,g) for g in valid]
    overlap=0.
    for i in range(len(geoms)):
        for j in range(i):
            if geoms[i].intersects(geoms[j]):
                overlap+=geoms[i].intersection(geoms[j]).area
    union=unary_union(geoms)
    area=union.area/1e6
    if overlap>200:
        raise ValueError(f"{city}: overlaps between official districts {overlap:.2f} sqm")
    expect={"stuttgart":(205,210,23),"duesseldorf":(214,222,10)}
    low,high,n=expect[city]
    if len(features)!=n or not(low<area<high):
        raise ValueError(f"{city}: {len(features)} official districts area={area:.2f} km²")
    out={"type":"FeatureCollection","meta":{
          "city":city,"year":2025,"status":"candidate_geometry_only",
          "source_url":source,"source_name":"Official municipality small-area administrative boundaries",
          "invalid_source_polygons_safely_repaired":repair_audit,
          "districts":len(features),"area_km2":round(area,4),
          "overlap_m2":round(overlap,3),"unclassified_police_metrics":True,
          "warning":"Administrative polygons alone do not demonstrate local criminal statistics."},
         "features":features}
    TARGET.mkdir(exist_ok=True)
    (TARGET/f"{city}_district_boundaries_candidate.geojson").write_text(
        json.dumps(out,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf8")
    print("[city-geography] PASS",json.dumps({"city":city,
        "districts":len(features),"union_km2":round(area,3),
        "overlap_m2":round(overlap,3),"repaired":len(repair_audit),"fields":audit},ensure_ascii=False),flush=True)

def stuttgart():
    raw=download(STUTTGART)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        sources=[n for n in z.namelist() if n.lower().endswith(".gpkg")]
        if len(sources)!=1:raise ValueError("Official Stuttgart ZIP should contain one GeoPackage")
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/"official.gpkg"
            with z.open(sources[0]) as src,path.open("wb") as dest:shutil.copyfileobj(src,dest)
            con=sqlite3.connect(path)
            table="KLGL_BRUTTO_STADTBEZIRK"
            rows=con.execute(f'SELECT STADTBEZIRKNR,STADTBEZIRKNAME,SHAPE FROM "{table}"').fetchall()
            # An independent official complete city boundary for coverage.
            municipal=con.execute('SELECT SHAPE FROM "KLGL_BRUTTO_GEMEINDE"').fetchone()
            con.close()
    if len(rows)!=23:raise ValueError(f"Stuttgart expected 23 districts got {len(rows)}")
    features=[]
    for code,name,blob in rows:
        geom=from_gpkg(blob)
        features.append({"type":"Feature","id":"stuttgart-"+str(code).zfill(2),
          "properties":{"city":"Stuttgart","district_code":str(code).zfill(2),
            "name":name,"official_crime_values":None},
          "geometry":mapping(geom)})
    municipal_area=transform(TO_METRIC,from_gpkg(municipal[0]))
    union=unary_union([transform(TO_METRIC,shape(f["geometry"])) for f in features])
    if municipal_area.symmetric_difference(union).area>municipal_area.area*.001:
        raise ValueError("Stuttgart districts do not align with official city outline")
    save("stuttgart",STUTTGART,features,
         {"county_vs_district_diff_m2":round(municipal_area.symmetric_difference(union).area,2),
          "source_crs":"EPSG:25832 → EPSG:4326", "source_license":"CC BY 4.0"})

def duesseldorf():
    obj=json.loads(download(DUSSELDORF).decode("utf-8-sig"))
    source=obj["features"]
    features=[]
    for f in source:
        code=str(f["properties"]["Stadtbezirke"]).zfill(2)
        features.append({"type":"Feature","id":"duesseldorf-"+code,
         "properties":{"city":"Düsseldorf","district_code":code,
                       "name":"Stadtbezirk "+str(int(code)),"official_crime_values":None},
         "geometry":f["geometry"]})
    save("duesseldorf",DUSSELDORF,features,
         {"source_crs":"EPSG:4326", "police_cases_attached":False})

def main():
    stuttgart()
    duesseldorf()
if __name__=="__main__":main()
