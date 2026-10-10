#!/usr/bin/env python3
"""2022 German census: exact 400-county rents, vacant housing duration/reason.

Use official nationwide Zensus 2022 regional XLSX only (no geographic
name-matching or interpolation). Ratios here are DERIVED from official counts:
- vacancy lasting >=12 months among VACANT dwellings;
- vacant dwellings available for occupancy within 3 months (REASON, not
  a market-active vacancy rate or count of rental advertisements).
Disclosure adjustments mean category sums may differ by small amounts.
"""
from __future__ import annotations
import csv,json,math,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
WEB=ROOT/"topics/housing/data"; QA=ROOT/"research/housing/qa"; OUT=ROOT/"research/housing/data"
RAW=WEB/"zensus2022-county-archive.json"
CODEBOOK=QA/"zensus2022_official_housing_column_codebook.json"
SOURCE="https://www.destatis.de/static/DE/zensus/gitterdaten/Regionaltabelle_Gebaeude_Wohnungen.xlsx"
CODES={
 "existing_cold_rent_2022_eur_m2":"QMMIETE",
 "census_vacancy_2022_pct":"LEQ",
 "census_ownership_2022_pct":"ETQ",
 "housing_units_in_buildings_2022":"GEBAEUDEART_SYS_1",
 "vacant_housing_units_2022":"LEERSTAND_INSGESAMT",
 "vacant_12mo_plus_2022":"LEERSTAND_DAUER__4",
 "vacant_available_3mo_2022":"LEERSTAND_GRUND__1",
 "vacant_due_construction_2022":"LEERSTAND_GRUND__2",
 "vacant_demolition_2022":"LEERSTAND_GRUND__3",
 "vacant_due_sale_2022":"LEERSTAND_GRUND__4",
 "vacant_future_selfuse_2022":"LEERSTAND_GRUND__5",
 "vacant_other_reason_2022":"LEERSTAND_GRUND__6"
}
INT_FIELDS={k for k in CODES if k not in ("existing_cold_rent_2022_eur_m2","census_vacancy_2022_pct","census_ownership_2022_pct")}
def positive(v,name,ags):
 if v is None:return None
 if not isinstance(v,(int,float)) or not math.isfinite(v) or v<0:
  raise ValueError(f"Invalid Zensus original field {name}: {ags}={v!r}")
 return v
def pct(a,b):return round(a/b*100,2) if a is not None and b and b>0 else None
def main():
 archive=json.loads(RAW.read_text(encoding="utf-8"))
 dictionary=json.loads(CODEBOOK.read_text(encoding="utf-8"))["rows"]["dwellings"]
 for dest,code in CODES.items():
  if code not in dictionary:raise ValueError(f"Official code missing definition: {code}")
  if not dictionary[code]["labels"]:raise ValueError(f"Source label absent for {code}")
 raw=archive["sheets"]["dwellings"]["counties"]
 if len(raw)!=400:raise ValueError(f"Not 400 current census county records {len(raw)}")
 result=[];audits=[]
 for row in raw:
  key=row["id"];v=row["values"];out={"id":key,"name":row["name"]}
  for field,code in CODES.items():
   number=positive(v.get(code),field,key)
   if number is not None and field in INT_FIELDS and not isinstance(number,int):
    if float(number).is_integer():number=int(number)
    else:raise ValueError(f"Noninteger dwelling count for {key} {field}={number}")
   out[field]=number
  vacant=out["vacant_housing_units_2022"]
  units=out["housing_units_in_buildings_2022"]
  if vacant is not None and units is not None and vacant>units:
   raise ValueError(f"Vacancy exceeds all dwelling units: {key}")
  out["vacant_12mo_plus_of_vacant_2022_pct"]=pct(out["vacant_12mo_plus_2022"],vacant)
  out["vacant_available_3mo_of_vacant_2022_pct"]=pct(out["vacant_available_3mo_2022"],vacant)
  out["vacant_available_3mo_of_all_2022_pct"]=pct(out["vacant_available_3mo_2022"],units)
  for name in ("vacant_12mo_plus_of_vacant_2022_pct","vacant_available_3mo_of_vacant_2022_pct"):
   if out[name] is not None and out[name]>100.5:
    raise ValueError(f"Impossible vacancy category share: {key} {name}={out[name]}")
  aud={}
  durations=[v.get("LEERSTAND_DAUER__"+str(i)) for i in range(1,5)]
  reasons=[v.get("LEERSTAND_GRUND__"+str(i)) for i in range(1,7)]
  if all(isinstance(x,(float,int)) for x in durations) and vacant is not None:
   aud["durations_minus_total"]=sum(durations)-vacant
  if all(isinstance(x,(float,int)) for x in reasons) and vacant is not None:
   aud["reasons_minus_total"]=sum(reasons)-vacant
  audits.append(aud)
  result.append(out)
 for metric in ("existing_cold_rent_2022_eur_m2","census_vacancy_2022_pct",
   "vacant_12mo_plus_of_vacant_2022_pct","vacant_available_3mo_of_vacant_2022_pct"):
  nums=[r[metric] for r in result if r[metric] is not None]
  print("VALID",metric,len(nums),"min",min(nums) if nums else None,"max",max(nums) if nums else None,flush=True)
  if len(nums)<380:raise ValueError(f"Too sparse census indicator {metric}: {len(nums)}")
 rmap={r["id"]:r for r in result}
 checks={"Flensburg":{"ags":"01001","value":6.96},"Kiel":{"ags":"01002","value":7.64},
         "Lübeck":{"ags":"01003","value":7.47},"Neumünster":{"ags":"01004","value":6.22}}
 for n,item in checks.items():
  got=rmap[item["ags"]]["existing_cold_rent_2022_eur_m2"]
  if got!=item["value"]:raise ValueError(f"Zensus 2022 city rent independent check {n}: {got} vs {item['value']}")
 benchmark=sum(x["housing_units_in_buildings_2022"] for x in result)
 if abs(benchmark-43106589)>5000:raise ValueError(f"National census 2022 dwelling sum far from source total 43,106,589: {benchmark}")
 if len(set(r["id"] for r in result))!=400:raise ValueError("Duplicate census county AGS")
 payload={"meta":{"year":"2022","reference_date":"2022-05-15","publisher":"Statistische Ämter des Bundes und der Länder",
   "source":SOURCE,"level":"Kreise (Zensus 2022 geographic vintage)","district_count":400,
   "existing_rent":"Census actual net cold rent paid by renting households, not 2025 new asking rents",
   "vacant_12mo_share":"Percentage of all vacant dwellings vacant for 12+ months; NOT percentage of all dwellings",
   "available_3mo_share":"Percentage of all vacant dwellings reported as available for occupancy within 3 months; NOT equivalent to market-active multi-family rental vacancy",
   "available_3mo_total_share":"Same 3mo-available vacancies divided by all dwellings in buildings with living space; DIFFERENT denominator",
   "census_2022_vs_HA26_vacancy":"Census LEQ housing universe is not assumed identical to Deutschlandatlas BBSR wohn_leer",
   "suppression":"Unknown or withheld values retained as null; totals can differ slightly due confidentiality adjustments",
   "code_dictionary":"research/housing/qa/zensus2022_official_housing_column_codebook.json",
   "attribution":"© Statistische Ämter des Bundes und der Länder, Zensus 2022, dl-de/by-2-0"},
   "counties":result}
 WEB.mkdir(parents=True,exist_ok=True);QA.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 (WEB/"zensus2022-housing-indicators-counties.json").write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
 with (OUT/"zensus2022_official_district_rents_vacancy_breakdown.csv").open("w",encoding="utf-8",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(result[0]));w.writeheader();w.writerows(result)
 audit={"original_source":SOURCE,"district_count":400,"crosschecks_2022_census_existing_rent_eur_m2":checks,
  "county_sum_housing_units":benchmark,"national_original_housing_units":43106589,
  "county_sum_minus_national":benchmark-43106589,
  "coverage":{k:sum(d[k] is not None for d in result) for k in result[0] if k not in ("id","name")},
  "duration_plus_original_delta_max_abs":max([abs(x["durations_minus_total"]) for x in audits if "durations_minus_total" in x] or [None]),
  "reason_plus_original_delta_max_abs":max([abs(x["reasons_minus_total"]) for x in audits if "reasons_minus_total" in x] or [None]),
  "field_mapping":{k:{"source_code":code,"official_labels":dictionary[code]["labels"]} for k,code in CODES.items()},
  "notes":["The original Zensus 2022 source was downloaded and archived in research/housing/raw",
   "Long-term vacancy and short-term availability shares are analytical ratios of distinct official classes, not official published vacancy-rate series",
   "All calculations preserve exact five-digit Kreis AGS; no interpolation or name-based join"]}
 (QA/"zensus2022_rent_vacancy_400_county_audit.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("PASS full census 2022 housing rent/vacancy 400 districts sum",benchmark,flush=True)
if __name__=="__main__":main()
