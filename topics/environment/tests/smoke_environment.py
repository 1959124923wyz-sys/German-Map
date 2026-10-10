#!/usr/bin/env python3
"""Environment 06: evidence semantics, shared Leaflet map and responsive UI."""
import os
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[3]
ASSET=ROOT/"node_modules/leaflet/dist"
BASE=os.getenv("GERMAN_MAP_TEST_BASE","http://127.0.0.1:8765/")
EXPECTED={"all":154,"archive":41,"policy":10,"project":11,"facility":92}

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
    page.wait_for_function("""() => window.__ENVIRONMENT_MAP__?.getMarkerCount()===154
        && window.GermanEnvironment06Data?.length===154
        && window.__ENVIRONMENT_TAXONOMY__?.all===154
        && document.querySelectorAll('#environment-map .leaflet-marker-icon.env-marker-icon').length>=40""",timeout=30000)
    assert page.locator(".modebar a.modebtn").count()>=8
    assert page.locator('.modebar a[href="../infrastructure/"]').count()==1
    assert page.locator(".modebar .modebtn.active").inner_text()=="环保争议"
    assert page.locator("#environment-map .leaflet-control-zoom-in").is_visible()
    assert page.locator("#environment-map .leaflet-tile-pane").count()==1
    assert page.locator("#environment-map .crime-city-label").count()>=5
    assert page.locator("#summaryPanel .area-title").is_hidden()
    # The category tabs are the only navigation/filter controls in the sidebar.
    for removed in ("#taxonomyGuide","#mapTools","#org","#search","#action","#phase",
                    "#clearFilters","#filterState",'[data-shortcut]'):
        assert page.locator(removed).count()==0,removed
    assert "街道底图" in page.locator("#mapStatus").inner_text() or "底图" in page.locator("#mapStatus").inner_text()

    facts=page.evaluate(r"""() => {
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
    page.wait_for_function("""() => window.__ENVIRONMENT_MAP__.map.getPane('environmentStates')?.querySelectorAll('path').length>=16""",timeout=20000)
    assert page.locator('[data-mode]').count()==5
    census=page.evaluate("window.__ENVIRONMENT_TAXONOMY__")
    assert census=={"all":154,"archive":41,"policy":10,"project":11,"facility":92},census
    assert census["archive"]+census["policy"]+census["project"]+census["facility"]==census["all"]
    for mode,expected in EXPECTED.items():
        button=page.locator('[data-mode="'+mode+'"]')
        assert button.locator(".env-tab-count").inner_text()==str(expected),mode
        button.click()
        assert button.get_attribute("aria-pressed")=="true"
        assert page.locator("#count").inner_text()==str(expected),mode
        assert page.evaluate("window.__ENVIRONMENT_MAP__.getMarkerCount()")==expected,mode
        assert page.locator("#listCount").inner_text()==str(expected)+" 条",mode

    page.locator('[data-mode="project"]').click()
    project=page.evaluate("window.__ENVIRONMENT_MAP__.getRows().map(e=>e.kind)")
    assert project.count("organization")==10 and project.count("facility_story")==1,project
    page.locator('[data-mode="facility"]').click()
    assert "未来退出计划" in page.locator("#legend").inner_text()
    assert page.locator("#count").inner_text()=="92"
    page.locator('[data-mode="archive"]').click()
    assert "交通干扰" in page.locator("#legend").inner_text()
    assert page.locator("#count").inner_text()=="41"
    page.locator('[data-mode="all"]').click()
    assert page.locator("#count").inner_text()=="154"
    assert int(page.locator("#sourceCount").inner_text())>=100
    # Preserve detail links and the list navigation with no secondary filters.
    page.locator('[data-mode="archive"]').click()
    # Click a real Leaflet marker and verify actual source-linked detail in the sidebar.
    first=page.evaluate("window.__ENVIRONMENT_MAP__.getRows()[0].id")
    page.evaluate("""id => window.__ENVIRONMENT_MAP__.getMarkers().get(id).fire('click')""",first)
    assert page.evaluate("window.__ENVIRONMENT_MAP__.getSelected()")==first
    assert page.locator("#detail").is_visible()
    assert page.locator("#summaryPanel .area-title").is_visible()
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
    zoom=page.evaluate("window.__ENVIRONMENT_MAP__.map.getZoom()")
    page.locator("#environment-map .leaflet-control-zoom-out").click()
    page.wait_for_function("(z) => window.__ENVIRONMENT_MAP__.map.getZoom() < z",arg=zoom,timeout=10000)
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
