#!/usr/bin/env python3
"""Regression test for staged, not yet production-joined, finance data."""
from pathlib import Path
import sys,csv,json,collections
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE))
import build_research
root=BASE/'source';derive=BASE/'derived'
def rows(path):
 with path.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
assert len(rows(derive/'district_debt_2025_qa_only.csv'))==58
D=rows(derive/'district_debt_2025_qa_only.csv')
assert len({r['ags5'] for r in D})==58
assert all(r['comparison_status']=='not_cross_state_comparable' for r in D)
assert len([r for r in D if r['value_eur_percap']])==42
assert all(r['value_eur_percap']!='0' for r in D if r['quality_flag']=='published_dash_not_numeric_zero')
assert all(r['geo_code_status'].startswith('ags5_matches_derived') for r in D)
P=rows(root/'bavaria_planning_regions_debt_2024_2025.csv')
assert all(r['join_warning']=='DO_NOT_JOIN_COUNTY_BOUNDARY' for r in P)
C=rows(root/'major_city_primary_finance_2024_2026.csv')
assert len(C)==20 and len({c['ags5'] for c in C})==8
assert all(c['source_url'].startswith('https://') for c in C)
assert all(c['metric_id'] not in ('municipal_finance_risk_score','national_county_core_deficit') for c in C)
assert all('forecast' in c['release_status'] for c in C if c['metric_id'].endswith('_forecast'))
# Essen 2025 has net +1.1m AND ordinary -73.8m, not a contradiction.
essen={(x['metric_id'],x['value_eur']) for x in C if x['ags5']=='05113' and x['reference_year']=='2025'}
assert ('annual_financial_result','1100000') in essen and ('ordinary_financial_result','-73800000') in essen
# Frankfurt 2025 group and city figures remain explicitly different.
fr=[r for r in C if r['ags5']=='06412' and r['reference_year']=='2025']
assert any(r['metric_id']=='consolidated_group_result' for r in fr)
assert any(r['metric_id']=='annual_financial_result' for r in fr)
S=json.loads((derive/'quality_audit.json').read_text(encoding='utf-8'))
assert (S['district_candidates_2025_total'],S['district_candidates_numeric_percap'],S['ungocoded_local_debt_rows'],S['bavaria_planning_regions'],S['major_city_metrics'])==(58,42,32,18,20)
assert S['numeric_records_eligible_for_nationwide_choropleth']==0
print('PASS: finance regional expansion 17+ integrity, scope and comparison assertions')
