#!/usr/bin/env python3
"""Download Dresden's official COMPLETE municipal boundary for display stitching.

The city publishes a KUEK5 cadastral overview (1:5,000), NodeId=111, L84.
This is deliberately NOT the union of 61 police-atlas Stadtteile: those cover
only part of Dresden. The boundary is display-only; no crime rate is imputed.
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform

from city_build_common import download_bytes, write_geojson

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/dresden-city-boundary.geojson"
WFS = "https://kommisdd.dresden.de/net3/public/ogc.ashx"
PARAMS = {
    "NODEID": "111",
    "SERVICE": "WFS",
    "VERSION": "2.0.0",
    "REQUEST": "GetFeature",
    "TYPENAMES": "cls:L84",
    "SRSNAME": "EPSG:4326",
}
NS = {"gml": "http://www.opengis.net/gml/3.2"}
TO_METRIC = Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True).transform


def read_ring(pos):
    if pos is None or not pos.text:
        raise ValueError("Dresden WFS polygon is missing its GML coordinates")
    vals = [float(value) for value in pos.text.split()]
    if len(vals) < 8 or len(vals) % 2:
        raise ValueError("Dresden WFS returned a malformed boundary ring")
    # For EPSG:4326 WFS 2.0 uses latitude/longitude, GeoJSON longitude/latitude.
    coords = [[round(vals[i + 1], 8), round(vals[i], 8)]
              for i in range(0, len(vals), 2)]
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    return coords


def extract_polygon(poly):
    exterior = poly.find("./gml:exterior/gml:LinearRing/gml:posList", NS)
    rings = [read_ring(exterior)]
    for pos in poly.findall("./gml:interior/gml:LinearRing/gml:posList", NS):
        rings.append(read_ring(pos))
    return rings


def main():
    raw = download_bytes(WFS, params=PARAMS, timeout=100)
    root = ET.fromstring(raw)
    polygons = [extract_polygon(poly) for poly in root.findall(".//gml:Polygon", NS)]
    if not polygons:
        raise RuntimeError("Dresden's official KUEK5 WFS has no polygon")
    geometry = (
        {"type": "Polygon", "coordinates": polygons[0]}
        if len(polygons) == 1
        else {"type": "MultiPolygon", "coordinates": polygons}
    )
    boundary = shape(geometry)
    if boundary.is_empty or not boundary.is_valid:
        raise RuntimeError("Dresden's official city boundary is invalid")
    area_sqkm = transform(TO_METRIC, boundary).area / 1e6
    west, south, east, north = boundary.bounds
    # Fail closed rather than publishing another CRS, region or partial city.
    if not (300 < area_sqkm < 360 and
            13.4 < west < 13.8 and 13.8 < east < 14.2 and
            50.8 < south < 51.2 and 51.0 < north < 51.3):
        raise RuntimeError(
            f"Dresden WFS unexpected extent/area: {boundary.bounds} "
            f"area={area_sqkm:.3f} km2"
        )
    output = {
        "type": "FeatureCollection",
        "meta": {
            "purpose": "display-only Dresden complete municipal boundary",
            "source": "Landeshauptstadt Dresden KUEK5 – Stadtgrenze",
            "source_url": WFS + "?NodeId=111&Service=WFS&Request=GetCapabilities",
            "layer": "cls:L84",
            "scale": "1:5000",
            "data_license": "Datenlizenz Deutschland – Namensnennung – Version 2.0",
            "district_detail_is_partial": True,
            "area_sqkm": round(area_sqkm, 3),
            "note": "Complete official municipal outline. The 61 Dresden Stadtteile are a partial crime-detail overlay only."
        },
        "features": [{
            "type": "Feature",
            "id": "14612",
            "properties": {"name": "Dresden", "AGS": "14612"},
            "geometry": geometry
        }]
    }
    changed = write_geojson(OUT, output)
    print("[dresden-city-boundary]", json.dumps({
        "area_sqkm": round(area_sqkm, 3),
        "polygon_count": len(polygons),
        "bounds": boundary.bounds,
        "changed": changed
    }), flush=True)


if __name__ == "__main__":
    main()
