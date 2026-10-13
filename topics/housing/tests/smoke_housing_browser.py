#!/usr/bin/env python3
"""Real-browser smoke: load German housing project preview with local Leaflet.

Geometries must match existing project map, all housing indicators stay separate,
and optional stock metrics must not override official rental rates.
"""
from __future__ import annotations
import base64
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE="http://127.0.0.1:8765/topics/housing/"
LEAFLET=Path("node_modules/leaflet/dist")
PIX=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9YA0sEUAAAAASUVORK5CYII=")

def run(browser,mobile=False):
    label="mobile" if mobile else "desktop"
    page=browser.new_page(viewport={"width":390 if mobile else 1440,"height":844 if mobile else 900},device_scale_factor=1)
    errors=[]
    page.on("pageerror",lambda error:errors.append(str(error)))
    page.route("https://unpkg.com/leaflet@1.9.4/dist/leaflet.js",lambda r:r.fulfill(path=str(LEAFLET/"leaflet.js"),content_type="text/javascript"))
    page.route("https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",lambda r:r.fulfill(path=str(LEAFLET/"leaflet.css"),content_type="text/css"))
    page.route("**tile.openstreetmap.org/**",lambda r:r.fulfill(status=200,body=PIX,content_type="image/png"))
    page.goto(BASE,wait_until="domcontentloaded",timeout=45000)
    page.wait_for_function("window.GermanHousingResearch?.state()?.validCount===400",timeout=45000)
    state=page.evaluate("GermanHousingResearch.state()")
    print(label,"initial",state)
    assert state["countyShapes"]==400
    assert state["stockReady"] is True
    assert state["structureReady"] is True
    assert page.locator("#housingDossier").is_hidden()
    assert page.locator("#housingMap .leaflet-control-zoom-in").count()==1
    assert page.locator("#stateJump option").count()==17
    assert len(page.locator("#quickStats .housing-quick-card").all())==4
    assert page.locator("#sourceLink").get_attribute("href").startswith("https://")
    assert "中位数" in page.locator("#description").inner_text()
    assert "2025" in page.locator("#legend").inner_text()
    assert "欧元" in page.locator("#value").inner_text()
    assert page.locator("#housingNationalHint").is_visible()
    assert page.locator("main .housing-rank-row").count()==8
    # True county polygon hit, including on 390px. Prior tests clicked
    # only sidebar lists and never detected the overlaid state SVG path.
    page.locator("#housingMap").scroll_into_view_if_needed()
    page.evaluate("""() => {
      GermanHousingResearch.getMap().setView([50.72,9.1],9,{animate:false});
      return true;
    }""")
    page.wait_for_timeout(180)
    probe=json.loads(page.evaluate("""() => {
      const q=GermanHousingResearch,m=q.getMap(),ll=[50.72,9.1];
      const xy=m.latLngToContainerPoint(ll),r=m.getContainer().getBoundingClientRect();
      const lp=m.latLngToLayerPoint(ll),x=r.left+xy.x,y=r.top+xy.y;
      const matches=q.getCountyLayer().getLayers()
        .filter(l=>l._containsPoint?.(lp)).map(l=>String(l.feature?.id||''));
      const stack=document.elementsFromPoint(x,y).slice(0,7)
        .map(el=>({tag:String(el.tagName),classes:String(el.getAttribute('class')||'')}));
      return JSON.stringify({x:Number(x),y:Number(y),matches,stack,
        stateInteractive:q.getStateLayer().getLayers().some(l=>l.options.interactive)});
    }"""))
    assert probe["matches"],("Point is outside GIS county polygons",probe)
    assert not probe["stateInteractive"],"Decorative state outlines must stay pointer-passive"
    assert any('leaflet-interactive' in el['classes'] for el in probe['stack']),(
        "An upper layer may have intercepted the county",probe)
    before_pointer=page.evaluate("GermanHousingResearch.state()")
    page.mouse.click(probe['x'],probe['y'])
    after_pointer=page.evaluate("GermanHousingResearch.state()")
    assert after_pointer['selectedCounty'] in probe['matches'],(
        "Actual county mouse click did not open the corresponding dossier",probe,after_pointer)
    assert after_pointer['zoom']==before_pointer['zoom']
    assert abs(after_pointer['view']['lat']-before_pointer['view']['lat'])<1e-5
    assert abs(after_pointer['view']['lng']-before_pointer['view']['lng'])<1e-5
    # A polygon-selected Kreis must remain selected while switching data layers.
    # Repainting a 400-county map must not silently reset selection, the
    # camera, or the 7-step legend while changing statistical interpretation.
    county=after_pointer['selectedCounty']
    for key in (
        'living_area_2022_m2_person',
        'vacancy_2022_pct',
        'sheltered_homeless_2025',
        'asking_rent_2025_eur_m2',
        'completed_dwellings_new_residential_buildings_2023'
    ):
        page.locator("#housingMetric").select_option(key)
        metric_state=page.evaluate("GermanHousingResearch.state()")
        assert metric_state['selectedCounty']==county, (key,metric_state)
        assert metric_state['focusState']==county[:2], (key,metric_state)
        assert metric_state['metric']==key, (key,metric_state)
        assert metric_state['zoom']==after_pointer['zoom']
        assert abs(metric_state['view']['lat']-after_pointer['view']['lat'])<1e-5
        assert abs(metric_state['view']['lng']-after_pointer['view']['lng'])<1e-5
        assert page.locator("#legend .housing-scale i").count()==7
        assert page.locator("#sourceLink").get_attribute("href").startswith("https://")
        assert page.locator("#housingDossier").is_visible()
    page.locator("#resetView").click()
    assert page.evaluate("GermanHousingResearch.state().metric")=='completed_dwellings_new_residential_buildings_2023', (
        "Returning national map must preserve the explicitly chosen metric")
    page.locator("#housingMetric").select_option("asking_rent_2025_eur_m2")
    assert page.evaluate("GermanHousingResearch.state().selectedCounty") is None
    assert page.locator("#housingMetric option").count()==15
    assert page.evaluate("Object.keys(AtlasColorSemantics.registry.housing).length")==15
    for key,direction,note in [
        ("asking_rent_2025_eur_m2","pressure-high","问题相关指标升高"),
        ("living_area_2022_m2_person","pressure-low","条件改善"),
        ("vacancy_2022_pct","neutral","不代表严重程度"),
        ("sheltered_homeless_2025","neutral","不代表严重程度"),
        ("renewable_heat_stock_2022_pct","neutral","不代表严重程度"),
    ]:
        page.locator("#housingMetric").select_option(key)
        d=page.evaluate("""() => {
          const q=GermanHousingResearch;
          return {direction:q.colorDirection(),lo:q.colorFor(-1e12),
             hi:q.colorFor(1e12),colors:q.palette()};
        }""")
        assert d["direction"]==direction,(key,d)
        assert d["lo"]==d["colors"][0] and d["hi"]==d["colors"][-1]
        assert note in page.locator("#legend").inner_text(),(key,note)
        if direction=="pressure-low":
            assert "低值" in page.locator("#rankBox .housing-rank-head").inner_text()
        elif direction=="neutral":
            assert "非住房问题排名" in page.locator("#rankBox .housing-rank-head").inner_text()
        if direction=="pressure-low":
            assert d["lo"]=="#a52d37" and d["hi"]=="#f5ead9",(key,d)
        elif direction=="pressure-high":
            assert d["lo"]=="#f5ead9" and d["hi"]=="#a52d37",(key,d)
        else:
            assert d["lo"]=="#eff5f9" and d["hi"]=="#1b5278",(key,d)
    page.locator("#housingMetric").select_option("asking_rent_2025_eur_m2")
    assert page.evaluate("GermanHousingResearch.state().censusReady") is True
    for metric,valueUnit in (
        ("existing_cold_rent_2022_eur_m2","欧元"),
        ("vacant_12mo_plus_of_vacant_2022_pct","%"),
        ("vacant_available_3mo_of_vacant_2022_pct","%")
    ):
        page.locator("#housingMetric").select_option(metric)
        assert page.evaluate("GermanHousingResearch.state().validCount")==400
        assert valueUnit in page.locator("#value").inner_text()
        assert "2022" in page.locator("#yearLabel").inner_text()
        assert "Zensus 2022" in page.locator("#sourceCredit").inner_text()
    page.locator("#housingMetric").select_option("asking_rent_2025_eur_m2")
    assert page.evaluate("GermanHousingResearch.state().completionsReady") is True
    page.locator("#housingMetric").select_option("completed_dwellings_new_residential_buildings_2023")
    assert page.evaluate("GermanHousingResearch.state().validCount")==400
    assert "Regionalstatistik" in page.locator("#sourceCredit").inner_text()
    assert "2023" in page.locator("#yearLabel").inner_text()
    page.locator("#housingMetric").select_option("asking_rent_2025_eur_m2")
    assert page.evaluate("GermanHousingResearch.state().homelessReady") is True
    page.locator("#housingMetric").select_option("sheltered_homeless_2025")
    assert page.evaluate("GermanHousingResearch.state().validCount")==394
    assert "Destatis" in page.locator("#sourceCredit").inner_text()
    assert "2025年1月31日" in page.locator("#yearLabel").inner_text()
    page.locator("#housingMetric").select_option("asking_rent_2025_eur_m2")
    for opt,needle in [("vacancy_2022_pct","2022"),("homes_per_1000_people_2025","2025"),
                       ("housing_stock_growth_2022_2025_pct","2022—2025")]:
        page.locator("#housingMetric").select_option(opt)
        assert needle in page.locator("#yearLabel").inner_text()
        assert page.evaluate("GermanHousingResearch.state().validCount")==400
        assert page.locator("#legend .housing-scale i").count()==7
        assert "00000" not in page.evaluate("GermanHousingResearch.state().sampleTooltip")
    page.locator("#housingMetric").select_option("asking_rent_2025_eur_m2")
    # Previously each source only appeared after selecting one particular county;
    # all 192 independently scoped rows now have a searchable state-level entrance.
    assert page.locator("#housingStateArchive").is_hidden()
    page.locator("#stateJump").select_option("05")
    assert page.evaluate("GermanHousingResearch.state().localArchiveRows")==53
    page.locator('[data-dossier-tab="structure"]').click()
    page.locator("#stateJump").select_option("09")
    assert page.locator('[data-dossier-tab="structure"]').get_attribute("aria-selected")=="true"
    assert page.locator("#housingStructure").is_visible()
    page.locator("#stateJump").select_option("05")
    assert page.locator('[data-dossier-tab="structure"]').get_attribute("aria-selected")=="true"
    page.locator('[data-dossier-tab="archive"]').click()
    assert page.locator("#housingStateArchive").is_visible()
    assert page.locator("#housingStateArchive").get_attribute("open") is None
    page.locator("#housingStateArchive > summary").click()
    assert page.locator("#housingLocalRows .housing-local-entry").count()==53
    assert page.locator("#housingLocalYear option").count()==11
    assert page.locator("#housingLocalYear").input_value()=="2025"
    assert "53个地区" in page.locator("#housingLocalSummary").inner_text()
    page.locator("#housingLocalSearch").fill("05111")
    assert page.locator("#housingLocalRows .housing-local-entry").count()==1
    assert "1,525" in page.locator("#housingLocalRows").inner_text()
    assert page.locator("#housingLocalMetric option").count()==4
    page.locator("#housingLocalMetric").select_option("buildings")
    assert "136" in page.locator("#housingLocalRows").inner_text()
    assert "栋" in page.locator("#housingLocalRows").inner_text()
    page.locator("#housingLocalMetric").select_option("rooms")
    assert "4,223" in page.locator("#housingLocalRows").inner_text()
    page.locator("#housingLocalMetric").select_option("area")
    assert "120,825" in page.locator("#housingLocalRows").inner_text()
    assert "㎡" in page.locator("#housingLocalRows").inner_text()
    page.locator("#housingLocalMetric").select_option("dwellings")
    oldview=page.evaluate("GermanHousingResearch.state()")
    page.locator("#housingLocalRows [data-local-county]").first.click()
    assert page.evaluate("GermanHousingResearch.state().selectedCounty")=="05111"
    newview=page.evaluate("GermanHousingResearch.state()")
    assert newview["zoom"]==oldview["zoom"]
    assert abs(newview["view"]["lat"]-oldview["view"]["lat"])<1e-5
    assert page.locator("#nrwCompletions").is_visible()
    assert page.locator("#housingStateArchive").get_attribute("open") is not None
    page.locator("#stateJump").select_option("09")
    assert page.evaluate("GermanHousingResearch.state().localArchiveRows")==96
    page.locator('[data-dossier-tab="archive"]').click()
    page.locator("#housingStateArchive > summary").click()
    assert page.locator("#housingLocalYear option").count()==1
    page.locator("#housingLocalSearch").fill("München")
    assert "3,960" in page.locator("#housingLocalRows").inner_text()
    assert page.locator("#housingLocalMetric option").count()==3
    page.locator("#housingLocalMetric").select_option("buildings")
    assert "593" in page.locator("#housingLocalRows").inner_text()
    page.locator("#housingLocalMetric").select_option("all")
    assert "4,324" in page.locator("#housingLocalRows").inner_text()
    page.locator("#stateJump").select_option("12")
    assert page.evaluate("GermanHousingResearch.state().localArchiveRows")==18
    page.locator('[data-dossier-tab="archive"]').click()
    page.locator("#housingStateArchive > summary").click()
    assert page.locator("#housingLocalYear option").count()==2
    page.locator("#housingLocalSearch").fill("Potsdam, Stadt")
    assert "933" in page.locator("#housingLocalRows").inner_text()
    assert page.locator("#housingLocalMetric option").count()==2
    page.locator("#housingLocalMetric").select_option("new_all")
    assert "908" in page.locator("#housingLocalRows").inner_text()
    assert "新建各类建筑" in page.locator("#housingLocalMetric option:checked").inner_text()
    page.locator("#housingLocalMetric").select_option("dwellings")
    assert "全部建筑措施" in page.locator("#housingStateArchiveScope").inner_text()
    page.locator("#housingLocalYear").select_option("2024")
    assert "1,039" in page.locator("#housingLocalRows").inner_text()
    page.locator("#stateJump").select_option("11")
    assert page.evaluate("GermanHousingResearch.state().localArchiveRows")==12
    page.locator('[data-dossier-tab="archive"]').click()
    page.locator("#housingStateArchive > summary").click()
    page.locator("#housingLocalSearch").fill("Mitte")
    assert "1,049" in page.locator("#housingLocalRows").inner_text()
    page.locator("#housingLocalMetric").select_option("new_all")
    assert "927" in page.locator("#housingLocalRows").inner_text()
    assert page.locator("#housingLocalRows [data-local-county]").count()==0
    assert "Bezirke" in page.locator("#housingStateArchiveScope").inner_text()
    page.locator("#stateJump").select_option("14")
    assert page.evaluate("GermanHousingResearch.state().localArchiveRows")==13
    page.locator('[data-dossier-tab="archive"]').click()
    page.locator("#housingStateArchive > summary").click()
    assert page.locator("#housingLocalYear option").count()==5
    page.locator("#housingLocalSearch").fill("Leipzig, Stadt")
    assert "2,735" in page.locator("#housingLocalRows").inner_text()
    assert page.locator("#housingLocalMetric option").count()==1
    assert "不包括全部露宿者" in page.locator("#housingLocalCaveat").inner_text()
    page.locator("#stateJump").select_option("07")
    assert page.evaluate("GermanHousingResearch.state().localArchiveRows")==0
    page.locator('[data-dossier-tab="archive"]').click()
    assert page.locator("#housingStateArchive").is_hidden()
    page.locator("#housingMetric").select_option("asking_rent_2025_eur_m2")
    page.locator("#stateJump").select_option("07")
    assert page.evaluate("GermanHousingResearch.state().focusState")=="07"
    assert page.locator("#stateJump").input_value()=="07"
    assert "欧元" in page.locator("#value").inner_text()
    assert page.locator("#housingDossier").is_visible()
    # GREIX is a separate city-level nominal advertised-rent archive, not the
    # 400-county Zensus indicator and not automatically loaded nationwide.
    assert page.evaluate("GermanHousingResearch.state().greixReady") is False
    page.locator('[data-dossier-tab="rent-series"]').click()
    page.wait_for_function("GermanHousingResearch.state().greixReady===true",timeout=30000)
    assert "本州暂无GREIX" in page.locator("#greixCity").inner_text()
    page.locator("#stateJump").select_option("01")
    page.locator('[data-dossier-tab="rent-series"]').click()
    page.wait_for_function("GermanHousingResearch.state().greixReady===true",timeout=30000)
    assert page.locator("#greixCity").input_value() in ("Kiel","Lübeck")
    page.locator("#greixCity").select_option("Kiel")
    assert "2026-06" in page.locator("#greixChartNote").inner_text()
    assert page.locator("#greixChart polyline").count()==1
    assert "11.79" in page.locator("#greixSummary").inner_text()
    page.locator("#stateJump").select_option("05")
    page.locator('[data-dossier-tab="rent-series"]').click()
    assert "Kiel" not in [x.get_attribute("value") for x in page.locator("#greixCity option").all()]
    page.locator("#greixCity").select_option("Düsseldorf")
    assert "15.01" in page.locator("#greixSummary").inner_text()
    page.locator("#stateJump").select_option("07")
    page.locator('[data-dossier-tab="structure"]').click()
    assert "2022住房普查" in page.locator("#housingStructureCoverage").inner_text()
    assert page.locator("#housingStructure .dossier-metrics").count()==0
    assert page.locator("#housingStructure>div").count()==6
    assert "租金" in page.locator("#housingStructure").inner_text()
    page.locator('[data-dossier-tab="districts"]').click()
    page.locator("#housingCountySearch").fill("07111")
    assert page.locator("#housingCountyResults .dossier-entry").count()>=0
    if not mobile:
        # A real ranking-button choice of another county must not keep the
        # previous district's AGS/name search and show an empty county list.
        old_camera=page.evaluate("GermanHousingResearch.state()")
        page.locator('#topRank .housing-rank-row:not([data-id="07111"])').first.click()
        assert page.locator("#housingCountySearch").input_value()=="", (
            "Choosing a different housing county kept an unrelated AGS query")
        assert page.evaluate("GermanHousingResearch.state().selectedCounty")!="07111"
        assert page.evaluate("GermanHousingResearch.state().zoom")==old_camera["zoom"]
        assert abs(page.evaluate("GermanHousingResearch.state().view.lat")-old_camera["view"]["lat"])<1e-5
        assert page.locator("#housingCountyResults .dossier-entry").count()>1, (
            "The new county still inherited the previous search restriction")
    page.locator("#housingCountySearch").fill("")
    row=page.locator("#topRank .housing-rank-row").first
    row.click()
    s=page.evaluate("GermanHousingResearch.state()")
    assert s["selectedCounty"] is not None and s["selectedCounty"].startswith("07"),s
    assert "行政区编码" in page.locator("#coverage").inner_text()
    assert "中位数" not in page.locator("#description").inner_text()
    # Corrected 2025 Berlin borough data: Berlin itself is ONE Kreis 11000.
    page.locator("#stateJump").select_option("11")
    assert page.evaluate("GermanHousingResearch.state().berlinBoroughReady") is True
    page.locator('[data-dossier-tab="districts"]').click()
    page.locator("#topRank .housing-rank-row").first.click()
    page.locator('[data-dossier-tab="archive"]').click()
    assert page.locator("#berlinBoroughCompletions").is_visible()
    assert page.locator("#bavariaCompletions").is_hidden()
    assert page.locator("#brandenburgCompletions").is_hidden()
    page.locator("#berlinBoroughCompletions summary").click()
    assert "2025" in page.locator("#berlinBoroughHistory").inner_text()
    assert "11,027" in page.locator("#berlinBoroughHistory").inner_text()
    assert page.locator("#berlinBoroughHistory .housing-archive-grid>div").count()==12
    # Brandenburg: 18 county source; all residential/nonresidential new-build
    # accounting must remain separate from NRW/Bavaria 'new residential' data.
    page.locator("#stateJump").select_option("12")
    assert page.evaluate("GermanHousingResearch.state().brandenburgReady") is True
    page.locator('[data-dossier-tab="districts"]').click()
    page.locator("#topRank .housing-rank-row").first.click()
    page.locator('[data-dossier-tab="archive"]').click()
    assert page.locator("#brandenburgCompletions").is_visible()
    assert page.locator("#nrwCompletions").is_hidden()
    assert page.locator("#bavariaCompletions").is_hidden()
    page.locator("#brandenburgCompletions summary").click()
    assert "2025" in page.locator("#brandenburgHistory").inner_text()
    assert "非住宅建筑" in page.locator("#brandenburgHistory").inner_text()
    page.locator("#stateJump").select_option("09")
    assert page.evaluate("GermanHousingResearch.state().focusState")=="09"
    assert page.evaluate("GermanHousingResearch.state().bavariaReady") is True
    page.locator('[data-dossier-tab="districts"]').click()
    page.locator("#topRank .housing-rank-row").first.click()
    page.locator('[data-dossier-tab="archive"]').click()
    assert page.locator("#bavariaCompletions").is_visible(),"Bavaria official 2025 district source should appear only on Bavarian county"
    assert page.locator("#nrwCompletions").is_hidden()
    page.locator("#bavariaCompletions summary").click()
    assert "2025" in page.locator("#bavariaHistory").inner_text()
    assert "巴伐利亚统计局" in page.locator("#bavariaHistory").inner_text()
    page.locator("#stateJump").select_option("09")
    assert page.evaluate("GermanHousingResearch.state().selectedCounty") is None
    # State-specific evidence: no pseudo-national construction/homelessness overlay.
    page.locator("#stateJump").select_option("05")
    page.locator('[data-dossier-tab="districts"]').click()
    page.locator("#topRank .housing-rank-row").first.click()
    page.locator('[data-dossier-tab="archive"]').click()
    assert page.locator("#nrwCompletions").is_visible(),"NRW local source must be available"
    assert page.locator("#landPriceBand").is_visible(),"2024 land price is an ordinal band"
    page.locator("#nrwCompletions summary").click()
    assert "2025" in page.locator("#nrwHistory").inner_text()
    page.locator("#stateJump").select_option("14")
    page.locator('[data-dossier-tab="districts"]').click()
    page.locator("#topRank .housing-rank-row").first.click()
    page.locator('[data-dossier-tab="archive"]').click()
    assert page.locator("#saxonyDetails").is_visible(),"Saxony official 13-county series must be available"
    assert page.locator("#nrwCompletions").is_hidden(),"NRW history must not leak into Sachsen"
    page.locator("#saxonyDetails summary").click()
    assert "2026" in page.locator("#saxonyHistory").inner_text()
    page.locator("#resetView").click()
    assert page.evaluate("GermanHousingResearch.state().focusState") is None
    assert page.evaluate("GermanHousingResearch.state().selectedCounty") is None
    assert page.locator("#stateJump").input_value()==""
    assert page.locator("#housingDossier").is_hidden()
    assert page.locator("#housingNationalHint").is_visible()
    assert not errors,errors
    page.screenshot(path=f"/tmp/housing-research-{label}.png",full_page=True)
    if mobile:
        width=page.evaluate("document.documentElement.scrollWidth")
        assert width<=400,f"mobile horizontal overflow {width}"
    page.close()
    print(label,"PASS")

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    run(browser,False)
    run(browser,True)
    browser.close()
