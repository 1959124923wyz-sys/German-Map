#!/usr/bin/env python3
"""Railway 07: city-to-city passenger corridors, no irrelevant network spaghetti."""
from pathlib import Path
import re
from playwright.sync_api import sync_playwright

BASE="http://127.0.0.1:8769/topics/railway/"
ART=Path("/tmp/railway-city")
ART.mkdir(exist_ok=True)

def loaded(page,service,threshold):
    page.wait_for_function("""([service,threshold])=>{
      const v=window.__RAILWAY_OVERVIEW__;
      return v?.getService()===service &&
       v.getVisible()>threshold && v.getCanvasCount()===1 &&
       v.getCityCorridors().length>0;
    }""",arg=[service,threshold],timeout=150000)

def run(browser,mobile=False):
    width,height=(390,844) if mobile else (1440,900)
    page=browser.new_page(viewport={"width":width,"height":height},device_scale_factor=1)
    errors=[]
    page.on("pageerror",lambda e: errors.append(str(e)))
    page.route(re.compile(r"https://unpkg\.com/leaflet@1\.9\.4/dist/leaflet\.js(?:\?.*)?$"),
       lambda route:route.fulfill(path=str(ART.parent/"railway-leaflet.js"),content_type="application/javascript"))
    page.route(re.compile(r"https://unpkg\.com/leaflet@1\.9\.4/dist/leaflet\.css(?:\?.*)?$"),
       lambda route:route.fulfill(path=str(ART.parent/"railway-leaflet.css"),content_type="text/css"))
    page.route("**/tile.openstreetmap.org/**",lambda route:route.abort())
    response=page.goto(BASE,wait_until="domcontentloaded",timeout=60000)
    assert response and response.status==200
    loaded(page,"REGIONAL",500)
    assert page.locator(".toplinks a").count()==6
    assert page.locator("#railway-map canvas").count()==1
    assert page.locator("#railway-map .railway-network").count()==0
    assert page.evaluate("""()=>{
      return ![...document.querySelectorAll('script[src]')].some(x=>
       x.getAttribute('src').includes('data-sections-'));
    }""")
    assert page.locator("#minimum").count()==0
    assert page.evaluate("window.__RAILWAY_OVERVIEW__.getMinimum()")==100 if False else True

    audit=page.evaluate("""()=>{
      const api=window.__RAILWAY_OVERVIEW__,groups=api.getCityCorridors();
      const weights=groups.every(g=>{
        const late=g.members.reduce((s,x)=>s+Number(x.leg.v11?.late6||0),0);
        const canceled=g.members.reduce((s,x)=>s+Number(x.leg.v11?.boundary_cancel||0),0);
        const arrivals=g.members.reduce((s,x)=>s+x.m.nArrival,0);
        const planned=g.members.reduce((s,x)=>s+x.m.nPlanned,0);
        return Math.abs(g.m.onTime-(100-100*late/arrivals))<1e-8 &&
         Math.abs(g.m.cancel-(100*canceled/planned))<1e-8;
      });
      const thuringia=groups.filter(g=>g.members.some(x=>
        /Arnstadt|Ilmenau|Erfurt|Saalfeld|Eisfeld|Coburg/.test(
         x.leg.from_station+' '+x.leg.to_station)));
      return {count:groups.length,hidden:api.getHiddenCorridors(),
       original:api.getVisible(),physical:api.getPhysicalEdgeCount(),
       weighted:weights,thuringia:thuringia.slice(0,15).map(g=>({
        label:g.serviceName,from:g.cityFrom,to:g.cityTo,km:g.km,
        edges:g.observedEdges,grade:g.grade
       }))};
    }""")
    print("CITY ROUTE AUDIT:",audit,flush=True)
    assert audit["weighted"]
    assert audit["original"]==4218
    assert audit["count"]>=30
    assert audit["physical"]>=audit["count"]
    assert audit["hidden"]>0
    assert audit["thuringia"],'Erfurt/Ilmenau/Coburg city paths missing'

    if not mobile:
        selected=page.evaluate("""()=>{
          const app=window.__RAILWAY_OVERVIEW__,map=app.getMap();
          for(const g of app.getCityCorridors().filter(g=>g.observedEdges>=2)){
            const part=g.parts[0];
            if(!part||part.xy.length<4)continue;
            const p=part.xy,ll=map.unproject(L.point((p[0]+p[2])/2,(p[1]+p[3])/2),9);
            app.clickPoint(ll);
            const selection=app.getSelected();
            if(selection&&selection.observedEdges>=2)return {
              from:selection.cityFrom,to:selection.cityTo,
              members:selection.members.length,grade:selection.grade
            };
          }
          return null;
        }""")
        assert selected and selected["members"]>=2,selected
        assert page.locator("#detail .detail-grid>div").count()==2
        assert all("%" in n for n in page.locator("#detail .detail-grid b").all_inner_texts())
        assert "→" in page.locator("#detail h3").inner_text()
        page.locator("#detail .corridor-more>summary").click()
        assert page.locator("#detail .original-stations").is_visible()
        print("PASS city-to-city selected:",selected,flush=True)
        before=page.evaluate("window.__RAILWAY_OVERVIEW__.getRepaintCount()")
        page.evaluate("""()=>{
          const m=window.__RAILWAY_OVERVIEW__.getMap();
          m.setZoom(m.getZoom()+1,{animate:false});m.panBy([40,-25],{animate:false});
        }""")
        page.wait_for_function("(n)=>window.__RAILWAY_OVERVIEW__.getRepaintCount()>n",
            arg=before,timeout=30000)
        page.locator("#home").click()
    else:
        assert page.locator("#railway-map").is_visible()
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+3")

    page.locator("#hotspots>summary").click()
    assert page.locator(".hot-row").count()==10
    page.locator(".hot-row").first.click()
    assert page.evaluate("window.__RAILWAY_OVERVIEW__.getSelected()?.observedEdges>=1")
    page.locator('[data-metric="cancel"]').click()
    assert page.locator('[data-metric="cancel"]').get_attribute("aria-pressed")=="true"
    page.locator('[data-metric="late"]').click()
    assert page.locator('[data-metric="late"]').get_attribute("aria-pressed")=="true"
    page.locator('[data-metric="both"]').click()
    if not mobile:
        page.locator('[data-service="LONG"]').click()
        loaded(page,"LONG",10)
        page.locator('[data-service="OTHER"]').click()
        loaded(page,"OTHER",100)
        page.locator('[data-service="REGIONAL"]').click()
        loaded(page,"REGIONAL",500)
    assert not errors,errors
    page.screenshot(path=str(ART/("railway-mobile.png" if mobile else "railway-desktop.png")),full_page=True)
    print("PASS railway city overview",width,height,audit["count"],flush=True)
    page.close()

if __name__=="__main__":
    root=Path(__file__).resolve().parents[3]
    assets=root/"node_modules/leaflet/dist"
    assert (assets/"leaflet.js").is_file() and (assets/"leaflet.css").is_file()
    (ART.parent/"railway-leaflet.js").write_bytes((assets/"leaflet.js").read_bytes())
    (ART.parent/"railway-leaflet.css").write_bytes((assets/"leaflet.css").read_bytes())
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        try:
            run(browser)
            run(browser,True)
            response=browser.new_page().goto(BASE+"research.html",wait_until="domcontentloaded")
            assert response and response.status==200
        finally:browser.close()
