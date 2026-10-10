#!/usr/bin/env python3
"""Prepare compact, validated 400-county BKG district geometry for German-Map preview.

Original BKG 2025-12-31 research GeoJSON stays untouched. Retains licence
metadata and geometry AGS keys, conservative polygon simplification and
separate bridge condition evidence with small-denominator cautions.
"""
from __future__ import annotations
import json
import pathlib
from shapely.geometry import shape,mapping
from shapely.validation import make_valid

ROOT=pathlib.Path(__file__).resolve().parents[4]
R=ROOT/"topics/infrastructure/research"
DATA=ROOT/"topics/infrastructure/data"
RAW=R/"germany-counties-bkg-official-2025.geojson"
METRICS=R/"candidate_bridge_official_bkg_counties_2025.json"
OUT=DATA/"bridge_bkg_counties_2025.geojson"
TABLE=DATA/"bridge_county_metrics_2025.json"
AUDIT=R/"bkg_county_display_simplification_audit.json"
TOLERANCE_DEG=0.0005

def main():
    official=json.loads(RAW.read_text())
    metrics=json.loads(METRICS.read_text())
    source={str(f["id"]):f for f in official["features"]}
    rating={x["ags"]:x for x in metrics["data"]}
    assert len(source)==len(rating)==400 and set(source)==set(rating)
    output=[]
    exceeded=[];fallback_invalid=[];ratios=[]
    source_vertices=0;display_vertices=0
    for ags in sorted(source):
        old=source[ags];v=shape(old["geometry"])
        assert v.is_valid and not v.is_empty
        new=v.simplify(TOLERANCE_DEG,preserve_topology=True)
        area_ratio=abs(new.area/v.area-1) if v.area else float("inf")
        if not new.is_valid:
            fallback_invalid.append(ags);new=v
        elif area_ratio>0.01:
            exceeded.append({"ags":ags,"original_area_degrees_sq":v.area,"delta_pct":round(area_ratio*100,3)})
            new=v
        assert new.is_valid
        ratios.append(round(abs(new.area/v.area-1)*100,4))
        meta=old["properties"].copy()
        output.append({"type":"Feature","id":ags,
            "properties":{"ags":ags,"name":meta["name"],"iso":meta["iso"],
                          "districtType":meta["districtType"]},
            "geometry":mapping(new)})
    tagged={"type":"FeatureCollection",
      "metadata":{"source":"BKG VG250 2025-12-31; displayed shape is simplified from official boundary",
                  "snapshot":"2025-12-31",
                  "license":"© BKG (2026) dl-de/by-2-0; see BKG attribution and data providers",
                  "official_page":"https://gdz.bkg.bund.de/index.php/default/digitale-geodaten/verwaltungsgebiete/verwaltungsgebiete-1-250-000-stand-31-12-vg250-31-12.html",
                  "display_simplification_tolerance_degrees":TOLERANCE_DEG,
                  "exact_administrative_border_not_guaranteed":True},
      "features":output}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(tagged,ensure_ascii=False,separators=(",",":"))+"\n")
    values=[]
    for ags in sorted(rating):
        x=rating[ags]
        assert x["iso"]==source[ags]["properties"]["iso"]
        values.append({"ags":ags,"iso":x["iso"],"name":x["name"],
          "parts":x["parts"],"poor_parts":x["poor_parts"],
          "poor_pct_count":x["poor_pct_count"],"area_m2":x["area_m2"],
          "poor_area_m2":x["bad_area_m2"],"poor_pct_area":x["poor_pct_area"],
          "low_sample_under_20":x["parts"]<20,
          "source_vintage":"BASt derived 2025-09",
          "condition_threshold":"DIN1076 >= 3.0",
          "scope":"federal motorway and B road bridge Teilbauwerke only"})
    table={"status":"CANDIDATE_NOT_OFFICIAL_ALL_BRIDGES_QUALITY_RANKING",
      "bridge_snapshot":"2025-09","county_geometry_snapshot":"2025-12-31",
      "polygon_file":"bridge_bkg_counties_2025.geojson",
      "source":"https://services2.arcgis.com/jUpNdisbWqRpMo35/arcgis/rest/services/Br%C3%BCckenstatistik_Deutschland/FeatureServer/0",
      "counts_are_substructures_not_distinct_bridges":True,
      "bridge_counties":values}
    TABLE.write_text(json.dumps(table,ensure_ascii=False,indent=2)+"\n")
    audit={"source_geometry_file_bytes":RAW.stat().st_size,
           "output_display_geojson_bytes":OUT.stat().st_size,
           "table_bytes":TABLE.stat().st_size,
           "polygons":len(output),
           "source_snapshot":"2025-12-31","simplify_tolerance_degrees":TOLERANCE_DEG,
           "fallback_invalid":fallback_invalid,
           "fallback_excessive_area_change":exceeded,
           "max_area_change_pct_of_stored_geometry":max(ratios),
           "official_geometry_remains_unmodified":True,
           "total_bridge_parts":sum(x["parts"] for x in values),
           "small_N_count":sum(x["low_sample_under_20"] for x in values)}
    assert audit["total_bridge_parts"]==metrics["assigned"]
    assert OUT.stat().st_size<RAW.stat().st_size
    AUDIT.write_text(json.dumps(audit,ensure_ascii=False,indent=2)+"\n")
    print("PASS BKG display polygons",len(output),"source",RAW.stat().st_size,"display",OUT.stat().st_size,
      "low-N",audit["small_N_count"],"conservative original falls backs",len(exceeded),flush=True)
if __name__=="__main__":main()
