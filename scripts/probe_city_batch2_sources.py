#!/usr/bin/env python3
"""Read-only second batch checks: official Stuttgart CSV and Bremen PKS districts.

Do not publish census or criminal data until metric definitions/geometry join
are validated. Store compact findings in GitHub Actions logs.
"""
from __future__ import annotations
import csv,io,json,re
from pypdf import PdfReader
from city_build_common import download_bytes

STUTTGART="https://opendata.stuttgart.de/dataset/a8503936-5046-4d5b-995f-f2327f8054a3/resource/c3b927af-32c4-4377-ac4a-0c870b700bbc/download/komunis-9903-v1-kriminalitat__strassen-_und_gewaltkriminalitat_seit_2008.csv"
BREMEN="https://www.rathaus.bremen.de/sixcms/media.php/13/20260623_top_28_Kriminalitaet_in_den_Stadtteilen_Bremens.pdf"

def stuttgart():
    b=download_bytes(STUTTGART,timeout=70)
    txt=None
    for codec in ('utf-8-sig','cp1252','latin-1'):
        try:txt=b.decode(codec);break
        except UnicodeDecodeError:pass
    delim=max((";",",","\t"),key=lambda x:txt[:3000].count(x))
    rows=list(csv.reader(io.StringIO(txt),delimiter=delim))
    years={year:sum(year in cell for row in rows for cell in row)
           for year in ("2023","2024","2025","2026")}
    print("[batch2] stuttgart",json.dumps({
        "bytes":len(b),"rows":len(rows),"header":rows[:6],
        "tail":rows[-3:],"year_occurrences":years
    },ensure_ascii=False)[:9800],flush=True)

def bremen():
    b=download_bytes(BREMEN,timeout=75)
    reader=PdfReader(io.BytesIO(b))
    text="\n".join(page.extract_text() or '' for page in reader.pages)
    titles=re.findall(r"Tabelle\s+(\d+):\s+PKS-Fallzahlen im (.+?)(?:\n| von 2024)",text)
    metrics={x:len(re.findall(re.escape(x),text)) for x in
            ("Straftaten insgesamt","Wohnungseinbruchdiebstahl","Diebstahl insgesamt",
            "Rauschgiftdelikte","Körperverletzung","Raub")}
    print("[batch2] bremen",json.dumps({
        "bytes":len(b),"pages":len(reader.pages),
        "table_numbers":[int(x[0]) for x in titles],
        "headings":titles[:25],"metric_mentions":metrics,
        "intro":text[:1200]
    },ensure_ascii=False)[:10500],flush=True)
    if len(titles)<20:
        raise RuntimeError("Bremen district statistic table structure not recognized")

def main():
    failures=[]
    for name,probe in (("stuttgart",stuttgart),("bremen",bremen)):
        try:probe()
        except Exception as e:
            print("[batch2] "+name+" ERROR "+repr(e),flush=True)
            failures.append(name)
    if failures:
        raise SystemExit("Official batch2 source probes failed: "+", ".join(failures))

if __name__=="__main__":main()
