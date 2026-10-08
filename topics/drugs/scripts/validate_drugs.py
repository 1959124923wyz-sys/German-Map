#!/usr/bin/env python3
"""Reject incomplete or invented county figures before preview/publishing."""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "topics/drugs/data/pks_drugs_2025.json"
GEO = ROOT / "data/germany-counties.geojson"

def validate():
    obj = json.loads(DATA.read_text(encoding="utf-8"))
    meta, rows = obj["meta"], obj["records"]
    assert meta["year"] == 2025
    assert meta["metric"] == "Rauschgiftdelikte"
    assert len(rows) >= 390, f"Missing county records: {len(rows)}"
    assert len(rows) == meta["county_count"]
    assert len({r["state"] for r in rows.values()}) == 16
    assert len(obj["errors"]) <= 12
    for ags, rec in rows.items():
        assert len(ags) == 5 and ags.isdigit()
        assert rec["ags"] == ags and rec["name"] and rec["state"]
        assert rec["source_url"].startswith("https://kriminalitaets-karte.de/kriminalitaet/")
        datum = rec["drug_crime"]
        assert type(datum["cases"]) is int and datum["cases"] >= 0
        assert isinstance(datum["rate"], (float, int))
        assert math.isfinite(datum["rate"]) and 0 <= datum["rate"] <= 25000
        assert datum["cases"] == 0 or datum["rate"] > 0
    geo = json.loads(GEO.read_text(encoding="utf-8"))
    aliases = meta.get("geometry_aliases", {})
    ids = [str(f.get("id", f.get("properties", {}).get("AGS", ""))).zfill(5)
           for f in geo["features"]]
    matches = sum(ags in rows or aliases.get(ags) in rows for ags in ids)
    assert matches >= 390 and matches == meta["matched_geometry"]
    assert 390 <= len(ids) <= 410
    assert [r["ags"] for r in obj["top15"]] == [
        r["ags"] for r in sorted(rows.values(),
                                 key=lambda r: r["drug_crime"]["rate"],
                                 reverse=True)[:15]]
    # 164,991 is a separate national indicator, not an automatic checksum.
    assert meta["national_BKA_rauschgiftkriminalitaet_2025"] == 164991
    print(f"PASS 2025 drug data: {len(rows)} records, {matches}/{len(ids)} geometry matches, 16 states")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(validate())
    except (OSError, ValueError, AssertionError, KeyError, TypeError) as error:
        print(f"FAIL drug data: {error}", file=sys.stderr)
        sys.exit(1)
