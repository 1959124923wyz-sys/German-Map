#!/usr/bin/env python3
"""2025 Stuttgart / Düsseldorf authoritative source reconnaissance, no publication.

Stuttgart police PDF includes district tables; the older municipal open CSV
does NOT. This script reads the actual 2025 police report and inspects
municipal district polygon geodata without publishing data or inventing rates.
"""
from __future__ import annotations
import io,json,re
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

ROOT_STUTTGART="https://ppstuttgart.polizei-bw.de"
PAGES=[
  ROOT_STUTTGART+"/statistiken/",
  ROOT_STUTTGART+"/polizeiliche-kriminalstatistik-pks-2025-fuer-stuttgart-veroeffentlicht/"
]
CKAN="https://opendata.stuttgart.de/api/3/action/package_show"
CKAN_NAME="kleinraeumige-gliederung"
DUSSELDORF=[
  "https://www.duesseldorf.de/medienportal/pressedienst-einzelansicht/pld/sitzung-der-bezirksvertretung-1-22",
  "https://www.duesseldorf.de/medienportal/pressedienst-einzelansicht/pld/ob-dr-keller-besucht-die-bezirksvertretung-2",
]
HTTP=requests.Session()
HTTP.headers.update({"User-Agent":"German-Map official district PKS research (https://github.com/1959124923wyz-sys/German-Map)","Accept":"text/html,application/pdf,application/json,*/*"})

def fetch(url,timeout=55):
    r=HTTP.get(url,timeout=timeout)
    r.raise_for_status()
    return r

def police_report():
    links=[]
    for url in PAGES:
        try:
            page=fetch(url)
            soup=BeautifulSoup(page.content,"html.parser")
            items=[]
            for a in soup.select("a[href]"):
                link=urljoin(url,a["href"])
                label=a.get_text(" ",strip=True)
                if "pks" in (label+" "+link).lower() or "kriminalstatistik" in (label+" "+link).lower():
                    items.append({"text":label[:80],"url":link})
                if ".pdf" in link.lower() and ("2025" in label or "2025" in link):
                    links.append(link)
            print("[stuttgart-2025] official page",json.dumps({"url":url,"status":page.status_code,"interesting_links":items[:24]},ensure_ascii=False),flush=True)
        except Exception as e:
            print("[stuttgart-2025] page warning",url,repr(e),flush=True)
    links=list(dict.fromkeys(links))
    selected=[]
    for link in links:
        try:
            r=fetch(link,timeout=95)
            if not r.content.startswith(b"%PDF-"):continue
            reader=PdfReader(io.BytesIO(r.content))
            hits=[]
            for idx,page in enumerate(reader.pages):
                text=page.extract_text() or ""
                if ("Stadtbezirke" in text or "Stadtbezirk" in text) and (
                    "Fallzahlen" in text or "Absolut" in text or "Einwohner" in text or "Straftatenaufkommen" in text):
                    hits.append({"pdf_page":idx+1,"excerpt":text[:4500]})
            info={"url":link,"bytes":len(r.content),"pages":len(reader.pages),"district_page_hits":hits[:6]}
            selected.append(info)
            print("[stuttgart-2025] PDF",json.dumps(info,ensure_ascii=False)[:14500],flush=True)
        except Exception as e:
            print("[stuttgart-2025] PDF probe error",link,repr(e),flush=True)
    if not selected:
        print("[stuttgart-2025] BLOCKER: no downloadable 2025 PDF yet; do not publish",flush=True)
    return selected

def geometry():
    r=fetch(CKAN,timeout=50) if False else HTTP.get(CKAN,params={"id":CKAN_NAME},timeout=50)
    r.raise_for_status()
    payload=r.json()
    if payload.get("success") is not True:raise ValueError("Kleinräumige Gliederung CKAN failed")
    x=payload["result"]
    out={"title":x.get("title"),"license":x.get("license_title"),
         "resources":[{"name":z.get("name"),"format":z.get("format"),"url":z.get("url"),"size":z.get("size")} for z in x.get("resources",[])]}
    print("[stuttgart-geo] district polygon data",json.dumps(out,ensure_ascii=False)[:7500],flush=True)

def duesseldorf():
    for url in DUSSELDORF:
        try:
            r=fetch(url,timeout=40)
            soup=BeautifulSoup(r.content,"html.parser")
            text=soup.get_text(" ",strip=True)
            links=[{"text":a.get_text(" ",strip=True)[:65],"url":urljoin(url,a["href"])}
                   for a in soup.select("a[href]") if any(s in a.get_text(" ",strip=True).lower() for s in ("sitzung","kriminal","rat"))]
            print("[duesseldorf-2025] official council evidence",json.dumps({"url":url,
               "crime_stats_2025":bool(re.search(r"Kriminalstatistik\s+2025",text,re.I)),
               "discussion_excerpt":text[max(0,text.lower().find("kriminalstatistik")-100):text.lower().find("kriminalstatistik")+500],
               "links":links[:8]},ensure_ascii=False)[:4200],flush=True)
        except Exception as e:
            print("[duesseldorf-2025] warning",url,repr(e),flush=True)

def main():
    police_report()
    try:geometry()
    except Exception as e:print("[stuttgart-geo] warning",repr(e),flush=True)
    duesseldorf()

if __name__=="__main__":main()
