#!/usr/bin/env python3
"""Candidate-only Bremen 2025 PKS reporting-area polygons, official WFS GML.

Uses the 22 audited reporting-unit names, never publishes counts, and never
alters the public city registry or the raw Germany county layer.
"""
from __future__ import annotations

import argparse
import io
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from pypdf import PdfReader
from shapely.geometry import Polygon, MultiPolygon, mapping
from shapely.ops import transform, unary_union
from pyproj import Transformer

from audit_bremen_district_joins import PKS, WFS, police_titles, joining, normal
from city_build_common import download_bytes, write_geojson

GML = "{http://www.opengis.net/gml/3.2}"
WFS_NS = "{http://www.opengis.net/wfs/2.0}"
TO_METRIC = Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True).transform


def ring(pos):
    if pos is None or not pos.text:
        raise ValueError("Missing GML ring posList; do not publish incomplete polygon")
    nums = [float(x) for x in pos.text.split()]
    if len(nums) < 8 or len(nums) % 2:
        raise ValueError("GML 2D coordinate count is invalid")
    # The verified Bremen EPSG:4326 GML service returns longitude then latitude.
    coords = [(nums[i], nums[i + 1]) for i in range(0, len(nums), 2)]
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    if any(not (8.3 < x < 9.3 and 52.9 < y < 53.3) for x, y in coords):
        raise ValueError("Bremen coordinates have unexpected axis order / bounds")
    return coords


def parse_polygon(poly):
    outer = poly.find("./" + GML + "exterior/" + GML + "LinearRing/" + GML + "posList")
    holes = poly.findall("./" + GML + "interior/" + GML + "LinearRing/" + GML + "posList")
    geom = Polygon(ring(outer), [ring(p) for p in holes])
    if not geom.is_valid or geom.area <= 0:
        raise ValueError("Invalid native GML polygon; geometry must remain authoritative")
    return geom


def fetch_units(kind):
    urltype = "Stadtteile_Bremen" if kind == "stadtteil" else "Ortsteile_Bremen"
    raw = download_bytes(WFS, {
        "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
        "TYPENAMES": "app:" + urltype, "SRSNAME": "EPSG:4326"
    }, timeout=70)
    root = ET.fromstring(raw)
    namestr, codestr = ("bez_st", "sch_st") if kind == "stadtteil" else ("bez_ot", "sch_ot")
    units = {}
    for member in root.findall(".//" + WFS_NS + "member"):
        feature = next(iter(member), None)
        if feature is None:
            continue
        props = {x.tag.split("}")[-1]: (x.text or "").strip()
                 for x in feature if x.tag.split("}")[-1] != "geom"}
        name, code = props.get(namestr), props.get(codestr)
        if not name or not code or normal(name) in units:
            raise ValueError(f"Duplicate/missing official Bremen {kind} ID: {name}/{code}")
        polygons = [parse_polygon(poly) for poly in feature.findall(".//" + GML + "Polygon")]
        if not polygons:
            raise ValueError(f"{kind} {name}: GML contains no supported polygons")
        union = unary_union(polygons)
        if union.geom_type not in ("Polygon", "MultiPolygon") or not union.is_valid:
            raise ValueError(f"{kind} {name}: polygon union invalid")
        units[normal(name)] = {
            "kind": kind, "name": name, "code": code,
            "parent_stadtteil": props.get("bez_st", ""),
            "geom": union
        }
    expected = 19 if kind == "stadtteil" else 87
    if len(units) != expected:
        raise ValueError(f"Expected {expected} official {kind} regions, got {len(units)}")
    return units


def km2(geo):
    return round(transform(TO_METRIC, geo).area / 1e6, 3)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/bremen_areas_staging.geojson")
    args = parser.parse_args()
    path = Path(args.output)
    if "data/" in path.as_posix() or "city_layers" in path.as_posix():
        raise ValueError("Candidate GeoJSON cannot overwrite public runtime data")
    titles = police_titles(download_bytes(PKS, timeout=75))
    districts = fetch_units("stadtteil")
    neighbourhoods = fetch_units("ortsteil")
    rows, errors, left = joining(titles, districts, neighbourhoods)
    if errors or len(rows) != 22 or any(r["status"] != "matched" for r in rows):
        raise ValueError(f"Bremen 22-area join failed: {errors}")
    shapes, results = [], []
    for row in rows:
        parts = []
        for unit in row["geometry_units"]:
            source = districts if unit["kind"] == "stadtteil" else neighbourhoods
            item = source[normal(unit["name"])]
            if item["code"] != unit["code"]:
                raise ValueError("Bremen administrative region code changed unexpectedly")
            parts.append(item["geom"])
        geom = unary_union(parts)
        if geom.is_empty or not geom.is_valid or geom.geom_type not in ("Polygon", "MultiPolygon"):
            raise ValueError(f"PKS reporting-area polygon invalid {row['police_table']}")
        results.append({
            "type": "Feature",
            "id": f"bremen-pks-{row['police_table']:02d}",
            "properties": {
                "city": "Bremen", "year": 2025,
                "police_table": row["police_table"],
                "name": row["police_area"],
                "source_regions": [
                    {"kind": u["kind"], "name": u["name"], "code": u["code"]}
                    for u in row["geometry_units"]
                ],
                "area_km2": km2(geom),
                "offense_cases": None,
                "population": None,
                "crime_rate": None
            },
            "geometry": mapping(geom)
        })
        shapes.append(geom)
    # Metric spatial comparisons: never mistake a different cartographic
    # scale for missing crimes. All area tests use a common EPSG:3035 CRS.
    projected = [transform(TO_METRIC, g) for g in shapes]
    pair_overlap = []
    for i in range(len(projected)):
        for j in range(i):
            if projected[i].intersects(projected[j]):
                a = projected[i].intersection(projected[j]).area
                if a > 1:
                    pair_overlap.append((i+1, j+1, round(a, 2)))
    # Stadtteile omit the standalone rural Ortsteile (Blockland, Borgfeld,
    # Seehausen, Strom); they are NOT an exhaustive city boundary.
    # The official 87 Ortsteile are the complete municipality partition.
    city_from_admin = unary_union([v["geom"] for v in neighbourhoods.values()])
    drawn = unary_union(shapes)
    official_m = transform(TO_METRIC, city_from_admin)
    drawn_m = transform(TO_METRIC, drawn)
    gap = official_m.difference(drawn_m).area
    extra = drawn_m.difference(official_m).area
    overlap_m2 = sum(projected[i].intersection(projected[j]).area
                     for i in range(len(projected)) for j in range(i))
    audit = {
        "status": "candidate_geometry_only",
        "reporting_areas": len(shapes),
        "official_stadtteile": len(districts),
        "official_ortsteile": len(neighbourhoods),
        "baseline": "union of all 87 official Bremen Ortsteile (not just 19 Stadtteile)",
        "official_area_km2": km2(city_from_admin),
        "mapped_area_km2": km2(drawn),
        "uncovered_km2": round(gap / 1e6, 4),
        "outside_official_km2": round(extra / 1e6, 4),
        "internal_overlap_m2": round(overlap_m2, 2),
        "significant_overlap_pairs": pair_overlap[:20],
        "unmapped_aggregate_stadtteil": left,
    }
    print("[bremen-geometry] audit", json.dumps(audit, ensure_ascii=False), flush=True)
    # A sub-kilometre gap can be a geometric precision issue. A larger
    # gap or an administrative overlap is not acceptable for publication.
    if not (300 < km2(city_from_admin) < 390):
        raise ValueError("Bremen official area implausible / CRS wrong")
    if gap > 0.005 * official_m.area or extra > 0.005 * official_m.area:
        raise ValueError("Bremen candidate geometry does not cover official city")
    if overlap_m2 > 100:
        raise ValueError(f"Bremen police areas overlap significantly: {pair_overlap}")
    doc = {
        "type": "FeatureCollection",
        "meta": {
            **audit,
            "source": WFS,
            "source_police_area_titles": PKS,
            "source_licensing": "GeoInformation Bremen source; further reuse review before publication",
            "disclaimer": "Unpublished candidate geometry, no offense counts or rates."
        },
        "features": results
    }
    write_geojson(path, doc)
    print("[bremen-geometry] PASS: official GML geometry joined into 22 non-overlapping candidate regions", flush=True)


if __name__ == "__main__":
    main()
