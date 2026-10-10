#!/usr/bin/env python3
"""Convert the Destatis 2022–2024 state-level integrated MUNICIPAL debt table.

Separate dataset and metric. Do not mix with 2025 municipality financing flows or
ordinary cash/investment loan stock. City-states are genuinely NOT APPLICABLE.
The publication's 2024 national total conflicts with the displayed state rows;
this pipeline deliberately does not derive or display a national euro total.
"""
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / 'research/finance/a/integrated_municipal_debt_states_2022_2024.csv'
DEST = Path(__file__).with_name('finance-integrated.js')
SOURCE_URL = ('https://www.destatis.de/DE/Themen/Staat/Oeffentliche-Finanzen/'
              'Schulden-Finanzvermoegen/Tabellen/liste-vierteljaehrlichen-schulden.html')

with SRC.open(encoding='utf-8-sig', newline='') as handle:
    source = list(csv.DictReader(handle))
assert len(source) == 48
assert Counter(r['year'] for r in source) == {'2022': 16, '2023': 16, '2024': 16}
assert len({(r['iso_state'], r['year']) for r in source}) == 48

states = {}
for row in source:
    code, year = row['iso_state'], row['year']
    assert row['source_url'].startswith('https://www.destatis.de/')
    if code not in states:
        states[code] = {'id': code, 'name': row['state_name_de'], 'per_capita_eur': {}, 'total_million_eur': {}}
    record = states[code]
    if code in ('DE-BE', 'DE-HB', 'DE-HH'):
        assert row['value_status'] == 'not_applicable_city_state'
        assert row['integrated_debt_eur_per_capita'] == row['integrated_debt_million_eur'] == ''
        record['per_capita_eur'][year] = None
        record['total_million_eur'][year] = None
        continue
    assert row['value_status'] == 'verified_in_indexed_official_html'
    assert row['integrated_debt_eur_per_capita'].isdigit()
    assert row['integrated_debt_million_eur'].isdigit()
    record['per_capita_eur'][year] = int(row['integrated_debt_eur_per_capita'])
    record['total_million_eur'][year] = int(row['integrated_debt_million_eur'])

assert len(states) == 16
assert all(len(x['per_capita_eur']) == len(x['total_million_eur']) == 3 for x in states.values())
assert sum(v['per_capita_eur']['2024'] is not None for v in states.values()) == 13
assert states['DE-HE']['per_capita_eur']['2024'] == 6291
assert states['DE-SL']['per_capita_eur']['2024'] == 6100
assert states['DE-NW']['per_capita_eur']['2024'] == 5271
assert states['DE-BB']['per_capita_eur']['2024'] == 2587
assert sum(v['total_million_eur']['2024'] or 0 for v in states.values()) == 343762
assert sum(v['total_million_eur']['2023'] or 0 for v in states.values()) == 322906

payload = {
    'meta': {
        'years': [2022, 2023, 2024],
        'scope': 'integrated_municipal_debt_to_non_public_sector_including_modelled_affiliates',
        'geography': '13_non_city_states',
        'unit': 'euro_per_capita',
        'source': SOURCE_URL,
        'as_of': '2026-10-10',
        'limits': ('City-states are not municipal units in this Destatis series. '
                   'The 2023 and 2024 population denominators are based on different census vintages; '
                   'per-capita differences are descriptive, not an official change rate. '
                   'Do not sum the 2024 state debt totals to claim a reconciled national figure: '
                   'published national table total differs from its own 13 state totals by 1001 million EUR.'),
    },
    'states': [states[k] for k in sorted(states)],
}
DEST.write_text('/* Official Destatis state integrated municipal debt; generated file. */\n'
                'window.GermanFinance08Integrated=' + json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + ';\n',
                encoding='utf-8')
print('Generated', DEST, '16 state codes / 39 numeric state-year records / 9 N/A')