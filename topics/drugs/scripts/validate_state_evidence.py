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
    ok(len(deaths)<=16 and len(offences)<=16,"Impossible state coverage")
    allowed_scope_kinds={
        "general_offence", "trade_or_smuggling", "statutory_total",
        "multi_offence_substance", "multi_offence_all_drugs",
        "subgroup", "other_statutory_offence"
    }
    # The original JSON stays backward-compatible with the browser. The audit
    # expands its (year, state) keys into self-contained, typed source records.
    records=[]
    def add_record(year, state, metric, value, case_scope, law, source_url, source_type):
        record=dict(year=year,state=state,metric=metric,value=value,
                    case_scope=case_scope,law=law,
                    source_url=source_url,source_type=source_type)
        ok(year==2025 and state in states,"Invalid audit year or state")
        ok(type(value) is int and value>=0,"Invalid audit value: "+metric)
        ok(case_scope and law and source_url.startswith("https://") and source_type,
           "Incomplete audit provenance: "+state+"/"+metric)
        records.append(record)
    for state,entry in deaths.items():
        ok(type(entry.get("cases")) is int and entry["cases"]>=0, state+" invalid death count")
        ok(entry.get("source_url","").startswith("https://"),state+" missing death original")
        prev=entry.get("previous_2024")
        ok(prev is None or (type(prev) is int and prev>=0),state+" previous deaths")
        ok(entry.get("source_type") and entry.get("source_title"),
           state+" mortality source quality is unspecified")
        add_record(2025,state,"drug_related_deaths",entry["cases"],
                   "mortality","registered_drug_death",entry["source_url"],entry["source_type"])
        rate=entry.get("rate_per_100k")
        ok(rate is None or (isinstance(rate,(float,int)) and rate>=0),state+" invalid death rate")
    for state,entry in offences.items():
        ok(entry.get("source_type") in {"state_police","state_government"},
           state+" group data not from primary state authority")
        ok(entry.get("source_url","").startswith("https://"),state+" missing PKS source")
        ok(entry.get("source_title") and entry.get("notes"),
           state+" offence source context is missing")
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
            ok(row.get("law"),state+" missing law for paired offence")
            if row.get("general_code") and row.get("trade_code"):
                ok(row["general_code"]!=row["trade_code"],
                   state+" general and trade code incorrectly identical")
            for field,kind,code in (
                ("general","general_offence",row.get("general_code") or row["law"]),
                ("trade","trade_or_smuggling",row.get("trade_code") or row["law"])):
                add_record(2025,state,row["name"]+"/"+field,row[field],kind,
                           str(code),entry["source_url"],entry["source_type"])
        metrics=set()
        all_named={x["name"]:x for x in more if x.get("name")}
        for row in more:
            ok(row.get("name") and row["name"] not in metrics,state+" duplicate additional name")
            metrics.add(row["name"])
            ok(type(row.get("cases")) is int and row["cases"]>=0,state+" invalid additional count")
            ok(row.get("code"),state+" additional metric has no law/PKS key")
            scope_kind=row.get("scope_kind")
            ok(scope_kind in allowed_scope_kinds,state+" missing/unknown case_scope: "+row["name"])
            if scope_kind=="subgroup":
                parent=row.get("subset_of")
                ok(parent in all_named and parent!=row["name"],
                   state+" subgroup lacks named parent: "+row["name"])
                ok(row["cases"]<=all_named[parent]["cases"],
                   state+" subgroup exceeds parent count: "+row["name"])
            else:
                ok(not row.get("subset_of"),state+" unexpected parent: "+row["name"])
            add_record(2025,state,row["name"],row["cases"],scope_kind,str(row["code"]),
                       entry["source_url"],entry["source_type"])
            prev=row.get("previous_2024")
            ok(prev is None or (type(prev) is int and prev>=0),state+" invalid 2024 metric")
    for state,entry in health.items():
        ok(entry.get("source_url","").startswith("https://"),state+" missing hospital data source")
        ok(entry.get("metrics"),state+" no health indicators")
        for row in entry["metrics"]:
            ok(row.get("name") and type(row.get("cases")) is int and row["cases"]>=0,
               state+" invalid health value")
            add_record(2025,state,row["name"],row["cases"],
                       "hospital_diagnosis",row["name"],
                       entry["source_url"],entry.get("source_type","secondary_health_source"))
    rlp=offences.get("Rheinland-Pfalz")
    ok(rlp is not None and rlp.get("source_type")=="state_police",
       "RLP primary PKS evidence missing")
    r={x["name"]:x for x in rlp.get("additional_metrics",[])}
    for name,cases,scope in (
        ("大麻 · KCanG §34全部罪名",2319,"statutory_total"),
        ("其中大麻非法走私",495,"subgroup"),
        ("其中大麻特别严重案件",316,"subgroup"),
        ("其中非法种植大麻",86,"subgroup"),
        ("其中大麻 §34 Abs.4 重罪",47,"subgroup"),
        ("新精神活性物质 · BtMG一般违法",173,"general_offence"),
        ("新精神活性物质 · NpSG违法",178,"other_statutory_offence")):
        row=r.get(name)
        ok(row is not None and (row["cases"],row["scope_kind"])==(cases,scope),
           "RLP PKS2025 Table15 offence key mismatch: "+name)
    ok(rlp["groups"][0]["general"]==515 and rlp["groups"][0]["trade"]==858,
       "RLP KCanG group changed")
    ok(r["大麻 · KCanG §34全部罪名"]["cases"]>=
       rlp["groups"][0]["general"]+rlp["groups"][0]["trade"],
       "RLP KCanG groups exceed the statutory total")
    # 2025 statewide original from Saxony-Anhalt's Interior Ministry.
    sa=offences.get("Sachsen-Anhalt")
    ok(sa is not None and sa.get("source_type")=="state_government",
       "Sachsen-Anhalt 2025 original state source missing")
    sa_fields={x["name"]:x for x in sa.get("additional_metrics",[])}
    for name,value,prev,scope in (
        ("甲基苯丙胺（冰毒）· 一般违法",1222,1080,"general_offence"),
        ("苯丙胺 · 一般违法",839,788,"general_offence"),
        ("全部毒品相关登记案件",4544,5887,"multi_offence_all_drugs"),
        ("毒品非法交易与走私（多物质）",379,598,"trade_or_smuggling")):
        entry=sa_fields.get(name)
        ok(entry is not None and
           (entry["cases"],entry["previous_2024"],entry["scope_kind"])==
           (value,prev,scope),"Sachsen-Anhalt official PKS2025 mismatch: "+name)
    ok(deaths["Sachsen-Anhalt"]["source_type"]=="state_government" and
       deaths["Sachsen-Anhalt"]["source_url"]==sa["source_url"] and
       (deaths["Sachsen-Anhalt"]["cases"],deaths["Sachsen-Anhalt"]["previous_2024"])==(61,48),
       "Sachsen-Anhalt official death source not upgraded")
    hessen=offences.get("Hessen")
    ok(hessen is not None and hessen.get("source_type")=="state_police",
       "Hessen official 2025 PKS report missing")
    he_fields={x["name"]:x for x in hessen["additional_metrics"]}
    for name,value,scope in (
        ("冰毒（甲基苯丙胺）· 一般违法",153,"general_offence"),
        ("快克（Crack）· 非法交易",157,"trade_or_smuggling"),
        ("可卡因 · 非法交易",263,"trade_or_smuggling")):
        entry=he_fields.get(name)
        ok(entry is not None and (entry["cases"],entry["scope_kind"])==(value,scope),
           "Hessen official 2025 PKS drug breakdown mismatch: "+name)
    # 2025 all-state total issued by the Mainz municipal government for RLP.
    rlp_deaths=deaths.get("Rheinland-Pfalz")
    ok(rlp_deaths is not None and rlp_deaths["cases"]==34 and
       rlp_deaths["previous_2024"] is None and
       rlp_deaths["source_type"]=="city_government_citing_statewide_figure" and
       "mainz.de" in rlp_deaths["source_url"],
       "2025 Rheinland-Pfalz statewide deaths must cite Mainz city government's official 34 figure")
    ok(len(deaths)==14,"Expected fourteen 2025 state-level drug death counts")
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
    # Two additional 2025 statewide PKS originals: preserve the broader
    # "offences involving a substance" scope, NOT §29 general-only counts.
    bav=offences.get("Bayern")
    ok(bav is not None and bav.get("source_type")=="state_police",
       "Bavaria official state-level PKS source missing")
    b={x["name"]:x for x in bav.get("additional_metrics",[])}
    for name,number,previous in (
        ("大麻及其制品 · 涉及违法案件",7164,15270),
        ("可卡因／快克 · 涉BtMG违法案件",4440,3972),
        ("新精神活性物质（NpS）· 违法案件",1308,823)):
        row=b.get(name)
        ok(row is not None and (row["cases"],row["previous_2024"])==(number,previous),
           "Bavaria 2025 official PKS metric mismatch: "+name)
    ok("BtMG" in b["可卡因／快克 · 涉BtMG违法案件"]["code"] and
       "2024年4月" in b["大麻及其制品 · 涉及违法案件"]["note"],
       "Bavaria legal scope and cannabis law caveat missing")
    nrw=offences.get("Nordrhein-Westfalen")
    ok(nrw is not None and nrw.get("source_type")=="state_government",
       "NRW Interior Ministry original missing")
    c=next((x for x in nrw.get("additional_metrics",[])
            if x["name"]=="可卡因／快克 · 涉及违法案件"),None)
    ok(c is not None and (c["cases"],c["previous_2024"])==(7507,6433),
       "NRW official 2025 cocaine incl. crack count mismatch")
    ok("包括快克" in nrw.get("notes","") and "可卡因／快克" in c["name"],
       "NRW broad-scope warning missing")
    mv=deaths.get("Mecklenburg-Vorpommern")
    ok(mv is not None and (mv["cases"],mv["previous_2024"])==(24,15) and
       mv["source_type"]=="regional_newspaper_citing_LKA",
       "MV 2025 secondary-source drug mortality record mismatch")
    ok(len(records)==len({(r["state"],r["metric"],r["case_scope"]) for r in records}),
       "Duplicate 2025 state evidence entries after source normalization")
    ok(len(offences)==12,"Expected twelve states with at least one original PKS substance metric")
    print("PASS verified state evidence:",
          len(deaths),"death states,",len(offences),"PKS drug-substance states,",
          len(health),"health-source states,",len(records),
          "fully attributed, scope-classified audit records")

if __name__=="__main__":
    validate()
