#!/usr/bin/env python3
"""Build research-only BKG 2025 county polygon GeoJSON from SHA-pinned official VG250.

Requires shapely>=2, pyproj>=3 on CI. Output coordinates WGS84 GeoJSON and
a geometry audit; no website changes. Note 2025 boundaries exclude Jan-2026
Hanau district-free split, which MUST be separately handled for 2026 mapping.
"""
from __future__ import annotations
import collections,csv,hashlib,json,re,sqlite3,urllib.request,zipfile
from pathlib import Path
from shapely import wkb
from shapely.ops import transform,unary_union
from pyproj import Transformer

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'derived/bkg2025'
OUT.mkdir(parents=True,exist_ok=True)
TMP=Path('/tmp/finance08-bkg-geo2025')
TMP.mkdir(parents=True,exist_ok=True)
URL='https://daten.gdz.bkg.bund.de/produkte/vg/vg250_ebenen_1231/aktuell/vg250_12-31.utm32s.gpkg.ebenen.zip'
PINNED_SHA='df71d6a7ec0a0ca38e0559d9a90523a81c7948c74e7c7c3ddeab79041d1046f5'
ENV_BYTES={0:0,1:32,2:48,3:48,4:64}

def parse_gpkg_geom(blob):
 if not blob or blob[:2]!=b'GP':raise ValueError('invalid GeoPackage geometry header')
 flags=blob[3]
 envelope=(flags>>1)&7
 if envelope not in ENV_BYTES:raise ValueError('unsupported GPKG envelope')
 return wkb.loads(blob[8+ENV_BYTES[envelope]:])

def download():
 req=urllib.request.Request(URL,headers={'User-Agent':'Mozilla/5.0 GermanMapFinanceResearch'})
 with urllib.request.urlopen(req,timeout=240) as r:data=r.read()
 got=hashlib.sha256(data).hexdigest()
 if got!=PINNED_SHA:raise ValueError('BKG official package checksum changed, stop: '+got)
 zpath=TMP/'bkg2025_original.zip';zpath.write_bytes(data)
 with zipfile.ZipFile(zpath) as z:
  gp=[n for n in z.namelist() if n.endswith('.gpkg')]
  if len(gp)!=1:raise ValueError('unexpected GeoPackage entries: '+str(gp))
  target=TMP/'bkg2025.gpkg'
  with z.open(gp[0]) as src,target.open('wb') as dest:
   while block:=src.read(8*1024*1024):dest.write(block)
 return target,len(data)

def main():
 db,size=download()
 conn=sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True)
 # Physical county features, not the similarly named v_vg250_krs virtual view.
 q=conn.execute('SELECT column_name,srs_id FROM gpkg_geometry_columns WHERE table_name=?',('vg250_krs',)).fetchone()
 assert q,q
 geom_col,srs=q
 assert srs in (25832,32632),'Unexpected BKG projection, inspect before conversion: '+str(srs)
 code_cols=[a[1] for a in conn.execute('PRAGMA table_info("vg250_krs")')]
 assert 'AGS' in code_cols and 'GEN' in code_cols
 rows=conn.execute('SELECT "AGS","GEN","'+geom_col+'" FROM "vg250_krs"').fetchall()
 conn.close()
 assert len(rows)==433,len(rows)
 groups=collections.defaultdict(list)
 names={}
 for code,name,blob in rows:
  code=str(code).strip()
  assert re.fullmatch(r'\d{5}',code),code
  polygon=parse_gpkg_geom(blob)
  assert polygon.geom_type in ('Polygon','MultiPolygon') and not polygon.is_empty,(code,polygon.geom_type)
  groups[code].append(polygon)
  if name and code not in names:names[code]=str(name).strip()
 assert len(groups)==400,len(groups)
 with (ROOT/'derived/official_atlas_municipalities_2025_ags.csv').open(encoding='utf-8-sig',newline='') as f:
  atlas_parents={r['ags8'][:5] for r in csv.DictReader(f)}
 assert set(groups)==atlas_parents,('2025 Atlas/BKG county key mismatch',sorted(set(groups)^atlas_parents))
 transformer=Transformer.from_crs('EPSG:'+str(srs),'EPSG:4326',always_xy=True)
 total_raw_area=0
 total_simple_area=0
 features=[]
 for code in sorted(groups):
  g=unary_union(groups[code])
  if not g.is_valid:g=g.buffer(0)
  assert g.geom_type in ('Polygon','MultiPolygon') and g.is_valid,(code,g.geom_type)
  original_area=g.area
  # Source is projected in metres. No simplification greater than 125 m.
  simplified=g.simplify(125,preserve_topology=True)
  assert not simplified.is_empty and simplified.is_valid
  total_raw_area+=original_area
  total_simple_area+=simplified.area
  projected=transform(transformer.transform,simplified)
  minx,miny,maxx,maxy=projected.bounds
  assert 4<minx<maxx<17 and 46<miny<maxy<56,(code,projected.bounds)
  geo=projected.__geo_interface__
  features.append({'type':'Feature','id':code,'properties':{
    'ags5':code,'name_de':names.get(code,''),'state_code':code[:2],
    'reference_date':'2025-12-31','geometry_pieces':len(groups[code]),
    'source':'BKG_VG250_2025','generalized_geometry':True,
    'geometry_simplification_m':125},'geometry':geo})
 assert 300000<total_raw_area/1e6<420000,('Germany area estimate unexpectedly outside range',total_raw_area/1e6)
 doc={'type':'FeatureCollection','name':'BKG VG250 county boundaries 2025-12-31 simplified 125 m',
      'source_url':URL,'source_sha256':PINNED_SHA,
      'attribution':'© BKG (2026) dl-de/by-2-0, https://www.bkg.bund.de , https://www.govdata.de/dl-de/by-2-0',
      'geometry_year':2025,'geography_status':'verified_2025_not_valid_for_all_2026_changes',
      'features':features}
 dst=OUT/'county_boundaries_2025_simplified.geojson'
 dst.write_text(json.dumps(doc,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
 audit={'source_sha256':PINNED_SHA,'source_zip_bytes':size,'reference_date':'2025-12-31',
        'gpkg_srs_id':srs,'source_polygon_rows':len(rows),'unique_county_ags5':len(groups),
        'features_geojson':len(features),'raw_county_area_km2':round(total_raw_area/1e6,1),
        'simplified_area_km2':round(total_simple_area/1e6,1),
        'simplification_tolerance_m':125,'created_map_payload_bytes':dst.stat().st_size,
        'hanau_2026_handling':'2025-12-31 geometry keeps Hanau under Main-Kinzig-Kreis 06435; 2026 district-free Hanau 06415 missing',
        'status':'research_only_not_published','license':'© BKG (2026) dl-de/by-2-0'}
 (OUT/'county_geometry_2025_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('PASS: BKG 2025 400 county polygons',len(rows),'source parts, GeoJSON bytes',dst.stat().st_size)
if __name__=='__main__':main()
