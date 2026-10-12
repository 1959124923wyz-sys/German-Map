#!/usr/bin/env python3
"""Cross-year matched 2023/2024 German municipal debt panel (research only).

Match SAME original official reporting-unit code and SAME legal entity class.
Retain reported totals, per-capita fields, population denominators separately.
Never generate a synthetic risk rating, never sum municipalities with joint
administrations or county governments, and do not infer an adjusted YoY rate.
"""
from __future__ import annotations
import csv,json
from collections import Counter
from pathlib import Path

BASE=Path(__file__).resolve().parent
DER=BASE/'derived'
OUT=DER/'integrated_panel_2023_2024'
OUT.mkdir(parents=True,exist_ok=True)
STATE_IDS=('01','03','05','06','07','08','09','10','12','13','14','15','16')
DATA_COLS=['total_integrated_debt_eur','integrated_debt_eur_per_person','core_budget_debt_eur',
           'extra_budget_proportional_debt_eur','public_enterprise_proportional_debt_eur']

def rows(path):
 with path.open(encoding='utf-8',newline='') as f:
  return list(csv.DictReader(f))

def main():
 pairs=[]
 summary=[]
 for state in STATE_IDS:
  a=rows(DER/'integrated_debt_2023_by_state'/('DE-'+state+'.csv'))
  b=rows(DER/'integrated_debt_2024_by_state'/('DE-'+state+'.csv'))
  p={r['original_region_key']:r for r in a}
  q={r['original_region_key']:r for r in b}
  assert len(p)==len(a) and len(q)==len(b)
  matched=set(p)&set(q)
  state_rows=[]
  for key in sorted(matched):
   x,y=p[key],q[key]
   assert x['reporting_unit_class']==y['reporting_unit_class'],(key,'official reporting entity class changed')
   assert x['state_code']==y['state_code']==state
   status='legal_name_or_form_changed_review' if (x['name_de']!=y['name_de'] or x['legal_form_de']!=y['legal_form_de']) else 'matching_original_identifier_and_class'
   r={'original_region_key':key,'state_code':state,
      'reporting_unit_class':x['reporting_unit_class'],'name_de_2023':x['name_de'],'name_de_2024':y['name_de'],
      'legal_form_2023':x['legal_form_de'],'legal_form_2024':y['legal_form_de'],
      'municipality_ags8_2023_candidate':x['municipality_ags8_candidate'],
      'municipality_ags8_2024_candidate':y['municipality_ags8_candidate'],
      'population_2023_06_30':x['population_2023_06_30'],
      'population_2024_06_30':y['population_2024_06_30'],
      'source_id_2023':x['source_id'],'source_id_2024':y['source_id'],
      'entity_match_status':status,
      'percap_cross_year_comparable':'not_certified_requires_population_and_entity_scope_audit',
      'not_county_sum':'different_fiscal_unit_classes_cannot_be_summed'}
   for c in DATA_COLS:
    r[c+'_2023']=x[c]
    r[c+'_2024']=y[c]
   # Crucially no debt ratio / growth fields are calculated.
   state_rows.append(r)
  assert state_rows,(state,'no matched unit')
  cols=list(state_rows[0])
  output=OUT/('DE-'+state+'.csv')
  with output.open('w',encoding='utf-8',newline='') as f:
   w=csv.DictWriter(f,fieldnames=cols,lineterminator='\n');w.writeheader();w.writerows(state_rows)
  pairs+=state_rows
  summary.append({'state_code':state,'entities_2023':len(a),'entities_2024':len(b),
                  'stable_original_identifiers':len(matched),
                  '2023_only':len(p.keys()-q.keys()),'2024_only':len(q.keys()-p.keys()),
                  'legal_name_or_form_changed_review':sum(x['entity_match_status'].startswith('legal_') for x in state_rows)})
 assert len(pairs)==11867,len(pairs)
 assert len({r['original_region_key'] for r in pairs})==11867
 assert sum(x['2023_only'] for x in summary)==29
 assert sum(x['2024_only'] for x in summary)==7
 audit={'dataset':'integrated_2023_2024_stable_unit_panel','report_years':[2023,2024],
        'stable_units':len(pairs),'unit_classes':dict(Counter(r['reporting_unit_class'] for r in pairs)),
        'per_capita_population_vintages':{'2023':'published_2023_06_30','2024':'published_2024_06_30'},
        'valid_for_annual_growth_rates':False,'valid_for_cross_class_county_aggregation':False,
        'source_workbook_sha256_2023':'af5b3e0ff66cd30f7566721028e57374bce2bffd1b1cb0fe3a870344b3bb53d0',
        'source_workbook_sha256_2024':'8712ff40e0a2dba71bc43c6a6fa720cdc847dd913e077c876aef5bc79e25198f',
        'state_coverage':summary,'status':'research_only_not_published',
        'cautions':['stable official identifier is not proof of population comparability',
                    'do not sum municipalities, joint administrations and counties',
                    'additional verification needed for entity mergers and ownership changes',
                    'not a nationwide county-level integrated debt series']}
 (OUT/'panel_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('PASS 2023-2024 integrated-debt matched official reporting units',len(pairs))
 print('CHECK legal name/form changes',sum(x['legal_name_or_form_changed_review'] for x in summary))
if __name__=='__main__':main()
