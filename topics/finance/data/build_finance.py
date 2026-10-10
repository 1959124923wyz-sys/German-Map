#!/usr/bin/env python3
"""Generate finance-data.js from A/B validated, original tabular handoffs.
No imputation, artificial municipality coordinates, or cross-scope aggregation.
"""
from __future__ import annotations
import csv, json, pathlib, re
ROOT = pathlib.Path(__file__).resolve().parents[3]
DATA = pathlib.Path(__file__).resolve().parent
A = ROOT / 'research/finance/a'
B = ROOT / 'research/finance/b'


def read(path):
    with open(path, newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def num(v):
    return float(v) if v not in ('', None) else None

states_all = read(A / 'state_municipal_balance_percapita_2010_2025.csv')
states = [dict(id=r['state_iso'], name=r['state_de'], value=num(r['municipal_balance_eur_per_capita']),
               year=2025, source=r['source_url']) for r in states_all if r['year'] == '2025']
assert len(states) == 16 and len({x['id'] for x in states}) == 16
assert sum(x['value'] is not None for x in states) == 13

rp_all = read(A / 'rp_regional_finance_verified_2025_2026.csv')
cities = [dict(id=r['ags5'], name=r['name_de'], value=num(r['financing_balance_per_resident_eur']),
               year=2025, source=r['source_url'],scope='non_district_city')
          for r in rp_all if r['period']=='2025-full' and r['entity_scope']=='kreisfreie_stadt']
assert len(cities)==12 and len({x['id'] for x in cities})==12

all_cases = read(B/'cases.csv'); map_cases = read(B/'cases_map_ready.csv')
assert len(all_cases)==170 and len(map_cases)==72
case_by_id = {r['event_id']: r for r in all_cases}
assert len(case_by_id)==170 and all(x['event_id'] in case_by_id for x in map_cases)
base_ids = {x['event_id'] for x in map_cases}
assert len(base_ids)==72
valid_status={'effective','completed','reversed','withdrawn','adopted','announced','proposed','rejected','under_review'}


def category(row):
    typ=row['event_type'].lower()
    if any(x in typ for x in ('pool','swimming','library','adult_education','public_facility','cultural_facility','classroom','culture','cultural')):
        return 'facilities'
    if any(x in typ for x in ('transit','bus','transport','traffic')): return 'transit'
    if 'investment' in typ or 'road_work' in typ or 'fire_brigade' in typ: return 'investment'
    if any(x in typ for x in ('staff','personnel','recruitment','vacancy')): return 'staffing'
    if any(x in typ for x in ('tax','fee','price')): return 'taxfees'
    if any(x in typ for x in ('budget','supervis','credit_limit','grant','social','financ')): return 'budget'
    return 'other'


def safe_url(s):
    return s if re.match(r'^https://[^\s<>]+$',s or '') else ''

cases=[]
for row in all_cases:
    eid=row['event_id']; ismap=eid in base_ids
    ags=row['ags'].strip(); county=row['county_key'].strip() or (ags[:5] if ags else '')
    if ismap:
        assert row['geo_level']=='municipality' and re.fullmatch(r'\d{8}',ags)
        assert re.fullmatch(r'\d{5}',county)
        assert row['status'] in {'effective','completed','reversed','withdrawn'}
    assert row['status'] in valid_status
    cases.append(dict(id=eid, state=row['state'], city=row['municipality'], ags=ags,
        county=county, geo_level=row['geo_level'], type=row['event_type'],
        category=category(row), status=row['status'], map_ready=ismap,
        decision=row['decision_date'], effective=row['effective_date'],
        facility=row['facility_name'], amount=num(row['amount_eur']), amount_kind=row['amount_kind'],
        description=row['description_zh'], note=row['notes'], parent=row['parent_event_id'],
        source=safe_url(row['primary_source_url']), source2=safe_url(row['secondary_source_url']),
        verified=row['last_verified'], source_page=row['source_page']))

obj = dict(meta=dict(as_of='2026-10-09', states_total=16, state_available=13,
                     city_available=12, all_cases=170, map_ready=72,
                     state_scope='non_city_states_municipal_core_plus_extra',
                     city_scope='rheinland_pfalz_12_kreisfreie_staedte_cash_financing_balance',
                     case_scope='selected_source_linked_case_archive_not_population_representative'),
           states=states,cities=cities,cases=cases)
DATA.joinpath('finance-data.js').write_text('/* Generated. Do not edit manually; see build_finance.py. */\nwindow.GermanFinance08Data='+json.dumps(obj,ensure_ascii=False,separators=(',',':'),allow_nan=False)+';\n',encoding='utf-8')
DATA.joinpath('finance-audit.json').write_text(json.dumps({
    'all_cases':len(cases),'map_ready':sum(x['map_ready'] for x in cases),
    'states_with_data':sum(x['value'] is not None for x in states),
    'rp_city_rows':len(cities),
    'map_counties':len({x['county'] for x in cases if x['map_ready']}),
    'all_case_status':{s:sum(x['status']==s for x in cases) for s in sorted(valid_status)},
    'missing_primary_sources':sum(not x['source'] for x in cases if x['map_ready']),
    'notes':'地图事件均是县域中心的汇总锚点，不是设施精准坐标。'
},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('built',len(states),'states',len(cities),'cities',len(cases),'cases',len(base_ids),'map candidates')
if __name__ == '__main__': pass