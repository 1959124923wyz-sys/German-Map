#!/usr/bin/env python3
"""Extract nationwide 2025 sheltered homelessness by county from Destatis 22971-0080.

GENESIS static CSV is a 3-row geographic index and three dimensions along
columns (nationality, gender, age). ONLY the intersecting 'Insgesamt' of ALL
three is valid as an aggregate. Do not sum other cells (double-counting).
The downloadable file is for 31.01.2025 even though the interactive Destatis
database already contains 2026; distinguish publication from statistical year.
"""
from __future__ import annotations
import csv,io,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/"research/housing/raw/destatis_22971-0080_national_counties.csv"
QA=ROOT/"research/housing/qa"
OUT=ROOT/"research/housing/data"
WEB=ROOT/"topics/housing/data"
ATLAS=WEB/"atlas-counties.json"
URL="https://genesis.destatis.de/genesisWS/downloads/00/tables/22971-0080_00.csv"
CRED="© Statistisches Bundesamt (Destatis), 2026"
def parse(v):
 s=str(v).strip()
 if s in ("", ".", "..", "...", "/", "-", "x"):return None
 if not re.fullmatch(r"[0-9][0-9.]*",s):raise ValueError(f"Invalid official sheltered person figure {v!r}")
 n=int(s.replace(".",""))
 if not 0<=n<=200_000:raise ValueError(f"Outlier district sheltered person count {n}")
 return n
def run():
 raw=SOURCE.read_bytes().decode("cp1252")
 rows=list(csv.reader(io.StringIO(raw),delimiter=";"))
 if rows[0][0].strip()!="Tabelle: 22971-0080":raise ValueError("Unrecognized GENESIS source")
 for i in (4,5,6):
  if len(rows[i])<80:raise ValueError(f"GENESIS dimension row {i+1} incomplete")
 headers=rows[4:7]
 columns=min(map(len,headers))
 total_cols=[i for i in range(3,columns) if all(h[i].strip()=="Insgesamt" for h in headers)]
 if len(total_cols)!=1:
  raise ValueError(f"All-nationality, all-gender, all-age total has ambiguous positions: {total_cols}")
 allcol=total_cols[0]
 base=json.loads(ATLAS.read_text(encoding="utf-8"))
 expected={d["id"] for d in base["counties"]}
 if len(expected)!=400:raise ValueError("Need 400 official HA26 current IDs before national join")
 extracted={};legacy=[];duplicate=[]
 dates=set();miss=[]
 for row in rows[7:]:
  if len(row)<=allcol or not re.fullmatch(r"\d{5}",row[1].strip()):continue
  date,key,name=row[0].strip(),row[1].strip(),row[2].strip()
  dates.add(date)
  if date!="31.01.2025":raise ValueError(f"Unexpected non-2025 observation date {date}")
  val=parse(row[allcol])
  if key not in expected:
   legacy.append({"id":key,"name":name,"count":val})
   continue
  if key in extracted:duplicate.append(key)
  extracted[key]={"id":key,"name":name,"sheltered_homeless_2025":val}
 if duplicate:raise ValueError(f"Duplicate current county codes: {duplicate[:10]}")
 missing=sorted(expected-set(extracted))
 if missing:raise ValueError(f"Missing current county codes {missing}")
 counts=[r["sheltered_homeless_2025"] for r in extracted.values() if r["sheltered_homeless_2025"] is not None]
 if len(counts)<350:raise ValueError(f"Insufficient complete district observations: {len(counts)}")
 if any(n%5 for n in counts):raise ValueError("Expected 5-person disclosure rounding")
 total=sum(counts)
 if not 300_000 <= total <= 650_000:raise ValueError(f"Implausible 2025 district subtotal {total}")
 # Independent federal press release (2025-07-08) rounded national count: 474,700.
 # County disclosure-rounded totals need not add exactly, but should be close.
 if abs(total-474_700)>1_000:raise ValueError(f'County subtotal {total} inconsistent with official 2025 national 474,700')
 for p in (QA,OUT,WEB):p.mkdir(parents=True,exist_ok=True)
 saxony=json.loads((WEB/"saxony-homeless-counties.json").read_text(encoding="utf-8"))
 sax_checks=[]
 for s in saxony["counties"]:
  key=s["id"];canon=extracted.get(key,{}).get("sheltered_homeless_2025")
  target=s["annual_counts"].get("2025")
  if target is not None and canon is not None:
   sax_checks.append({"id":key,"destatis_national_2025":canon,"saxony_2025":target,"difference":canon-target})
 # Differences may reflect statistical revisions; preserve both rather than substituting.
 payload={
  "meta":{"indicator":"On 31 Jan 2025 persons without a home accommodated by public or contracted providers",
    "year":2025,"country":"Germany","level":"Kreise (2024 county AGS)",
    "source":URL,"publisher":"Statistisches Bundesamt (Destatis)",
    "source_license":"Data Licence Germany Attribution 2.0",
    "credit":CRED,"raw_code":"22971-0080",
    "coverage_numerical":len(counts),"districts":400,
    "subset_warning":"Does NOT include rough sleepers or persons hidden homeless; district counts disclosure-rounded to nearest five",
    "missing_value":"Null for missing/suppressed/dash values, not zero",
    "national_subtotal_caution":"Summing rounded districts differs from official unrounded national total; do not call subtotal exact national result",
    "staleness":"CSV currently returns 31 January 2025. 2026 is available in the interactive Destatis database but not this static CSV source at acquisition."},
  "counties":[extracted[k] for k in sorted(extracted)]}
 (WEB/"germany-homeless-counties-2025.json").write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
 with (OUT/"destatis_sheltered_homeless_counties_2025.csv").open("w",encoding="utf-8",newline="") as f:
  writer=csv.DictWriter(f,fieldnames=["id","name","sheltered_homeless_2025"])
  writer.writeheader();writer.writerows(payload["counties"])
 audit={"source":URL,"table":"22971-0080","table_dates":sorted(dates),"dimension_headers_total_col":allcol,
        "exact_3_dimension_totals":[headers[0][allcol],headers[1][allcol],headers[2][allcol]],
        "county_keys":len(extracted),"numerical":len(counts),"nulls":400-len(counts),
        "rounded_subtotal":total,"destatis_published_national_2025":474700,
        "national_check_difference":total-474700,
        "destatis_published_national_source":"https://www.destatis.de/DE/Presse/Pressemitteilungen/2025/07/PD25_246_229.html",
        "legacy_or_deprecated_codes":legacy,
        "saxony_checks":sax_checks,
        "saxony_differences":sum(c["difference"]!=0 for c in sax_checks),
        "warnings":["This is JAN 2025 rather than 2026","Do not sum country-nationality or sex disaggregated counts",
        "5-person disclosure-rounded counts; excluded categories of homelessness"]}
 (QA/"destatis_homeless_2025_county_audit.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("DEST 22971-0080 SUCCESS",len(counts),"/400 numeric 2025 county totals; sum of rounded districts",total,flush=True)
 print("SAXONY cross-check",len(sax_checks),"matched",audit["saxony_differences"],"different",flush=True)
if __name__=="__main__":run()
