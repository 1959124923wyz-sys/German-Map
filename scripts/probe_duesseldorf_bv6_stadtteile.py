#!/usr/bin/env python3
"""Inspect 2025 official Düsseldorf Stadtteile GEOJSON and BV6 original police PDF."""
from __future__ import annotations
import io,json
from pypdf import PdfReader
from city_build_common import download_bytes
URL="https://opendata.duesseldorf.de/sites/default/files/Stadtteile_2025_WGS84_EPSG4326_1.geojson"
PDF="http://ris-oparl.itk-rheinland.de/Oparl/bodies/0015/downloadfiles/00589618.pdf"
NAMES={"Lichtenbroich","Unterrath","Rath","Mörsenbroich"}
def main():
    doc=json.loads(download_bytes(URL,timeout=75).decode("utf-8-sig"))
    fs=doc.get("features",[])
    matching=[{"id":f.get("id"),"properties":f.get("properties"),"type":f.get("geometry",{}).get("type")}
              for f in fs if f.get("properties",{}).get("Name") in NAMES]
    print("[bv6-geo-probe]",json.dumps({"source":URL,"total_city_stadtteile":len(fs),
        "example":[f.get("properties") for f in fs[:3]],"matched":matching,
        "geom_types":list({f.get("geometry",{}).get("type") for f in fs})},ensure_ascii=False),flush=True)
    if len(matching)!=4:raise ValueError("Official BV6 4 Stadtteile names not uniquely present")
    pdf=PdfReader(io.BytesIO(download_bytes(PDF,timeout=75)))
    for i in range(3,11):
        t=pdf.pages[i].extract_text() or ""
        print("[bv6-pdf]",json.dumps({"pdf_page":i+1,"text":t[:1400]},ensure_ascii=False),flush=True)
if __name__=="__main__":main()
