#!/usr/bin/env python3
"""Build 2026 municipality-level BKG GeoJSON files, partitioned by 16 states.

Use SHA-pinned federal VG250 and a conservatively topology-preserving 80m
simplification per municipality; polygon boundaries can have slight edge
differences after independent simplification. Research only, not live Pages.
"""
from __future__ import annotations
import collections,csv,hashlib,json,re,sqlite3,urllib.request,zipfile
from pathlib import Path
from shapely import wkb
from shapely.ops import transform,unary_union
from pyproj import Transformer

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'derived/bkg2026'
DEST=OUT/'municipal_geometry_by_state'
DEST.mkdir(parents=True,exist_ok=True)
TMP=Path('/tmp/finance08-bkg2026-municipal-geo')
TMP.mkdir(exist_ok=True)
URL='https://daten.gdz.bkg.bund.de/produkte/vg/vg250_ebenen_0101/aktuell/vg250_01-01.utm32s.gpkg.ebenen.zip'
SHA='6b096eb4862b4eafda9294e425fb5a6d0e7773eb5815a4d4edc78b639ec2728f'
ENV={0:0,1:32,2:48,3:48,4:64}
def fetch():
 request=urllib.request.Request(URL,headers={'User-Agent':'Mozilla/5.0 GermanMapResearch'})
 with urllib.request.urlopen(request,timeout=240) as response:data=response.read()
 assert hashlib.sha256(data).hexdigest()==SHA,'Official source checksum changed; do not trust geography'
 with zipfile.ZipFile(__import__('io').BytesIO(data)) as z:
  gp=[n for n in z.namelist() if n.endswith('.gpkg')]
  assert len(gp)==1,gp
  path=TMP/'official.gpkg'
  with z.open(gp[0]) as src,path.open('wb') as dst:
   while chunk:=src.read(8*1024*1024):dst.write(chunk)
 return path

def parse(blob):
 assert blob and blob[:2]==b'GP'
 flags=blob[3]
 mode=(flags>>1)&7
 assert mode in ENV
 g=wkb.loads(blob[8+ENV[mode]:])
 assert g.geom_type in ('Polygon','MultiPolygon') and not g.is_empty
 return g

def main():
 db=fetch()
 con=sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True)
 result=con.execute("SELECT column_name,srs_id FROM gpkg_geometry_columns WHERE table_name='vg250_gem'").fetchone()
 assert result,result
 geom,srs=result
 assert srs in (25832,32632),srs
 raw=con.execute('SELECT AGS,GEN,"'+geom+'" FROM vg250_gem').fetchall()
 con.close()
 assert len(raw)==11094,len(raw)
 parts=collections.defaultdict(list)
 names={}
 for code,name,blob in raw:
  key=str(code).strip()
  assert re.fullmatch(r'\d{8}',key),key
  parts[key].append(parse(blob))
  if key not in names:names[key]=str(name or '').strip()
 assert len(parts)==10939,len(parts)
 ags={r['ags8'] for r in csv.DictReader((OUT/'official_municipalities_2026_ags.csv').open(encoding='utf-8',newline=''))}
 assert set(parts)==ags,('official geo and own published AGS census differ',len(parts),len(ags))
 tr=Transformer.from_crs('EPSG:'+str(srs),'EPSG:4326',always_xy=True)
 counts={}
 sizes={}
 area=0
 for state in sorted({k[:2] for k in parts}):
  features=[]
  for code in sorted(k for k in parts if k.startswith(state)):
   g=unary_union(parts[code])
   if not g.is_valid:g=g.buffer(0)
   assert g.geom_type in ('Polygon','MultiPolygon') and g.is_valid,code
   area+=g.area
   sg=g.simplify(80,preserve_topology=True)
   assert not sg.is_empty and sg.is_valid,code
   p=transform(tr.transform,sg)
   minx,miny,maxx,maxy=p.bounds
   assert 4<minx<maxx<17 and 46<miny<maxy<56,(code,p.bounds)
   features.append({'type':'Feature','id':code,'properties':{
     'ags8':code,'county_ags5':code[:5],'state_code':state,
     'name_de':names[code],'valid_at':'2026-01-01',
     'source':'BKG_VG250_2026','part_count':len(parts[code]),
     'simplified_tolerance_m':80},'geometry':p.__geo_interface__})
  assert features,'empty 2026 federal state'
  document={'type':'FeatureCollection',
    'name':'BKG VG250 2026 municipalities DE-'+state,
    'source_url':URL,'source_sha256':SHA,
    'attribution':'© BKG (2026) dl-de/by-2-0 (see licence)',
    'status':'research_only_not_published',
    'features':features}
  target=DEST/('DE-'+state+'.geojson')
  target.write_text(json.dumps(document,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
  counts[state]=len(features);sizes[state]=target.stat().st_size
 assert sum(counts.values())==10939
 audit={'reference_date':'2026-01-01','source_sha256':SHA,
     'source_polygon_rows':len(raw),'unique_municipality_codes':len(parts),
     'features_saved':sum(counts.values()),'count_by_state':counts,
     'geojson_bytes_by_state':sizes,'geojson_total_bytes':sum(sizes.values()),
     'total_area_km2':round(area/1e6,1),'simplification_m':80,
     'code_match':'all 10939 municipality codes in independently saved 2026 official AGS census',
     'hanau_2026_independent_geometry_present':'06415000' in parts,
     'status':'research_only_not_published',
     'warning':'2026 geometry is not a 2023/2024 municipal debt map without vintage ID remapping; independent polygon simplification may leave small boundary slivers.',
     'license':'© BKG (2026) dl-de/by-2-0'}
 (OUT/'municipality_geometry_2026_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('PASS official 2026 municipality geometry',sum(counts.values()),'states',len(counts),'bytes',sum(sizes.values()))
if __name__=='__main__':main()
