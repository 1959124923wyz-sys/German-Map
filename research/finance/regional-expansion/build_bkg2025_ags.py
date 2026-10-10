#!/usr/bin/env python3
"""Validate BKG 31.12.2025 AGS against finance data; geography research only."""
import csv,hashlib,json,re,sqlite3,urllib.request,zipfile
from pathlib import Path
from collections import Counter
BASE=Path(__file__).resolve().parent
OUT=BASE/'derived/bkg2025';OUT.mkdir(parents=True,exist_ok=True)
TMP=Path('/tmp/finance08-bkg-2025');TMP.mkdir(exist_ok=True)
URL='https://daten.gdz.bkg.bund.de/produkte/vg/vg250_ebenen_1231/aktuell/'
NAME='vg250_12-31.utm32s.gpkg.ebenen.zip'
# Published BKG MD5 observed from official directory on 2026-10-10.
PINNED_MD5='e6b4cf28d4b83557b4d6e3236713dec0'
def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 FinanceMapResearch'})
    with urllib.request.urlopen(req,timeout=180) as r:return r.read()
def ids(path,col):
    with path.open(encoding='utf-8-sig',newline='') as f:return {r[col] for r in csv.DictReader(f)}
def main():
    md5text=get(URL+NAME+'.md5').decode('utf-8')
    wanted=re.search(r'\b[0-9a-fA-F]{32}\b',md5text)
    assert wanted,md5text
    assert wanted.group().lower()==PINNED_MD5,'BKG upstream source changed; re-verify date and update provenance before parsing'
    data=get(URL+NAME)
    assert hashlib.md5(data).hexdigest()==wanted.group().lower(),'official BKG MD5 mismatch'
    p=TMP/NAME;p.write_bytes(data)
    with zipfile.ZipFile(p) as z:
        gp=[n for n in z.namelist() if n.lower().endswith('.gpkg')]
        assert len(gp)==1,gp
        dest=TMP/'official.gpkg'
        with z.open(gp[0]) as a,dest.open('wb') as b:
            while part:=a.read(8*1024*1024):b.write(part)
    c=sqlite3.connect('file:'+str(dest)+'?mode=ro',uri=True)
    candidates=c.execute("SELECT table_name FROM gpkg_contents WHERE data_type='features'").fetchall()
    names=[x[0] for x in candidates if x[0].upper().endswith('_KRS')]
    assert len(names)==1,(candidates,names)
    tab=names[0]
    columns=[x[1] for x in c.execute('PRAGMA table_info("'+tab+'")')]
    code=next((x for x in columns if x.upper()=='AGS'),None)
    name=next((x for x in columns if x.upper()=='GEN'),None)
    assert code and name,columns
    content=c.execute('SELECT "'+code+'","'+name+'" FROM "'+tab+'"').fetchall()
    c.close()
    geo={}
    pieces=Counter()
    for a,n in content:
        k=str(a).strip()
        assert re.fullmatch(r'\d{5}',k),k
        geo[k]=n
        pieces[k]+=1
    assert len(geo)==400,('2025 official county count',len(geo))
    records=[{'ags5':k,'name_de':geo[k],'state_code':k[:2],
              'geometry_parts':pieces[k],'valid_at':'2025-12-31',
              'source_id':'BKG_VG250_2025'} for k in sorted(geo)]
    with (OUT/'official_counties_2025_ags.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    older=ids(BASE/'derived/county_cash_credits_2023.csv','ags5')
    derived=ids(BASE/'source/district_ids_2025_derived_for_qc_only.csv','ags5')
    parents=set()
    for csvpath in sorted((BASE/'derived/integrated_debt_2024_by_state').glob('DE-*.csv')):
        with csvpath.open(encoding='utf-8',newline='') as f:
            parents.update(r['county_ags5'] for r in csv.DictReader(f) if r['reporting_unit_class']=='municipality')
    current=set(geo)
    with (BASE/'derived/official_atlas_municipalities_2025_ags.csv').open(encoding='utf-8-sig',newline='') as f:
        current_municipality_county_parents={r['ags8'][:5] for r in csv.DictReader(f)}
    assert len(current_municipality_county_parents)==400,'unexpected 2025 municipality roster parent count'
    audit={'boundary_date':'2025-12-31','download_url':URL+NAME,
           'official_md5_url':URL+NAME+'.md5','official_md5':wanted.group().lower(),
           'zip_sha256':hashlib.sha256(data).hexdigest(),'source_bytes':len(data),
           'county_geometry_rows':len(content),'official_ags5_count':len(geo),
           'official_2025_municipality_parent_count':len(current_municipality_county_parents),
           '2025_atlas_parents_missing_from_bkg':sorted(current_municipality_county_parents-current),
           '2025_bkg_counties_missing_from_atlas_parents':sorted(current-current_municipality_county_parents),
           'by_state':dict(sorted(Counter(k[:2] for k in current).items())),
           'old_2023_count':len(older),'old_2023_missing_from_2025':sorted(older-current),
           'new_since_2023':sorted(current-older),'derived_2025_ags_count':len(derived),
           'derived_2025_missing_official':sorted(derived-current),
           'official_2025_missing_derived':sorted(current-derived),
           'municipality_2024_parent_count':len(parents),
           'municipality_2024_parent_missing_2025_polygon':sorted(parents-current),
           'geometry_extracted':False,'published_on_map':False,
           'license':'dl-de/by-2-0; credit BKG and original sources'}
    # Source equality is required before using the result as an official county boundary index.
    audit['atlas_county_codes_all_match_bkg']=(current==current_municipality_county_parents)
    (OUT/'official_counties_2025_audit.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('PASS BKG official 2025 county AGS',len(current),'geometries',len(content))
    print('R13 audit:',json.dumps({k:v for k,v in audit.items() if 'missing' in k or k in ('by_state','new_since_2023')},ensure_ascii=False))
if __name__=='__main__':main()
