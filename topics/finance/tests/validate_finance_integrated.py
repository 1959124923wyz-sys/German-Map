#!/usr/bin/env python3
"""Finance 08 integrated debt: defensible mapping and source regression checks."""
import csv
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / 'topics/finance/data/build_finance_integrated.py'
RAW = ROOT / 'research/finance/a/integrated_municipal_debt_states_2022_2024.csv'
OUT = ROOT / 'topics/finance/data/finance-integrated.js'
assert SCRIPT.is_file() and RAW.is_file() and OUT.is_file()
s = OUT.read_text(encoding='utf-8')
data = json.loads(s.split('window.GermanFinance08Integrated=', 1)[1].rstrip(' \n;'))
rows = list(csv.DictReader(RAW.open(encoding='utf-8-sig', newline='')))
assert len(rows) == 48 and len(data['states']) == 16
states = {x['id']: x for x in data['states']}
assert len(states) == 16
for year in ('2022', '2023', '2024'):
    actual = [s['per_capita_eur'][year] for s in states.values()]
    assert len([x for x in actual if x is not None]) == 13
    for city_state in ('DE-BE', 'DE-HB', 'DE-HH'):
        assert states[city_state]['per_capita_eur'][year] is None
    for x in rows:
        if x['year'] == year and x['integrated_debt_eur_per_capita']:
            assert states[x['iso_state']]['per_capita_eur'][year] == int(x['integrated_debt_eur_per_capita'])
assert states['DE-HE']['per_capita_eur']['2024'] == 6291
assert states['DE-BB']['per_capita_eur']['2024'] == 2587
assert '1001 million' in data['meta']['limits']
page = (ROOT / 'topics/finance/index.html').read_text(encoding='utf-8')
assert 'finance-integrated.js' in page and 'id="stateMetric"' in page
script = (ROOT / 'topics/finance/topic.js').read_text(encoding='utf-8')
assert 'GermanFinance08Integrated' in script and 'stateMetric' in script
print('PASS: 16 state codes, 39 observations, no fabricated city-state debt, official values/source, UI references')