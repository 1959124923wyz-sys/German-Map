#!/usr/bin/env python3
"""Distinguish current 2023 counties from 73 historical empty GENESIS AGS rows.

Official GENESIS static downloader retains historical extinct county IDs
with all seven numeric columns blank. Use the independently downloaded Atlas
2023 KRS AGS roster, and **never** turn '-' or missing into numeric 0.
"""
from __future__ import annotations
import csv,json
from pathlib import Path
BASE=Path(__file__).resolve().parent
ROOT=BASE/'derived'
OUT=ROOT/'regional_core_debt'
def load(p):
 with p.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def write(p,rs):
 with p.open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rs[0]),lineterminator='\n');w.writeheader();w.writerows(rs)
def main():
 cases=load(OUT/'county_core_budget_debt_2023.csv')
 atlas={r['ags5'] for r in load(ROOT/'county_cash_credits_2023.csv')}
 active=[x for x in cases if x['ags5'] in atlas]
 history=[x for x in cases if x['ags5'] not in atlas]
 assert (len(cases),len(active),len(history))==(471,398,73)
 assert all(not x['debt_per_capita_eur'] and not x['core_budget_debt_thousand_eur'] for x in history), '2023 historic code has real number; needs manual review'
 assert sum(bool(x['debt_per_capita_eur']) for x in active)==392
 assert sum(bool(x['core_budget_debt_thousand_eur']) for x in active)==392
 only_atlas=sorted(atlas-{x['ags5'] for x in active})
 assert only_atlas==['02000','11000'],('Atlas differs',only_atlas)
 assert all(x['report_date']=='31.12.2023' for x in active)
 write(OUT/'county_core_budget_debt_2023_active.csv',active)
 write(OUT/'county_core_debt_2023_historical_codes_excluded.csv',history)
 audit={'original_regional_county_rows':471,'official_atlas_2023_county_codes':400,
   'same_ags_2023_regional_atlas':398,'regional_historical_extinct_codes':73,
   'historical_rows_with_numeric_values':0,'active_with_true_numeric_debt':392,
   'active_without_numeric_debt':6,
   'city_state_nonmatching_ags5':['02000','11000'],
   'valid_date':'2023-12-31',
   'valid_layer':'2023_398_county_active_rows_392_numerical_values',
   'source_raw_sha256':'28f034e26731bd538bfec5461a8375156be085b41ac33eb62798167a7b88b80b',
   'not_current_2026_counties':True,
   'warning':'two city-state municipality-level Atlas codes not included in core-budget district table; do not fill with zero',
   'geography_warning':'2026 county set gained Hanau 06415; do not render 2023 06435 on 2026 boundary without a historical-vintage warning',
   'statistical_scope':'2023 municipal and associations core budget, NOT 2023 integrated full entities',
   'readiness':'research_data_ready_with_explicit_missing; not yet front-end reviewed'}
 (OUT/'county_core_2023_active_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('PASS 2023 nationwide county core debt 392 numeric 6 official missing 73 historical empty excluded; 398 active AGS')
if __name__=='__main__':main()
