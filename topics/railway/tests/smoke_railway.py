#!/usr/bin/env python3
"""07 staging: verify real railway geography, visual shell and line inspection.

The fixture is the latest *available* locally authored official-geometry draft.
This is a staging smoke; it does not authorize production release.
"""
from pathlib import Path
import os
import re
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[3]
LEAFLET=ROOT/"node_modules/leaflet/dist"
BASE=os.environ.get("GERMAN_MAP_TEST_BASE","http://127.0.0.1:8765")

def run(browser, mobile=False):
    width,height=(390,844) if mobile else (1440,900)
    page=browser.new_page(viewport={"width":width,"height":height})
    errors=[]
    page.on("pageerror",lambda err:errors.append(str(err)))
    page.route(re.compile(r"https://unpkg\.com/leaflet@1\.9\.4/dist/leaflet\.js"),
        lambda route:route.fulfill(path=str(LEAFLET/"leaflet.js"),content_type="application/javascript"))
    page.route(re.compile(r"https://unpkg\.com/leaflet@1\.9\.4/dist/leaflet\.css"),
        lambda route:route.fulfill(path=str(LEAFLET/"leaflet.css"),content_type="text/css"))
    page.route("**/tile.openstreetmap.org/**",lambda route:route.abort())
    response=page.goto(BASE+"/topics/railway/",wait_until="domcontentloaded",timeout=60000)
    assert response and response.ok,("railway shell HTTP",response.status if response else None)
    page.wait_for_function("""() => window.__RAILWAY_07__?.getGeometryCount()===33547
      && window.__RAILWAY_07__?.getRouteCount()===1546
      && document.querySelector('#routeCount')?.textContent==='1,546'
      && document.querySelector('#railway-map .leaflet-control-zoom-in')
    """,timeout=95000)
    assert page.locator('.modebar .modebtn').count()==6
    assert page.locator('.modebar .modebtn.active').inner_text()=="铁路交通"
    assert page.locator("#railway-map .leaflet-tile-pane").count()==1
    assert page.locator("#railway-map .rail-canvas").count()==1
    assert page.locator("#railway-map .crime-city-label").count()>=5
    page.wait_for_function("""() => window.__RAILWAY_07__.getMap()
     .getPane('railway-states')?.querySelectorAll('path').length>=16""",timeout=30000)
    d=page.evaluate("""() => {
      const R=window.__RAILWAY_07__, data=R.getSource();
      return { routes:data.routes.length,sections:data.sections.length,
        states:Object.keys(data.states).length, sourceRows:data.qa.source_rows,
        germanyRows:data.qa.in_german_states, geometry:data.qa.source_line_geometries,
        missing:data.qa.missing_wkt_records, selected:R.getSelected(),
        rendered:R.getVisibleGeometryCount()};
    }""")
    assert d["routes"]==1546 and d["sections"]==33547 and d["states"]==16,d
    assert d["sourceRows"]==33425 and d["germanyRows"]==33376,d
    assert d["geometry"]==33547 and d["missing"]==0,d
    assert d["selected"] is None and d["rendered"]>500,d
    for mode in ("elec","tracks","speed"):
        page.locator('[data-style="'+mode+'"]').click()
        assert page.locator('[data-style="'+mode+'"]').get_attribute("aria-pressed")=="true"
        assert page.evaluate("window.__RAILWAY_07__.getStyle()")==mode
        assert page.locator("#legend .rail-legend-item").count()>=3
    page.locator("#routeSearch").fill("1733")
    assert page.locator("#matches button").count()>0
    page.locator("#matches button").first.click()
    assert page.locator("#detailBadge").inner_text()=="#1733"
    assert page.locator("#routeLabel").inner_text()=="该线路原始分段"
    assert page.locator("#facts .rail-fact").count()>=8
    assert page.locator("#stops").is_visible()
    assert page.evaluate("window.__RAILWAY_07__.getSelected()") is not None
    assert page.evaluate("window.__RAILWAY_07__.getMap().getZoom()")>=5
    assert page.evaluate("window.__RAILWAY_07__.search('Kassel').length")>0
    page.locator("#clearRoute").click()
    assert page.locator("#routeCount").inner_text()=="1,546"
    assert page.locator("#selectedTools").is_hidden()
    assert page.evaluate("window.__RAILWAY_07__.getSelected()") is None
    assert page.locator('.rail-source').count()==1
    if mobile:
        assert page.locator('.railway-sidebar').is_visible()
        assert page.evaluate("document.body.scrollWidth <= innerWidth+3")
        visible=page.evaluate("""() => {
          const active=document.querySelector('.modebar .modebtn.active').getBoundingClientRect();
          const nav=document.querySelector('.modebar').getBoundingClientRect();
          return active.left >= nav.left-2 && active.right <= nav.right+2;
        }""")
        assert visible, "The railway tab must be visible on mobile without manual horizontal scrolling"
        assert page.evaluate("""() => {
          const m=window.__RAILWAY_07__.getMap();
          return m.getBounds().contains(L.latLngBounds([[47.05,5.45],[55.15,15.65]]));
        }"""), "National network must fit inside the mobile map at overview zoom"
    else:
        assert page.evaluate("""document.querySelector('.railway-sidebar')
          .getBoundingClientRect().left > innerWidth*.55""")
    page.screenshot(path="/tmp/railway07-"+("mobile" if mobile else "desktop")+".png",full_page=True)
    assert not errors,errors
    print("PASS 07 staging",width,"x",height,d,flush=True)
    page.close()

if __name__=="__main__":
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        try:
            run(browser)
            run(browser,True)
        finally:browser.close()
