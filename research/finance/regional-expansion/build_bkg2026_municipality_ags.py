#!/usr/bin/env python3
"""Audit official BKG Jan-2026 municipality polygons and join 2024 debt / 2025 AGS.

Research only. Distinguish AGS8 legal municipality from AGS5 county and
from 9-/12-digit municipality-association debt reporting units.
No guessed geometries; download must match earlier official SHA256.
"""
from __future__ import annotations
import csv,hashlib,json,re,sqlite3,urllib.request,zipfile
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'derived/bkg2026'
OUT.mkdir(parents=True,exist_ok=True)
TMP=Path('/tmp/finance08-bkg2026-municipal')
TMP.mkdir(exist_ok=True)
URL='https://daten.gdz.bkg.bund.de/produkte/vg/vg250_ebenen_0101/aktuell/vg250_01-01.utm32s.gpkg.ebenen.zip'
SHA='6b096eb4862b4eafda9294e425fb5a6d0e7773eb5815a4d4edc78b639ec2728f'
def read(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def get_database():
 req=urllib.request.Request(URL,headers={'User-Agent':'Mozilla/5.0 GermanMapResearch'})
 with urllib.request.urlopen(req,timeout=240) as response:data=response.read()
 assert hashlib.sha256(data).hexdigest()==SHA,'BKG official 2026 package changed'
 with zipfile.ZipFile(__import__('io').BytesIO(data)) as z:
  gp=[n for n in z.namelist() if n.endswith('.gpkg')]
  assert len(gp)==1,gp
  db=TMP/'official_2026.gpkg'
  with z.open(gp[0]) as source,db.open('wb') as dst:
   while chunk:=source.read(8*1024*1024):dst.write(chunk)
 return db
def main():
 db=get_database()
 conn=sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True)
 cols={x[1] for x in conn.execute('PRAGMA table_info("vg250_gem")')}
 assert {'AGS','GEN'}<=cols,cols
 rows=conn.execute('SELECT AGS,GEN FROM vg250_gem').fetchall()
 conn.close()
 groups=defaultdict(list)
 for k,n in rows:
  code=str(k).strip()
  assert re.fullmatch(r'\d{8}',code),('unexpected municipality AGS',code)
  groups[code].append(str(n or '').strip())
 current=set(groups)
 assert len(current)>=10_000,('Unexpectedly sparse official BKG municipality source',len(current))
 atlas={r['ags8']:r for r in read(ROOT/'derived/official_atlas_municipalities_2025_ags.csv')}
 assert len(atlas)==10949,len(atlas)
 old_debt={}
 for f in sorted((ROOT/'derived/integrated_debt_2024_by_state').glob('DE-*.csv')):
  for row in read(f):
   if row['reporting_unit_class']=='municipality':
    old_debt[row['municipality_ags8_candidate']]=row
 assert len(old_debt)==10750,len(old_debt)
 overlap_tax=current&set(atlas)
 overlap_debt=current&set(old_debt)
 assert len(overlap_debt)>10600,('Large unexplained vintage mismatch',len(overlap_debt))
 assert '06415000' in current, 'Hanau municipality 2026 AGS not represented in official BKG municipality data'
 old_parent='06435014'
 # 2025 tax name files are previous vintage; no recoding across county split.
 assert old_parent not in current or (old_parent in current and old_parent not in overlap_tax),'Hanau status must be checked explicitly'
 obs=[]
 for k in sorted(current):
  obs.append({'ags8':k,'name_de':groups[k][0],'state_code':k[:2],
    'county_ags5':k[:5],'geometry_parts':len(groups[k]),
    'present_in_2025_atlas':str(k in atlas).lower(),
    'present_in_2024_integrated_debt':str(k in old_debt).lower(),
    'reference_date':'2026-01-01','source_id':'BKG_VG250_2026_01_01'})
 with (OUT/'official_municipalities_2026_ags.csv').open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(obs[0]));w.writeheader();w.writerows(obs)
 audit={'reference_date':'2026-01-01','official_source_url':URL,'source_sha256':SHA,
       'official_municipality_polygon_rows':len(rows),
       'unique_official_municipality_ags8':len(current),
       '2025_atlas_municipality_ags':len(atlas),
       '2024_debt_municipality_ags':len(old_debt),
       'same_ags_2025_atlas_and_2026_bkg':len(overlap_tax),
       'atlas_2025_only_count':len(set(atlas)-current),
       'bkg_2026_only_relative_to_atlas_count':len(current-set(atlas)),
       'same_ags_2024_debt_and_2026_bkg':len(overlap_debt),
       'old_debt_2024_not_in_bkg2026_count':len(set(old_debt)-current),
       'old_debt_2024_not_in_bkg2026_sample':sorted(set(old_debt)-current)[:120],
       'new_2026_hanau_in_municipality_geometry':'06415000' in current,
       'old_hanau_06435014_in_municipality_geometry':old_parent in current,
       'municipal_geometry_extracted':False,'status':'research_only_not_map_ready',
       'license':'© BKG (2026) dl-de/by-2-0',
       'warning':'A municipality-level source unit must be assigned to its exact year; old debt values cannot be silently remapped across mergers and the 2026 Hanau boundary reform.'}
 (OUT/'municipality_2026_ags_audit.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 print('PASS BKG 2026 municipality AGS',len(current),'polygon rows',len(rows),'joined debt2024',len(overlap_debt),'2025 Atlas',len(overlap_tax))
if __name__=='__main__':main()
