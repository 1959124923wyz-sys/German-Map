#!/usr/bin/env python3
"""Profile existing German-Map county polygons against BASt ArcGIS 'kreis' labels.

Only exact, independently verifiable official AGS joins can be marked matched.
This first phase is an audit, not an automatic join by fuzzy similarity.
"""
import collections
import json
import pathlib

ROOT=pathlib.Path(__file__).resolve().parents[4]
RESEARCH=ROOT/"topics/infrastructure/research"
COUNTIES=ROOT/"data/germany-counties.geojson"
BAST=RESEARCH/"candidate_bridge_counties_arcgis_2025.json"
OUT=RESEARCH/"county_crosswalk_profile.json"

def main():
    shapes=json.loads(COUNTIES.read_text(encoding="utf-8"))
    candidates=json.loads(BAST.read_text(encoding="utf-8"))
    assert shapes["type"]=="FeatureCollection"
    features=shapes["features"]
    county=candidates["counties"]
    columns=collections.Counter()
    fields={}
    for i,f in enumerate(features):
        p=f["properties"]
        columns.update(p.keys())
        for k,v in p.items():
            if len(fields.setdefault(k,[]))<5:
                fields[k].append(str(v)[:110])
    top_by_state=collections.defaultdict(list)
    labels=collections.Counter()
    for x in county:
        labels[x["kreis_source_label"]]+=1
        if len(top_by_state[x["iso"]])<15:
            top_by_state[x["iso"]].append({"source_label":x["kreis_source_label"],"features":x["features"]})
    result={
      "dataset":"German-Map existing Germany county boundary versus BASt ArcGIS source county name",
      "geojson_source":"data/germany-counties.geojson",
      "bast_candidate_source":"topics/infrastructure/research/candidate_bridge_counties_arcgis_2025.json",
      "geometry_feature_count":len(features),
      "geometry_property_keys":dict(columns),
      "geometry_property_samples":fields,
      "geometry_first_features":[f["properties"] for f in features[:12]],
      "bast_source_county_groups":len(county),
      "bast_distinct_source_label_count":len(labels),
      "top_source_labels_by_state":dict(top_by_state),
      "mode":"PROFILE_ONLY_NO_UNVERIFIED_JOINS",
      "source_label_examples":dict(labels.most_common(30))
    }
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    assert len(features)>=380 and len(county)>=400
    print("Saved county-profile",OUT, "geo features",len(features),"source groups",len(county))

if __name__=="__main__":
    main()
