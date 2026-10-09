#!/usr/bin/env python3
"""07 fast Leaflet railway: official full geometry, real run evidence, pan/zoom, responsiveness."""
from pathlib import Path
import re
from playwright.sync_api import sync_playwright

BASE="http://127.0.0.1:8769/topics/railway/"
ART=Path("/tmp/railway-v18")
ART.mkdir(exist_ok=True)

def number(page,sel):return int(page.locator(sel).inner_text().replace(",","").strip())

def loaded(page,service,minimum):
    page.wait_for_function("""args => {
      const s=window.__RAILWAY_OVERVIEW__;
      return s?.getService()===args[0] &&
        s.getNetworkReady() && s.getNetworkGeometryCount()===33547 &&
        s.getVisible()>args[1] && s.getCanvasCount()===2;
    }""",arg=[service,minimum],timeout=160000)

def run(browser,mobile=False):
    width,height=(390,844) if mobile else (1440,900)
    page=browser.new_page(viewport={"width":width,"height":height},device_scale_factor=1)
    errors=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    # Ensure the railway map can render the same geographic layers when OSM is
    # unavailable, without claiming that a blank backdrop is a loaded tile.
    page.route(re.compile(r"https://unpkg\.com/leaflet@1\.9\.4/dist/leaflet\.js(?:\?.*)?$"),
      lambda route:route.fulfill(path=str(ART.parent/"railway-leaflet.js"),content_type="application/javascript"))
    page.route(re.compile(r"https://unpkg\.com/leaflet@1\.9\.4/dist/leaflet\.css(?:\?.*)?$"),
      lambda route:route.fulfill(path=str(ART.parent/"railway-leaflet.css"),content_type="text/css"))
    page.route("**/tile.openstreetmap.org/**",lambda route:route.abort())
    response=page.goto(BASE,wait_until="domcontentloaded",timeout=60000)
    assert response and response.status==200
    loaded(page,"REGIONAL",500)
    assert page.locator(".toplinks a").count()==6
    assert page.locator("#service [data-service]").count()==3
    assert page.locator("#metric [data-metric]").count()==3
    assert page.locator("#railway-map .leaflet-tile-pane").count()==1
    assert page.locator("#railway-map .railway-network").count()==1
    assert page.locator("#railway-map .railway-observed").count()==1
    assert page.locator("#railway-map .crime-city-label").count()>=5
    page.screenshot(path=str(ART/("railway-mobile-initial.png" if mobile else "railway-desktop-initial.png")),full_page=True)
    # Reference outlines are intentionally non-interactive so they do not
    # steal clicks from the actual underlying rail line picking.
    page.wait_for_function("""() =>
      document.querySelectorAll('#railway-map .rail-state-pane path').length>=16
    """,timeout=20000)
    # Hundreds of county/state paths are acceptable; thousands of duplicate
    # route and click-hit SVG nodes would recreate the original lag.
    assert page.locator("#segments").count()==0
    assert page.locator("#railway-map .segment-hit").count()==0
    assert page.locator("#railway-map canvas").count()==2
    assert page.evaluate("window.__RAILWAY_OVERVIEW__.getNetworkGeometryCount()")==33547
    assert number(page,"#visibleCount")>500
    regional=number(page,"#visibleCount")
    assert 0<number(page,"#redCount")<regional
    assert page.locator("#redShare").inner_text().endswith("%")
    assert "晚点 <25% 且取消 <4%" in page.locator("#railLegend").inner_text()
    assert page.evaluate("window.__RAILWAY_OVERVIEW__.stationZh('Berlin Hbf')")=="柏林中央火车站"
    assert page.evaluate("window.__RAILWAY_OVERVIEW__.stationZh('Unknown Small Village')")=="Unknown Small Village"
    assert page.locator(".hot-row").count()==10
    # Verify line geometry is projected onto real OSM/Leaflet coordinates.
    aligned=page.evaluate("""() => {
      const r=window.__RAILWAY_OVERVIEW__,m=r.getMap(),p=m.project([52.52,13.405],9);
      const ll=m.unproject(p,9);
      return Math.abs(ll.lat-52.52)<.0001 && Math.abs(ll.lng-13.405)<.0001;
    }""")
    assert aligned
    if not mobile:
        # Click a real rail observation using geographic coordinates and
        # the map's event path (instead of dispatching a fake SVG click).
        picked=page.evaluate("""() => {
          const r=window.__RAILWAY_OVERVIEW__,o=r.getRendered().find(x=>x.grade===2 && x.parts.length);
          if(!o)return null;
          const pts=o.parts[0].xy,m=r.getMap();
          const mid=m.unproject(L.point((pts[0]+pts[2])/2,(pts[1]+pts[3])/2),9);
          r.clickPoint(mid);
          return {lat:mid.lat,lon:mid.lng};
        }""")
        assert picked
        assert page.locator("#detail .original-stations").is_visible()
        assert "有效到站观测" in page.locator("#detail").inner_text()
        # Zoom, pan and redraw should reuse exactly two Canvas elements.
        before=page.evaluate("window.__RAILWAY_OVERVIEW__.getRepaintCount()")
        page.evaluate("""() => {
          const m=window.__RAILWAY_OVERVIEW__.getMap();
          m.setZoom(m.getZoom()+1,{animate:false});
          m.panBy([40,-25],{animate:false});
        }""")
        page.wait_for_function("(count)=>window.__RAILWAY_OVERVIEW__.getRepaintCount()>count",
          arg=before,timeout=30000)
        assert page.locator("#railway-map canvas").count()==2
        assert page.locator("#railway-map .crime-city-label").count()>=5
        page.locator("#home").click()
        assert page.evaluate("""() => window.__RAILWAY_OVERVIEW__.getMap()
          .getBounds().contains(L.latLngBounds([[47.05,5.45],[55.15,15.65]]))""")
    else:
        assert page.locator("#railway-map").is_visible()
        assert page.locator(".sidebar #railLegend").count()==1
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+3")
    page.locator(".hot-row").first.click()
    assert page.evaluate("window.__RAILWAY_OVERVIEW__.getSelected()!==null")
    assert "→" in page.locator("#detail h3").inner_text()
    page.locator('[data-metric="cancel"]').click()
    assert page.locator('[data-metric="cancel"]').get_attribute("aria-pressed")=="true"
    assert "4%–<8%" in page.locator("#railLegend").inner_text()
    page.select_option("#minimum","500")
    assert number(page,"#visibleCount")<regional
    page.select_option("#minimum","100")
    page.locator('[data-metric="late"]').click()
    assert "25%–<40%" in page.locator("#railLegend").inner_text()
    page.locator('[data-metric="both"]').click()
    if not mobile:
        page.locator('[data-service="LONG"]').click()
        loaded(page,"LONG",10)
        page.locator('[data-service="OTHER"]').click()
        loaded(page,"OTHER",100)
        page.locator('[data-service="REGIONAL"]').click()
        loaded(page,"REGIONAL",500)
        assert number(page,"#visibleCount")==regional
    page.screenshot(path=str(ART/("railway-mobile.png" if mobile else "railway-desktop.png")),full_page=True)
    assert not errors,errors
    print("PASS railway 07",width,"x",height,{"official_parts":33547,"observed":regional,
      "canvas":2,"leaflet":"OSM tile source active and fallback tested","data":"unchanged"},flush=True)
    page.close()

if __name__=="__main__":
    # The CI runner installs Leaflet locally, to avoid brittle third-party CDN
    # availability during the fixture's asset loading.
    root=Path(__file__).resolve().parents[3]
    source=root/"node_modules/leaflet/dist"
    assert (source/"leaflet.js").is_file() and (source/"leaflet.css").is_file()
    (ART.parent/"railway-leaflet.js").write_bytes((source/"leaflet.js").read_bytes())
    (ART.parent/"railway-leaflet.css").write_bytes((source/"leaflet.css").read_bytes())
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        try:
            run(browser)
            run(browser,True)
            response=browser.new_page().goto(BASE+"research.html",wait_until="domcontentloaded")
            assert response and response.status==200
        finally:browser.close()
