#!/usr/bin/env python3
"""Correct exactly two documented, expired Kreis boundaries in the legacy map.

This is a derivative geometry candidate, NOT an official BKG 2025 boundary layer.
DO NOT replace the shared site boundary without cartographic review.
"""
import copy
import json
import pathlib
from shapely.geometry import shape, mapping
from shapely.ops import unary_union
from shapely.validation import make_valid

ROOT=pathlib.Path(__file__).resolve().parents[4]
BASE=ROOT/"data/germany-counties.geojson"
OUT=ROOT/"topics/infrastructure/research/germany-counties-mergers-candidate.geojson"
AUDIT=ROOT/"topics/infrastructure/research/germany-counties-mergers-candidate-audit.json"
MERGERS=[
 ("03156","03152","2016-11-01",
  "Niedersachsen: Osterode am Harz district abolished and merged into Göttingen",
  "https://www.statistik.niedersachsen.de/presse/zahl-der-kreise-und-gemeinden-in-niedersachsen-geht-zurueck-148228.html"),
 ("16056","16063","2021-07-01",
  "Thüringen: Eisenach lost independent district status and joined Wartburgkreis",
  "https://www.eisenach.de/rathaus/fusion-der-stadt-eisenach/")
]
def main():
    source=json.loads(BASE.read_text())
    f={str(x.get("id")).zfill(5):copy.deepcopy(x) for x in source["features"]}
    assert len(f)==402 and len(set(f))==402
    # Legacy polygons include invalid shapes unrelated to these two mergers.
    # Do NOT union the full national collection or alter unrelated features.
    invalid_original_ags=[k for k,v in f.items() if not shape(v["geometry"]).is_valid]
    total_original_area=sum(shape(v["geometry"]).area for v in f.values())
    local_repairs=[]
    progress=[]
    for src,dst,date,why,url in MERGERS:
        assert src in f and dst in f, (src,dst)
        before_src=shape(f[src]["geometry"])
        before_dst=shape(f[dst]["geometry"])
        src_geom=before_src if before_src.is_valid else make_valid(before_src)
        dst_geom=before_dst if before_dst.is_valid else make_valid(before_dst)
        if not before_src.is_valid:local_repairs.append(src)
        if not before_dst.is_valid:local_repairs.append(dst)
        merged=unary_union([src_geom,dst_geom])
        assert merged.is_valid and merged.area>=max(src_geom.area,dst_geom.area)
        f[dst]["geometry"]=mapping(merged)
        del f[src]
        progress.append({"obsolete_ags":src,"surviving_ags":dst,"effective_date":date,
           "reason":why,"official_verification_source":url,
           "area_input_approx_degrees_sq":[round(before_src.area,7),round(before_dst.area,7)],
           "merged_area_approx_degrees_sq":round(merged.area,7)})
    assert len(f)==400
    # After two locally checked dissolves, the national sum of individual
    # polygon areas should be conserved apart from preexisting border overlaps.
    total_updated_area=sum(shape(v["geometry"]).area for v in f.values())
    discrepancy=abs(total_original_area-total_updated_area)
    assert discrepancy < 0.002, ("unexpected area change",discrepancy)
    output={"type":"FeatureCollection","features":list(f.values())}
    OUT.write_text(json.dumps(output,ensure_ascii=False,separators=(",",":"))+"\n")
    audit={
      "status":"CANDIDATE_400_KREISE_NOT_OFFICIAL_BKG_CURRENT_GEOMETRY",
      "source":"data/germany-counties.geojson",
      "source_geometry_provenance":"https://github.com/m-ad/geofeatures-ags-germany/blob/master/geojson/counties.json",
      "old_count":402,"new_count":400,"mergers":progress,
      "difference_in_total_individual_polygon_area_degrees_sq":discrepancy,
      "legacy_polygons_with_invalid_topology":invalid_original_ags,
      "legacy_invalid_count":len(invalid_original_ags),
      "only_merger_target_shapes_repaired_with_make_valid":local_repairs,
      "national_topology_union_not_attempted":"Legacy non-target polygons have invalid topology; original features outside two mergers preserved exactly",
      "scope_limitation":"Only two independently verified historical mergers applied; other current borders, cadastral accuracy and corrections not independently checked",
      "not_for_main_site_without_approval":True,
      "new_geojson":str(OUT.relative_to(ROOT))
    }
    AUDIT.write_text(json.dumps(audit,ensure_ascii=False,indent=2)+"\n")
    print("PASS updated 400 polygons, two official mergers, area delta",discrepancy,"invalid originals",len(invalid_original_ags))
if __name__=="__main__":main()
