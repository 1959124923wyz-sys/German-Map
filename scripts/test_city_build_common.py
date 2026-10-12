#!/usr/bin/env python3
"""Local, network-free contract test for deterministic city GeoJSON publishing."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from city_build_common import write_geojson


def main() -> None:
    with TemporaryDirectory() as tmp:
        target = Path(tmp) / "city.geojson"
        first = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "id": "test-001",
                "properties": {"name": "München", "crime_total": {"cases": 2, "rate": 10.5}},
                "geometry": {"type": "Polygon", "coordinates": []}
            }]
        }
        assert write_geojson(target, first) is True
        original = target.read_bytes()
        original_mtime = target.stat().st_mtime_ns
        assert write_geojson(target, first) is False, "identical data should not be republished"
        assert target.read_bytes() == original
        assert target.stat().st_mtime_ns == original_mtime
        assert json.loads(original)["features"][0]["properties"]["name"] == "München"

        changed = {**first, "features": [{**first["features"][0], "id": "test-002"}]}
        assert write_geojson(target, changed) is True
        assert json.loads(target.read_text(encoding="utf-8"))["features"][0]["id"] == "test-002"
    print("[city-build-common] PASS: UTF-8, deterministic no-op, atomic content replacement")


def test_source_fallback_contract() -> None:
    """A transient HTTP outage may reuse vetted GeoJSON; bad data must fail."""
    import copy
    import subprocess
    from types import SimpleNamespace
    from unittest.mock import Mock, patch

    import requests
    from build_city_layers import ROOT, run_city_builder, verified_cached_snapshot
    from city_build_common import (
        TEMPORARY_SOURCE_EXIT, download_bytes, download_json,
    )

    # Official temporary statuses produce the dedicated subprocess exit code.
    for status in (429, 500, 502, 503, 504):
        response = Mock(status_code=status, content=b'{"ok":true}')
        with patch("city_build_common.requests.get", return_value=response):
            try:
                download_bytes("https://example.org/official")
            except SystemExit as exc:
                assert exc.code == TEMPORARY_SOURCE_EXIT
            else:
                raise AssertionError(f"HTTP {status} was not classified as transient")

    for error in (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        with patch("city_build_common.requests.get", side_effect=error):
            try:
                download_bytes("https://example.org/official")
            except SystemExit as exc:
                assert exc.code == TEMPORARY_SOURCE_EXIT
            else:
                raise AssertionError(f"{error} was not classified as transient")

    bad_source = Mock(status_code=404)
    bad_source.raise_for_status.side_effect = requests.exceptions.HTTPError("404")
    with patch("city_build_common.requests.get", return_value=bad_source):
        try:
            download_bytes("https://example.org/official")
        except requests.exceptions.HTTPError:
            pass
        else:
            raise AssertionError("A changed 404 source URL was silently ignored")

    invalid_source = Mock(status_code=200, content=b"{invalid json")
    with patch("city_build_common.requests.get", return_value=invalid_source):
        try:
            download_json("https://example.org/official")
        except json.JSONDecodeError:
            pass
        else:
            raise AssertionError("Malformed official response was swallowed")

    registry = json.loads((ROOT / "data/city_layers.json").read_text(encoding="utf-8"))
    city = next(x for x in registry["cities"] if x["id"] == "munich")
    cached = ROOT / city["file"]
    assert verified_cached_snapshot(city), "Committed Munich 25-district snapshot must be sound"
    original = cached.read_bytes()
    builder = ROOT / city["builder"]

    temporary = SimpleNamespace(returncode=TEMPORARY_SOURCE_EXIT, args=["python", str(builder)])
    failure = SimpleNamespace(returncode=1, args=["python", str(builder)])
    with patch("build_city_layers.subprocess.run", return_value=temporary):
        run_city_builder("munich", builder, city)
    assert cached.read_bytes() == original, "Outage fallback must not rewrite source data"

    with patch("build_city_layers.subprocess.run", return_value=failure):
        try:
            run_city_builder("munich", builder, city)
        except subprocess.CalledProcessError as exc:
            assert exc.returncode == 1
        else:
            raise AssertionError("An invalid parser/schema was treated as temporary")

    with TemporaryDirectory() as tmp:
        temp_root = Path(tmp)
        output = temp_root / "data" / "munich_local_2025.geojson"
        output.parent.mkdir()
        broken = json.loads(original)
        broken["features"] = broken["features"][:-1]
        output.write_text(json.dumps(broken), encoding="utf-8")
        assert not verified_cached_snapshot(city, temp_root)
        with patch("build_city_layers.subprocess.run", return_value=temporary):
            try:
                run_city_builder("munich", builder, city, root=temp_root)
            except subprocess.CalledProcessError as exc:
                assert exc.returncode == TEMPORARY_SOURCE_EXIT
            else:
                raise AssertionError("Incomplete cached districts incorrectly passed")
        output.unlink()
        assert not verified_cached_snapshot(city, temp_root)

    print("[city-source-fallback] PASS: HTTP 503, timeouts, 404, JSON corruption, verified cache and fail-closed")


if __name__ == "__main__":
    main()
    test_source_fallback_contract()
