#!/usr/bin/env python3
"""Reproducible 2025-09 BASt bridge-substructure AGS pilot from exact source joins.

Combines bridge-count and *bridge-area* numerators/denominators, never averages
percentages. Uses historical AGS IDs from German-Map GeoJSON and declines 2026
statutory currency guarantees. Does not modify published 16-state index.
"""
from __future__ import annotations
import collections
import json
import pathlib
import re
ROOT=pathlib.Path(__file__).resolve().parents[4]
R=ROOT/"topics/infrastructure/research"
SRC=json.loads((R/"candidate_bridge_county_geometry_join.json").read_text())
OUT=R/"candidate_bridge_county_ags_2025.json"
def main():
    assert SRC["polygon_has_AGS"] is True and SRC["matched_unique_county_polygons"]>=350
    grouped=collections.defaultdict(list)
    for src in SRC["joined"]:
        code=src["official_AGS"]
        assert re.fullmatch(r"\d{5}",code)
        grouped[code].append(src)
    points=[]
    for ags, rows in sorted(grouped.items()):
        assert len({x["geometry_name"] for x in rows})==1
        assert len({x["iso"] for x in rows})==1
        totals={}
        for key in ("features","poor_features"):
            totals[key]=sum(int(x[key]) for x in rows)
        for key in ("valid_area_m2","poor_area_m2"):
            totals[key]=round(sum(float(x[key]) for x in rows),2)
        assert totals["features"]>=totals["poor_features"]>=0
        assert totals["valid_area_m2"]>=totals["poor_area_m2"]>=0
        count=round(100*totals["poor_features"]/totals["features"],3) if totals["features"] else None
        area=round(100*totals["poor_area_m2"]/totals["valid_area_m2"],3) if totals["valid_area_m2"] else None
        points.append(dict(ags=ags,iso=rows[0]["iso"],name=rows[0]["geometry_name"],
            geometry_feature_index=rows[0]["geometry_feature_index"],
            district_type=rows[0]["geometry_district_type"],
            substructure_count=totals["features"],poor_substructure_count=totals["poor_features"],
            poor_pct_count=count,area_sqm=totals["valid_area_m2"],
            poor_area_sqm=totals["poor_area_m2"],poor_pct_area=area,
            observed_source_labels=[r["kreis_source_label"] for r in rows],
            small_denominator_warning=totals["features"]<20,
            current_ags_validity_unverified=True))
    total=sum(x["substructure_count"] for x in points)
    unmatched=SRC["unmatched_source_features"]
    source_count=total+unmatched
    assert total==SRC["matched_source_features"]
    assert source_count==51664
    geo=json.loads((ROOT/"data/germany-counties.geojson").read_text())
    full_ags=set(str(x["id"]).zfill(5) for x in geo["features"])
    output_ids={p["ags"] for p in points}
    assert len(points)==len(output_ids)
    empty=sorted(full_ags-output_ids)
    assert len(empty)==len(geo["features"])-len(points)
    result={
      "status":"CANDIDATE_2025_09_NOT_YET_PUBLISHED",
      "asset":"BASt-derived federal motorway and B-road bridge Teilbauwerke (not unique bridges)",
      "metric":"DIN1076 inspection condition >=3.0, count- and structure-area-weighted",
      "province_count":16,
      "geometry_ags_source":"data/germany-counties.geojson Feature.id",
      "geometry_source_upstream":"https://github.com/m-ad/geofeatures-ags-germany/blob/master/geojson/counties.json",
      "geometry_source_blob_sha":"d4fb08f16444b40b462ba26beb4d4c97cf236888",
      "ags_currency":"IDs valid to geometry snapshot; NOT crossvalidated with BKG official 2025 district directory",
      "condition_snapshot":"2025-09",
      "do_not_use_for_live_map_without_quality_review":True,
      "do_not_modify_16_state_composite":True,
      "denominator_contract":"Each bridge substructure counts once; poor area sums square meters of DIN>=3.0 substructures over all valid recorded areas",
      "geojson_county_polygons":len(geo["features"]),
      "candidate_county_ags":len(points),
      "geometry_counties_missing_any_join":empty,
      "matched_substructures":total,
      "unmatched_but_county_labeled_substructures":unmatched,
      "missing_county_label_substructures":43,
      "missing_state_label_substructures":846,
      "total_arcgis_substructures":52553,
      "matched_pct_arcgis":round(100*total/52553,3),
      "small_denominator_count":sum(x["small_denominator_warning"] for x in points),
      "data":points
    }
    assert total+unmatched+43+846==52553
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print("PASS joined official-format AGS:",len(points),"of",len(geo["features"]),
          "linked BASt substructures",total,"unresolved",52553-total,
          "small denominators",result["small_denominator_count"],flush=True)

if __name__=="__main__":main()
