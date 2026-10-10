#!/usr/bin/env python3
"""Fetch Germany Regionalatlas county indicators (research-only candidate layer).

Based on bundesAPI/regionalatlas-api public ArcGIS REST documentation.
This tool does not modify the displayed manufacturing employment choropleth.
The GIS API availability and field names can vary. Treat a response as a
candidate; always inspect source fields and compare with official metadata.

Usage:
    python scripts/try_regionalatlas_county.py --year 2024 --table ai007_1_5 --execute
    python scripts/try_regionalatlas_county.py --year 2019 --table ai004_3 --execute
Without --execute only prints the documented request URL for inspection.
"""
from __future__ import annotations
import argparse
import json
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = ("https://www.gis-idmz.nrw.de/arcgis/rest/services/"
        "stba/regionalatlas/MapServer/dynamicLayer/query")
# Only known indicator table-name candidates from regionalatlas-api docs;
# future readers must check taskrunner/services.json for current data source.
TABLE_CHOICES = ("ai007_1_5", "ai004_3", "ai010_1", "ai010_2_5")

def query_url(year: int, table: str) -> str:
    sql = (
        "SELECT * FROM verwaltungsgrenzen_gesamt "
        f"LEFT OUTER JOIN {table} ON ags = ags2 and jahr = jahr2 "
        f"WHERE typ = 3 AND jahr = {year} "
        f"AND (jahr2 = {year} OR jahr2 IS NULL)"
    )
    layer = {
        "source": {
            "dataSource": {
                "geometryType": "esriGeometryPolygon",
                "workspaceId": "gdb",
                "query": sql,
                "oidFields": "id",
                "spatialReference": {"wkid": 25832},
                "type": "queryTable",
            },
            "type": "dataLayer",
        }
    }
    params = {
        "layer": json.dumps(layer, separators=(",", ":")),
        "f": "json",
        "outFields": "*",
        "returnGeometry": "false",
        "spatialRel": "esriSpatialRelIntersects",
        "where": "1=1",
    }
    return BASE + "?" + urllib.parse.urlencode(params)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--year", type=int, required=True)
    p.add_argument("--table", choices=TABLE_CHOICES, required=True)
    p.add_argument("--execute", action="store_true", help="actually request the ArcGIS service")
    p.add_argument("--out", default=None, help="candidate output JSON file")
    args = p.parse_args()
    if not (2010 <= args.year <= 2026):
        p.error("year outside supported research interval")
    url = query_url(args.year, args.table)
    if not args.execute:
        print(url)
        print("DRY RUN ONLY: no county data have been obtained.")
        return 0
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "German-Map/industry-research"})
        with urllib.request.urlopen(req, timeout=50) as resp:
            payload = json.load(resp)
    except (OSError, ValueError, urllib.error.URLError) as exc:
        print("DOWNLOAD FAILED: " + str(exc), file=sys.stderr)
        return 2
    if payload.get("error"):
        print("ArcGIS response error: " + json.dumps(payload["error"], ensure_ascii=False), file=sys.stderr)
        return 3
    features = payload.get("features")
    if not isinstance(features, list) or not features:
        print("EMPTY or unsupported ArcGIS response; refusing to treat it as zero districts.", file=sys.stderr)
        return 4
    ids = set()
    for feat in features:
        attrs = feat.get("attributes") or {}
        ags = str(attrs.get("ags") or attrs.get("AGS") or "")
        if ags:
            ids.add(ags)
    checks = {
        "year": args.year, "table": args.table,
        "returned_features": len(features), "distinct_reported_ags": len(ids),
        "exceeded_transfer_limit": bool(payload.get("exceededTransferLimit")),
        "first_attribute_fields": sorted((features[0].get("attributes") or {}).keys()),
        "warning": "Unverified candidate only; may be truncated, missing historical districts, or wrong indicator.",
        "source": url,
    }
    print(json.dumps(checks, indent=2, ensure_ascii=False))
    if checks["exceeded_transfer_limit"] or len(features) < 350:
        print("COVERAGE ALERT: this result is not nationally complete; do not publish.", file=sys.stderr)
    path = pathlib.Path(args.out or f"regionalatlas_{args.table}_{args.year}_candidate.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"audit": checks, "raw_response": payload}, ensure_ascii=False), encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
