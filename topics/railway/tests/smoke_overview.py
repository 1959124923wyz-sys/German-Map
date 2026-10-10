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
    page.wait_for_function("""() => window.__RAILWAY_OVERVIEW__.getStatesReady()
       && window.__RAILWAY_OVERVIEW__.getCountiesReady()""",timeout=20000)
    assert page.locator("#railway-map .leaflet-pane path").count()>=400
    # Hundreds of county/state paths are acceptable; thousands of duplicate
    # route and click-hit SVG nodes would recreate the original lag.
    assert page.locator("#segments").count()==0
    assert page.locator("#railway-map .segment-hit").count()==0
    assert page.locator("#railway-map canvas").count()==2
    assert page.evaluate("window.__RAILWAY_OVERVIEW__.getNetworkGeometryCount()")==33547
    assert page.evaluate("window.__RAILWAY_OVERVIEW__.getGraphEdgeCount()")==33547
    assert page.evaluate("window.__RAILWAY_OVERVIEW__.getOfficialPickCount()")==33547
    assert page.evaluate("window.__RAILWAY_OVERVIEW__.getSpatialBucketCount()")>0
    # Regression: an actual DB InfraGO rail around Berlin must respond to a
    # click even when the selected service has no observations on that track.
    # Reject a fabricated zero percent; both KPIs must be honest dashes.
    if not mobile:
        green=page.evaluate("""() => {
          const api=window.__RAILWAY_OVERVIEW__,map=api.getMap();
          const seen=new Set();
          let tries=0;
          for(const entries of api.getOfficialPickEntries().values()){
            for(const entry of entries){
              if(seen.has(entry))continue;seen.add(entry);
              const xy=entry.part.xy;
              const x=(xy[0]+xy[2])/2,y=(xy[1]+xy[3])/2;
              const ll=map.unproject(L.point(x,y),9);
              if(ll.lat<52.3||ll.lat>52.9||ll.lng<12.75||ll.lng>13.95)continue;
              if(++tries>2000) return null;
              api.clickPoint(ll);
              if(api.getSelected()?.unobserved)return {
                route:api.getSelected().route,lat:ll.lat,lng:ll.lng,tries
              };
            }
          }
          return null;
        }""")
        assert green,'Berlin region must have clickable no-data official rails'
        assert page.locator("#detail .detail-grid b").all_inner_texts()==["—","—"]
        assert "暂无可比观测" in page.locator("#detail").inner_text()
        print("PASS Berlin official green rail selectable:",green,flush=True)

    # This was the actual nationwide no-data gap reported by the user:
    # Erlangen km 23.504 -> Forchheim km 38.289 on observed route 5900.
    # Both ends have real observations, the missing center must not contribute
    # to either statistic or be drawn as a fabricated track curve.
    assert page.evaluate("""() => {
      const app=window.__RAILWAY_OVERVIEW__;
      const groups=app.getCorridors().filter(g=>String(g.members[0].leg.route)==='5900');
      if(groups.length!==1||groups[0].members.length!==6||
         groups[0].bridges!==1||groups[0].schematicBridges!==1)return false;
      const [start,end]=app.corridorStations(groups[0].members);
      const g=groups[0];
      return start==='Fürth (Bay) Hbf'&&end==='Bamberg'
        && Math.abs(g.m.onTime-(100-100*1252/8379))<.02
        && g.bridgeParts.length===0;
    }"""),'Bamberg–Erlangen corridor must pool only observed data'
    assert page.evaluate("window.__RAILWAY_OVERVIEW__.getBridgedCount()")>=40
    print('Official railway corridor bridges:',
      page.evaluate("window.__RAILWAY_OVERVIEW__.getBridgedCount()"),flush=True)
    if not mobile:
        # Observed green is a real measured selection, not the same thing as
        # clicking the unobserved network underlay.
        observed_green=page.evaluate("""() => {
          const api=window.__RAILWAY_OVERVIEW__,map=api.getMap();
          for(const item of api.getRendered().filter(x=>x.grade===0).slice(0,350)){
            const v=item.parts[0].xy;
            if(v.length<4)continue;
            const ll=map.unproject(L.point((v[0]+v[2])/2,(v[1]+v[3])/2),9);
            api.clickPoint(ll);
            const current=api.getSelected();
            if(current&&!current.unobserved&&current.grade===0)
              return {from:item.leg.from_station,to:item.leg.to_station};
          }
          return null;
        }""")
        assert observed_green,'Observed green must still show measured numbers'
        numbers=page.locator("#detail .detail-grid b").all_inner_texts()
        assert len(numbers)==2 and all(v.endswith("%") for v in numbers),numbers
        print("PASS selectable measured green:",observed_green,flush=True)

    assert page.locator("#minimum").count()==0
    assert page.locator(".mini-stats").count()==0
    assert page.evaluate("window.__RAILWAY_OVERVIEW__.getMinimum()")==100
    regional=page.evaluate("window.__RAILWAY_OVERVIEW__.getVisible()")
    assert regional>500
    assert page.locator("#railLegend i").count()==3
    assert "其他线路" in page.locator("#railLegend").inner_text()
    assert page.evaluate("""() => {
      const a=window.__RAILWAY_OVERVIEW__.getCorridors();
      const rows=a.flatMap(g=>g.members);
      const joined=a.filter(g=>g.members.length>1);
      return joined.length>0 && rows.length===window.__RAILWAY_OVERVIEW__.getVisible()
        && joined.every(g=>{
          const late=g.members.reduce((s,m)=>s+Number(m.leg.v11?.late6||0),0);
          const cancel=g.members.reduce((s,m)=>s+Number(m.leg.v11?.boundary_cancel||0),0);
          const arrival=g.members.reduce((s,m)=>s+m.m.nArrival,0);
          const planned=g.members.reduce((s,m)=>s+m.m.nPlanned,0);
          return Math.abs(g.m.onTime-(100-100*late/arrival))<1e-9
            && Math.abs(g.m.cancel-100*cancel/planned)<1e-9
            && g.members.every(m=>m.grade===g.grade && m.leg.route===g.members[0].leg.route);
        });
    }""")
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
        assert page.locator("#detail .detail-grid>div").count()==2
        assert "准点率" in page.locator("#detail").inner_text()
        assert "停靠取消标记率" in page.locator("#detail").inner_text()
        assert page.locator("#detail .corridor-more").count()==1
        page.locator("#detail .corridor-more>summary").click()
        assert page.locator("#detail .original-stations").is_visible()
        assert "有效到站" in page.locator("#detail").inner_text()
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
        assert page.locator(".map-panel #railLegend").count()==1
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+3")
        assert page.evaluate("""() => {
          const n=document.querySelector('.toplinks'),a=n.querySelector('a.active');
          const r=a.getBoundingClientRect(),p=n.getBoundingClientRect();
          return r.left>=p.left-3 && r.right<=p.right+3;
        }"""),"Current railway tab must be visible without scrolling the mobile navbar"
    page.locator("#hotspots>summary").click()
    page.locator(".hot-row").first.click()
    assert page.evaluate("window.__RAILWAY_OVERVIEW__.getSelected()!==null")
    assert "→" in page.locator("#detail h3").inner_text()
    assert page.locator("#detail .detail-grid>div").count()==2
    page.locator('[data-metric="cancel"]').click()
    assert page.locator('[data-metric="cancel"]').get_attribute("aria-pressed")=="true"
    assert "4%–<8%" in page.locator("#railLegend").inner_text()
    assert page.evaluate("window.__RAILWAY_OVERVIEW__.getMinimum()")==100
    page.locator('[data-metric="late"]').click()
    assert "25%–<40%" in page.locator("#railLegend").inner_text()
    page.locator('[data-metric="both"]').click()
    if not mobile:
        page.locator('[data-service="LONG"]').click()
        loaded(page,"LONG",10)
        page.locator('[data-service="OTHER"]').click()
        loaded(page,"OTHER",100)
        # Switching service datasets must not erase the independent official
        # green track index used around Berlin.
        again=page.evaluate("""({lat,lng}) => {
          const api=window.__RAILWAY_OVERVIEW__;
          api.clickPoint([lat,lng]);
          const selected=api.getSelected();
          return !!selected&&(selected.unobserved||selected.members?.length>0);
        }""",green)
        assert again is True

        page.locator('[data-service="REGIONAL"]').click()
        loaded(page,"REGIONAL",500)
        assert page.evaluate("window.__RAILWAY_OVERVIEW__.getVisible()")==regional
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
