#!/usr/bin/env python3
"""R16 integrity tests: 2023 official integrated debt + cross-year unit identities.
No maps, no automatic risk rankings, no cross-scope sums."""
from __future__ import annotations
from pathlib import Path
from collections import Counter
import csv,json,re
ROOT=Path(__file__).resolve().parents[1]/'derived'
def read(path):
 with path.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
old=[r for p in sorted((ROOT/'integrated_debt_2024_by_state').glob('DE-*.csv')) for r in read(p)]
now=[r for p in sorted((ROOT/'integrated_debt_2023_by_state').glob('DE-*.csv')) for r in read(p)]
assert len(now)==11896 and len(old)==11874,(len(now),len(old))
assert Counter(r['reporting_unit_class'] for r in now)=={'municipality':10771,'county_administration':294,'joint_administration':831}
assert all(re.fullmatch(r'\d{5}|\d{9}|\d{12}',r['original_region_key']) for r in now)
assert all(r['report_year']=='2023' and r['source_id']=='STATISTIKPORTAL_INTEGRATED_2023_T1' for r in now)
assert all(r['population_2023_06_30'].isdigit() for r in now)
assert all(float(r['total_integrated_debt_eur'])>=0 and float(r['integrated_debt_eur_per_person'])>=0 for r in now)
keys={r['original_region_key'] for r in now}
assert len(keys)==len(now)
old_keys={r['original_region_key'] for r in old}
audit=json.loads((ROOT/'integrated_2023/integrated_2023_vs_2024_entity_audit.json').read_text(encoding='utf-8'))
source=json.loads((ROOT/'integrated_2023/source_2023_download.json').read_text(encoding='utf-8'))
assert source['sha256']=='af5b3e0ff66cd30f7566721028e57374bce2bffd1b1cb0fe3a870344b3bb53d0'
assert (len(keys&old_keys),len(keys-old_keys),len(old_keys-keys))==(11867,29,7)
assert (audit['matched_reporting_units_stable_2023_2024'],audit['in_2023_not_in_2024_count'],audit['in_2024_not_in_2023_count'])==(11867,29,7)
assert len({r['state_code'] for r in now})==13
# A matched code is not a certification of comparable debt and census denominator.
assert audit['status']=='research_only_not_published'
assert audit['year_comparison_warning']
print('PASS 2023 national integrated debt: 11,896 units; 10,771 municipalities; 294 county budgets; 831 joint administrations')
print('PASS 2023/2024 immutable region key overlap 11,867; 2023-only 29; 2024-only 7 (not a debt-level comparison)')
