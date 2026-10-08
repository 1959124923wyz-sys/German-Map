#!/usr/bin/env python3
"""Audit 2025 Düsseldorf BV7 and BV9 police statistical annexes.

Do not publish on agenda evidence alone. Print actual PDF tabular content,
regional labels, source dates, and structural 2025/2024 rows, for independent
geographic reconciliation against original 50-Stadtteil 2025 GIS.
"""
from __future__ import annotations
import io,re,json
from pypdf import PdfReader
from city_build_common import download_bytes
SOURCES={
 "07":"http://ris-oparl.itk-rheinland.de/Oparl/bodies/0015/downloadfiles/00588348.pdf",
 "09":"http://ris-oparl.itk-rheinland.de/Oparl/bodies/0015/downloadfiles/00592935.pdf"
}
def main():
 for district,url in SOURCES.items():
    print("[duesseldorf-next] START",district,url,flush=True)
    raw=download_bytes(url,timeout=75)
    if not raw.startswith(b"%PDF-"):raise ValueError(f"BV{district}: no actual official PDF")
    reader=PdfReader(io.BytesIO(raw))
    print("[duesseldorf-next] SOURCE",json.dumps({"district":district,"url":url,"bytes":len(raw),
       "pages":len(reader.pages)},ensure_ascii=False),flush=True)
    for i,page in enumerate(reader.pages):
        t=page.extract_text() or ""
        rows=[line.strip() for line in t.splitlines() if re.match(r"^202[2-5]\s+",line.strip())]
        kws=[v for v in ("Gesamtkriminalität","Straßenkriminalität","Raub","Körperverletzung",
              "Diebstahl","Wohnungseinbruch","Betrug","2025","Stadtteile","Stadtbezirk")
            if v.lower() in t.lower()]
        print("[duesseldorf-next] PAGE",json.dumps({"bv":district,"page":i+1,
             "chars":len(t),"keywords":kws,"year_rows":rows[:7],"preview":t[:2200] if i<17 else t[:650]},
            ensure_ascii=False)[:5500],flush=True)
if __name__=="__main__":main()
