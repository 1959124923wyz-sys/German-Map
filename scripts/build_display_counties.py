#!/usr/bin/env python3
"""Create a topology-consistent display county layer for detailed cities.

The fine-grained official PLR/Stadtbezirk geometry is kept byte-for-byte in the
source data. Only a *separate display-only* nationwide county GeoJSON is
harmonised to the high-resolution outer municipal boundaries.

Why: country/county geometry and municipal WFS geometry use different mapping
scales. Their boundary mismatch creates narrow city-coloured/white "teeth" when
both are rendered in Leaflet.

No crime figures, district ids or source city geometry are changed.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import shape, mapping, Polygon, MultiPolygon
from shapely.ops import transform, unary_union

from city_build_common import write_geojson

ROOT=Path(__file__).resolve().parents[1]
COUNTY_FILE=ROOT/"data/germany-counties.geojson"
OUT=ROOT/"data/germany-counties-display.geojson"

# These metro boundaries have verified high-resolution polygon coverage.
CITY_SOURCES={
  "11000":"data/berlin_violent_2025.geojson",  # Berlin
  "09162":"data/munich_local_2025.geojson",    # München Stadt, NOT Landkreis 09184
  "02000":"data/hamburg_local_2025.geojson",
  "14713":"data/leipzig_local_2025.geojson",
  "14511":"data/chemnitz_local_2025.geojson",
  # Dresden's two available boundaries differ by >20% in overlap.
  # Deliberately keep Dresden's existing official county geometry until a
  # matching high-resolution boundary dataset is confirmed.
}
TO_METRIC=Transformer.from_crs("EPSG:4326","EPSG:3035",always_xy=True).transform
TO_WGS84=Transformer.from_crs("EPSG:3035","EPSG:4326",always_xy=True).transform


def parts(geometry):
    if geometry.is_empty:return []
    if geometry.geom_type=="Polygon":return [geometry]
    if geometry.geom_type=="MultiPolygon":return list(geometry.geoms)
    if hasattr(geometry,"geoms"):
        return [p for child in geometry.geoms for p in parts(child)]
    return []


def polygons_only(geometry):
    polygons=[p for p in parts(geometry) if p.area>.01]
    if not polygons: return Polygon()
    if len(polygons)==1:return polygons[0]
    return MultiPolygon(polygons)


def valid(geometry):
    return geometry if geometry.is_valid else geometry.buffer(0)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def area_km(geometry):
    return round(geometry.area/1e6,4)


def main():
    src=load(COUNTY_FILE)
    features=src["features"]
    by_id={str(f.get("id")):i for i,f in enumerate(features)}
    county=[valid(transform(TO_METRIC,shape(f["geometry"]))) for f in features]
    changed=set()
    stats=[]
    baseline_area=sum(g.area for g in county)

    for ags,local_path in CITY_SOURCES.items():
        if ags not in by_id:raise RuntimeError("Missing urban Kreis AGS "+ags)
        index=by_id[ags]
        coarse=county[index]
        local=load(ROOT/local_path)
        fine=valid(unary_union([
            valid(transform(TO_METRIC,shape(f["geometry"])))
            for f in local["features"]
        ]))

        inside=coarse.intersection(fine).area
        coverage=inside/max(coarse.area,fine.area)
        if coverage<.92:
            raise RuntimeError(f"Unsafe boundary replacement {ags}: coverage {coverage:.3%}")

        missing=polygons_only(coarse.difference(fine))
        extra=polygons_only(fine.difference(coarse))
        removed_area=area_km(missing)
        added_area=area_km(extra)

        # The new municipal outer ring is authoritative for the display layer.
        county[index]=fine
        changed.add(index)

        # Where the old nationwide Kreis protruded beyond the authoritative
        # municipal boundary, transfer its former area to the adjacent county.
        # This prevents hairline gaps or unfilled "teeth" without changing city
        # district polygons.
        assigned=defaultdict(list)
        unassigned=[]
        for gap in parts(missing):
            if gap.area<.01:continue
            candidates=[]
            for k,geom in enumerate(county):
                if k==index or not geom.bounds:continue
                if (geom.bounds[0]>gap.bounds[2]+2000 or
                    geom.bounds[2]<gap.bounds[0]-2000 or
                    geom.bounds[1]>gap.bounds[3]+2000 or
                    geom.bounds[3]<gap.bounds[1]-2000):continue
                distance=geom.distance(gap)
                if distance>2000:continue
                # Prefer an existing common border. The 15m tolerance compensates
                # for already known coarse geo-boundary simplification.
                touch=gap.boundary.intersection(geom.buffer(15)).length
                candidates.append((touch,distance,k))
            if not candidates:
                unassigned.append(gap)
                continue
            candidates.sort(key=lambda x:(-x[0],x[1],x[2]))
            touch,distance,winner=candidates[0]
            # True holes inside the city are not municipalities. Do not
            # arbitrarily assign inland enclaves to distant neighbours.
            if touch<1 and distance>100:
                unassigned.append(gap)
                continue
            assigned[winner].append(gap)

        # Preserve genuine internal holes as part of the urban municipality,
        # because no district geometry is present in such exceptional spaces.
        if unassigned:
            county[index]=polygons_only(valid(unary_union([county[index],*unassigned])))
            changed.add(index)

        for k,gaps in assigned.items():
            county[k]=polygons_only(valid(unary_union([county[k],*gaps])))
            changed.add(k)

        # Clip surrounding counties anywhere the higher-resolution city extends
        # beyond its former coarse border; no overlapping fill is allowed.
        for k,geom in enumerate(county):
            if k==index:continue
            if not geom.intersects(fine):continue
            overlap=geom.intersection(fine)
            if overlap.area>0.01:
                county[k]=polygons_only(valid(geom.difference(fine)))
                changed.add(k)

        # Make sure no other county paints above/under the same city pixels.
        overlap_m2=sum(county[k].intersection(fine).area
                       for k in range(len(county)) if k!=index and county[k].intersects(fine))
        if overlap_m2>10:
            raise RuntimeError(f"{ags}: residual overlap {overlap_m2:.2f} m2")

        stat={
            "ags":ags,
            "detail_source":local_path,
            "coarse_area_km2":area_km(coarse),
            "fine_area_km2":area_km(fine),
            "old_county_outside_detail_km2":removed_area,
            "detail_outside_old_county_km2":added_area,
            "fragments_to_neighbours":sum(map(len,assigned.values())),
            "unassigned_fragments":len(unassigned),
            "overlap_m2_after":round(overlap_m2,2),
        }
        stats.append(stat)
        print("[county-stitch]",json.dumps(stat,ensure_ascii=False),flush=True)

    result_features=[]
    for i,feature in enumerate(features):
        result=dict(feature)
        if i in changed:
            result["geometry"]=mapping(polygons_only(county[i]))
            # Round when serializing via JSON; Shapely returns tuples which are
            # valid JSON arrays once dumped.
        result_features.append(result)

    output={"type":"FeatureCollection",
            "meta":{
                "purpose":"display-only boundary harmonisation",
                "official_source_geometry":"data/germany-counties.geojson",
                "detail_sources":CITY_SOURCES,
                "policy":"preserve fine city geometry; reassign coarse county fringe to adjoining counties; raw boundaries and crime statistics unchanged",
                "city_seams":stats
            },
            "features":result_features}
    # Geographic conversion is required for all changed metric geometries.
    for i in changed:
        g=valid(transform(TO_WGS84,county[i]))
        output["features"][i]["geometry"]=mapping(polygons_only(g))

    changed_file=write_geojson(OUT,output)
    if len(result_features)!=len(features):
        raise RuntimeError("County count changed unexpectedly")
    print("[county-stitch] output=",OUT.name,
          "county_count=",len(features),"changed_count=",len(changed),
          "changed_file=",changed_file,
          "base_area_sqkm=",round(baseline_area/1e6,2),flush=True)


if __name__=="__main__":
    main()
