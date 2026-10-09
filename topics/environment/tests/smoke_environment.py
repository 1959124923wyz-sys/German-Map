#!/usr/bin/env python3
"""Environment 06: evidence semantics, shared Leaflet map and responsive UI."""
import os
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[3]
ASSET=ROOT/"node_modules/leaflet/dist"
BASE=os.getenv("GERMAN_MAP_TEST_BASE","http://127.0.0.1:8765/")
EXPECTED={"overview":64,"focus":21,"policy":10,"organization":10,"facility":92,"archive":41}

def check(browser, mobile=False):
    width,height=(390,844) if mobile else (1440,900)
    page=browser.new_page(viewport={"width":width,"height":height},device_scale_factor=1)
    errors=[]
    page.on("pageerror",lambda e: errors.append(str(e)))
    page.route(re.compile(r"https://unpkg\.com/leaflet@1\.9\.4/dist/leaflet\.js"),
               lambda r:r.fulfill(path=str(ASSET/"leaflet.js"),content_type="application/javascript"))
    page.route(re.compile(r"https://unpkg\.com/leaflet@1\.9\.4/dist/leaflet\.css"),
               lambda r:r.fulfill(path=str(ASSET/"leaflet.css"),content_type="text/css"))
    # Verify that unresponsive network tiles do not remove Leaflet controls or point data.
    page.route("**/tile.openstreetmap.org/**",lambda route:route.abort())
    resp=page.goto(BASE+"topics/environment/",wait_until="domcontentloaded",timeout=30000)
    assert resp and resp.ok, ("HTTP",resp.status if resp else None)
    page.wait_for_function("""() => window.__ENVIRONMENT_MAP__?.getMarkerCount()===64
        && window.GermanEnvironment06Data?.length===154
        && document.querySelectorAll('#environment-map .leaflet-marker-icon.env-marker-icon').length>=64""",timeout=30000)
    assert page.locator(".modebar a.modebtn").count()==5
    assert page.locator(".modebar .modebtn.active").inner_text()=="环保争议"
    assert page.locator("#environment-map .leaflet-control-zoom-in").is_visible()
    assert page.locator("#environment-map .leaflet-tile-pane").count()==1
    assert page.locator("#environment-map .crime-city-label").count()>=5
    assert "街道底图" in page.locator("#mapStatus").inner_text() or "底图" in page.locator("#mapStatus").inner_text()

    facts=page.evaluate("""() => {
      const rows=window.GermanEnvironment06Data;
      const count=k=>rows.filter(x=>x.kind===k).length;
      const good=rows.every(x=>/^\d{4}-\d{2}-\d{2}$/.test(x.date)
       && Number.isFinite(x.coordinates?.lat)&&Number.isFinite(x.coordinates?.lon)
       && x.sources?.length>0&&x.sources.every(s=>/^https:\/\//.test(s.url)));
      const phases={};
      for(const x of rows.filter(x=>x.kind==='facility'))
        phases[x.facility_phase]=(phases[x.facility_phase]||0)+1;
      return {total:rows.length,good,archive:count('archive'),policy:count('policy'),
        organization:count('organization'),facility:count('facility'),
        facility_story:count('facility_story'),phases};
    }""")
    assert facts["total"]==154 and facts["good"],facts
    assert [facts[k] for k in ("archive","policy","organization","facility","facility_story")]==[41,10,10,92,1],facts
    assert facts["phases"]=={"retired":32,"awarded":36,"ordered":3,"scheduled":21},facts
    page.wait_for_function("""() => document.querySelectorAll('#environment-map .leaflet-pane.environmentStates path').length>=16""",timeout=20000)
    # Presentation and filters remain correlated with the data, not mere decoration.
    for mode,expected in EXPECTED.items():
        page.locator('[data-mode="'+mode+'"]').click()
        assert page.locator("#count").inner_text()==str(expected),mode
        assert page.evaluate("window.__ENVIRONMENT_MAP__.getMarkerCount()")==expected,mode
        assert page.locator("#listCount").inner_text()==str(expected)+" 条",mode
    page.locator('[data-mode="facility"]').click()
    page.locator('#phase').select_option("scheduled")
    assert page.locator("#count").inner_text()=="21"
    assert "计划" in page.locator("#listHint").inner_text() or "退出" in page.locator("#listHint").inner_text()
    page.locator('#phase').select_option("retired")
    assert page.locator("#count").inner_text()=="32"
    page.locator('[data-mode="archive"]').click()
    page.locator("#search").fill("机场")
    assert 0<int(page.locator("#count").inner_text())<=41
    page.locator("#search").fill("")
    page.locator('#action').select_option("traffic")
    assert page.locator("#count").inner_text()=="21"
    page.locator('#action').select_option("all")
    # Click a real Leaflet marker and verify actual source-linked detail in the sidebar.
    first=page.evaluate("window.__ENVIRONMENT_MAP__.getRows()[0].id")
    page.evaluate("""id => window.__ENVIRONMENT_MAP__.getMarkers().get(id).fire('click')""",first)
    assert page.evaluate("window.__ENVIRONMENT_MAP__.getSelected()")==first
    assert page.locator("#detail").is_visible()
    assert page.locator("#detail .env-sources a[href^='https://']").count()>=1
    assert page.locator("#detail .env-detail-section").count()>=3
    page.locator("#closeDetail").click()
    assert page.locator("#detail").is_hidden()
    page.locator("#recordDrawer summary").click()
    assert page.locator("#entries .env-entry").count()==18
    page.locator("#moreRecords").click()
    assert page.locator("#entries .env-entry").count()==41
    page.locator("#entries .env-entry").first.click()
    assert page.locator("#detail").is_visible()
    assert page.evaluate("window.__ENVIRONMENT_MAP__.map.getZoom()")>=8
    page.locator("#viewGermany").click()
    assert page.evaluate("window.__ENVIRONMENT_MAP__.map.getZoom()")<8
    if mobile:
        assert page.locator(".environment-sidebar").is_visible()
        assert page.evaluate("document.body.scrollWidth <= innerWidth+3")
    else:
        assert page.evaluate("document.querySelector('.environment-sidebar').getBoundingClientRect().left > innerWidth*0.55")
    page.screenshot(path="/tmp/environment-06-"+("mobile" if mobile else "desktop")+".png",full_page=True)
    assert not errors,errors
    print("PASS Environment 06",width,"x",height,"Leaflet, OSM fallback, 16 states, 154 sourced records, all modes, drilldown, responsive",flush=True)
    page.close()

if __name__=="__main__":
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(headless=True)
        try:
            check(browser)
            check(browser,True)
        finally:
            browser.close()
