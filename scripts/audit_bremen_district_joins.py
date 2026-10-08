#!/usr/bin/env python3
"""Read-only, source-audited Bremen 2025 PKS-area → municipal geometry crosswalk.

Only checks reporting-unit names and official feature IDs. It does NOT
generate public polygons, distribute crimes or assume population denominators.
"""
from __future__ import annotations

import io
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from pypdf import PdfReader
from city_build_common import download_bytes

PKS = "https://www.bremische-buergerschaft.de/dokumente/wp21/land/drucksache/D21L1866.pdf"
WFS = "https://geodienste.bremen.de/wfs_verwaltungsgrenzen"
OUT = Path("artifacts/bremen_join_audit.json")
TYPES = ("Stadtteile_Bremen", "Ortsteile_Bremen")


def normal(name):
    v = unicodedata.normalize("NFKC", name).casefold().replace("ß", "ss")
    return re.sub(r"[\W_]+", "", v, flags=re.UNICODE)


def police_titles(pdf):
    pdf_text = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages)
    matches = re.findall(
        r"Tabelle\s+(\d+):\s+PKS-Fallzahlen im\s+"
        r"(.+?)\s+von\s+2024\s+bis\s+2025",
        pdf_text, flags=re.I | re.S
    )
    titles = {int(n): re.sub(r"\s+", " ", label).strip() for n, label in matches}
    if sorted(titles) != list(range(1, 23)):
        raise RuntimeError(f"Police report must have exactly tables 1–22, got {sorted(titles)}")
    return titles


def municipal_units(feature_type):
    raw = download_bytes(
        WFS, {"SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
              "TYPENAMES": "app:" + feature_type, "SRSNAME": "EPSG:4326"},
        timeout=70
    )
    root = ET.fromstring(raw)
    units = {}
    unit_kind = "ortsteil" if feature_type.startswith("Ortsteile") else "stadtteil"
    name_field = "bez_ot" if unit_kind == "ortsteil" else "bez_st"
    id_field = "sch_ot" if unit_kind == "ortsteil" else "sch_st"
    for member in root.findall(".//{http://www.opengis.net/wfs/2.0}member"):
        feature = next(iter(member), None)
        if feature is None:
            continue
        props = {e.tag.split("}")[-1]: (e.text or "").strip()
                 for e in feature if e.tag.split("}")[-1] != "geom"}
        name = props.get(name_field, "")
        code = props.get(id_field, "")
        if not name or not code or normal(name) in units:
            raise RuntimeError(f"Malformed/duplicate official {unit_kind}: {name!r} / {code!r}")
        units[normal(name)] = {"kind": unit_kind, "name": name, "code": code}
    expected = 87 if unit_kind == "ortsteil" else 19
    if len(units) != expected:
        raise RuntimeError(f"Expected {expected} {feature_type}, got {len(units)}")
    return units


def joining(titles, districts, neighbourhoods):
    records = []
    problems = []
    for number, label in sorted(titles.items()):
        label_norm = normal(label)
        # The police deliberately groups these areas in Tables 6 and 22.
        # No numerical split between component polygons is implied.
        if number == 6:
            target = [("stadtteil", "Gröpelingen"), ("ortsteil", "Industriehäfen")]
        elif number == 22:
            target = [("stadtteil", "Woltmershausen"), ("ortsteil", "Neustädter Hafen")]
        elif label_norm.startswith("stadtteil"):
            target = [("stadtteil", re.sub(r"^Stadtteil\s+", "", label, flags=re.I))]
        elif label_norm.startswith("ortsteil"):
            target = [("ortsteil", re.sub(r"^Ortsteil\s+", "", label, flags=re.I))]
        else:
            target = []
            problems.append({"table": number, "reason": "unrecognised police geographic unit", "label": label})
        joined = []
        for kind, name in target:
            lookup = districts if kind == "stadtteil" else neighbourhoods
            geo = lookup.get(normal(name))
            if geo is None:
                problems.append({"table": number, "reason": "official feature not found", "expected": f"{kind} {name}"})
            else:
                joined.append(geo)
        records.append({
            "police_table": number,
            "police_area": label,
            "geometry_units": joined,
            "status": "matched" if len(joined) == len(target) and target else "unmatched"
        })
    if len({(x["kind"], x["code"]) for r in records for x in r["geometry_units"]}) != sum(len(r["geometry_units"]) for r in records):
        problems.append({"reason": "same official polygon reused in two police statistical areas"})
    uncovered_districts = [v["name"] for k, v in districts.items()
                           if not any(v["code"] == x["code"] for r in records for x in r["geometry_units"])]
    return records, problems, uncovered_districts


def main():
    titles = police_titles(download_bytes(PKS, timeout=75))
    districts = municipal_units(TYPES[0])
    neighbourhoods = municipal_units(TYPES[1])
    rows, problems, uncovered = joining(titles, districts, neighbourhoods)
    result = {
        "status": "candidate_geometry_name_join_only",
        "source": {"police": PKS, "geometry": WFS},
        "police_tables": len(rows),
        "matched_tables": sum(r["status"] == "matched" for r in rows),
        "official_stadtteile": len(districts),
        "official_ortsteile": len(neighbourhoods),
        "unmapped_stadtteile": uncovered,
        "problems": problems,
        "reporting_units": rows,
        "warnings": [
            "Name join is not a polygon topology or full-coverage validation.",
            "Häfen or other official geographic areas without reported police counts remain unclassified.",
            "No PKS offense count has been assigned to a polygon and no city layer is published."
        ]
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("[bremen-join] summary", json.dumps(
        {k: result[k] for k in ("police_tables","matched_tables","official_stadtteile",
        "official_ortsteile","unmapped_stadtteile","problems")}, ensure_ascii=False), flush=True)
    print("[bremen-join] area crosswalk", json.dumps(
        [{"table": r["police_table"], "area": r["police_area"],
          "matched": [u["name"] for u in r["geometry_units"]]} for r in rows],
        ensure_ascii=False), flush=True)
    if problems or len(rows) != 22 or result["matched_tables"] != 22:
        raise SystemExit("Bremen join NOT accepted; inspect downloadable diagnostic artifact")
    print("[bremen-join] PASS: 22 police reporting names matched to official geographic units", flush=True)


if __name__ == "__main__":
    main()
