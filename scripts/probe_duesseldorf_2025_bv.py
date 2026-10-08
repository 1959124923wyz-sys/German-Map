#!/usr/bin/env python3
"""Research Düsseldorf's original 2025 BV police presentation attachments.

Never promote meeting *announcements* to numeric crime data. Save evidence
only under artifacts/; no geodata or published crime layer is modified.
"""
from __future__ import annotations
import io,json,re,sys
from pathlib import Path
from urllib.parse import unquote,urlparse,parse_qs
from bs4 import BeautifulSoup
import requests
from pypdf import PdfReader

PORTAL="https://duesseldorf-radar.de"
MEETINGS={
  "01":"https://duesseldorf-radar.de/sitzung/2026/05/bezirksvertretung-1",
  "02":"https://duesseldorf-radar.de/sitzung/2026/06/bezirksvertretung-2-09",
  "03":"https://duesseldorf-radar.de/sitzung/2026/05/bezirksvertretung-3",
  "06":"https://duesseldorf-radar.de/sitzung/2026/06/bezirksvertretung-6",
  "07":"https://duesseldorf-radar.de/sitzung/2026/05/bezirksvertretung-7",
  "10":"https://duesseldorf-radar.de/sitzung/2026/06/bezirksvertretung-10"
}
KNOWN_OFFICIAL={
 "06":"http://ris-oparl.itk-rheinland.de/Oparl/bodies/0015/downloadfiles/00589618.pdf"
}
OUT=Path("artifacts/duesseldorf_2025_attachment_probe.json")
s=requests.Session()
s.headers["User-Agent"]="German-Map official published PKS source audit (https://github.com/1959124923wyz-sys/German-Map)"

def probe_pdf(url,bez):
    rec={"district":bez,"url":url}
    for target in [url,url.replace("http://","https://",1)]:
        try:
            r=s.get(target,timeout=23)
            rec.setdefault("requests",[]).append({"url":target,"status":r.status_code,"bytes":len(r.content),
                 "content_type":r.headers.get("content-type","")})
            if r.status_code!=200 or not r.content.startswith(b"%PDF-"):continue
            pdf=PdfReader(io.BytesIO(r.content))
            snippets=[]
            for i,p in enumerate(pdf.pages):
                t=p.extract_text() or ""
                if any(k in t.lower() for k in ("kriminal", "delikt", "strafrat", "2025")):
                    snippets.append({"page":i+1,"text":t[:4500]})
            rec.update({"downloaded":True,"pages":len(pdf.pages),"extracted_pages":snippets[:14],
                        "text_pages":sum(bool((p.extract_text() or "").strip()) for p in pdf.pages)})
            break
        except Exception as e:
            rec.setdefault("errors",[]).append(type(e).__name__+": "+str(e)[:260])
    print("[duesseldorf-2025-pdf]",json.dumps(rec,ensure_ascii=False)[:22000],flush=True)
    return rec

def main():
    outcomes=[]
    for district,url in MEETINGS.items():
        rec={"district":district,"meeting":url}
        try:
            r=s.get(url,timeout=18)
            rec["status"]=r.status_code
            if r.ok:
                soup=BeautifulSoup(r.content,"html.parser")
                links=[]
                for a in soup.select('a[href]'):
                    label=a.get_text(" ",strip=True)
                    if any(x in label.casefold() for x in ("kriminal", "pks", "2026-06-10 top 4")):
                        href=a.get("href","")
                        if href.startswith("/"):href=PORTAL+href
                        originals=parse_qs(urlparse(href).query).get("url",[])
                        links.append({"text":label[:130],"page_url":href,"original_url":unquote(originals[0]) if originals else ""})
                rec["documents"]=links[:12]
                for link in links:
                    if link["original_url"].endswith(".pdf"):
                        rec.setdefault("original_pdf_checks",[]).append(probe_pdf(link["original_url"],district))
        except Exception as e:
            rec["error"]=repr(e)[:240]
        print("[duesseldorf-2025-meeting]",json.dumps(rec,ensure_ascii=False)[:20000],flush=True)
        outcomes.append(rec)
    for district,u in KNOWN_OFFICIAL.items():
        if not any(record.get("original_pdf_checks") for record in outcomes if record["district"]==district):
            outcomes.append({"standalone_pdf":probe_pdf(u,district)})
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(outcomes,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    ok=sum(bool(rec.get("downloaded")) for rec in outcomes for rec in rec.get("original_pdf_checks",[]))
    print("[duesseldorf-source-audit] COMPLETE",json.dumps({
        "districts_probed":len(MEETINGS),"source_pdfs_downloaded":ok,
        "candidate_only":True,"artifacts":str(OUT)},ensure_ascii=False),flush=True)

if __name__=="__main__":main()
