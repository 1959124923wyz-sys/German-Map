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
    assert page.locator("#housingMap .leaflet-control-zoom-in").count()==1
    assert page.locator("#stateJump option").count()==17
    assert len(page.locator("#quickStats .housing-quick-card").all())==4
    assert page.locator("#sourceLink").get_attribute("href").startswith("https://")
    assert "中位数" in page.locator("#description").inner_text()
    assert "2025" in page.locator("#legend").inner_text()
    assert "欧元" in page.locator("#value").inner_text()
    assert page.locator("main .housing-rank-row").count()==8
    assert page.locator("#housingMetric option").count()==10
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
    row=page.locator("#topRank .housing-rank-row").first
    row.click()
    s=page.evaluate("GermanHousingResearch.state()")
    assert s["selectedCounty"] is not None and s["selectedCounty"].startswith("07"),s
    assert "行政区编码" in page.locator("#coverage").inner_text()
    assert "中位数" not in page.locator("#description").inner_text()
    page.locator("#stateJump").select_option("09")
    assert page.evaluate("GermanHousingResearch.state().focusState")=="09"
    assert page.evaluate("GermanHousingResearch.state().selectedCounty") is None
    # State-specific evidence: no pseudo-national construction/homelessness overlay.
    page.locator("#stateJump").select_option("05")
    page.locator("#topRank .housing-rank-row").first.click()
    assert page.locator("#nrwCompletions").is_visible(),"NRW local source must be available"
    assert page.locator("#landPriceBand").is_visible(),"2024 land price is an ordinal band"
    page.locator("#nrwCompletions summary").click()
    assert "2025" in page.locator("#nrwHistory").inner_text()
    page.locator("#stateJump").select_option("14")
    page.locator("#topRank .housing-rank-row").first.click()
    assert page.locator("#saxonyDetails").is_visible(),"Saxony official 13-county series must be available"
    assert page.locator("#nrwCompletions").is_hidden(),"NRW history must not leak into Sachsen"
    page.locator("#saxonyDetails summary").click()
    assert "2026" in page.locator("#saxonyHistory").inner_text()
    page.locator("#resetView").click()
    assert page.evaluate("GermanHousingResearch.state().focusState") is None
    assert page.evaluate("GermanHousingResearch.state().selectedCounty") is None
    assert page.locator("#stateJump").input_value()==""
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
