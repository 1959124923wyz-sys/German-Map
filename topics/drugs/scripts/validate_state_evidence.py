#!/usr/bin/env python3
"""Validate 2025 drug-related state evidence and prevent common map-data traps.

Do not infer missing state figures. A blank substance/PKS code is NOT zero.
PKS generic offence, trade, and KCanG subsection totals must not be summed
without checking that their scopes are non-overlapping.
"""
from __future__ import annotations
import json
from pathlib import Path

BASE=Path(__file__).resolve().parents[3]
EVIDENCE=BASE/"topics/drugs/data/state_health_offences_2025.json"
STATE_GEO=BASE/"data/germany-states.geojson"

def ok(condition, message):
    if not condition:
        raise AssertionError(message)

def validate():
    data=json.loads(EVIDENCE.read_text(encoding="utf-8"))
    states={f["properties"]["name"] for f in json.loads(STATE_GEO.read_text(encoding="utf-8"))["features"]}
    ok(len(states)==16,"Unexpected Germany state geometry set")
    ok(data["meta"]["year"]==2025,"Wrong statistical year")
    deaths=data["mortality_by_state"]
    offences=data["selected_offence_codes_by_state"]
    health=data.get("other_health_indicators_by_state",{})
    ok(set(deaths)<=states,"Mortality recorded under unknown state: "+str(set(deaths)-states))
    ok(set(offences)<=states,"PKS offence recorded under unknown state: "+str(set(offences)-states))
    ok(set(health)<=states,"Health record for unknown state: "+str(set(health)-states))
    ok(data["meta"]["mortality_coverage_states"]==len(deaths),"Outdated death coverage metadata")
    ok(data["meta"]["drug_specific_offence_coverage_states"]==len(offences),"Outdated offence coverage metadata")
    ok(data["meta"]["health_case_coverage_states"]==len(health),"Outdated health coverage metadata")
    for state,entry in deaths.items():
        ok(type(entry.get("cases")) is int and entry["cases"]>=0, state+" invalid death count")
        ok(entry.get("source_url","").startswith("https://"),state+" missing death original")
        prev=entry.get("previous_2024")
        ok(prev is None or (type(prev) is int and prev>=0),state+" previous deaths")
        rate=entry.get("rate_per_100k")
        ok(rate is None or (isinstance(rate,(float,int)) and rate>=0),state+" invalid death rate")
    for state,entry in offences.items():
        ok(entry.get("source_type") in {"state_police","state_government"},
           state+" group data not from primary state authority")
        ok(entry.get("source_url","").startswith("https://"),state+" missing PKS source")
        groups=entry.get("groups",[])
        more=entry.get("additional_metrics",[])
        ok(groups or more,state+" has no offence counts")
        keys=set()
        for row in groups:
            for field in ("general","trade"):
                ok(type(row.get(field)) is int and row[field]>=0,state+" "+field+" invalid")
            ok(row.get("name") and row["name"] not in keys,state+" duplicate PKS substance")
            keys.add(row["name"])
            ok(row.get("general_code") or row.get("law"),state+" missing PKS scope")
        metrics=set()
        for row in more:
            ok(row.get("name") and row["name"] not in metrics,state+" duplicate additional name")
            metrics.add(row["name"])
            ok(type(row.get("cases")) is int and row["cases"]>=0,state+" invalid additional count")
            ok(row.get("code"),state+" additional metric has no law/PKS key")
            prev=row.get("previous_2024")
            ok(prev is None or (type(prev) is int and prev>=0),state+" invalid 2024 metric")
    for state,entry in health.items():
        ok(entry.get("source_url","").startswith("https://"),state+" missing hospital data source")
        ok(entry.get("metrics"),state+" no health indicators")
    # Overlap-sensitive controls: 2025 KCanG subgroup is INSIDE KCanG
    # overall total; Berlin's cocaine case types belong to separate legal keys.
    berlin=offences.get("Berlin")
    ok(berlin is not None,"Missing Berlin official 2025 PKS breakdown")
    row=next((x for x in berlin["groups"] if x["name"]=="可卡因／快克"),None)
    ok(row is not None and
       (row["general"],row["trade"],row["general_code"],row["trade_code"])==
       (2218,1432,"731200","732200"),"Berlin cocaine PKS row mismatch")
    named={x["name"]:x["cases"] for x in berlin["additional_metrics"]}
    ok(named.get("大麻 · KCanG §34全部罪名")==2343 and
       named.get("其中大麻非法交易")==1309,
       "Berlin cannabis KCanG subsection is missing or inconsistent")
    ok(named["其中大麻非法交易"]<=named["大麻 · KCanG §34全部罪名"],
       "Berlin cannabis subgroup exceeds overall count")
    bw=offences.get("Baden-Württemberg")
    ok(bw is not None,"Baden-Württemberg NPS primary-source metrics missing")
    metrics={x["name"]:x["cases"] for x in bw.get("additional_metrics",[])}
    ok(metrics.get("新精神活性物质 · NpSG违法")==156 and
       metrics.get("新精神活性物质 · BtMG非法交易")==61,
       "Baden-Württemberg source NPS law categories incorrectly merged")
    ok(len(offences)==9,"Expected nine states with at least one original PKS substance metric")
    print("PASS verified state evidence:",
          len(deaths),"death states,",len(offences),"PKS drug-substance states,",
          len(health),"health-source states; Berlin PKS 2025 codes and KCanG overlap verified")

if __name__=="__main__":
    validate()
