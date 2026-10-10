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
    old_union=unary_union([shape(v["geometry"]) for v in f.values()])
    progress=[]
    for src,dst,date,why,url in MERGERS:
        assert src in f and dst in f, (src,dst)
        before_src=shape(f[src]["geometry"])
        before_dst=shape(f[dst]["geometry"])
        merged=unary_union([before_src,before_dst])
        assert merged.is_valid and merged.area>max(before_src.area,before_dst.area)
        f[dst]["geometry"]=mapping(merged)
        del f[src]
        progress.append({"obsolete_ags":src,"surviving_ags":dst,"effective_date":date,
           "reason":why,"official_verification_source":url,
           "area_input_approx_degrees_sq":[round(before_src.area,7),round(before_dst.area,7)],
           "merged_area_approx_degrees_sq":round(merged.area,7)})
    assert len(f)==400
    new_union=unary_union([shape(v["geometry"]) for v in f.values()])
    discrepancy=old_union.symmetric_difference(new_union).area
    assert discrepancy < 1e-8, ("topology area lost",discrepancy)
    output={"type":"FeatureCollection","features":list(f.values())}
    OUT.write_text(json.dumps(output,ensure_ascii=False,separators=(",",":"))+"\n")
    audit={
      "status":"CANDIDATE_400_KREISE_NOT_OFFICIAL_BKG_CURRENT_GEOMETRY",
      "source":"data/germany-counties.geojson",
      "source_geometry_provenance":"https://github.com/m-ad/geofeatures-ags-germany/blob/master/geojson/counties.json",
      "old_count":402,"new_count":400,"mergers":progress,
      "union_difference_area_degrees_sq":discrepancy,
      "scope_limitation":"Only two independently verified historical mergers applied; other current borders, cadastral accuracy and corrections not independently checked",
      "not_for_main_site_without_approval":True,
      "new_geojson":str(OUT.relative_to(ROOT))
    }
    AUDIT.write_text(json.dumps(audit,ensure_ascii=False,indent=2)+"\n")
    print("PASS updated 400 polygons, two official mergers, union difference",discrepancy)
if __name__=="__main__":main()
