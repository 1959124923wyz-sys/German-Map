#!/usr/bin/env python3
"""Build or validate Finance 08 per-state 2024 municipality evidence.

The 2024 integrated-debt source distinguishes 10,750 municipalities from
830 joint-administrations and 294 county administrations. This builder
intentionally does not aggregate across legal reporting entities.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ARCHIVE = ROOT / "research/finance/published_20261010"
OUT = ROOT / "topics/finance/data/municipal-2024"
STATES = "01 03 05 06 07 08 09 10 12 13 14 15 16".split()

def records(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))

def num(value):
    if value == "" or value is None:
        return None
    v = float(value)
    assert abs(v) < 1e15
    return int(v) if v.is_integer() else v

def build(st):
    debt = records(ARCHIVE / "municipal_debt_2024_by_state" / ("DE-" + st + ".csv"))
    taxes = records(ARCHIVE / "municipal_tax_2024_by_state" / ("DE-" + st + ".csv"))
    tax_index = {r["ags8"]: r for r in taxes}
    assert len(tax_index) == len(taxes)
    out = []
    for row in debt:
        assert row["report_year"] == "2024"
        if row["reporting_unit_class"] != "municipality":
            assert row["reporting_unit_class"] in ("county_administration", "joint_administration")
            continue
        ags = row["municipality_ags8_candidate"]
        assert len(ags) == 8 and ags.isdigit() and ags.startswith(st)
        assert row["ags_match_2024_atlas"] == "matched"
        tax = tax_index[ags]
        assert tax["year"] == "2024"
        value = num(row["integrated_debt_eur_per_person"])
        assert value is not None and value >= 0
        tax_value = num(tax["tax_capacity_eur_per_capita"]) if tax["value_status"] == "published_numeric" else None
        if tax_value is not None:
            assert tax_value != -9999
        out.append([ags, row["name_de"], value, tax_value])
    out.sort(key=lambda row: row[0])
    assert len(set(row[0] for row in out)) == len(out)
    return {"year": 2024, "state": st, "count": len(out), "municipal": out}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true", help="Compare generated records to checked-in files")
    args = parser.parse_args()
    total = 0
    for st in STATES:
        target = OUT / ("DE-" + st + ".json")
        expected = build(st)
        total += expected["count"]
        if args.verify:
            assert json.loads(target.read_text(encoding="utf-8")) == expected, target
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(expected, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    assert total == 10750, total
    all_tax = []
    for st in ("02", "04", "11"):
        all_tax.extend(records(ARCHIVE / "municipal_tax_2024_by_state" / ("DE-" + st + ".csv")))
    assert len(all_tax) == 4, len(all_tax)
    print("PASS 2024 municipal debt: 10,750 municipalities in 13 states, 2024 tax-year matched, source types kept separate")

if __name__ == "__main__":
    main()
