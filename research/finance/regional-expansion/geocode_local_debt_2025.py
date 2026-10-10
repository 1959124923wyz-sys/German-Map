#!/usr/bin/env python3
"""Resolve 32 local-debt records against official historical administrative codes.
Only research candidates: 2025 code validity and financial scopes not harmonized.
"""
import csv,json,re,unicodedata
from collections import Counter
from pathlib import Path
R=Path(__file__).resolve().parent
def read(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def n(s):
 s=re.sub(r'\([^)]*\)','',s.split(',')[0]).lower().replace('ß','ss')
 s=unicodedata.normalize('NFKD',s)
 return re.sub('[^a-z0-9]','',re.sub('[\u0300-\u036f]','',s))
def unique(name,rr):
 m=[v for v in rr if n(v['name_de'])==n(name)]
 if len(m)!=1:raise ValueError('Nonunique '+name+' '+str(len(m)))
 return m[0]
towns=sum([read(R/f'derived/municipality_tax_2024_by_state/DE-{k}.csv') for k in ['03','05','06']],[])
counties=read(R/'derived/county_cash_credits_2023.csv')
unions=[dict(x,name_de=x['name_de'].removeprefix('SG ')) for x in read(R/'derived/integrated_debt_2024_by_state/DE-03.csv') if x['reporting_unit_class']=='joint_administration']
src=read(R/'source/selected_local_debt_2025_ungeocoded.csv')
assert len(src)==32
states={'Hessen':'06','Nordrhein-Westfalen':'05','Niedersachsen':'03'}
out=[]
for a in src:
 state=states[a['state']];level=a['geo_level'];name=a['name']
 if name=='Bad Homburg vor der Höhe':name='Bad Homburg v. d. Höhe'
 if level=='county':
  b=unique(name,[x for x in counties if x['state_code']==state])
  key=b['ags5'];typ='county_ags5';year='2023'
 elif level=='samtgemeindebereich':
  b=unique(name,[x for x in unions if x['state_code']==state])
  key=b['original_region_key'];typ='joint_administration_rs9';year='2024'
 else:
  assert level in ('municipality','independent_city')
  b=unique(name,[x for x in towns if x['state_code']==state])
  key=b['ags8'];typ='municipality_ags8';year='2024'
 assert re.fullmatch(r'\d{5}|\d{8}|\d{9}',key)
 assert len(key)=={'county_ags5':5,'municipality_ags8':8,'joint_administration_rs9':9}[typ]
 out.append(dict(**a,linked_region_key=key,linked_ref_type=typ,county_ags5=key[:5],reference_name_de=b['name_de'],
  reference_year=year,identity_status='unique_historical_catalog_match_pending_2025_boundary_review',
  map_eligible='no_scope_not_harmonized'))
assert len({x['linked_region_key'] for x in out})==32
dest=R/'derived/local_debt_2025_ags_candidate_32.csv'
with dest.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(out[0]),lineterminator='\n');w.writeheader();w.writerows(out)
audit={'as_of':'2026-10-10','count':32,'uniquely_matched':32,'unmatched':0,'ambiguous':0,
 'by_type':dict(sorted(Counter(x['linked_ref_type'] for x in out).items())),
 'special_alias':'Bad Homburg v. d. Höhe / SG Heeseberg','2025_boundary_checked':False,
 'national_choropleth_eligible':0,'scope_comparable':False}
(R/'derived/local_debt_2025_identity_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
print('PASS historic AGS matched 32/32',audit['by_type'])
