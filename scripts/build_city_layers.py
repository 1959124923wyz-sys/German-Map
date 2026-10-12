#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path

from city_build_common import TEMPORARY_SOURCE_EXIT
from validate_city_layers import validate_city_coordinates

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "city_layers.json"


def verified_cached_snapshot(city: dict, root: Path = ROOT) -> bool:
    """Admit last-known-good data ONLY if its existing source/shape is plausible.

    This is a read-only preflight; full city-layer validation still runs in the
    publishing pipeline. Incomplete downloads and malformed schema must fail.
    """
    relative_file = city.get("file")
    if not isinstance(relative_file, str) or not relative_file.startswith("data/"):
        return False
    path = root / relative_file
    try:
        geo = json.loads(path.read_text(encoding="utf-8"))
        if geo.get("type") != "FeatureCollection":
            return False
        meta = geo.get("meta")
        features = geo.get("features")
        if not isinstance(meta, dict) or not isinstance(features, list) or not features:
            return False

        # A cached 2024 series cannot stand in for the published 2025 layer.
        year = re.search(r"_([12]\d{3})\.geojson$", relative_file)
        if year and str(meta.get("year")) != year.group(1):
            return False
        if meta.get("feature_count") is not None and meta["feature_count"] != len(features):
            return False

        ids = [f.get("id") for f in features]
        if any(not isinstance(fid, str) or not fid for fid in ids) or len(ids) != len(set(ids)):
            return False
        if city.get("id") == "munich":
            if set(ids) != {f"munich-{i:02d}" for i in range(1, 26)}:
                return False
            if any(
                (f.get("properties") or {}).get("population", 0) <= 0
                for f in features
            ):
                return False

        for metric in (city.get("metrics") or {}).values():
            field = (metric or {}).get("field")
            if not field or not any(
                isinstance((f.get("properties") or {}).get(field), dict)
                and isinstance((f["properties"][field]).get("rate"), (int, float))
                and not isinstance(f["properties"][field]["rate"], bool)
                and math.isfinite(f["properties"][field]["rate"])
                for f in features
            ):
                return False

        # Reject wrong CRS/out-of-city geometry; source/data checks run again
        # after building display geometry, before any new publication.
        validate_city_coordinates(city["id"], features, city["bounds"])
    except (ValueError, TypeError, KeyError, OSError, AttributeError, SystemExit):
        return False
    return True


def run_city_builder(cid: str, path: Path, city: dict, root: Path = ROOT) -> None:
    result = subprocess.run([sys.executable, str(path)], cwd=root, check=False)
    if result.returncode == 0:
        return
    if result.returncode == TEMPORARY_SOURCE_EXIT and verified_cached_snapshot(city, root):
        print(
            f"::warning::[city-build] {cid}: official service temporarily unavailable; "
            f"retaining verified last-known-good {city['file']}; no source freshness claimed",
            flush=True,
        )
        return
    # A parser failure, unknown HTTP status or invalid/missing cached dataset
    # must remain a blocking error. Never publish fabricated zeroes or empty GIS.
    raise subprocess.CalledProcessError(result.returncode, result.args)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build registered Germany city detail layers.")
    parser.add_argument(
        "--city",
        action="append",
        default=[],
        help="Build only the given city id. May be passed multiple times.",
    )
    args = parser.parse_args()

    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    wanted = set(args.city)
    selected = []
    seen_builders: set[str] = set()

    for city in registry.get("cities", []):
        cid = city.get("id")
        builder = city.get("builder")
        if wanted and cid not in wanted:
            continue
        if not builder:
            print(f"[city-build] {cid}: no builder declared; preserve existing data")
            continue
        if builder in seen_builders:
            continue

        path = ROOT / builder
        if not path.is_file():
            raise SystemExit(f"[city-build] {cid}: builder missing: {builder}")

        seen_builders.add(builder)
        selected.append((cid, path, city))

    if wanted:
        known = {city.get("id") for city in registry.get("cities", [])}
        missing = sorted(wanted - known)
        if missing:
            raise SystemExit(f"[city-build] unknown city id(s): {', '.join(missing)}")

    if not selected:
        print("[city-build] nothing to build")
        return

    for cid, path, city in selected:
        rel = path.relative_to(ROOT)
        print(f"[city-build] {cid}: {rel}", flush=True)
        run_city_builder(cid, path, city)

    print(f"[city-build] OK: {len(selected)} builder(s)")


if __name__ == "__main__":
    main()
