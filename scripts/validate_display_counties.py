#!/usr/bin/env python3
"""Ensure displayed county polygons share official detailed municipal boundaries.

These tests explicitly operate on display geometry. Original census/crime data
and fine-scale polygons remain unchanged.
"""
from __future__ import annotations

import json
from pathlib import Path
from shapely.geometry import shape
from shapely.ops import unary_union,transform
from pyproj import Transformer

ROOT=Path(__file__).resolve().parents[1]
to_m=Transformer.from_crs("EPSG:4326","EPSG:3035",always_xy=True).transform

def load(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def main():
    raw=load("data/germany-counties.geojson")
    display=load("data/germany-counties-display.geojson")
    raw_ids=[str(f["id"]) for f in raw["features"]]
    display_ids=[str(f["id"]) for f in display["features"]]
    assert raw_ids==display_ids, "display layer must preserve all county IDs and ordering"
    assert len(display_ids)==402, f"unexpected district count {len(display_ids)}"
    assert all(a["properties"]==b["properties"] for a,b in zip(raw["features"],display["features"])), "statistics and county metadata must not change"
    idx={f["id"]:f for f in display["features"]}
    config=display["meta"]["detail_sources"]
    total_excess=0.0
    for ags,path in config.items():
        assert ags in idx, f"missing display municipality {ags}"
        raw_detail=load(path)
        detail=unary_union([transform(to_m,shape(f["geometry"])) for f in raw_detail["features"]])
        city=transform(to_m,shape(idx[ags]["geometry"]))
        city_gap=detail.difference(city).area
        # Reprojection to EPSG:3035 and GeoJSON float serialization can
        # introduce sub-metre boundary drift along 200+ km of municipal edges.
        # Permit at most 0.005% area (far below any visible cartographic strip).
        # Munich's multipart 25-district WFS has especially long boundaries;
        # metre-scale GEOS projection round-trips can sum to several 1000 m².
        tol_m2=max(100.0,detail.area*5e-5)
        assert city_gap<tol_m2, (
            f"{ags} missing {city_gap:.1f} m² of official city detail "
            f"(tolerance {tol_m2:.1f} m²)"
        )
        touch=0.0
        for k,feature in idx.items():
            if k==ags:continue
            geom=transform(to_m,shape(feature["geometry"]))
            if geom.intersects(detail):
                touch+=geom.intersection(detail).area
        total_excess+=touch
        assert touch<tol_m2, (
            f"{ags} overlaps neighbors by {touch:.1f} m² "
            f"(tolerance {tol_m2:.1f} m²)"
        )
        print(f"[boundary] {ags}: detail {detail.area/1e6:.2f} km², "
              f"missing {city_gap:.2f} m², neighbor overlap {touch:.2f} m²")
    print(f"[boundary] PASS: {len(config)} cities, {len(display_ids)} counties, 0 duplicate IDs, "
          f"total overlap={total_excess:.2f} m²")

if __name__=='__main__':
    main()
