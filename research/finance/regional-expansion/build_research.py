#!/usr/bin/env python3
"""Make QA-only, deliberately NON-harmonized federal/local finance research tables.

No production frontend output.  No geocoordinate synthesis.  Stdlib Python only.
"""
from __future__ import annotations
from pathlib import Path
import csv,collections,json
ROOT=Path(__file__).resolve().parent
SRC=ROOT/'source'
OUT=ROOT/'derived'
OUT.mkdir(exist_ok=True)

def load(name):
    with (SRC/name).open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def write(name,rows,fields):
    with (OUT/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows)
state_iso={'Thüringen':'DE-TH','Rheinland-Pfalz':'DE-RP','Schleswig-Holstein':'DE-SH',
           'Hessen':'DE-HE','Nordrhein-Westfalen':'DE-NW','Niedersachsen':'DE-NI'}
districts=load('district_debt_2025_mixed_scope.csv')
known={r['ags5'] for r in load('district_ids_2025_derived_for_qc_only.csv')}
assert len(known)==400, f'expected derived-only candidate roster of 400, got {len(known)}'
assert len(districts)==58 and len({x['ags5'] for x in districts})==58
out=[]
for x in districts:
    assert x['ags5'] in known
    assert x['year']=='2025'
    assert x['harmonized_national_metric']=='no'
    val=x['value_eur_percap']
    if val: assert val.isdigit()
    out.append(dict(ags5=x['ags5'],name_de=x['name_de'],state_iso=state_iso[x['state']],year='2025',
       metric_id='municipal_debt_eur_percap',value_eur_percap=val,
       series_id=x['series_id'],boundary_meaning=x['boundary_type'],
       comparison_status='not_cross_state_comparable',quality_flag=x['quality_flag'],
       geo_code_status='ags5_matches_derived_2025_roster_not_official_geometry_validation',
       source_url=x['source_url']))
write('district_debt_2025_qa_only.csv',out,list(out[0]))
assert sum(bool(x['value_eur_percap']) for x in out)==42
selected=load('selected_local_debt_2025_ungeocoded.csv')
assert len(selected)==32
assert all(not r['ags5_or_ags8'] for r in selected)
# Retain original 32 rows; never fabricate county IDs from ambiguous names.
bavaria=load('bavaria_planning_regions_debt_2024_2025.csv')
assert len(bavaria)==18 and len({r['planning_region_id'] for r in bavaria})==18
assert all(r['join_warning']=='DO_NOT_JOIN_COUNTY_BOUNDARY' for r in bavaria)
city=load('major_city_primary_finance_2024_2026.csv')
assert len(city)>=20
assert all(c['source_url'].startswith('https://') for c in city)
assert all(c['ags5'] in known for c in city)
assert len({(c['ags5'],c['reference_year'],c['period'],c['metric_id'],c['scope']) for c in city})==len(city)
assert all(c['comparison_status']=='single_entity_only' for c in city)
assert all('forecast' in r['release_status'] and 'projection' in r['scope'] for r in city if 'forecast' in r['metric_id'])
rp=load('rp_12_cities_2025_balance_debt.csv');assert len(rp)==12
half=load('rp_36_areas_h1_delta_2025_2026.csv');assert len(half)==36
assert len({r['ags5'] for r in half})==36
assert {r['ags5'] for r in rp}.issubset({r['ags5'] for r in half})
# Avoid falsely counting user-entered 12 RP joins as 12 additional independent districts.
coverage=[]
state_iso_2025=['DE-SH','DE-HH','DE-NI','DE-HB','DE-NW','DE-HE','DE-RP','DE-BW',
  'DE-BY','DE-SL','DE-BE','DE-BB','DE-MV','DE-SN','DE-ST','DE-TH']
for state in state_iso_2025:
    dr=[r for r in out if r['state_iso']==state]
    sr=[r for r in selected if state_iso[r['state']]==state]
    cr=[r for r in city if r['state_iso']==state]
    coverage.append(dict(state_iso=state,district_rows=len(dr),district_rows_with_numeric_percap=sum(bool(r['value_eur_percap']) for r in dr),
       additional_ungocoded_local_rows=len(sr),big_city_primary_metrics=len(cr),
       direct_production_choropleth='false',reason='different_scopes_and_partial_coverage'))
write('coverage_by_state.csv',coverage,list(coverage[0]))
assert sum(int(r['district_rows']) for r in coverage)==58
assert sum(int(r['district_rows_with_numeric_percap']) for r in coverage)==42
assert sum(int(r['additional_ungocoded_local_rows']) for r in coverage)==32
assert sum(int(r['big_city_primary_metrics']) for r in coverage)==len(city)
summary={
 'build_version':'2026-10-10-r11',
 'district_candidates_2025_total':len(out),
 'district_candidates_numeric_percap':42,
 'district_candidates_nonnumeric':16,
 'district_candidates_by_state':dict(collections.Counter(r['state_iso'] for r in out)),
 'ungocoded_local_debt_rows':len(selected),
 'bavaria_planning_regions':len(bavaria),
 'rp_city_debt_balance_join':len(rp),
 'rp_areas_2025H1_2026H1_comparison':len(half),
 'major_city_metrics':len(city),
 'major_city_unique_entities':len({r['ags5'] for r in city}),
 'independent_city_entities':len({r['ags5'] for r in city if r['entity_role']=='independent_city'}),
 'county_region_entities':len({r['ags5'] for r in city if r['entity_role']=='county_region_admin'}),
 'official_bulk_source_registry':len(load('national_official_bulk_inventory.csv')),
 'numeric_records_eligible_for_nationwide_choropleth':0,
 'notes':['No national county harmonization. Counts are dataset records, not independent cities or full coverage.','AGS roster is a 2025 derived QA index, NOT certified current geometry.', 'The 32 un-geocoded records are NOT plotted.','Bavarian planning region figures are NOT county aggregates.', 'The nationwide 2024 integrated XLSX remains un-ingested.']
}
(OUT/'quality_audit.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
