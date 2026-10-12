#!/usr/bin/env python3
"""Parse SHA-pinned 2023 German regionalstatistik county CORE-budget debt.

Dataset 71327-01-05-4: 2023 snapshot, unlike integrated local debt including
proportional public enterprise debt. Preserve missing '-' separately from ZERO.
Keep source cp1252 original 44KB in research branch for permanent evidence.
"""
from __future__ import annotations
import csv,hashlib,json,re,shutil
from decimal import Decimal
from pathlib import Path
BASE=Path(__file__).resolve().parent
OUT=BASE/'derived/regional_core_debt'
OUT.mkdir(parents=True,exist_ok=True)
RAW=Path('/tmp/finance08-regional-core/regional_71327-01-05-4_raw.csv')
PINNED='28f034e26731bd538bfec5461a8375156be085b41ac33eb62798167a7b88b80b'
COLS=['ags5','state_code','name_de','report_date','debt_per_capita_eur',
      'core_budget_debt_thousand_eur','marketable_securities_thousand_eur',
      'nonpublic_loans_thousand_eur','nonpublic_cash_credits_thousand_eur',
      'public_loans_thousand_eur','public_cash_credits_thousand_eur',
      'per_capita_value_status','total_value_status','source_id','scope_note']
def numeric(s):
 t=s.strip().replace(' ','').replace(',','.')
 if t in {'','-','.','x','X','/','...',':'}:return ''
 if not re.fullmatch(r'-?\d+(?:\.\d+)?',t):raise ValueError(('not numeric',s))
 return str(Decimal(t))
def main():
 assert RAW.exists(),'First fetch exact source in same CI job'
 contents=RAW.read_bytes()
 assert hashlib.sha256(contents).hexdigest()==PINNED,'Official core budget file changed; fail rather than publish'
 source_dst=OUT/'official_regional_71327_2023_raw_cp1252.csv'
 shutil.copyfile(RAW,source_dst)
 records=[]
 state_summary=[]
 dates=set()
 with RAW.open(encoding='cp1252',newline='') as f:
  for r in csv.reader(f,delimiter=';'):
   if len(r)<10 or not r[0].startswith('31.12.'):continue
   code=r[1].strip()
   if code in {'DG'} or re.fullmatch(r'\d{2}',code):
    state_summary.append({'code':code,'name_de':r[2].strip(),'date':r[0]})
    continue
   if not re.fullmatch(r'\d{5}',code):continue
   dates.add(r[0])
   v=[numeric(r[i]) for i in range(3,10)]
   records.append(dict(ags5=code,state_code=code[:2],name_de=r[2].strip(),
     report_date=r[0],debt_per_capita_eur=v[0],
     core_budget_debt_thousand_eur=v[1],
     marketable_securities_thousand_eur=v[2],
     nonpublic_loans_thousand_eur=v[3],
     nonpublic_cash_credits_thousand_eur=v[4],
     public_loans_thousand_eur=v[5],
     public_cash_credits_thousand_eur=v[6],
     per_capita_value_status='published_numeric' if v[0] else 'no_published_numeric',
     total_value_status='published_numeric' if v[1] else 'no_published_numeric',
     source_id='REGIONALSTATISTIK_71327-01-05-4_2023',
     scope_note='core_budgets_only_not_integrated_public_enterprise_debt'))
 assert dates=={'31.12.2023'},('unexpected year scope',dates)
 ids={r['ags5'] for r in records}
 assert len(records)==len(ids),'duplicate county code'
 assert len(records)>380,('too few counties',len(records))
 atlas_path=BASE/'derived/county_cash_credits_2023.csv'
 with atlas_path.open(encoding='utf-8',newline='') as f:
  atlas={r['ags5'] for r in csv.DictReader(f)}
 matched=ids&atlas
 # No automatic missing fill. Preserve scope and date differences.
 output=OUT/'county_core_budget_debt_2023.csv'
 with output.open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=COLS,lineterminator='\n')
  w.writeheader();w.writerows(sorted(records,key=lambda x:x['ags5']))
 audit={'original_bytes':len(contents),'official_source_sha256':PINNED,
       'reference_date':'2023-12-31','reporting_counties':len(ids),
       'county_ags_overlap_atlas_2023':len(matched),
       'atlas_only_count':len(atlas-ids),'regional_only_count':len(ids-atlas),
       'atlas_only_codes':sorted(atlas-ids),'regional_only_codes':sorted(ids-atlas),
       'published_per_capita_numeric':sum(bool(x['debt_per_capita_eur']) for x in records),
       'published_total_numeric':sum(bool(x['core_budget_debt_thousand_eur']) for x in records),
       'state_or_nation_level_original_records':len(state_summary),
       'original_source_encoding':'cp1252','original_source_in_git':str(source_dst.relative_to(BASE)),
       'conversion':'Tsd. EUR means 1000 EUR; original thousand amounts retained without multiplying or adding',
       'period_scope':'2023_only_not_latest_2025',
       'financial_scope':'core_budget_debt; not municipal comprehensive/integrated debt',
       'status':'research_only_not_published',
       'official_url':'https://www.regionalstatistik.de/genesisws/downloader/00/tables/71327-01-05-4_00.csv'}
 (OUT/'county_core_debt_2023_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('PASS regionalstatistik 2023 county core debt',len(records),
       'AGS match',len(matched),'numeric',audit['published_per_capita_numeric'])
 print('UNMATCHED CODES',audit['atlas_only_codes'][:15],audit['regional_only_codes'][:15])
if __name__=='__main__':main()
