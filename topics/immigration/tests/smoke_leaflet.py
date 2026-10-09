#!/usr/bin/env python3
"""05: actual geometry, pointer interaction and layout regression in Chromium."""
from pathlib import Path
import re
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[3]
ASSET=ROOT/"node_modules/leaflet/dist"
URL="http://127.0.0.1:8765/topics/immigration/"
def check(browser, mobile=False):
    page=browser.new_page(viewport={"width":390 if mobile else 1460,"height":820 if mobile else 900})
    errors=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    page.route(re.compile(r"https://unpkg\.com/leaflet@1\.9\.4/dist/leaflet\.js"),lambda r:r.fulfill(path=str(ASSET/"leaflet.js"),content_type="application/javascript"))
    page.route(re.compile(r"https://unpkg\.com/leaflet@1\.9\.4/dist/leaflet\.css"),lambda r:r.fulfill(path=str(ASSET/"leaflet.css"),content_type="text/css"))
    page.route(re.compile(r"https://tile\.openstreetmap\.org/"),lambda r:r.abort())
    page.goto(URL,wait_until="domcontentloaded",timeout=30000)
    page.wait_for_function("()=>window.__IMMIGRATION_READY__===true",timeout=45000)
    # Raw AZR files remain independent of presentation and all four source
    # payloads must load before the interactive map initializes.
    assert page.locator('script[src^="data/azr-records.js"]').count()==1
    assert page.evaluate("""() => [
      window.__IMMIGRATION_INLINE_FOREIGN__,
      window.__IMMIGRATION_INLINE_TREND__,
      window.__IMMIGRATION_INLINE_SHARE__,
      window.__IMMIGRATION_INLINE_COUNTIES__
    ].every(Boolean)""")
    assert not page.locator("script:not([src])").count()
    # A new topic must retain all existing links, in a deterministic order.
    nav=page.locator(".toplinks .modebtn")
    assert nav.count()==5
    assert [name.strip() for name in nav.all_inner_texts()]==[
        "暴力犯罪","财产犯罪","毒品问题","移民人口","环保争议"]
    assert page.locator('.toplinks a[href="../environment/"]').count()==1
    assert page.locator(".toplinks .modebtn.active").inner_text()=="移民人口"
    assert page.locator("#immigration-map .crime-city-label").first.evaluate("(e)=>getComputedStyle(e).whiteSpace")=="nowrap"
    assert page.locator(".sidebar").evaluate("(e)=>getComputedStyle(e).backgroundColor")=="rgb(19, 26, 34)"
    page.screenshot(path="/tmp/immigration-unified-diagnostic-"+("mobile" if mobile else "desktop")+".png",full_page=True)
    state_count=page.evaluate("()=>window.__IMMIGRATION_MAP_V13__.getPane('immigrationStatePane').querySelectorAll('path').length")
    print("Diagnostics: panes",page.evaluate("()=>[...document.querySelectorAll('#immigration-map .leaflet-pane')].map(e=>[e.className,e.querySelectorAll('path').length])"),"state path count",state_count,flush=True)
    assert state_count>=16,("No 16 real state polygons",state_count)
    assert page.evaluate("()=>window.__IMMIGRATION_MAP_V13__.getPane('immigration-city-labels').style.pointerEvents") == "none"
    if not mobile: assert page.locator("#immigration-map .crime-city-label").count() >= 6
    assert page.locator("#state-list button").count()==16
    assert page.locator("#national-value").inner_text()=="14,070,225"
    page.locator("#population-year").select_option("2018")
    assert page.locator("#national-value").inner_text()=="10,915,455"
    page.locator("#population-year").select_option("2025")
    page.locator("#population-metric").select_option("share")
    assert page.locator("#national-value").inner_text()=="14.9%"
    assert page.locator("#population-year").is_disabled()
    page.locator("#population-metric").select_option("count")
    print("TRANSLATION_DIAGNOSTIC",page.evaluate("()=>({loaded:!!window.GermanPlaceNames,value:window.GermanPlaceNames?.translate('Berlin'),county:window.GermanPlaceNames?.byAGS('01001','Flensburg'),stateText:document.querySelector('#state-list')?.innerText?.slice(0,240),errors:[]})"),flush=True)
    page.locator("#state-list").get_by_text("柏林").click()
    assert "994,590" in page.locator("#region-value").inner_text()
    assert page.locator("#trend-chart polyline").count()==1
    page.locator("#back-country").click()
    page.locator("#state-list").get_by_text("石勒苏益格－荷尔斯泰因州").click()
    assert page.locator("#county-list button").count()==15
    page.locator("#show-counties").click()
    page.wait_for_function("()=>window.GermanMapTopics.immigration.getViewState().countyMode==='counties'",timeout=45000)
    assert page.evaluate("()=>window.__IMMIGRATION_MAP_V13__.getPane('immigrationCountyPane').querySelectorAll('path').length")>=15
    page.locator("#county-list").get_by_text("弗伦斯堡", exact=True).click()
    assert page.locator("#county-value").inner_text()=="17,910"
    page.locator("#show-counties").click()
    assert page.evaluate("()=>window.GermanMapTopics.immigration.getViewState().countyMode")=="states"
    assert page.evaluate("()=>getComputedStyle(window.__IMMIGRATION_MAP_V13__.getPane('immigrationStatePane').querySelector('path')).pointerEvents")!="none"
    page.locator("#back-country").click()
    page.locator("#state-list").get_by_text("巴伐利亚州").click()
    assert page.locator("#region-value").inner_text()=="2,386,525"
    page.locator("#reset-map").click()
    assert page.locator("#national-panel").is_visible()
    page.screenshot(path="/tmp/immigration-unified-"+("mobile" if mobile else "desktop")+".png",full_page=True)
    assert not errors,errors
    page.close()

with sync_playwright() as p:
    b=p.chromium.launch(headless=True)
    try:
        check(b,False);check(b,True)
        print("PASS: real state/county polygons, Leaflet, 5-topic nav, OSM-compatible map, mode/year, 25-county drilldown and state re-entry, desktop/mobile")
    finally:b.close()
