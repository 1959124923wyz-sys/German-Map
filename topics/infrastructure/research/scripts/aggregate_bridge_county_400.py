#!/usr/bin/env python3
"""Bridge condition pilot re-keyed onto verified 2016+2021 district mergers.

Candidate 400-region geometry is NOT government-certified current VG25/VG2500.
Abolished Eisenach district counts must be folded into Wartburgkreis.
"""
import copy
import json
import pathlib
ROOT=pathlib.Path(__file__).resolve().parents[4]
R=ROOT/"topics/infrastructure/research"
SOURCE=R/"candidate_bridge_county_ags_2025.json"
BOUNDARY=R/"germany-counties-mergers-candidate.geojson"
OUT=R/"candidate_bridge_county_ags_400d_2025.json"
def main():
    old=json.loads(SOURCE.read_text())
    geo=json.loads(BOUNDARY.read_text())
    official_ids={str(f["id"]).zfill(5):i for i,f in enumerate(geo["features"])}
    assert len(official_ids)==400
    hist={v["ags"]:copy.deepcopy(v) for v in old["data"]}
    assert "03156" not in hist, "16056" in hist and "16063" in hist
    city=hist.pop("16056")
    district=hist["16063"]
    district["observed_source_labels"]+=city["observed_source_labels"]
    district["historical_ags_integrated_from"]=["16056"]
    for field in ("substructure_count","poor_substructure_count","area_sqm","poor_area_sqm"):
        district[field]=round(district[field]+city[field],2) if "_sqm" in field else district[field]+city[field]
    district["poor_pct_count"]=round(100*district["poor_substructure_count"]/district["substructure_count"],3)
    district["poor_pct_area"]=round(100*district["poor_area_sqm"]/district["area_sqm"],3)
    out=[]
    for code,v in sorted(hist.items()):
        assert code in official_ids,"AGS absent from corrected boundary: "+code
        v["geometry_feature_index"]=official_ids[code]
        v["ags_boundary_version"]="two_known_mergers_corrected_old_geojson"
        out.append(v)
    total=sum(v["substructure_count"] for v in out)
    bad=sum(v["poor_substructure_count"] for v in out)
    assert total==old["matched_substructures"]==49820
    assert bad==sum(v["poor_substructure_count"] for v in old["data"])
    assert len(out)==old["candidate_county_ags"]-1==386
    assert district["substructure_count"]==171
    missing=sorted(set(official_ids)-set(hist))
    assert len(missing)==14
    result={"status":"400_DISTRICT_DERIVATIVE_CANDIDATE_DO_NOT_PUBLISH",
      "asof_data":"2025-09",
      "boundary_source":str(BOUNDARY.relative_to(ROOT)),
      "boundary_legality":"Two officially documented merges; not full BKG 2025 official survey",
      "former_ags_merged":[{"old":"16056","new":"16063","area_counts_conserved":True},
                            {"old":"03156","new":"03152","area_counts_conserved":True,"old_source_group_found":False}],
      "county_geometry_count":400,"covered_ags_count":len(out),
      "missing_ags":missing,
      "included_bast_substructures":total,
      "source_total_arcgis_substructures":old["total_arcgis_substructures"],
      "unmapped_bast_substructures":old["total_arcgis_substructures"]-total,
      "substructure_percent_covered":round(100*total/old["total_arcgis_substructures"],3),
      "denominator":"bridge Teilbauwerke, count or square meters, only after attributable county source label",
      "not_approved_for_production":True,
      "data":out}
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print("PASS 400 polygons,386 matched AGS,",total,"bridges parts; Eisenach and Wartburgkreis =>",district["substructure_count"])
if __name__=="__main__":main()
