#!/usr/bin/env python3
"""Real-browser smoke: load German housing project preview with local Leaflet.

Geometries must match existing project map, all housing indicators stay separate,
and optional stock metrics must not override official rental rates.
"""
from __future__ import annotations
import base64
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
    assert page.locator("#housingMetric option").count()==15
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
    page.locator("#housingMetric").select_option("asking_rent_2025_eur_m2")
    page.locator("#stateJump").select_option("07")
    assert page.evaluate("GermanHousingResearch.state().focusState")=="07"
    assert page.locator("#stateJump").input_value()=="07"
    assert "欧元" in page.locator("#value").inner_text()
    assert page.locator("#housingDossier").is_visible()
    page.locator('[data-dossier-tab="structure"]').click()
    assert "2022住房普查" in page.locator("#housingStructureCoverage").inner_text()
    assert page.locator("#housingStructure .dossier-metrics").count()==0
    assert page.locator("#housingStructure>div").count()==6
    assert "租金" in page.locator("#housingStructure").inner_text()
    page.locator('[data-dossier-tab="districts"]').click()
    page.locator("#housingCountySearch").fill("07111")
    assert page.locator("#housingCountyResults .dossier-entry").count()>=0
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
