#!/usr/bin/env python3
"""German Map drug related news: police-origin reports, no fabricated geolocations.

Automatically collects selected recent Presseportal police releases and retains a
small manually cross-checked seed and national health reference items.
Listing date = RELEASE date, not incident date. Geometry is approximate CITY ONLY.
No "number of news" is represented as number of crimes or deaths.

The reporter may fail or change markup; retain last-known-good items and never
replace a previous successful set with an empty scrape.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone, date
from pathlib import Path
from urllib.parse import quote,urljoin
from urllib.request import Request,urlopen
from collections import Counter
from html import unescape
import hashlib,json,re,time,sys

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError as e:
    raise SystemExit("pip install requests beautifulsoup4") from e

ROOT=Path(__file__).resolve().parents[3]
DATA=ROOT/"topics/drugs/data/drug_news.json"
CITIES=ROOT/"js/layers/city-labels.js"
GEO=ROOT/"data/germany-states.geojson"
CACHE=ROOT/"topics/drugs/data/drug_news_geocode.json"
WINDOW_DAYS=90
TODAY=datetime.now(timezone.utc).date()
CUTOFF=TODAY-timedelta(days=WINDOW_DAYS)
HEAD={"User-Agent":"German-Map-drug-news/1.0 (+https://github.com/1959124923wyz-sys/German-Map)","Accept-Language":"de,en;q=0.8"}
TAGS=("Drogenhandel","Rauschgift","Drogenfund","Drogenhändler","Überdosis")
BAD=re.compile(r"\bDrogerie(?:markt)?\b|(?:alkohol|alkoholisier|führerschein|betrunken|autofahr|fahruntüchtig)|\bUnfall\b|Verkehrskontrolle|Prävention|Aktionstag|Berufsmesse|Veranstaltung|Warnung\s+vor|Polizeibericht|Wochenendbericht",re.I)
DRUG=re.compile(r"Rauschgift|Betäubungsmittel|Drogen|Kokain|Crack|Cannabis|Marihuana|Haschisch|Amphetamin|Ecstasy|MDMA|Heroin|Fentanyl|Crystal.?Meth|Methamphetamin|Opioid|Überdosis",re.I)
DEATH=re.compile(r"Drogentot|Drogentod|drogenbedingte[rn]?\s+Todesf|(?:tödlich|tot|verstorben|gestorben)[^.]{0,70}(?:Überdosis|Kokain|Heroin|Fentanyl|Drogen)|(?:Überdosis|Kokain|Heroin|Fentanyl)[^.]{0,70}(?:verstorben|gestorben|tot)|(?:Notarzt|bewusstlos|reanimier|lebensgefahr)[^.]{0,90}(?:Drogen|Überdosis)|(?:Drogen|Überdosis)[^.]{0,90}(?:bewusstlos|reanimier)",re.I)
PRODUCTION=re.compile(r"(?:Drogen|Cannabis|Marihuana|Rauschgift).{0,28}(?:labor|plantage|anbau|produzier)|(?:labor|plantage|anbau|produzier).{0,25}(?:Cannabis|Drogen|Marihuana)|Cannabisplantage",re.I)
TRADE=re.compile(r"Drogenhandel|Rauschgifthandel|Betäubungsmittelhandel|Drogendealer|Drogenhändler|Rauschgifthändler|Handeltreiben|Handel\s+mit\s+(?:Drogen|Kokain|Cannabis|Betäubungsmittel)|Dealer|Schmuggel|geschmuggel|Drogenring",re.I)
SEIZURE=re.compile(r"sichergestellt|beschlagnahmt|Drogenfund|Rauschgiftfund|Durchsuchung|Kilogramm|kg\b|Festnahme|festgenommen",re.I)
LISTDATE=re.compile(r"(?<!\d)(\d{1,2})\.(\d{1,2})\.(20\d{2})(?!\d)")
URL=re.compile(r"^https://www\.presseportal\.de/blaulicht/pm/\d+/\d+$")
MONTHS={"januar":1,"februar":2,"märz":3,"april":4,"mai":5,"juni":6,"juli":7,"august":8,"september":9,"oktober":10,"november":11,"dezember":12}
# Verified official/public-primary releases. Seeds are not fabricated; original links
# and release dates have been individually checked against source pages.
SEED=[
 ("2026-10-06","Frankfurt am Main","trade","Frankfurt-Ostend：警方调查涉嫌非法销售大麻制品","https://www.presseportal.de/blaulicht/pm/4970/6365991","Polizeipräsidium Frankfurt am Main"),
 ("2026-10-06","Troisdorf","trade","Troisdorf：警方查获大量毒品和武器，嫌疑人被羁押","https://www.presseportal.de/blaulicht/pm/65853/6365443","Kreispolizeibehörde Rhein-Sieg-Kreis"),
 ("2026-10-05","Düsseldorf","trade","Düsseldorf：逆行驾驶人涉嫌非法贩卖可卡因","https://www.presseportal.de/blaulicht/pm/13248/6365202","Polizei Düsseldorf"),
 ("2026-10-03","Frankfurt am Main","trade","Frankfurt-Sachsenhausen：警方拘捕涉嫌贩卖可卡因的人员","https://www.presseportal.de/blaulicht/pm/4970/6364128","Polizeipräsidium Frankfurt am Main"),
 ("2026-10-02","Kaiserslautern","trade","Kaiserslautern：警方搜查涉嫌贩毒团伙并拘捕嫌疑人","https://www.presseportal.de/blaulicht/pm/117683/6363501","Polizeipräsidium Westpfalz"),
 ("2026-10-02","Göttingen","trade","Göttingen：警方开展打击街头毒品交易行动","https://www.presseportal.de/blaulicht/pm/119508/6363773","Polizeiinspektion Göttingen"),
]
NATIONAL=[
 {"id":"national-deaths-2025-2026","publication_date":"2026-07-07","category":"death",
 "city":"德国全国","title":"德国2025年因毒品消费死亡2,150人；其中528人不足30岁",
 "summary":"联邦官方年度通报。2025年的死亡人数不应误认为2026年7月发生的单起事件。",
 "source_agency":"德国联邦毒品事务负责人","source_url":"https://www.bundesdrogenbeauftragter.de/presse/detail/jeder-vierte-drogentote-ist-unter-30-jahre/",
 "lat":None,"lon":None,"state":"","precision":"national","kind":"statistical_report"},
 {"id":"national-crime-health-2026","publication_date":"2026-09-15","category":"health",
 "city":"德国全国","title":"联邦毒品事务负责人警告毒品交易造成严重健康和社会危害",
 "summary":"全国毒品形势专题讲话，涉及贩毒活动与2025年毒品死亡统计，并非单一城市事件。",
 "source_agency":"德国联邦毒品事务负责人","source_url":"https://www.bundesdrogenbeauftragter.de/presse/detail/statement-des-sucht-und-drogenbeauftragten-zum-rauschgiftlagebild/",
 "lat":None,"lon":None,"state":"","precision":"national","kind":"statistical_report"}
]
def clean(x):
    return re.sub(r"\s+"," ",BeautifulSoup(unescape(str(x or "")),"html.parser").get_text(" ",strip=True)).strip()
def load(p,default):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except (OSError,ValueError):return default
def save(p,datum):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(datum,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def canonical_city(city):
    city=re.sub(r"\s*(?:[-/]\s*Ortsteil|[-/]\s*Stadtteil).*","",str(city)).strip()
    aliases={"Frankfurt":"Frankfurt am Main","Frankfurt (Main)":"Frankfurt am Main",
             "Frankfurt/Main":"Frankfurt am Main","München":"München",
             "Suhl-Vesser":"Suhl","Stuttgart-Ost":"Stuttgart",
             "Frankfurt-Ostend":"Frankfurt am Main",
             "Stuttgart-Weilimdorf":"Stuttgart",
             "Köln-Kalk":"Köln","Köln-Ehrenfeld":"Köln"}
    return aliases.get(city,city)
def city_coords():
    # Shared human-readable city name layer contains high-confidence centres.
    src=CITIES.read_text(encoding="utf-8")
    return {k:(float(a),float(b)) for k,a,b in
            re.findall(r"\['([^']+)',\s*([\d.]+),\s*([\d.]+),\s*\d+\]",src)}
def in_ring(lon,lat,ring):
    inside=False
    for i in range(len(ring)):
        a,b=ring[i-1],ring[i]
        if (a[1]>lat)!=(b[1]>lat) and lon<((b[0]-a[0])*(lat-a[1])/(b[1]-a[1])+a[0]):
            inside=not inside
    return inside
def state_for(lat,lon,geo):
    for feature in geo["features"]:
        geom=feature["geometry"]
        polys=[geom["coordinates"]] if geom["type"]=="Polygon" else geom["coordinates"]
        for poly in polys:
            if in_ring(lon,lat,poly[0]) and not any(in_ring(lon,lat,h) for h in poly[1:]):
                return feature["properties"]["name"]
    return ""
def categorize(title,summary):
    if BAD.search(title):return None
    head=title+" "+summary[:450]
    if not DRUG.search(head):return None
    if DEATH.search(head):return "death"
    if PRODUCTION.search(head):return "production"
    if TRADE.search(head):return "trade"
    if SEIZURE.search(head):return "seizure"
    return None
def listing_date(body):
    m=LISTDATE.search(body[:130])
    if not m:return None
    try:return date(int(m.group(3)),int(m.group(2)),int(m.group(1)))
    except ValueError:return None
def article_url(node):
    ugly=node.get("data-url-ugly","")
    if ugly.startswith("https:@@"):return ugly.replace("@","/")
    a=node.find("a",href=re.compile(r"/blaulicht/pm/\d+/\d+"))
    return urljoin("https://www.presseportal.de",a["href"]).split("?")[0] if a else ""
def read_news_listing(session,tag,min_date,limit_pages=5):
    page="https://www.presseportal.de/blaulicht/st/"+quote(tag,safe="")+"?startDate="+min_date.isoformat()+"&endDate="+TODAY.isoformat()
    found=[]
    for page_num in range(limit_pages):
        try:
            response=session.get(page,headers=HEAD,timeout=25)
            response.raise_for_status()
            soup=BeautifulSoup(response.text,"html.parser")
        except Exception as e:
            print(f"WARN listing {tag} page={page_num}: {e}",flush=True)
            break
        nodes=soup.select("article.news")
        if not nodes:
            print(f"WARN no article.news in listing {tag}",flush=True)
            break
        oldest=None
        for node in nodes:
            flat=clean(node.get_text(" ",strip=True))
            pub=listing_date(flat)
            if pub:
                if oldest is None or pub<oldest:oldest=pub
                if pub<min_date or pub>TODAY:continue
            url=article_url(node)
            if not URL.fullmatch(url):continue
            title_node=node.find(["h2","h3"])
            title=clean(title_node.get_text(" ",strip=True) if title_node else "")
            city_node=node.select_one("a.news-topic")
            city=canonical_city(clean(city_node.get_text(" ",strip=True) if city_node else ""))
            if not city or len(city)>55 or re.search(r"\d{4}",city):continue
            teaser_node=node.find("p")
            summary=clean(teaser_node.get_text(" ",strip=True) if teaser_node else "")
            category=categorize(title,summary)
            if not category:continue
            if not pub:continue  # refuse to fabricate publication dates
            found.append({
                "id":"police-"+hashlib.sha1(url.encode()).hexdigest()[:16],
                "publication_date":pub.isoformat(),"category":category,
                "title":title[:220],"summary":summary[:260],"city":city,
                "source_agency":"警方公开通报（Presseportal转发）",
                "source_url":url,"kind":"police_release"})
        nxt=soup.find("link",rel=lambda x:x and "next" in x)
        if oldest and oldest<min_date:break
        if not nxt or not nxt.get("href"):break
        page=urljoin(page,nxt.get("href"))
        time.sleep(.1)
    print("LISTING",tag,"found",len(found),flush=True)
    return found

def geocode(session,city,cache,remaining):
    if city in cache:return cache[city]
    if remaining[0]<=0:return None
    remaining[0]-=1
    time.sleep(1.2)
    try:
        r=session.get("https://nominatim.openstreetmap.org/search",params={
            "q":city+", Germany","limit":1,"format":"jsonv2","countrycodes":"de",
            "featuretype":"city","addressdetails":1},headers=HEAD,timeout=15)
        r.raise_for_status()
        hits=r.json()
        if hits:
            lat,lon=float(hits[0]["lat"]),float(hits[0]["lon"])
            if 47<lat<56 and 5<lon<16:
                hit={"lat":round(lat,6),"lon":round(lon,6)}
                cache[city]=hit
                return hit
    except Exception as e:
        print("WARN geocode",city,str(e)[:140],flush=True)
    return None

def main():
    old=load(DATA,{"meta":{},"reports":[]})
    cache=load(CACHE,{})
    coords=city_coords()
    geom=json.loads(GEO.read_text(encoding="utf-8"))
    session=requests.Session()
    gathered={}
    # Preserve last-known-good reports; downgrade location, not content, when no GIS match.
    for entry in old.get("reports",[]):
        if TODAY-timedelta(days=160)<=date.fromisoformat(entry["publication_date"])<=TODAY:
            gathered[entry["source_url"]]=entry
    found_total=0
    for tag in TAGS:
        for entry in read_news_listing(session,tag,CUTOFF):
            found_total+=1
            gathered[entry["source_url"]]=entry
    for pub,city,category,title,url,agency in SEED:
        if not(CUTOFF<=date.fromisoformat(pub)<=TODAY):continue
        if url in gathered:continue
        gathered[url]={
            "id":"police-"+hashlib.sha1(url.encode()).hexdigest()[:16],
            "publication_date":pub,"category":category,
            "city":city,"title":title,"summary":"相关执法情况以警方原文为准；位置标记仅对应城市中心。",
            "source_agency":agency,"source_url":url,"kind":"police_release"}
    for entry in NATIONAL:
        if CUTOFF<=date.fromisoformat(entry["publication_date"])<=TODAY:
            gathered[entry["source_url"]]=entry
    remaining=[22]
    for row in gathered.values():
        row["city"]=canonical_city(row["city"])
        if row.get("kind")=="statistical_report":
            row.update({"lat":None,"lon":None,"state":"","precision":"national"})
            continue
        city=row["city"]
        hit=coords.get(city)
        if hit:
            row["lat"],row["lon"]=hit
            row["precision"]="city-centre"
        elif isinstance(cache.get(city),dict):
            row["lat"],row["lon"]=cache[city]["lat"],cache[city]["lon"]
            row["precision"]="city-approx"
        elif isinstance(row.get("lat"),(int,float)) and isinstance(row.get("lon"),(int,float)):
            row["precision"]="city-approx"
        else:
            place=geocode(session,city,cache,remaining)
            if place:
                row["lat"],row["lon"]=place["lat"],place["lon"]
                row["precision"]="city-approx"
            else:
                row.update({"lat":None,"lon":None,"precision":"not-geocoded"})
        if row["lat"] is not None and row["lon"] is not None:
            row["state"]=state_for(row["lat"],row["lon"],geom)
            if not row["state"]:
                row.update({"lat":None,"lon":None,"precision":"not-in-germany"})
        else:row["state"]=""
    reports=sorted(gathered.values(),key=lambda x:(x["publication_date"],x["source_url"]),reverse=True)[:280]
    if len(reports)<6:
        raise RuntimeError(f"Only {len(reports)} verified drug news reports")
    data={"meta":{
        "as_of":TODAY.isoformat(),"window_days":WINDOW_DAYS,
        "source":"Presseportal original police/prosecutor press releases, plus attributed national government health updates",
        "source_url":"https://www.presseportal.de/blaulicht/st/Drogenhandel",
        "count":len(reports),
        "with_coordinates":sum(isinstance(x.get("lat"),(int,float)) for x in reports),
        "counts":dict(Counter(x["category"] for x in reports)),
        "report_date_note":"Date is RELEASE date. It is not necessarily the day of the underlying incident.",
        "location_note":"Map pins indicate approximate city centres, never street-level crime scenes.",
        "coverage_note":"Non-exhaustive selection of public press releases; not a representative sample or official incident/death census.",
        "health_note":"National 2025 annual death figures are context, not single location incidents."
      },"reports":reports}
    save(DATA,data)
    save(CACHE,cache)
    print("DRUG_NEWS_READY",len(reports),"mapped",data["meta"]["with_coordinates"],"new_listing_hits",found_total,"by_category",data["meta"]["counts"],flush=True)

if __name__=="__main__":
    try:main()
    except Exception as e:print("DRUG NEWS BUILD FAILED:",e,file=sys.stderr);sys.exit(1)
