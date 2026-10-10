#!/usr/bin/env python3
"""Download and QA official Deutschlandatlas HA26 Kreis-level housing indicators.

Run from repo root:
    python research/housing/build_deutschlandatlas.py

Sources: Federal Deutschlandatlas release 2026-10-08.
This source has different geographic vintages. Use exact 5-digit AGS for joins,
keep unmatched features as null, never extrapolate or name-match.
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "research/housing/data"
QA_DIR = ROOT / "research/housing/qa"
WEB_DIR = ROOT / "topics/housing/data"
BASE = "https://deutschlandatlas.bund.de/fileadmin/Downloaddateien/HA26/"
SOURCES = {
    "2024": BASE + "Deutschlandatlas_KRS1224_HA26.csv",
    "2022": BASE + "Deutschlandatlas_KRS1222_HA26.csv",
}
METRICS = {
    "asking_rent_2025_eur_m2": ("2024", "preis_miet", "2025", "EUR/m2", "Wiedervermietungsmieten, internet advertised, net cold"),
    "vacancy_2022_pct": ("2022", "wohn_leer", "2022", "pct", "Unoccupied dwellings including non-marketable stock, excludes leisure homes"),
    "owner_occupier_2022_pct": ("2022", "wohn_eigen", "2022", "pct", "Share of households in self-occupied property, not proportion of flats"),
    "living_area_2022_m2_person": ("2024", "fl_wohn", "2022", "m2/person", "Average living area per capita, microcensus estimate"),
    "renewable_heat_new_2024_pct": ("2024", "heiz_wohn", "2024", "pct", "New completed residential buildings only"),
    "renewable_heat_stock_2022_pct": ("2022", "heiz_wohn_best", "2022", "pct", "Heating in existing residential stock"),
}
STRICT = {"asking_rent_2025_eur_m2", "vacancy_2022_pct", "owner_occupier_2022_pct"}
HEADERS = {k: v[1] for k, v in METRICS.items()}

def fetch(url: str) -> bytes:
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "GermanMapHousingResearch/1.0 (public statistical research)",
                "Accept": "text/csv, text/plain, */*",
            })
            with urllib.request.urlopen(req, timeout=55) as response:
                content = response.read()
                print("FETCH", response.status, url, "bytes", len(content))
                if len(content) < 10_000:
                    raise ValueError("Official CSV unexpectedly small")
                return content
        except (OSError, ValueError) as exc:
            last = exc
            print("Fetch attempt failed:", type(exc).__name__, str(exc), file=sys.stderr)
            if attempt < 2:
                time.sleep(attempt * 3 + 2)
    raise RuntimeError(f"Could not download {url}: {last}")

def decode(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "iso-8859-1"):
        try:
            s = raw.decode(encoding)
        except UnicodeError:
            continue
        if "preis_miet" in s or "wohn_leer" in s:
            return s
    raise ValueError("No expected official indicator names in downloaded CSV")

def read_official(raw: bytes, vintage: str):
    text = decode(raw)
    rows = list(csv.reader(io.StringIO(text), delimiter=";"))
    header_i = next((i for i, row in enumerate(rows[:40]) if
                    any(c.strip().lower() in {"preis_miet", "wohn_leer"} for c in row)), -1)
    if header_i == -1:
        print("First lines for debugging:", [r[:9] for r in rows[:8]], file=sys.stderr)
        raise ValueError(f"No indicator header in {vintage} CSV")
    header = [c.strip().lower().lstrip("\ufeff") for c in rows[header_i]]
    print("CSV HEAD", vintage, "header line", header_i+1, "fields", len(header), header[:18])
    idx = {s: header.index(s) for s in set(header)}
    requested = {metric: code for metric, (v, code, *_rest) in METRICS.items() if v == vintage}
    missing = [k for k in requested.values() if k not in idx]
    if missing and any(metric in STRICT for metric, code in requested.items() if code in missing):
        raise ValueError(f"Critical indicator codes absent in {vintage}: {missing}")
    result = {}
    sample_bad = []
    for line, row in enumerate(rows[header_i+1:], start=header_i+2):
        if not row or len(row) < 2:
            continue
        fields = [x.strip() for x in row]
        # The first source field is the official territorial key; do not use
        # a loosely matched five-digit substring of a description.
        leading = fields[0].lstrip("\ufeff")
        m = re.fullmatch(r"(\d{5,8})(?:\s+(.+))?", leading)
        if not m:
            if len(sample_bad) < 5: sample_bad.append([line, row[:3]])
            continue
        ags = (m.group(1).zfill(8)[:5] if len(m.group(1)) > 5 else m.group(1))
        name = (fields[1] if len(fields) > 1 else "") or (m.group(2) or "")
        if ags in result:
            raise ValueError(f"Duplicated AGS {ags} in {vintage}, lines include {line}")
        d = {"id": ags, "name": name}
        for metric, source_code in requested.items():
            d[metric] = parse_value(row[idx[source_code]]) if source_code in idx and len(row)>idx[source_code] else None
        result[ags] = d
    print("PARSED", vintage, len(result), "rows; examples", list(result.items())[:2],
          "unparsed examples", sample_bad[:2])
    if len(result) < 380 or len(result) > 420:
        raise ValueError(f"Implausible district count {len(result)} from {vintage}")
    return result, {"header_line": header_i+1, "header": header, "rows": len(result), "unparsed_examples": sample_bad}

def parse_value(v: str):
    s = str(v).strip().replace("\u00a0", "").replace(" ", "")
    if s in {"", ".", "-", "–", "…", "x", "/", "NA", "N/A", "-9999", "-99999"}:
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        n = float(s)
    except ValueError:
        return None
    if not (-9999 < n < 1e9):
        return None
    return round(n, 5)

def get_map_ids():
    # Read only existing official/display geometry; do not modify geometry.
    path = ROOT / "data/germany-counties-display.geojson"
    map_geo = json.loads(path.read_text(encoding="utf-8"))
    ids = [str(f["id"]).zfill(5) for f in map_geo["features"]]
    if len(ids) != 402 or len(set(ids)) != 402:
        raise ValueError("Existing map has unexpected AGS id coverage")
    return ids

def output():
    current = {v: read_official(fetch(url), v) for v, url in SOURCES.items()}
    county_ids = get_map_ids()
    data = []
    for ags in sorted(set(current["2024"][0]) | set(current["2022"][0])):
        d = {"id": ags, "name": current["2024"][0].get(ags, current["2022"][0].get(ags))["name"]}
        for metric, (vintage, _code, *_rest) in METRICS.items():
            d[metric] = current[vintage][0].get(ags, {}).get(metric)
        data.append(d)
    byid = {r["id"]: r for r in data}
    county_joined = [byid.get(ags, {"id": ags, "name": "", **{m:None for m in METRICS}})
                     for ags in county_ids]
    availability = {metric: sum(r[metric] is not None for r in county_joined) for metric in METRICS}
    print("COVERAGE", availability)
    for key in STRICT:
        if availability[key] < 380:
            raise ValueError(f"Insufficient official data coverage for {key}: {availability[key]}/402")
    units = {metric: {"year": spec[2], "unit": spec[3], "meaning": spec[4],
            "territorial_vintage": spec[0], "raw_code": spec[1], "source_url": SOURCES[spec[0]]}
             for metric, spec in METRICS.items()}
    payload = {"meta": {"project":"German-Map housing crisis","release":"HA26",
            "source_published":"2026-10-08","publisher":"Deutschlandatlas / Destatis / BBSR",
            "source_landing":"https://deutschlandatlas.bund.de/service/daten-herunterladen/aktuelle-downloaddaten/aktuelle-downloaddateien",
            "data_kind":"separate housing indicators; NOT a synthetic crisis ranking",
            "metric_definitions":units, "coverage_on_existing_402_map":availability},
            "counties":county_joined}
    diff = {}
    for v in ("2024","2022"):
        a = set(current[v][0])
        b = set(county_ids)
        diff[v] = {"not_in_project_map":sorted(a-b),"not_in_atlas":sorted(b-a),
                   "raw_count":len(a),"map_count":len(b)}
    QA_DIR.mkdir(parents=True,exist_ok=True)
    DATA_DIR.mkdir(parents=True,exist_ok=True)
    WEB_DIR.mkdir(parents=True,exist_ok=True)
    with (DATA_DIR/"deutschlandatlas_ha26_housing_counties.csv").open("w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f,fieldnames=["id","name",*METRICS])
        w.writeheader();w.writerows(data)
    (QA_DIR/"ha26_join_audit.json").write_text(json.dumps({
        "official_csv":SOURCES, "source_csv_headers":{k:v[1] for k,v in current.items()},
        "geo_crosswalk":diff,"coverage":availability,
        "notes":["No interpolation or name-based joins", "Different county boundary vintages",
                 "The project map contains 402 historical features; null means missing/unjoined, not zero"]
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (WEB_DIR/"atlas-counties.json").write_text(json.dumps(payload,ensure_ascii=False,
                                                   separators=(",",":"))+"\n", encoding="utf-8")
    print("SUCCESS", len(data), "official district rows ->",len(county_joined),"map features")
    print("OUTPUT", str(WEB_DIR/"atlas-counties.json"))
    print("JOIN mismatches:",diff)

if __name__ == "__main__":
    output()
