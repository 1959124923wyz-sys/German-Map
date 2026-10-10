#!/usr/bin/env python3
"""Finance 08 R9 data and UX contract regression test."""
from __future__ import annotations
import csv
import json
import pathlib
import re
ROOT=pathlib.Path(__file__).resolve().parents[3]
FIN=ROOT/'topics/finance'
A=ROOT/'research/finance/a'
js=(FIN/'data/finance-history.js').read_text(encoding='utf-8')
prefix='window.GermanFinance08History='
assert js.startswith('/*') and prefix in js
h=json.loads(js.split(prefix,1)[1].rsplit(';',1)[0])
assert h['meta']['debt_unit']=='million_eur'
assert h['meta']['regional_scope']=='city_budget_or_county_budget_only_not_combined'
assert h['meta']['years']==[2021,2022,2023,2024,2025]
assert len(h['states'])==13 and len({r['id'] for r in h['states']})==13
assert all(len(r['cash'])==len(r['investment'])==5 for r in h['states'])
assert all(v>=0 for r in h['states'] for v in (r['cash']+r['investment']))
for key in ('cash','investment'):
 assert h['totals'][key]==[sum(r[key][i] for r in h['states']) for i in range(5)]
assert h['totals']['cash']==[29461,28109,28960,31789,38587]
assert h['totals']['investment']==[100520,109124,122021,134808,155136]
with (A/'state_municipal_loans_2021_2025.csv').open(encoding='utf-8-sig',newline='') as f:
 loans=list(csv.DictReader(f))
assert len(loans)==160
assert len([x for x in loans if x['debt_million_eur']])==130
regional=h['regional']
assert len(regional)==72
assert len({(x['id'],x['period'],x['scope']) for x in regional})==72
assert all(re.fullmatch(r'\d{5}',x['id']) and x['source'].startswith('https://www.statistik.rlp.de/') for x in regional)
assert all(abs(x['balance_eur']-x['operating_eur']-x['capital_eur'])<=250 for x in regional)
for period in ('2025-H1','2026-H1'):
 rows=[x for x in regional if x['period']==period]
 assert len(rows)==36
 assert sum(x['scope']=='city' for x in rows)==12
 assert sum(x['scope']=='county_budget_only' for x in rows)==24
 assert not any(x['scope']=='county_budget_only' and x['value'] is None for x in rows)
assert all(x['value']<0 for x in regional if x['period']=='2026-H1' and x['scope']=='city')
with (A/'rp_regional_finance_verified_2025_2026.csv').open(encoding='utf-8-sig',newline='') as f:
 original=list(csv.DictReader(f))
assert len(original)==84
assert len([r for r in original if r['period']=='2025-full'])==12
page=(FIN/'index.html').read_text(encoding='utf-8')
logic=(FIN/'topic.js').read_text(encoding='utf-8')
for frag in ('data/finance-history.js','id="rpPeriod"','id="loanDrawer"','id="loanHistory"','id="loanScope"','2026-H1-counties'):
 assert frag in page,frag
for frag in ('H.totals','regionalRow(', 'regionOptions[view.rpPeriod]', "row.operating_eur", 'renderLoanHistory(id)'):
 assert frag in logic,frag
assert '县政府本级预算' in logic and '全年与半年不可直接比较' in logic
assert 'buildMapLayers()' in logic and 'countiesLayer=L.geoJSON(countyGeo' in logic
assert 'renderMap();' in logic and 'zoomToState(' in logic and 'stateMetric' not in logic
assert "for(const f of cf.features){const lyr=L.geoJSON(f)" not in logic

print('PASS Finance 08 history: 130 debt values, 72 RLP half-year rows, four scoped selections, source and UI contracts')
