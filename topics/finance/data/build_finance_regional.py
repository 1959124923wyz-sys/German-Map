#!/usr/bin/env python3
"""Deterministically publish two source-separated official fiscal datasets.

Inputs are exact CSV snapshots copied from research PR #36. Never merge
municipalities, independent cities, county governments or affiliated enterprises
as though they were one reporting entity.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "research/finance/published_20261010"
TARGET = Path(__file__).resolve().parent / "finance-regional-evidence.js"

def rows(name):
    with (SOURCE / name).open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))

def numeric(raw):
    if raw in ("", None):
        return None
    return float(raw) if "." in raw else int(raw)

def main():
    raw_counties = rows("county_core_budget_debt_2023_active.csv")
    raw_cities = rows("independent_cities_official_2024.csv")
    assert len(raw_counties) == 398 and len(raw_cities) == 102
    counties = []
    for row in raw_counties:
        code = row["ags5"]
        assert len(code) == 5 and code.isdigit()
        assert row["state_code"] == code[:2]
        assert row["report_date"] == "31.12.2023"
        assert row["scope_note"] == "core_budgets_only_not_integrated_public_enterprise_debt"
        status = row["per_capita_value_status"]
        assert status in ("published_numeric", "no_published_numeric")
        value = numeric(row["debt_per_capita_eur"])
        assert (value is not None) == (status == "published_numeric")
        counties.append({"id": code, "name": row["name_de"], "value": value})
    cities = []
    for row in raw_cities:
        code = row["ags5"]
        assert row["ags8"].startswith(code) and row["ags8"].endswith("000")
        assert row["state_code"] == code[:2]
        debt = numeric(row["integrated_debt_2024_eur_per_capita"])
        assert debt is not None and debt >= 0
        taxstatus = row["tax_capacity_2024_status"]
        cashstatus = row["cash_credits_2023_status"]
        assert taxstatus in ("published_numeric", "published_zero", "not_published", "missing", "published_negative", "no_published_numeric")
        assert cashstatus in ("published_numeric", "published_zero", "not_published", "missing", "no_published_numeric")
        cities.append({
            "id": code, "ags8": row["ags8"], "name": row["name_de"],
            "integrated2024": debt,
            "tax2024": numeric(row["tax_capacity_2024_eur_per_capita"]),
            "taxStatus": taxstatus,
            "cash2023": numeric(row["cash_credits_2023_eur_per_capita"]),
            "cashStatus": cashstatus
        })
    assert len({r["id"] for r in counties}) == 398
    assert sum(r["value"] is not None for r in counties) == 392
    assert len({r["id"] for r in cities}) == 102
    assert set(r["id"] for r in cities).issubset(set(r["id"] for r in counties))
    payload = {
        "meta": {
            "county_year": 2023,
            "city_year": 2024,
            "county_unit": "county_area_municipal_and_associations_core_budget",
            "city_unit": "independent_city_integrated_debt",
            "county_covered": 398,
            "county_numeric": 392,
            "cities": 102,
            "county_source": "https://www.regionalstatistik.de/genesisws/downloader/00/tables/71327-01-05-4_00.csv",
            "city_source": "https://www.statistikportal.de/sites/default/files/2025-12/Integrierte_Schulden_der_Gemeinden_und_Gemeindeverbaende_2024_Tabellenband_0.xlsx",
            "city_tax_source": "https://deutschlandatlas.bund.de/fileadmin/Downloaddateien/HA26/Deutschlandatlas_GEM1224_HA26.csv",
            "origin": "PR #36 research/finance-regional-expansion-20261010 R24",
            "quality_note": "different years and entities; no ratio between datasets, no county choropleth"
        },
        "counties": sorted(counties, key=lambda x: x["id"]),
        "cities": sorted(cities, key=lambda x: x["id"])
    }
    TARGET.write_text("window.GermanFinance08Regional="+
                      json.dumps(payload, ensure_ascii=False, separators=(",", ":"))+
                      ";\n", encoding="utf-8")
    print("PASS finance regional: 398 counties, 392 numeric; 102 cities")

if __name__ == "__main__":
    main()
