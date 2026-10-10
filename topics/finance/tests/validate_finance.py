#!/usr/bin/env python3
"""Finance 08 offline regression and data provenance checks."""
from __future__ import annotations
import csv, pathlib, json, re, sys
ROOT=pathlib.Path(__file__).resolve().parents[3]
FIN=ROOT/'topics/finance'
A=ROOT/'research/finance/a'
B=ROOT/'research/finance/b'

def load(path):
 with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def check(name, expr):
 if not expr:raise AssertionError(name)
 print('PASS',name)

src=(FIN/'data/finance-data.js').read_text(encoding='utf-8')
prefix='window.GermanFinance08Data='
check('generated finance JS wrapper',prefix in src)
json_body=src.split(prefix,1)[1].rsplit(';',1)[0]
obj=json.loads(json_body)
cases=obj['cases'];maps=[r for r in cases if r['map_ready']]
check('170 cases, 72 eligible',len(cases)==170 and len(maps)==72)
check('case ids unique',len({r['id'] for r in cases})==170)
check('map candidates municipality AGS8',all(re.fullmatch(r'\d{8}',r['ags']) and r['geo_level']=='municipality' for r in maps))
check('map candidates county AGS5',all(re.fullmatch(r'\d{5}',r['county']) for r in maps))
check('no missing primary map sources',all(r['source'].startswith('https://') for r in maps))
check('map status conservative',all(r['status'] in ('effective','completed','reversed','withdrawn') for r in maps))
check('source-linked parent references',all(not r['parent'] or r['parent'] in {x['id'] for x in cases} for r in cases))
check('original cases intact',len(load(B/'cases.csv'))==170 and len(load(B/'sources.csv'))==180)
check('no new municipality coordinates',all('lat' not in r and 'lon' not in r for r in cases))
check('state metrics 13/16',len(obj['states'])==16 and len([x for x in obj['states'] if x['value'] is not None])==13)
check('city metric 12 only',len(obj['cities'])==12 and len({x['id'] for x in obj['cities']})==12)
check('no city state filled as zero',all(x['value'] is None for x in obj['states'] if x['id'] in ('DE-BE','DE-HH','DE-HB')))
check('money amount_kind preserved',all(r['amount'] is None or r['amount_kind'] for r in cases))
check('page loads its own data',"data/finance-data.js" in (FIN/'index.html').read_text())
check('stats/source language',"非县辖市" in (FIN/'index.html').read_text() and "不代表设施地址" in (FIN/'index.html').read_text())
page=(FIN/'index.html').read_text(encoding='utf-8')
app=(FIN/'topic.js').read_text(encoding='utf-8')
check('single fixed balance choropleth',all('data-mode="'+x+'"' not in page for x in ('state','rp','events')) and 'id="stateMetric"' not in page and "getMode:()=> 'balance-2025'" in app)
check('event overlays opt-in', 'id="showEvents" type="checkbox"' in page and 'showEvents:false' in app)
check('advanced research controls collapsed', '<details class="finance-drawer"' in page)
check('simplified event list and archive switch retained',all('id="'+x+'"' in page for x in ('caseList','showMapCases','showAllCases','loadMore')))
check('shared Chinese place name assets included', 'js/core/place-names-zh.js' in page and 'js/layers/city-labels.js' in page)

check('source references archived',sum(bool(r['source']) for r in maps)==72)
check('source/aggregation audit',json.loads((FIN/'data/finance-audit.json').read_text())['map_ready']==72)

# Validate against checked 2025 county AGS list when copied into packaging.
lookup=ROOT/'research/finance/a/2025_district_ids.csv'
if lookup.exists():
 ids={r['ags5'] for r in load(lookup)}
 check('all map candidates belong to 2025 county code list',all(r['county'] in ids for r in maps))

print('SUCCESS: finance data and page contract passed')
check('state drilldown and county outlines', 'zoomToState(' in app and 'renderCountyOutline()' in app)
check('event preview hover and opt-in', 'finance-event-tooltip' in app and 'id="eventPanel"' in page and 'preview(r.description)' in app)
