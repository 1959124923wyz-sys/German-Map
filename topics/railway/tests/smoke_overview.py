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
      return v?.getService()===service && v.getNetworkReady() &&
       v.getNetworkGeometryCount()===33547 &&
       v.getOfficialPickCount()===33547 &&
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
    assert page.locator(".toplinks a").count()==7
    assert page.locator("#railway-map canvas").count()==1
    assert page.locator("#railway-map .railway-network").count()==0
    backbone=page.evaluate("window.__RAILWAY_OVERVIEW__.getBackboneCoverage()")
    print("OFFICIAL BACKBONE COVERAGE:",backbone,flush=True)
    assert backbone["all"]==33547 and backbone["sections"]>0
    assert page.evaluate("window.__RAILWAY_OVERVIEW__.getCompleteBackboneRoutes()")>100
    assert page.locator('script[src="data/data-sections-00.js"]').count()==1
    assert page.locator('script[src="data/data-sections-01.js"]').count()==1
    assert page.locator('script[src="data/data-sections-02.js"]').count()==1
    assert page.locator("#minimum").count()==0
    assert page.locator("[data-metric]").count()==0

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
       official:api.getNetworkGeometryCount(),active:api.getBackboneCoverage().sections,
       risky:api.getDrawnObserved().filter(x=>x.grade>0).length,
       weighted:weights,thuringia:thuringia.slice(0,15).map(g=>({
        label:g.serviceName,from:g.cityFrom,to:g.cityTo,km:g.km,
        edges:g.observedEdges,grade:g.grade
       }))};
    }""")
    print("CITY ROUTE AUDIT:",audit,flush=True)
    assert audit["weighted"]
    assert audit["official"]==33547
    assert audit["active"]>0 and audit["risky"]>0
    assert audit["original"]==4218
    assert audit["count"]>=30
    assert audit["physical"]>=audit["count"]
    assert audit["hidden"]>0
    assert audit["thuringia"],'Erfurt/Ilmenau/Coburg city paths missing'
    assert all(g["from"]!=g["to"] for g in audit["thuringia"])
    assert audit["count"]<550, "Public map must not restore 600+ station fragments"
    assert audit["hidden"]>300


    if not mobile:
        colour_report=page.evaluate("""()=>{
          const api=window.__RAILWAY_OVERVIEW__,map=api.getMap();
          let checked=0,mixed=0,compact=0,attempts=0,clicked=0,same=0;
          const examples=[],mismatches=[];
          for(const group of api.getCityCorridors().filter(g=>g.members.length>=2).slice(0,85)){
            const runs=api.getColourRuns(group);
            checked++;
            const grades=new Set(runs.map(r=>r.grade));
            if(grades.size<2)continue;
            mixed++;
            const eligible=runs.filter(r=>r.members.length>=2&&r.grade>0);
            compact+=eligible.length;
            if(examples.length<7)examples.push({from:group.cityFrom,to:group.cityTo,
              grades:runs.map(r=>r.grade),pieces:runs.map(r=>r.members.length)});
            for(const run of eligible.slice(0,2)){
              // Click on the rendered observed curve rather than an
              // adjacent parallel official track during the national test.
              const source=run.members.find(x=>x.grade===run.grade)||run.members[0];
              const piece=source.parts[Math.floor(source.parts.length/2)];
              const v=piece.xy;
              const idx=Math.floor((v.length/2-1)/2)*2;
              const j=Math.min(v.length-2,idx+2);
              // Real user clicks a stroke interior, not a shared station
              // vertex that also belongs to a different-colour neighbour.
              const ll=map.unproject(L.point((v[idx]+v[j])/2,(v[idx+1]+v[j+1])/2),9);
              api.clickPoint(ll);attempts++;
              const current=api.getCurrentColourRun();
              if(current){
                clicked++;
                if(current===run)same++;
                else mismatches.push({from:group.cityFrom,to:group.cityTo,
                  target:run.grade,selected:current.grade,correctRoute:
                  run.route===current.route,targetLength:run.parts.length,
                  currentLength:current.parts.length});
              }
            }
          }
          return {checked,mixed,compact,attempts,clicked,same,examples,mismatches};
        }""")
        print('REAL SAME-COLOUR RUN AUDIT:',colour_report,flush=True)
        assert colour_report["mixed"]>=1,colour_report
        assert colour_report["compact"]>=1,colour_report
        assert colour_report["same"]>=1,colour_report

    if not mobile:
        path_report=page.evaluate("""()=>{
          const api=window.__RAILWAY_OVERVIEW__;
          const chosen=api.getCityCorridors().filter(g=>g.members.length>=2);
          const output=[];
          for(const g of chosen.slice(0,28)){
            const traced=api.traceVerifiedCorridor(g);
            output.push({from:g.cityFrom,to:g.cityTo,route:g.members[0].leg.route,
              count:g.members.length,official:traced?.length||0});
          }
          return output;
        }""")
        verified=[x for x in path_report if x["official"]>0]
        print('REAL official A-to-B verified paths:',verified[:12],
          'count',len(verified),'checked',len(path_report),flush=True)
        # Real source geometries can have junction gaps, but at least some
        # physically verified city corridors must select a whole curve.
        assert len(verified)>=1, 'Full railway highlight never follows verified A-to-B geometry'

    if not mobile:
        # Unobserved green official line must be selectable rather than absent.
        green=page.evaluate("""() => {
          const api=window.__RAILWAY_OVERVIEW__,map=api.getMap();
          const seen=new Set();
          for(const entries of api.getOfficialPickEntries().values()){
            for(const entry of entries){
              if(seen.has(entry))continue;seen.add(entry);
              if(seen.size>6000)return null;
              const xy=entry.part.xy;
              const ll=map.unproject(L.point((xy[0]+xy[2])/2,(xy[1]+xy[3])/2),9);
              if(ll.lat<49||ll.lat>54||ll.lng<8||ll.lng>15)continue;
              api.clickPoint(ll);
              const g=api.getSelected();
              if(g?.unobserved&&g.parts.length>1)return {
                 route:g.route,parts:g.parts.length,lat:ll.lat,lng:ll.lng
              };
            }
          }
          return null;
        }""")
        assert green,'Real unmeasured DB railway must have connected green selection'
        assert page.locator("#detail .detail-grid b").all_inner_texts()==["—","—"]
        print('PASS nationwide continuous no-data green railway:',green,flush=True)
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
    if not mobile:
        page.locator('[data-service="LONG"]').click()
        loaded(page,"LONG",10)
        page.locator('[data-service="OTHER"]').click()
        loaded(page,"OTHER",100)
        page.locator('[data-service="REGIONAL"]').click()
        loaded(page,"REGIONAL",500)
    assert not errors,errors
    page.screenshot(path=str(ART/("railway-mobile.png" if mobile else "railway-desktop.png")),full_page=True)
    print("PASS continuous backbone",width,height,audit["count"],audit["official"],flush=True)
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
