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
BREMEN_SOURCES=[
    "https://www.bremische-buergerschaft.de/dokumente/wp21/land/drucksache/D21L1866.pdf",
    "https://www.rathaus.bremen.de/sixcms/media.php/13/20260623_top_28_Kriminalitaet_in_den_Stadtteilen_Bremens.pdf",
]

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
    b=None
    for url in BREMEN_SOURCES:
        try:
            b=download_bytes(url,timeout=60)
            print("[batch2] bremen PDF mirror",url,flush=True)
            break
        except Exception as ex:
            print("[batch2] Bremen mirror unavailable",url,repr(ex),flush=True)
    if b is None:
        print("[batch2] bremen status=source_unreachable; do not publish local districts",flush=True)
        return
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


def bremen_geometry():
    import xml.etree.ElementTree as ET
    url="https://geodienste.bremen.de/wfs_verwaltungsgrenzen"
    raw=download_bytes(url,{"SERVICE":"WFS","REQUEST":"GetCapabilities"},timeout=55)
    root=ET.fromstring(raw)
    names=[]
    for ft in root.iter():
        if ft.tag.split("}")[-1]=="FeatureType":
            items=[v.text for v in ft if v.tag.split("}")[-1] in ("Name","Title")]
            names.append(items)
    print("[batch2] bremen WFS",json.dumps({
        "bytes":len(raw),"features":names[:35]},ensure_ascii=False)[:5400],flush=True)

def main():
    for name,probe in (("stuttgart",stuttgart),("bremen",bremen),("bremen_geo",bremen_geometry)):
        try:probe()
        except Exception as e:
            print("[batch2] "+name+" BLOCKED "+repr(e),flush=True)
            print("[batch2] WARNING: could not validate source. Do not promote this city.",flush=True)

if __name__=="__main__":main()
