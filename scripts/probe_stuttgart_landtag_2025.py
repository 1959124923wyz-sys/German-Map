#!/usr/bin/env python3
"""Read authoritative 2025 BW Landtag answer about Stuttgart public-space violent crime."""
from __future__ import annotations
import io,re,json
from pypdf import PdfReader
from city_build_common import download_bytes
URL="https://www.landtag-bw.de/resource/blob/620460/1a5fd7fcd9c3aea2600f92f0fca27952/17_10292_D.pdf"
def main():
    pdf=download_bytes(URL,timeout=60)
    assert pdf.startswith(b"%PDF-")
    doc=PdfReader(io.BytesIO(pdf))
    print("[stuttgart-pks2025] source",json.dumps({"bytes":len(pdf),"pages":len(doc.pages),"url":URL}),flush=True)
    for i in (2,3,4):
        text=doc.pages[i].extract_text(extraction_mode="layout") or doc.pages[i].extract_text() or ""
        print("[stuttgart-pks2025] PAGE",i+1,repr(text[:23000]),flush=True)
if __name__=="__main__":main()
