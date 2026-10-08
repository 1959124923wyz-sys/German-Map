#!/usr/bin/env python3
"""Inspect official Kiel statistical Stadtteile population download.

Read only: don't publish denominators before verifying the 2025 year,
all district codes and total-population column semantics.
"""
from __future__ import annotations
import csv,io,json
from city_build_common import download_bytes

URL="https://www.kiel.de/opendata/kiel_bevoelkerung_stadtteile.csv"
def main():
    blob=download_bytes(URL,timeout=60)
    text=blob.decode("utf-8-sig")
    print("[kiel-pop] bytes",len(blob),"preview",repr(text[:1700]),flush=True)
    try:dialect=csv.Sniffer().sniff(text[:4096],delimiters=";,\t")
    except csv.Error:dialect=csv.excel
    rows=list(csv.reader(io.StringIO(text),dialect))
    print("[kiel-pop] rows",len(rows),"head",json.dumps(rows[:8],ensure_ascii=False),flush=True)
    print("[kiel-pop] tail",json.dumps(rows[-6:],ensure_ascii=False),flush=True)
    if len(rows)<10:raise RuntimeError("population CSV empty or unexpected")
if __name__=="__main__":main()
