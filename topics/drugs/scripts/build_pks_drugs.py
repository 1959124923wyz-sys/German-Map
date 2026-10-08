#!/usr/bin/env python3
"""Reproducible 2025 county drug-offence baseline.

BKA Kreis T01 is the authoritative statistical source. The BKA download
endpoint sometimes blocks automation; this adapter extracts the
"Rauschgiftdelikte" field from a public BKA-attributed county mirror.
It NEVER replaces missing fields with zero, and preserves both source URLs.
The mirror's indicator is not silently equated to BKA's nationwide
"Rauschgiftkriminalitaet" summary (which has a distinct definition).
"""
from __future__ import annotations

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[3]
BASE = "https://kriminalitaets-karte.de/kriminalitaet/"
BKA = ("https://data.gov.de/suche/daten/"
       "2025-polizeiliche-kriminalstatistik-t01-grundtabelle-kreise-ausgewahlte-straftaten-gruppen")
OUTPUT = ROOT / "topics/drugs/data/pks_drugs_2025.json"
GEO = ROOT / "data/germany-counties.geojson"
VIOLENCE = ROOT / "data/pks_violent_2025.json"
UA = "GermanMap-drugs-research/1.0 (+https://github.com/1959124923wyz-sys/German-Map)"

def session():
    s = requests.Session()
    adapter = HTTPAdapter(max_retries=Retry(
        total=3, backoff_factor=0.7,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET"])))
    s.mount("https://", adapter)
    s.headers["User-Agent"] = UA
    return s

def numeric(text):
    val = str(text).strip().replace("\xa0", "").replace(" ", "")
    val = val.replace(".", "").replace(",", ".")
    if not re.fullmatch(r"-?\d+(?:\.\d+)?", val):
        raise ValueError("invalid numeric cell: " + repr(text))
    return float(val)

def scrape(item):
    ags, name, url = item
    response = session().get(url, timeout=40)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    if "2025" not in soup.get_text(" ", strip=True)[:3500]:
        raise ValueError("2025 not found in source")
    for tr in soup.find_all("tr"):
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
        if len(cells) < 3 or cells[0].strip() != "Rauschgiftdelikte":
            continue
        cases = numeric(cells[1])
        rate = numeric(cells[2])
        if cases < 0 or int(cases) != cases or rate < 0 or rate > 25000:
            raise ValueError("invalid cases/rate " + ags)
        if cases > 0 and rate == 0:
            raise ValueError("positive cases and zero rate " + ags)
        return ags, {
            "ags": ags, "name": name, "drug_crime": {
                "cases": int(cases), "rate": rate,
                "change": cells[3] if len(cells) > 3 else None,
            },
            "source_url": url,
        }
    raise ValueError("2025 Rauschgiftdelikte not found: " + ags)

def main():
    index_response = session().get(BASE, timeout=45)
    index_response.raise_for_status()
    soup = BeautifulSoup(index_response.content, "html.parser")
    links = {}
    for a in soup.find_all("a", href=True):
        url = urljoin(BASE, a["href"]).split("?")[0]
        match = re.search(r"/kriminalitaet/([^/]+)-(\d{5})\.html$", url)
        if not match:
            continue
        ags = match.group(2)
        # Nationwide index contains county pages, not Berlin subdivisions.
        links[ags] = (ags, a.get_text(" ", strip=True), url)
    if not 390 <= len(links) <= 420:
        raise RuntimeError(f"Expected about 400 counties; discovered {len(links)}")
    geo = json.loads(GEO.read_text(encoding="utf-8"))
    properties = {str(f.get("id", f.get("properties", {}).get("AGS", ""))).zfill(5):
                  f.get("properties", {}) for f in geo["features"]}
    aliases = json.loads(VIOLENCE.read_text(encoding="utf-8"))["meta"].get("geometry_aliases", {})
    results, errors = {}, []
    with ThreadPoolExecutor(max_workers=8) as pool:
        jobs = {pool.submit(scrape, item): item[0] for item in links.values()}
        for done in as_completed(jobs):
            try:
                ags, rec = done.result()
                geom_id = next((g for g in properties if g == ags or aliases.get(g) == ags), None)
                if geom_id is None:
                    raise ValueError("AGS has no source geometry")
                rec["state"] = properties[geom_id].get("state")
                if not rec["state"]:
                    raise ValueError("no state from geometry")
                results[ags] = rec
            except Exception as exc:
                errors.append({"ags": jobs[done], "message": str(exc)[:200]})
    match_count = sum(1 for g in properties if g in results or aliases.get(g) in results)
    if len(results) < 390 or match_count < 390 or len(errors) > 12:
        raise RuntimeError(f"Dataset incomplete: {len(results)} rows, {match_count} geometry joins, errors {errors[:8]}")
    states = {r["state"] for r in results.values()}
    if len(states) != 16:
        raise RuntimeError(f"Expected 16 states; found {sorted(states)}")
    ordered = {k: results[k] for k in sorted(results)}
    summary = sorted(ordered.values(), key=lambda r: r["drug_crime"]["rate"], reverse=True)
    output = {
        "meta": {
            "year": 2025,
            "metric": "Rauschgiftdelikte",
            "metric_zh": "警方登记毒品违法案件（县级T01指标）",
            "unit": "cases per 100,000 residents",
            "source": "Bundeskriminalamt (BKA), PKS 2025 Kreistabelle T01, via attributed public mirror",
            "official_source_url": BKA,
            "mirror_index_url": BASE,
            "download_method": "BKA-attributed HTML county mirror; not direct official download",
            "scope_note": "Mirror label Rauschgiftdelikte, not necessarily interchangeable with nationwide Rauschgiftkriminalitaet summary",
            "legal_break_note": "Cannabis partial legalization from 2024-04-01 changes recorded offence definitions",
            "dark_figure_note": "Police-recorded cases depend on controls and do not measure population drug consumption",
            "county_count": len(ordered),
            "matched_geometry": match_count,
            "geometry_count": len(properties),
            "geometry_aliases": aliases,
            "national_BKA_rauschgiftkriminalitaet_2025": 164991,
            "national_BKA_scope": "separate BKA nationwide summary; do not sum/compare directly to county mirror metric",
        },
        "records": ordered,
        "top15": [{"ags": r["ags"], "name": r["name"], "state": r["state"],
                    "cases": r["drug_crime"]["cases"], "rate": r["drug_crime"]["rate"]}
                   for r in summary[:15]],
        "errors": sorted(errors, key=lambda e: e["ags"]),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    blob = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    if OUTPUT.exists() and OUTPUT.read_text(encoding="utf-8") == blob:
        print("No change in verified dataset", len(ordered))
        return
    OUTPUT.write_text(blob, encoding="utf-8")
    print(f"Built {OUTPUT.relative_to(ROOT)}: {len(ordered)} counties, {match_count} geometry joins, {len(errors)} source failures")
    print("Top 3:", [(r["name"], r["drug_crime"]) for r in summary[:3]])

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"BUILD FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
