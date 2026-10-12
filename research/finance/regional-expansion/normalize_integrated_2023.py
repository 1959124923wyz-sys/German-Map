#!/usr/bin/env python3
"""Preserve 2023 official integrated municipal debt by distinct legal reporting unit.

The original source is pinned by SHA. Each output keeps the 2023 population
reference separate from 2024. NEVER add towns+county governments+associations,
and never infer an annual change without matching entity, population and scope.
"""
from __future__ import annotations
import csv,hashlib,json,re,zipfile
from collections import Counter
from decimal import Decimal
from pathlib import Path
from build_official_national_pipeline import STATE_IDS,TAG,dec,excel_rows,writecsv

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'derived'
SRC=Path('/tmp/finance08-2023/integrated_2023_original.xlsx')
SHA='af5b3e0ff66cd30f7566721028e57374bce2bffd1b1cb0fe3a870344b3bb53d0'
COLS=['report_year','state_code','county_ags5','reporting_unit_class','original_region_key',
      'municipality_ags8_candidate','ags_match_2024_atlas','name_de','legal_form_de',
      'population_2023_06_30','total_integrated_debt_eur','integrated_debt_eur_per_person',
      'core_budget_debt_eur','extra_budget_proportional_debt_eur',
      'public_enterprise_proportional_debt_eur','source_id']
def readcsv(p):
 with p.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def main():
 assert SRC.exists(),'First inspect the pinned original workbook in the same CI job'
 assert hashlib.sha256(SRC.read_bytes()).hexdigest()==SHA,'Original XLSX changed'
 atlas={r['ags8'] for p in (OUT/'municipality_tax_2024_by_state').glob('DE-*.csv') for r in readcsv(p)}
 old={r['original_region_key']:r for p in (OUT/'integrated_debt_2024_by_state').glob('DE-*.csv') for r in readcsv(p)}
 assert len(old)==11874 and len(atlas)==10956
 allrows=[]
 validation={'unit_codes_2023_unique':True,'2023_mapping_to_2024':False}
 with zipfile.ZipFile(SRC) as z:
  strings=[''.join(s.itertext()) for s in __import__('xml.etree.ElementTree',fromlist=['ElementTree']).fromstring(z.read('xl/sharedStrings.xml')).findall(TAG+'si')]
  assert len(strings)==36979
  for sheet_idx,state in enumerate(STATE_IDS,start=6):
   data=[]
   for fields in excel_rows(z,sheet_idx,strings):
    key=fields.get('A','').strip()
    if not re.fullmatch(r'\d{5}|\d{9}|\d{12}',key):continue
    assert key.startswith(state),(sheet_idx,state,key)
    level={5:'county_administration',9:'joint_administration',12:'municipality'}[len(key)]
    ags8=key[:5]+key[-3:] if level=='municipality' else ''
    pop=fields.get('D','').strip().strip('{}').replace(' ','')
    assert pop.isdigit() and int(pop)>0,(key,'population',pop)
    amount=dec(fields.get('E'))
    percap=dec(fields.get('G'))
    assert amount and percap,(key,'missing official amount/percap')
    # Detect wrong column mapping / changed population denominator without changing values.
    difference=abs(Decimal(amount)/Decimal(pop)-Decimal(percap))
    assert difference<Decimal('0.03'),(key,'per-capita does not match total and population',str(difference))
    data.append({
     'report_year':'2023','state_code':state,'county_ags5':key[:5],
     'reporting_unit_class':level,'original_region_key':key,
     'municipality_ags8_candidate':ags8,
     'ags_match_2024_atlas':'matched' if ags8 in atlas else 'not_in_2024_atlas' if ags8 else 'not_applicable',
     'name_de':fields.get('B','').strip(),'legal_form_de':fields.get('C','').strip(),
     'population_2023_06_30':pop,'total_integrated_debt_eur':amount,
     'integrated_debt_eur_per_person':percap,'core_budget_debt_eur':dec(fields.get('J')),
     'extra_budget_proportional_debt_eur':dec(fields.get('L')),
     'public_enterprise_proportional_debt_eur':dec(fields.get('Q')),
     'source_id':'STATISTIKPORTAL_INTEGRATED_2023_T1'})
   assert data,(state,'missing 2023 state sheet')
   writecsv(OUT/'integrated_debt_2023_by_state'/('DE-'+state+'.csv'),data,COLS)
   allrows+=data
 counts=Counter(r['reporting_unit_class'] for r in allrows)
 assert counts=={'municipality':10771,'county_administration':294,'joint_administration':831},counts
 keys={r['original_region_key'] for r in allrows}
 assert len(keys)==11896
 old_keys=set(old)
 stable=keys&old_keys
 rec={
  'source_sha256':SHA,'reference_year':2023,'source_sheet_state_order':list(STATE_IDS),
  'reporting_units_2023':len(allrows),'breakdown_2023':dict(counts),
  'matched_reporting_units_stable_2023_2024':len(stable),
  'in_2023_not_in_2024_count':len(keys-old_keys),
  'in_2024_not_in_2023_count':len(old_keys-keys),
  'in_2023_not_in_2024_examples':sorted(keys-old_keys)[:35],
  'in_2024_not_in_2023_examples':sorted(old_keys-keys)[:35],
  'source_audit':'derived/integrated_2023/source_2023_download.json',
  'status':'research_only_not_published',
  'year_comparison_warning':'Census / legal entity changes / 2023 vs 2024 population denominator, so not automatically comparable or an annual growth measure',
  'aggregation_warning':'municipalities, county governments and joint administrations must not be summed'
 }
 p=OUT/'integrated_2023/integrated_2023_vs_2024_entity_audit.json'
 p.write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('PASS: official 2023 integrated debt 13 states',len(allrows),'stable report codes',len(stable))
if __name__=='__main__':main()
