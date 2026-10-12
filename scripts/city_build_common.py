#!/usr/bin/env python3
"""Shared, deterministic I/O for annual official city-crime datasets.

Keep parsing, census population joins, and municipality-specific rules in each
builder. This module only normalizes transport and JSON file publication.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import requests

HEADERS = {
    "User-Agent": "GermanyCrimeMonitor/1.0 (+https://github.com/1959124923wyz-sys/German-Map)"
}

# EX_TEMPFAIL (sysexits.h): the city builder cannot currently reach an official
# source. The orchestration layer may preserve an independently validated,
# previously published snapshot. Parse/schema errors must NEVER use this exit.
TEMPORARY_SOURCE_EXIT = 75
TEMPORARY_HTTP_STATUSES = frozenset((429, 500, 502, 503, 504))


def download_bytes(url: str, params: dict | None = None, timeout: int = 120) -> bytes:
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
        print(f"[official-source] temporary transport failure: {url}: {type(exc).__name__}", file=sys.stderr)
        raise SystemExit(TEMPORARY_SOURCE_EXIT) from exc

    if response.status_code in TEMPORARY_HTTP_STATUSES:
        print(f"[official-source] temporary HTTP {response.status_code}: {url}", file=sys.stderr)
        raise SystemExit(TEMPORARY_SOURCE_EXIT)

    # Unknown statuses (e.g. 400/401/403/404) are NOT classified as transient:
    # a changed source URL or permission failure must be inspected, not hidden.
    response.raise_for_status()
    return response.content


def download_json(url: str, params: dict | None = None, timeout: int = 120) -> Any:
    return json.loads(download_bytes(url, params=params, timeout=timeout))


def download_text(url: str, params: dict | None = None, timeout: int = 120) -> str:
    content = download_bytes(url, params=params, timeout=timeout)
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def write_geojson(path: str | Path, data: dict) -> bool:
    """Publish atomically; do not rewrite a GeoJSON when bytes are unchanged."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n"
    if dest.exists() and dest.read_text(encoding="utf-8") == content:
        return False

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=dest.parent, prefix="." + dest.name + ".",
            suffix=".tmp", delete=False
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(content)
        os.replace(temp_path, dest)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()
    return True
