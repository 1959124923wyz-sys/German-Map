#!/usr/bin/env python3
"""Extract both years of Bremen's 22 official PKS district tables (candidate only).

Extracting annual police case counts does not authorize a per-100k rate.
The report's legal metadata and geographic comparability must be reviewed
before public map publication.
"""
from __future__ import annotations
import argparse
import io
import json
import re
from pathlib import Path

from pypdf import PdfReader
from audit_bremen_district_joins import PKS, police_titles
from city_build_common import download_bytes, write_geojson

CODES = {
    "------": "all_offenses",
    "100000": "sexual",
    "210000": "robbery",
    "220000": "bodily_injury",
    "435*00": "burglary",
    "****00": "theft",
    "730000": "drug",
}
ROW_START = re.compile(r"(?m)^[ \t]*(------|100000|210000|220000|435\*00|\*{4}00|730000)[ \t]+")
# Official PDF prints: key label [2024] [2025] [+/- absolute change] [%].
NUMBER = r"(?:\d{1,3}(?:\.\d{3})+|\d+)"
TAIL = re.compile(rf"(?m)[ \t]+({NUMBER}|-)[ \t]+({NUMBER}|-)[ \t]+([+-]?{NUMBER}|-)[ \t]+([+-]?\d+(?:,\d+)?|-)[ \t]*(?:\n|$)")

def integer(value):
    return int(value.replace(".", ""))

def read_tables(pdf_bytes):
    reader = PdfReader(io.BytesIO(pdf_bytes))
    full = "\n".join(p.extract_text() or "" for p in reader.pages)
    titles = police_titles(pdf_bytes)
    markers = list(re.finditer(r"Tabelle\s+(\d+):\s+PKS-Fallzahlen im\s+", full))
    entries = []
    for i, m in enumerate(markers):
        table_no = int(m.group(1))
        if not (1 <= table_no <= 22):
            continue
        section = full[m.end(): markers[i+1].start() if i+1 < len(markers) else len(full)]
        rows = {}
        codes = list(ROW_START.finditer(section))
        for j, token in enumerate(codes):
            # Table 22 is followed by explanatory narrative citing crime
            # codes again. Consume exactly the first seven table rows.
            if len(rows)==len(CODES):
                break
            code = token.group(1)
            if code not in CODES:
                continue
            content = section[token.end():codes[j+1].start() if j+1<len(codes) else len(section)]
            # Match only the actual end-of-line four-column numeric record.
            # Do not mistake the hyphen in "-BtMG-" for a missing year.
            candidates=list(TAIL.finditer(content))
            found = candidates[-1] if candidates else None
            if found is None:
                raise RuntimeError(f"PKS Table {table_no} code {code}: cannot parse year counts: {content[:140]!r}")
            y24,y25,reported_change,reported_percent=found.groups()
            n24,n25=(integer(y24) if y24!='-' else None),(integer(y25) if y25!='-' else None)
            # All observed source rows give numerical annual values.
            if (n24 is not None and n24<0) or (n25 is not None and n25<0):
                raise RuntimeError("negative Bremen PKS cases")
            if reported_change!='-' and n24 is not None and n25 is not None and n25-n24!=int(reported_change.replace(".","")):
                raise RuntimeError(f"PKS Table {table_no}/{code}: year delta disagreement {n24} {n25} {reported_change}")
            if code in rows:
                raise RuntimeError(f"PKS Table {table_no}: duplicated code {code}")
            rows[code]={"2024":n24,"2025":n25}
        if set(rows)!=set(CODES):
            raise RuntimeError(f"PKS Table {table_no}: wanted 7 metrics, got {sorted(rows)}")
        if table_no not in titles:
            raise RuntimeError(f"PKS Table {table_no}: official area title absent")
        entries.append({"table":table_no,"label":titles[table_no],
                        "metrics":{CODES[c]:rows[c] for c in CODES}})
    if len(entries)!=22 or [r["table"] for r in entries]!=list(range(1,23)):
        raise RuntimeError(f"Police report expected exactly 22 ordered sections, got {[x['table'] for x in entries]}")
    # Conservative semantic constraints; burglary and robbery are not all-offense totals.
    for ent in entries:
        m=ent["metrics"]
        for year in ("2024","2025"):
            total=m["all_offenses"][year]
            if total is None or total<=0:raise RuntimeError("missing/zero Bremen district total")
            if any(m[k][year] is not None and m[k][year]>total for k in CODES.values()):
                raise RuntimeError(f"District {ent['table']} metric exceeds all recorded offenses")
            if m["burglary"][year] is not None and m["theft"][year] is not None and m["burglary"][year]>m["theft"][year]:
                raise RuntimeError(f"District {ent['table']} burglary exceeds all thefts")
    print("[bremen-cases] PASS",json.dumps({
        "districts":len(entries),"metric_categories":len(CODES),"years":[2024,2025],
        "category_totals":{k:{"2024":sum(e["metrics"][k]["2024"] or 0 for e in entries),
                             "2025":sum(e["metrics"][k]["2025"] or 0 for e in entries),
                             "missing_2024":sum(e["metrics"][k]["2024"] is None for e in entries),
                             "missing_2025":sum(e["metrics"][k]["2025"] is None for e in entries)}
                           for k in CODES.values()},
        "sample_area":entries[9]
    },ensure_ascii=False),flush=True)
    return entries


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",default="artifacts/bremen_cases_staging.json")
    args=ap.parse_args()
    target=Path(args.output)
    if "data/" in target.as_posix():
        raise ValueError("candidate-only CSV/PDF extraction cannot publish public data")
    entries=read_tables(download_bytes(PKS,timeout=80))
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps({"status":"candidate_counts_only",
        "source":PKS,"year":2025,"metric_definitions":{
        "all_offenses":"------ Straftaten insgesamt",
        "sexual":"100000 Straftaten gegen die sexuelle Selbstbestimmung",
        "robbery":"210000 Raub, räuberische Erpressung und räuberischer Angriff auf Kraftfahrer",
        "bodily_injury":"220000 Körperverletzung",
        "burglary":"435*00 Wohnungseinbruchdiebstahl",
        "theft":"****00 Diebstahl insgesamt",
        "drug":"730000 Rauschgiftdelikte (BtMG)"},
        "records":entries,"no_population_rates":True},ensure_ascii=False,indent=2)+"\n",
        encoding="utf-8")


if __name__=="__main__":main()
