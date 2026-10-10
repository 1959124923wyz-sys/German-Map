#!/usr/bin/env python3
"""2025 federal municipality code list from HA26, cross-check R13 identity candidates."""
import csv,json,re,urllib.request
from collections import Counter
from pathlib import Path
R=Path(__file__).resolve().parent
D=R/'derived'
URL='https://deutschlandatlas.bund.de/fileadmin/Downloaddateien/HA26/Deutschlandatlas_GEM1225_HA26.csv'
req=urllib.request.Request(URL,headers={'User-Agent':'Mozilla/5.0 GermanMapOfficialAudit'})
with urllib.request.urlopen(req,timeout=90) as f: raw=f.read()
assert 200000<len(raw)<8000000
p=D/'official_atlas_municipalities_2025_ags.csv'
s=raw.decode('cp1252')
rows=[]
for x in csv.DictReader(s.splitlines(),delimiter=';'):
 k=x.get('Regionalschlüssel','').strip()
 if k in ('','Ende der Tabelle.'):continue
 assert re.fullmatch(r'\d{1,8}',k),(k,x)
 k=k.zfill(8)
 rows.append({'ags8':k,'county_ags5':k[:5],'name_de':x.get('Gemeindename',''),
              'boundary_date':'2025-12-31','source':'DE_ATLAS_HA26_GEM1225'})
allkeys={v['ags8'] for v in rows}
assert 10000<len(allkeys)<12000,(len(rows),len(allkeys))
assert len(rows)==len(allkeys)
assert len({x['ags8'][:2] for x in rows})==16
with p.open('w',encoding='utf-8',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(sorted(rows,key=lambda x:x['ags8']))
with (D/'local_debt_2025_ags_candidate_32.csv').open(encoding='utf-8-sig',newline='') as f:
 links=list(csv.DictReader(f))
assert len(links)==32
municipal=[x for x in links if x['linked_ref_type']=='municipality_ags8']
confirmed=[x for x in municipal if x['linked_region_key'] in allkeys]
missing=[x for x in municipal if x['linked_region_key'] not in allkeys]
districts={x['county_ags5'] for x in rows}
county=[x for x in links if x['linked_ref_type']=='county_ags5']
confirmed_county=[x for x in county if x['linked_region_key'] in districts]
missing_county=[x for x in county if x['linked_region_key'] not in districts]
audit={'as_of':'2026-10-10','source_url':URL,'raw_bytes':len(raw),
 'official_2025_municipality_ags':len(allkeys),
 'official_2025_unique_county_parents':len(districts),
 'official_2025_by_state':dict(sorted(Counter(x['ags8'][:2] for x in rows).items())),
 'r13_municipal_candidate_count':len(municipal),'r13_municipal_confirmed_2025':len(confirmed),
 'r13_municipal_missing_2025':[(x['name'],x['linked_region_key']) for x in missing],
 'r13_county_candidate_count':len(county),'r13_county_parent_confirmed_2025':len(confirmed_county),
 'r13_county_parent_missing_2025':[(x['name'],x['linked_region_key']) for x in missing_county],
 'r13_joint_administration_not_evaluable_by_municipality_file':1,
 'county_polygons_verified':False,'production_map_changes':False}
(D/'atlas_2025_ags_qa.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False)+'\n')
print('PASS federal 2025 municipality codes',len(allkeys),'matched R13',len(confirmed),'of',len(municipal))
print('County matched',len(confirmed_county),'of',len(county),'unverified',missing_county)
