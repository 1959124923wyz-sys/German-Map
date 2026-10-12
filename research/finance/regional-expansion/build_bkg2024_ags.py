#!/usr/bin/env python3
"""Audit EXACT 2024-year municipal polygon identifiers from BKG VG250-EW archive.

The 2024 13-state integrated debt dataset has 10750 municipality units. Only
accept official 2024 boundary codes (not 2025/2026 proxies) as original AGS8.
Preliminary source SHA is logged and must be pinned in a second review.
"""
from __future__ import annotations
import csv,hashlib,json,re,sqlite3,urllib.request,zipfile
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'derived/bkg2024'
OUT.mkdir(parents=True,exist_ok=True)
TMP=Path('/tmp/finance08-bkg2024')
TMP.mkdir(parents=True,exist_ok=True)
URL='https://daten.gdz.bkg.bund.de/produkte/vg/vg250-ew_ebenen_1231/2024/vg250-ew_12-31.utm32s.gpkg.ebenen.zip'
def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 GermanMapResearch'})
 with urllib.request.urlopen(req,timeout=240) as response:return response.read()
def main():
 # Historical BKG archives may not publish a .md5 companion (HTTP 404).
 # In that case record raw SHA256 for a SECOND pinned run, not an official-MD5 claim.
 try:
  md5_file=get(URL+'.md5').decode('utf-8',errors='replace')
 except urllib.error.HTTPError as ex:
  if ex.code!=404:raise
  md5_file=''
 matches=re.findall(r'\b[0-9a-fA-F]{32}\b',md5_file)
 assert len(matches)<=1,('ambiguous published checksum',md5_file[:500])
 md5=matches[0].lower() if matches else ''
 original=get(URL)
 got=hashlib.md5(original).hexdigest()
 if md5:assert got==md5,'BKG archive official MD5 mismatch'
 orig=TMP/'BKG_vg250ew_2024_original.zip'
 orig.write_bytes(original)
 with zipfile.ZipFile(orig) as z:
  candidates=[n for n in z.namelist() if n.lower().endswith('.gpkg')]
  assert len(candidates)==1,candidates
  out=TMP/'official.gpkg'
  with z.open(candidates[0]) as src,out.open('wb') as f:
   while chunk:=src.read(8*1024*1024):f.write(chunk)
 con=sqlite3.connect('file:'+str(out)+'?mode=ro',uri=True)
 tables={r[0] for r in con.execute("SELECT table_name FROM gpkg_contents WHERE data_type='features'")}
 gem=next((x for x in ('vg250_gem','vg250ew_gem','vg250_ew_gem') if x in tables),None)
 assert gem,('not official municipal physical layer',sorted(tables))
 cols={r[1] for r in con.execute('PRAGMA table_info("'+gem+'")')}
 assert {'AGS','GEN'}<=cols,(gem,cols)
 rows=con.execute('SELECT "AGS","GEN" FROM "'+gem+'"').fetchall()
 con.close()
 groups={}
 parts=Counter()
 for key,name in rows:
  code=str(key).strip()
  assert re.fullmatch(r'\d{8}',code),(gem,code)
  parts[code]+=1
  groups[code]=str(name or '').strip()
 official=set(groups)
 def read(p):
  with p.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
 atlas={x['ags8'] for x in read(ROOT/'derived/municipality_tax_2024_by_state/DE-01.csv')}
 for i in range(2,17):atlas.update(x['ags8'] for x in read(ROOT/'derived/municipality_tax_2024_by_state'/('DE-'+str(i).zfill(2)+'.csv')))
 assert len(atlas)==10956,len(atlas)
 debts={x['municipality_ags8_candidate'] for p in (ROOT/'derived/integrated_debt_2024_by_state').glob('DE-*.csv') for x in read(p) if x['reporting_unit_class']=='municipality'}
 assert len(debts)==10750,len(debts)
 overlap=official&debts
 assert len(overlap)>10690,('2024 official geometry mostly missing 2024 debt entities',len(overlap))
 inventory=[{'ags8':code,'county_ags5':code[:5],'state_code':code[:2],
             'name_de':groups[code],'polygon_pieces':parts[code],
             'present_debt_2024':str(code in debts).lower(),
             'present_atlas_2024':str(code in atlas).lower(),'valid_at':'2024-12-31'} for code in sorted(official)]
 with (OUT/'municipal_2024_official_ags.csv').open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(inventory[0]));w.writeheader();w.writerows(inventory)
 audit={'official_source_url':URL,'source_md5':md5,
       'source_zip_sha256':hashlib.sha256(original).hexdigest(),
       'source_zip_bytes':len(original),'valid_at':'2024-12-31',
       'municipal_physical_layer':gem,
       'raw_municipal_polygon_rows':len(rows),'unique_2024_ags8':len(official),
       'municipal_debt_entities_2024':len(debts),
       'matched_exact_year_debt_entities':len(overlap),
       'debt_entities_without_2024_geometry':sorted(debts-official),
       'atlas_2024_tax_ags_match_count':len(official&atlas),
       'municipality_geojson_not_yet_generated':True,
       'checksum_status':'official_MD5_matched' if md5 else 'historical_archive_no_official_MD5_second_SHA_pin_required',
       'status':'research_only_not_published',
       'license':'© BKG (2026) dl-de/by-2-0'}
 (OUT/'municipal_2024_ags_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('PASS BKG 2024 geometry AGS',len(official),'rows',len(rows),'match official debt',len(overlap),'SHA',audit['source_zip_sha256'])
if __name__=='__main__':main()
