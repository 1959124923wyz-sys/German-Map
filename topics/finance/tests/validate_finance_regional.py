#!/usr/bin/env python3
"""Finance 08 R24 publication gate: separate county/independent-city debt years."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "research/finance/published_20261010"
JS = ROOT / "topics/finance/data/finance-regional-evidence.js"
HTML = ROOT / "topics/finance/index.html"
APP = ROOT / "topics/finance/topic.js"

def read(name):
    with (SRC / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))

def main():
    raw_county = read("county_core_budget_debt_2023_active.csv")
    raw_city = read("independent_cities_official_2024.csv")
    assert len(raw_county) == 398 and len(raw_city) == 102
    assert len({r["ags5"] for r in raw_county}) == 398
    assert len({r["ags5"] for r in raw_city}) == 102
    assert sum(r["per_capita_value_status"] == "published_numeric" for r in raw_county) == 392
    assert sum(r["per_capita_value_status"] == "no_published_numeric" for r in raw_county) == 6
    assert all(r["source_id"] == "REGIONALSTATISTIK_71327-01-05-4_2023" for r in raw_county)
    assert all(r["source_integrated_id"] == "STATISTIKPORTAL_INTEGRATED_2024_T1" for r in raw_city)
    original = JS.read_bytes()
    subprocess.run([sys.executable, str(ROOT / "topics/finance/data/build_finance_regional.py")],check=True)
    assert JS.read_bytes() == original, "regional output must be reproducible from archived official CSV"
    prefix = "window.GermanFinance08Regional="
    body = original.decode("utf-8")
    assert body.startswith(prefix)
    data = json.loads(body[len(prefix):].rstrip(";\n"))
    assert data["meta"]["county_year"] == 2023 and data["meta"]["city_year"] == 2024
    assert len(data["counties"]) == 398 and len(data["cities"]) == 102
    assert sum(r["value"] is not None for r in data["counties"]) == 392
    assert {r["id"] for r in data["cities"]}.issubset({r["id"] for r in data["counties"]})
    assert all(r["integrated2024"] >= 0 for r in data["cities"])
    page = HTML.read_text(encoding="utf-8")
    app = APP.read_text(encoding="utf-8")
    assert 'id="regionalDebtDrawer"' in page and 'finance-regional-evidence.js' in page
    assert 'id="showEvents" type="checkbox"' in page and 'showEvents:false' in app
    assert "renderRegionalDebt(feature.id)" in app
    assert "getMode:()=>view.metric" in app
    assert "2023年县域" in app and "2024年非县辖市" in app
    assert "2025年" in page and "不作为2025年" in page
    print("PASS R24: 398 county rows (392 numeric, 6 missing), 102 independent cities; reproducible and detail-only")

if __name__ == "__main__":
    main()
