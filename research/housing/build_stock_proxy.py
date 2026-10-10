#!/usr/bin/env python3
"""Secondary cross-checkable 2022/2025 stock and population Kreis dataset.

Input is an explicitly CC BY 4.0 licensed third-party republication of data
derived from German official GENESIS/Zensus/Regionaldatenbank, NOT a Destatis
original download. Attribution is mandatory. No synthetic shortage scores.
"""
from __future__ import annotations
import hashlib,json,re,statistics,urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
URL="https://mietkautionskonto.info/data/wohnungsmarkt-kreise.json"
LANDING="https://mietkautionskonto.info/wohnungsmarkt-analyse-kreise/"
RAW=ROOT/"research/housing/raw"
QA=ROOT/"research/housing/qa"
OUT=ROOT/"topics/housing/data"
FIELDS=("einwohner_2022","einwohner_2025","wohnungen_2022","wohnungen_2025",
        "geschosswohnungen_anteil_prozent","nettokaltmiete_eur_je_qm_2022",
        "leerstandsquote_prozent_2022","leerstand_kurzfristig_verfuegbar_prozent_2022",
        "bauland_eur_je_qm","bauland_faelle")

def main():
    req=urllib.request.Request(URL,headers={"User-Agent":"GermanMap Housing Research (CC BY attribution retained)"})
    with urllib.request.urlopen(req,timeout=75) as r: raw=r.read()
    j=json.loads(raw)
    rows=j.get("daten")
    if not isinstance(rows,list) or len(rows)!=400:raise ValueError("Expected precisely 400 original Kreis records")
    for d in (RAW,QA,OUT):d.mkdir(parents=True,exist_ok=True)
    ids=set();data=[]
    for row in rows:
        ags=str(row.get("ags",""))
        if not re.fullmatch(r"\d{5}",ags) or ags in ids:raise ValueError(f"Bad or duplicate AGS {ags}")
        ids.add(ags)
        d={"id":ags,"name":row["kreis"]}
        for col in FIELDS:
            d[col]=row.get(col)
        for y in (2022,2025):
            dw=d[f"wohnungen_{y}"]
            pop=d[f"einwohner_{y}"]
            if not isinstance(dw,int) or dw<1000 or not isinstance(pop,int) or pop<1000:
                raise ValueError(f"Invalid stock/population for {ags} {y}: {dw}/{pop}")
            d[f"homes_per_1000_people_{y}"]=round(dw*1000/pop,2)
        d["housing_stock_growth_2022_2025_pct"]=round(100*(d["wohnungen_2025"]/d["wohnungen_2022"]-1),3)
        d["population_growth_2022_2025_pct"]=round(100*(d["einwohner_2025"]/d["einwohner_2022"]-1),3)
        data.append(d)
    # Independently verify specific published 2025 county figures, rather than
    # treating a commercial derived map as an official dataset without QA.
    expected={"01001":54372,"01002":141392,"01003":123030,"01004":42647}
    index={r["id"]:r for r in data}
    for ags,value in expected.items():
        if index[ags]["wohnungen_2025"]!=value:
            raise ValueError(f"Destatis crosscheck failed on {ags} (2025 housing stock)")
    total=sum(d["wohnungen_2025"] for d in data)
    if not 43_500_000<=total<=44_500_000:
        raise ValueError(f"National housing stock sum out of official band {total}")
    atlas=json.loads((OUT/"atlas-counties.json").read_text(encoding="utf-8"))
    atlas_by={r["id"]:r for r in atlas["counties"]}
    diffs=[];with_match=0
    for row in data:
        a=atlas_by.get(row["id"])
        if a and isinstance(a.get("vacancy_2022_pct"),(int,float)) and isinstance(row.get("leerstandsquote_prozent_2022"),(int,float)):
            diffs.append({"id":row["id"],"atlas_vacancy":a["vacancy_2022_pct"],
                "census_vacancy":row["leerstandsquote_prozent_2022"],
                "difference_pp":round(a["vacancy_2022_pct"]-row["leerstandsquote_prozent_2022"],3)})
            with_match+=1
    diffs.sort(key=lambda d:abs(d["difference_pp"]),reverse=True)
    # Deliberately do not overwrite/reconcile mismatching definitions.
    data.sort(key=lambda x:x["id"])
    archive=RAW/"wohnungsmarkt_kreise_2026_09_24.json"
    archive.write_bytes(raw)
    payload={"meta":{"source":URL,"source_page":LANDING,"secondary_republication":True,
       "attribution":"mietkautionskonto.info, Wohnungsmarkt-Analyse der Kreise (CC BY 4.0); Daten der Statistischen Ämter des Bundes und der Länder (dl-de/by-2-0)",
       "official_underlying_tables":["GENESIS 31231-0020","GENESIS 31231-0022","GENESIS 12411-0015","GENESIS 12411-0017","Zensus 2022"],
       "reference_period":"2022-12-31 through 2025-12-31 for housing/population; census rent and vacancy 2022-05-15",
       "warning":"Stock increase is not completed construction; ratio of housing to inhabitants is not households-to-dwellings shortage; do not infer rent affordability."},
       "counties":data}
    (OUT/"stock-counties.json").write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    qa={"source":URL,"sha256_raw":hashlib.sha256(raw).hexdigest(),
        "data_rows":len(data),"dwellings_2025_total":total,
        "official_checks_2025_homes":expected,"atlas_join_count":with_match,
        "vacancy_differences_median_pp":statistics.median(d["difference_pp"] for d in diffs) if diffs else None,
        "vacancy_differences_max_abs_pp":abs(diffs[0]["difference_pp"]) if diffs else None,
        "largest_10_vacancy_differences":diffs[:10],
        "important":["Secondary publisher data, not primary official download","Zensus 2022 vacancy denominator may differ between indicators; do not overwrite official BBSR vacancy","All source rows retained under CC BY 4.0 with full attribution"]}
    (QA/"stock_cross_source_audit.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("STOCK OK",len(data),"counties",total,"2025 units; atlas vacancy crosschecks",with_match)
    print("LARGEST DIFFERENCES",diffs[:5])
if __name__=="__main__":main()
