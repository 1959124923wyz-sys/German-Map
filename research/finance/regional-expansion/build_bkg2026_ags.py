#!/usr/bin/env python3
"""Research-only: acquire BKG 01.01.2026 official KRS roster, with 2025 delta.

MD5 pinned to official BKG public checksum. Includes the district-free Hanau
(AGS5 06415) excluded by the 31.12.2025 boundary vintage. Does NOT publish.
"""
from __future__ import annotations
import csv,hashlib,json,re,sqlite3,urllib.request,zipfile
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'derived/bkg2026'
OUT.mkdir(parents=True,exist_ok=True)
TMP=Path('/tmp/finance08-bkg2026')
TMP.mkdir(parents=True,exist_ok=True)
URL='https://daten.gdz.bkg.bund.de/produkte/vg/vg250_ebenen_0101/aktuell/vg250_01-01.utm32s.gpkg.ebenen.zip'
MD5_URL=URL+'.md5'
MD5='912ebecfc58bade695cf31271f4e0e85'
def request(url):
 req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 GermanMapFinanceResearch'})
 with urllib.request.urlopen(req,timeout=240) as response:return response.read()
def main():
 check=request(MD5_URL).decode('utf-8',errors='replace')
 assert MD5 in check.lower(),'BKG source MD5 metadata changed'
 blob=request(URL)
 assert hashlib.md5(blob).hexdigest()==MD5,'Official 2026 BKG source checksum mismatch'
 path=TMP/'bkg_2026_original.zip';path.write_bytes(blob)
 with zipfile.ZipFile(path) as z:
  candidates=[n for n in z.namelist() if n.endswith('.gpkg')]
  assert len(candidates)==1,candidates
  gpkg=TMP/'official_2026.gpkg'
  with z.open(candidates[0]) as src,gpkg.open('wb') as dst:
   while part:=src.read(8*1024*1024):dst.write(part)
 conn=sqlite3.connect('file:'+str(gpkg)+'?mode=ro',uri=True)
 physical={x[0] for x in conn.execute("SELECT table_name FROM gpkg_contents WHERE data_type='features'").fetchall()}
 assert 'vg250_krs' in physical,physical
 columns={x[1] for x in conn.execute('PRAGMA table_info("vg250_krs")')}
 assert 'AGS' in columns and 'GEN' in columns,columns
 records=conn.execute('SELECT AGS,GEN FROM vg250_krs').fetchall()
 conn.close()
 geo={}
 pieces=Counter()
 for code,name in records:
  a=str(code).strip()
  assert re.fullmatch(r'\d{5}',a),a
  geo[a]=str(name).strip()
  pieces[a]+=1
 assert len(geo)==401,('BKG 2026 official county count differs',len(geo))
 old_path=ROOT/'derived/bkg2025/official_counties_2025_ags.csv'
 with old_path.open(encoding='utf-8',newline='') as f:
  old={row['ags5'] for row in csv.DictReader(f)}
 assert len(old)==400,len(old)
 current=set(geo)
 added=sorted(current-old)
 removed=sorted(old-current)
 assert added==['06415'] and not removed,('Unexpected 2026 district reforms',added,removed)
 rows=[{'ags5':k,'name_de':geo[k],'state_code':k[:2],
        'geometry_parts':pieces[k],'valid_at':'2026-01-01',
        'source_id':'BKG_VG250_2026_01_01'} for k in sorted(geo)]
 with (OUT/'official_counties_2026_ags.csv').open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 audit={'boundary_date':'2026-01-01','official_source_url':URL,'official_md5':MD5,
        'source_bytes':len(blob),'source_sha256':hashlib.sha256(blob).hexdigest(),
        'source_polygon_rows':len(records),'official_2026_county_ags5':len(geo),
        'official_2025_county_ags5':len(old),'new_2026_codes':added,
        'removed_2025_codes':removed,
        'hanau_2025_ags8':'06435014','hanau_2026_ags8':'06415000',
        '2026_boundary_legal_source':'https://statistik.hessen.de/sites/statistik.hessen.de/files/2026-01/verz-2_26-01.pdf#page=26',
        'status':'research_only_not_published','geometry_extracted':False,
        'license':'© BKG (2026) dl-de/by-2-0',
        'warning':'Never paint 2026 new Hanau under 2025 county boundary 06435; country fiscal values still require per-year entity normalization.'}
 (OUT/'county_2026_ags_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('PASS BKG 2026 401 official county codes',len(records),'source pieces, added:',added)
if __name__=='__main__':main()
