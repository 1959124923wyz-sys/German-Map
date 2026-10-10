#!/usr/bin/env python3
"""Convert official nationwide 2022 Zensus rent bands and dwelling-owner types
into an auditable 400-county microstructure dataset.

Rent >=12 EUR/m² is a share of the 10 BINS of EXISTING rentals, not a
household housing cost burden (rent / disposable household income).
Owner types classify the OWNER OF THE BUILDING in which the dwelling exists,
NOT the occupant's tenure and NOT publicly price-regulated social housing.
"""
from __future__ import annotations
import csv,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/"topics/housing/data/zensus2022-county-archive.json"
BOOK=ROOT/"research/housing/qa/zensus2022_official_housing_column_codebook.json"
OUT=ROOT/"research/housing/data"
QA=ROOT/"research/housing/qa"
WEB=ROOT/"topics/housing/data"
URL="https://www.destatis.de/static/DE/zensus/gitterdaten/Regionaltabelle_Gebaeude_Wohnungen.xlsx"
def safe(v):
 if isinstance(v,(int,float)) and math.isfinite(v) and v>=0:return v
 return None
def pct(a,b):
 return round(100*a/b,2) if a is not None and b and b>0 else None
def main():
 src=json.loads(SRC.read_text(encoding="utf-8"))
 book=json.loads(BOOK.read_text(encoding="utf-8"))["rows"]["dwellings"]
 required=["GEBAEUDEART_SYS_1","NUTZUNG__02",*[f"MIETE_EURM2_2__{i:02d}" for i in range(1,11)],
          *[f"EIGENTUM__{i}" for i in range(1,9)],*[f"BAUJAHR_10JA__{i:02d}" for i in range(1,11)]]
 for code in required:
  if code not in book or not book[code]["labels"]:
   raise ValueError(f"Missing official meaning of {code}")
 rows=[];audit_diffs=[]
 for r in src["sheets"]["dwellings"]["counties"]:
  d=r["values"];key=r["id"];housing=safe(d["GEBAEUDEART_SYS_1"])
  if housing is None or housing<1000:raise ValueError(f"Bad housing denominator for {key}")
  bins=[safe(d[f"MIETE_EURM2_2__{i:02d}"]) for i in range(1,11)]
  owners=[safe(d[f"EIGENTUM__{i}"]) for i in range(1,9)]
  ages=[safe(d[f"BAUJAHR_10JA__{i:02d}"]) for i in range(1,11)]
  rented=safe(d["NUTZUNG__02"])
  if any(x is None for x in bins):
   priced=None;high=None;low=None
  else:
   priced=sum(bins);high=sum(bins[5:]);low=sum(bins[:3])
   if priced<100:raise ValueError(f"Unexpected rent bin denominator {key}={priced}")
  owner_sum=sum(owners) if all(x is not None for x in owners) else None
  age_sum=sum(ages) if all(x is not None for x in ages) else None
  pubcoop=sum(owners[i] for i in [2,3,6]) if all(owners[i] is not None for i in [2,3,6]) else None
  row={"id":key,"name":r["name"],"census_rent_eligible_units_binned_2022":priced,
      "rents_12eur_plus_2022_count":high,"rents_under8eur_2022_count":low,
      "rents_12eur_plus_of_paid_rental_2022_pct":pct(high,priced),
      "rents_under8eur_of_paid_rental_2022_pct":pct(low,priced),
      "rented_dwellings_2022":rented,
      "dwelling_units_built_since_2016_2022":ages[-1],
      "dwelling_units_built_since_2016_of_all_2022_pct":pct(ages[-1],housing),
      "cooperative_owned_dwelling_units_2022":owners[2],
      "municipal_owned_dwelling_units_2022":owners[3],
      "federal_state_owned_dwelling_units_2022":owners[6],
      "private_housing_company_owned_dwelling_units_2022":owners[4],
      "municipal_coop_state_owned_of_all_units_2022_pct":pct(pubcoop,housing),
      "cooperative_owned_of_all_units_2022_pct":pct(owners[2],housing),
      "municipal_owned_of_all_units_2022_pct":pct(owners[3],housing),
      "private_housing_company_owned_of_all_units_2022_pct":pct(owners[4],housing)}
  audit_diffs.append({
      "id":key,"rent_bands_minus_rented_units":priced-rented if priced is not None and rented is not None else None,
      "owner_classified_minus_all_units":owner_sum-housing if owner_sum is not None else None,
      "building_age_classified_minus_all_units":age_sum-housing if age_sum is not None else None})
  rows.append(row)
 if len(rows)!=400 or len({x["id"] for x in rows})!=400:raise ValueError("Expected 400 exact census counties")
 cover={k:sum(isinstance(r[k],(float,int)) for r in rows) for k in rows[0] if k not in ("id","name")}
 for core in ["rents_12eur_plus_of_paid_rental_2022_pct","cooperative_owned_of_all_units_2022_pct",
              "municipal_owned_of_all_units_2022_pct","dwelling_units_built_since_2016_of_all_2022_pct"]:
  if cover[core]<375:raise ValueError(f"Insufficient numeric district coverage {core}={cover[core]}")
 for row in rows:
  for key,v in row.items():
   if key.endswith("_pct") and v is not None and not 0<=v<=100.5:
    raise ValueError(f"Implausible share {row['id']} {key}={v}")
 qa={"publisher":"Statistische Ämter des Bundes und der Länder","source":URL,
     "reference_date":"2022-05-15","districts":400,"coverage":cover,
     "ranges":{k:{"min":min(x[k] for x in rows if x[k] is not None),
                  "max":max(x[k] for x in rows if x[k] is not None)}
               for k in cover if cover[k]>0},
     "crosscheck":{"sample_districts":[r for r in rows if r["id"] in ("01001","11000","09162")]},
     "differences":{"rent_band_vs_rented_units_max_abs":max(abs(x["rent_bands_minus_rented_units"]) for x in audit_diffs if x["rent_bands_minus_rented_units"] is not None),
         "owner_vs_all_units_max_abs":max(abs(x["owner_classified_minus_all_units"]) for x in audit_diffs if x["owner_classified_minus_all_units"] is not None),
         "building_age_vs_all_units_max_abs":max(abs(x["building_age_classified_minus_all_units"]) for x in audit_diffs if x["building_age_classified_minus_all_units"] is not None)},
     "warnings":["Price bands describe EXISTING rents paid in May 2022, not 2025 ads",
       "High-price rental share NOT actual income-based affordability or housing rent burden",
       "Municipal/coop/government building-owner classifications are NOT the same as housing with legal rent subsidy/Sozialwohnungen",
       "Class percentages use explicitly documented denominators; official confidentiality adjustments can make group sums differ slightly"]}
 payload={"meta":{"source":URL,"reference_date":"2022-05-15","counties":400,
     "rent_share_denominator":"sum of ten mutually exclusive paid EUR/m2 rent brackets, not household count or median income",
     "ownership_share_denominator":"all dwellings in buildings with living accommodation from 2022 census",
     "public_coop_rent_warning":"Building owner status is not social housing/subsidized housing",
     "not_income_based":"Do not label any metric here Wohnkostenbelastungsquote",
     "attribution":"© Statistische Ämter des Bundes und der Länder, Zensus 2022 dl-de/by-2-0"},
     "counties":rows}
 WEB.mkdir(parents=True,exist_ok=True);QA.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
 (WEB/"zensus2022-county-rent-owner-distribution.json").write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
 with (OUT/"zensus2022_rent_band_and_building_ownership_400_counties.csv").open("w",encoding="utf-8",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 (QA/"zensus2022_rent_band_owner_building_age_audit.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("PASS Zensus 2022 owner/rent-band/age all 400 counties; coverage",cover,flush=True)
if __name__=="__main__":main()
