#!/usr/bin/env python3
"""Official nationwide 2024 German municipal finance normalization for a DATA-ONLY research branch.
Runs on GitHub Actions with stdlib; raw XLSX and CSV SHA256 pinned.
Do not sum county governments, municipal unions and towns. No Pages deployment.
"""
from __future__ import annotations
import csv
import hashlib
import json
import re
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'derived'
RAW=Path('/tmp/finance08-national-raw')
FILES=[
 ('integrierte_schulden_2024.xlsx','https://www.statistikportal.de/sites/default/files/2025-12/Integrierte_Schulden_der_Gemeinden_und_Gemeindeverbaende_2024_Tabellenband_0.xlsx','8712ff40e0a2dba71bc43c6a6fa720cdc847dd913e077c876aef5bc79e25198f'),
 ('atlas_ha26_municipality_2024.csv','https://deutschlandatlas.bund.de/fileadmin/Downloaddateien/HA26/Deutschlandatlas_GEM1224_HA26.csv','28c8eb2423288222c3b1a757c42833a812833b124a09b33680b56ad90e465c99'),
 ('atlas_ha26_county_2023.csv','https://deutschlandatlas.bund.de/fileadmin/Downloaddateien/HA26/Deutschlandatlas_KRS1222_HA26.csv','c05b3ee80df70172e76834e9023c0db49a28eaf074eeb77073dac30a6792fc97')
]
STATE_IDS=('01','03','05','06','07','08','09','10','12','13','14','15','16')
NS='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
TAG='{'+NS+'}'
def writecsv(p,rows,cols):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=cols,lineterminator='\n');w.writeheader();w.writerows(rows)
def writemeta(name,obj):
 p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def dec(v):
 v=(v or '').strip()
 if not v or v in {'X','x','-','–','.','...'}:return ''
 return str(Decimal(v.replace(',','.')).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP))
def atlasnum(v):
 v=v.strip()
 if not v or v.startswith('-9999'):return ''
 return str(Decimal(v.replace('.','').replace(',','.')))
def download():
 RAW.mkdir(parents=True,exist_ok=True);audit=[]
 for name,url,expected in FILES:
  path=RAW/name
  request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 GermanMapResearch/1.0'})
  with urllib.request.urlopen(request,timeout=90) as response:data=response.read(26000000)
  sha=hashlib.sha256(data).hexdigest()
  if sha!=expected:raise ValueError('Source changed: '+name+' sha256 '+sha)
  path.write_bytes(data)
  audit.append({'name':name,'url':url,'sha256':sha,'bytes':len(data),'verified':True})
  if name.endswith('.xlsx'):
   with zipfile.ZipFile(path) as z:
    if 'xl/workbook.xml' not in z.namelist():raise ValueError('Not a genuine XLSX')
 writemeta('source_download_audit.json',audit)
 return {x[0]:RAW/x[0] for x in FILES}
def load_csv(path):
 with path.open(encoding='cp1252',newline='') as f:
  return [x for x in csv.DictReader(f,delimiter=';') if x.get('Regionalschlüssel','').strip()!='Ende der Tabelle.']
def load_atlas(paths):
 tax=[]
 for r in load_csv(paths['atlas_ha26_municipality_2024.csv']):
  code=r['Regionalschlüssel'].strip().zfill(8)
  assert re.fullmatch(r'\d{8}',code)
  v=atlasnum(r['st_einnkr'])
  status='published_missing_sentinel' if not v else 'negative_value_review_keep_numeric' if Decimal(v)<0 else 'published_numeric'
  tax.append(dict(ags8=code,county_ags5=code[:5],name_de=r['Gemeindename'],state_code=code[:2],year='2024',tax_capacity_eur_per_capita=v,value_status=status,source_id='DE_ATLAS_HA26_GEM_2024'))
 assert len(tax)==10956 and len({x['ags8'] for x in tax})==10956
 assert sum(x['value_status']=='published_missing_sentinel' for x in tax)==204
 assert sum(x['value_status']=='negative_value_review_keep_numeric' for x in tax)==3
 for st in range(1,17):
  subset=[x for x in tax if x['state_code']==f'{st:02d}']
  assert subset
  writecsv(OUT/'municipality_tax_2024_by_state'/f'DE-{st:02d}.csv',subset,list(tax[0]))
 county=[]
 for r in load_csv(paths['atlas_ha26_county_2023.csv']):
  code=r['Regionalschlüssel'].strip().zfill(8)[:5]
  v=atlasnum(r['ko_kasskred'])
  if code[:2] in {'02','04','11'}:status='not_applicable_city_state';v=''
  elif not v:status='published_missing'
  elif Decimal(v)==0:status='published_zero'
  else:status='published_numeric'
  county.append(dict(ags5=code,name_de=r['Kreisname'],state_code=code[:2],year='2023',cash_credits_eur_per_capita=v,value_status=status,geography_reference='KRS1222',source_id='DE_ATLAS_HA26_KRS_2023'))
 assert len(county)==400 and len({x['ags5'] for x in county})==400
 assert sum(x['value_status']=='not_applicable_city_state' for x in county)==4
 assert sum(x['value_status']=='published_zero' for x in county)==120
 writecsv(OUT/'county_cash_credits_2023.csv',county,list(county[0]))
 writemeta('atlas_raw_quality_audit.json',{'municipality_rows':10956,'municipality_numeric':10752,'municipality_missing':204,'municipality_negative':3,'county_rows':400,'county_numeric':396,'county_city_state_not_applicable':4,'county_genuine_zero':120,'source':'Deutschlandatlas HA26 2026','municipal_year':2024,'county_year':2023})
 return tax,county
def excel_rows(z,sheet_idx,strings):
 with z.open(f'xl/worksheets/sheet{sheet_idx}.xml') as f:
  for _,el in ET.iterparse(f,events=('end',)):
   if el.tag!=TAG+'row':continue
   d={}
   for cell in el.findall(TAG+'c'):
    col=re.match(r'[A-Z]+',cell.attrib['r']).group()
    if col not in ('A','B','C','D','E','G','J','L','Q'):continue
    val=cell.find(TAG+'v')
    if val is not None and val.text is not None:
     d[col]=strings[int(val.text)] if cell.attrib.get('t')=='s' else val.text
    else:
     v=cell.find(TAG+'is')
     if v is not None:d[col]=''.join(v.itertext())
   yield d
   el.clear()
DEBT_COLS=['report_year','state_code','county_ags5','reporting_unit_class','original_region_key','municipality_ags8_candidate','ags_match_2024_atlas','name_de','legal_form_de','population_2024_06_30','total_integrated_debt_eur','integrated_debt_eur_per_person','core_budget_debt_eur','extra_budget_proportional_debt_eur','public_enterprise_proportional_debt_eur','source_id']
def load_integrated(paths,tax):
 atlas_ids={x['ags8'] for x in tax}
 allrows=[]
 with zipfile.ZipFile(paths['integrierte_schulden_2024.xlsx']) as z:
  strings=[''.join(x.itertext()) for x in ET.fromstring(z.read('xl/sharedStrings.xml')).findall(TAG+'si')]
  assert len(strings)==36950
  for i,state in enumerate(STATE_IDS,start=7):
   rows=[]
   for v in excel_rows(z,i,strings):
    code=v.get('A','').strip()
    if not re.fullmatch(r'\d{5}|\d{9}|\d{12}',code):continue
    assert code.startswith(state)
    level={5:'county_administration',9:'joint_administration',12:'municipality'}[len(code)]
    ags8=code[:5]+code[-3:] if level=='municipality' else ''
    match=('matched' if ags8 in atlas_ids else 'not_in_atlas_2024') if ags8 else 'not_applicable'
    pop=v.get('D','').strip().strip('{}').replace(' ','')
    if pop:assert pop.isdigit(),(code,pop)
    row=dict(report_year='2024',state_code=state,county_ags5=code[:5],reporting_unit_class=level,original_region_key=code,municipality_ags8_candidate=ags8,ags_match_2024_atlas=match,name_de=v.get('B','').strip(),legal_form_de=v.get('C','').strip(),population_2024_06_30=pop,total_integrated_debt_eur=dec(v.get('E')),integrated_debt_eur_per_person=dec(v.get('G')),core_budget_debt_eur=dec(v.get('J')),extra_budget_proportional_debt_eur=dec(v.get('L')),public_enterprise_proportional_debt_eur=dec(v.get('Q')),source_id='STATISTIKPORTAL_INTEGRATED_2024_T1')
    assert row['integrated_debt_eur_per_person'] and row['total_integrated_debt_eur']
    if level=='municipality':assert match=='matched',(code,ags8)
    rows.append(row)
   assert rows
   writecsv(OUT/'integrated_debt_2024_by_state'/f'DE-{state}.csv',rows,DEBT_COLS)
   allrows+=rows
 counts=Counter(x['reporting_unit_class'] for x in allrows)
 assert counts=={'municipality':10750,'county_administration':294,'joint_administration':830},counts
 # These atlas rows are NOT omitted debt values: 4 city-state units are outside the
 # municipal debt workbook; 202 other atlas records have no tax-capacity metric
 # (primarily independent forest/lake/unincorporated geography). Preserve every one.
 integrated_ids={x['municipality_ags8_candidate'] for x in allrows if x['reporting_unit_class']=='municipality'}
 residual=[x for x in tax if x['ags8'] not in integrated_ids]
 assert len(residual)==206,len(residual)
 assert sum(x['state_code'] in {'02','04','11'} for x in residual)==4
 assert sum(not x['tax_capacity_eur_per_capita'] for x in residual)==202
 gap_rows=[dict(ags8=x['ags8'],name_de=x['name_de'],state_code=x['state_code'],
   tax_capacity_2024=x['tax_capacity_eur_per_capita'],
   reason='city_state_not_in_integrated_debt_scope' if x['state_code'] in {'02','04','11'} else 'tax_capacity_missing_no_integrated_debt_entity') for x in residual]
 writecsv(OUT/'atlas_tax_entities_without_integrated_debt_2024.csv',gap_rows,list(gap_rows[0]))
 assert len(allrows)==11874 and len({x['original_region_key'] for x in allrows})==11874
 audit={'source_url':FILES[0][1],'source_sha256':FILES[0][2],'reporting_rows':11874,'municipalities':10750,'county_administrations_not_full_county_totals':294,'joint_administrations':830,'municipal_ags_matched_other_official_2024_atlas':10750,'municipal_missing_from_atlas':0,'atlas_2024_tax_ags_without_debt_row':206,'atlas_2024_outside_integrated_city_states':4,'atlas_2024_outside_integrated_tax_missing_other':202,'cities_not_in_scope':'Berlin,Hamburg,Bremen','status':'research_only_not_national_choropleth','official_publication_discrepancy':'published national 342761 million EUR vs 13 state totals sum 343762 million EUR (1001 million) unresolved','caution':'Do not add county government / joint administrations / municipalities; different scopes can overlap. No missing values converted to zero.'}
 writemeta('integrated_debt_2024_audit.json',audit)
 return allrows
def join_cities(debt,tax,cash):
 taxes={x['ags8']:x for x in tax}
 loans={x['ags5']:x for x in cash}
 cities=[]
 for r in debt:
  if r['legal_form_de'] not in ('kreisfreie Stadt','Stadtkreis'):continue
  a=r['municipality_ags8_candidate']; c=r['county_ags5']
  assert a in taxes and c in loans,(a,c)
  t=taxes[a]; l=loans[c]
  cities.append(dict(ags8=a,ags5=c,state_code=r['state_code'],name_de=r['name_de'],population_2024_06_30=r['population_2024_06_30'],integrated_debt_2024_eur=r['total_integrated_debt_eur'],integrated_debt_2024_eur_per_capita=r['integrated_debt_eur_per_person'],core_budget_debt_2024_eur=r['core_budget_debt_eur'],extra_budget_debt_2024_eur=r['extra_budget_proportional_debt_eur'],allocated_enterprise_debt_2024_eur=r['public_enterprise_proportional_debt_eur'],tax_capacity_2024_eur_per_capita=t['tax_capacity_eur_per_capita'],tax_capacity_2024_status=t['value_status'],cash_credits_2023_eur_per_capita=l['cash_credits_eur_per_capita'],cash_credits_2023_status=l['value_status'],source_integrated_id='STATISTIKPORTAL_INTEGRATED_2024_T1',source_tax_id='DE_ATLAS_HA26_GEM_2024',source_cash_id='DE_ATLAS_HA26_KRS_2023'))
 assert len(cities)==102
 assert len({x['ags8'] for x in cities})==102
 assert all(x['tax_capacity_2024_eur_per_capita'] and x['cash_credits_2023_eur_per_capita'] for x in cities)
 cols=list(cities[0])
 writecsv(OUT/'independent_cities_official_2024.csv',sorted(cities,key=lambda x:x['ags8']),cols)
 writemeta('city_join_2024_audit.json',{'independent_cities_count':102,'city_integrated_debt_year':2024,'city_tax_capacity_year':2024,'city_core_cash_credit_year':2023,'warning':'Different definitions and years; do not add or call these metrics a single fiscal risk score.'})
 return cities
def main():
 paths=download()
 tax,cash=load_atlas(paths)
 debt=load_integrated(paths,tax)
 city=join_cities(debt,tax,cash)
 print('SUCCESS: 10956 municipal tax records, 400 county cash loans, 11874 integrated debt reporting units, 102 true independent cities',len(city))
if __name__=='__main__':main()
