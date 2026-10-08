#!/usr/bin/env python3
"""Browser smoke test for the current modular Germany crime map UI.

Run against a local HTTP server. Checks stable behavior, not legacy UI copy.
"""
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = os.getenv("SMOKE_URL", "http://127.0.0.1:8765/")
SCREENSHOT = Path(os.getenv("SMOKE_SCREENSHOT", "/tmp/germany-crime-map-national.png"))


def capture_errors(page):
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    return errors


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1480, "height": 900}, device_scale_factor=1)
    errors = capture_errors(page)
    page.on("console", lambda msg: print("[browser-console]", msg.text, flush=True)
            if "city detail skipped" in msg.text or "city-local" in msg.text else None)
    page.route("**/tile.openstreetmap.org/**", lambda route: route.abort())

    response = page.goto(URL, wait_until="domcontentloaded", timeout=60000)
    assert response and response.ok, f"HTTP error: {response.status if response else 'none'}"
    page.wait_for_function("""() => {
        const a=window.__CRIME_MAP__;
        return a && a.getCaseData() && a.getPksData() && a.getPropertyData()
          && a.getBerlinViolence() && a.getHeatData() && a.getCountyLayer();
    }""", timeout=30000)
    page.wait_for_timeout(4000)

    initial = page.evaluate("""() => {
        const a=window.__CRIME_MAP__;
        return {
            mode:a.getMode(),
            cases:a.getCaseData().cases.length,
            counties:a.getCountyLayer().getLayers().length,
            data:a.getPksData().meta?.county_count,
            legend:document.querySelector('#legend').textContent,
            area:document.querySelector('#areaName').textContent,
            mapHeight:document.querySelector('#map').getBoundingClientRect().height,
            status:document.querySelector('#mapStatus').textContent
        };
    }""")
    assert initial["mode"] == "violence", initial
    assert initial["cases"] >= 500, initial
    assert initial["counties"] >= 395, initial
    assert initial["mapHeight"] >= 480, initial
    assert initial["area"] and initial["legend"], initial
    SCREENSHOT.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SCREENSHOT), full_page=True)

    # The nationwide map must allow hover/click and replace the side-panel figures.
    county = page.evaluate("""() => {
        const layer=window.__CRIME_MAP__.getCountyLayer().getLayers()
          .find(x=>x.feature && x.feature.properties);
        layer.fire('mouseover');
        layer.fire('click');
        return {
            name:document.querySelector('#areaName').textContent,
            metric:document.querySelector('#areaMetric').textContent,
            rate:document.querySelector('#areaRate').textContent,
            pinned:!!window.__CRIME_MAP__.getPinnedArea()
        };
    }""")
    assert county["pinned"] and county["name"] and county["metric"] and county["rate"], county

    # A state's movable overview can close and reopen on a different state.
    page.click("#viewGermany")
    page.evaluate("""() => {
        const m=window.__CRIME_MAP__.map;
        m.setZoom(6,{animate:false});
    }""")
    page.wait_for_timeout(300)
    states = page.evaluate("""() => {
        const arr=[];
        window.__CRIME_MAP__.map.eachLayer(l=>{
            if(l instanceof L.GeoJSON && l.options?.pane==='statePane')
                arr.push(l);
        });
        const s=arr[0]?.getLayers()||[];
        if(s.length>=2){s[0].fire('click');return {ok:true,first:s[0].feature.properties.name,second:s[1].feature.properties.name};}
        return {ok:false,count:s.length};
    }""")
    assert states["ok"], states
    assert page.locator("#stateDrawer").evaluate("(e)=>e.classList.contains('open')")
    assert page.locator("#stateName").inner_text() == states["first"]
    page.click("#stateClose")
    page.wait_for_timeout(350)
    assert not page.locator("#stateDrawer").evaluate("(e)=>e.classList.contains('open')")
    page.evaluate("""() => {
        const m=window.__CRIME_MAP__.map;
        m.setZoom(6,{animate:false});
    }""")
    page.wait_for_timeout(350)
    second = page.evaluate("""() => {
        let state=null;
        window.__CRIME_MAP__.map.eachLayer(l=>{
            if(l instanceof L.GeoJSON && l.options?.pane==='statePane') state=l;
        });
        const layers=state?.getLayers()||[];
        layers[1]?.fire('click');
        return document.querySelector('#stateName').textContent;
    }""")
    assert second == states["second"], {"expected":states["second"],"actual":second}
    page.click("#stateClose")
    page.wait_for_timeout(900)

    # Real-pointer regression: state drawers must not trap the map.
    # Previous smoke tests only used Leaflet .fire('click'), bypassing actual
    # browser pointer hit-testing and the zoom threshold that caused the bug.
    sequences = [
        ("Sachsen", 51.05, 13.73),
        ("Thüringen", 50.98, 11.02),
        ("Brandenburg", 52.45, 12.65),
        ("Sachsen", 51.05, 13.73),
    ]
    def real_state_click(name, lat, lon):
        page.evaluate("""([lat,lon]) => {
            const m=window.__CRIME_MAP__.map;
            m.stop();
            m.setView([lat,lon],6,{animate:false});
        }""",[lat,lon])
        page.wait_for_timeout(250)
        diagnostic=page.evaluate("""([name,lat,lon]) => {
            const m=window.__CRIME_MAP__.map;
            let obj;
            m.eachLayer(l=>{
                if(l instanceof L.GeoJSON && l.options?.pane==='statePane'){
                    obj=l.getLayers().find(x=>x.feature?.properties?.name===name);
                }
            });
            const p=m.latLngToContainerPoint([lat,lon]),
                host=document.querySelector('#map').getBoundingClientRect();
            return {statePresent:!!obj,contains:!!obj&&
                window.CrimeMapUtils.pointInGeometry(lon,lat,obj.feature.geometry),
                zoom:m.getZoom(),pixel:[host.left+p.x,host.top+p.y],
                drawerOpen:document.querySelector('#stateDrawer').classList.contains('open')};
        }""",[name,lat,lon])
        assert diagnostic["statePresent"] and diagnostic["contains"],diagnostic
        target=page.evaluate("""([x,y]) => ({
            foreground:document.elementFromPoint(x,y)?.outerHTML?.slice(0,380),
            stack:document.elementsFromPoint(x,y).slice(0,6).map(e=>({
                node:e.tagName,cls:e.getAttribute('class'),pane:e.closest('.leaflet-pane')?.className
            }))
        })""",diagnostic["pixel"])
        print("[state-hit-target]",json.dumps({"name":name,"target":target},ensure_ascii=False),flush=True)
        page.mouse.click(*diagnostic["pixel"])
        page.wait_for_timeout(220)
        actual=page.locator("#stateName").inner_text()
        assert page.locator("#stateDrawer").evaluate("(e)=>e.classList.contains('open')"),diagnostic
        assert actual==name,{"expected":name,"actual":actual,**diagnostic}
        assert abs(page.evaluate("window.__CRIME_MAP__.map.getZoom()")-6)<.01, (
            "Opening a state must never change zoom")
        return diagnostic

    for i,(name,lat,lon) in enumerate(sequences):
        real_state_click(name,lat,lon)
        if i==0:
            # Switching directly from one open state drawer to another
            # must work without requiring the user to close the panel.
            real_state_click("Thüringen",50.98,11.02)
        page.locator("#stateClose").click()
        assert not page.locator("#stateDrawer").evaluate("(e)=>e.classList.contains('open')")
        assert abs(page.evaluate("window.__CRIME_MAP__.map.getZoom()")-6)<.01
    print("[state-pointer-regression] PASS: repeated real mouse state clicks and close/reopen",flush=True)

    # Berlin's official annual violence layer and rolling 90-day property layer.
    page.evaluate("() => { window.__CRIME_MAP__.map.stop(); }")
    page.click("#focusBerlin")
    page.wait_for_timeout(1300)
    berlin_state=page.evaluate("""() => {
        const a=window.__CRIME_MAP__;
        return {zoom:a.map.getZoom(),mode:a.getMode(),features:a.getBerlinLayer()?.getLayers()?.length||0};
    }""")
    assert berlin_state["zoom"]>=7.5 and berlin_state["features"]>50, berlin_state
    page.evaluate("""() => {
        window.__CRIME_MAP__.getBerlinLayer().getLayers()[0].fire('mouseover');
    }""")
    assert "Berlin" in page.locator("#areaMetric").inner_text() or "柏林" in page.locator("#areaMetric").inner_text()

    page.click("#modeProperty")
    page.wait_for_function("""() => {
        const a=window.__CRIME_MAP__;
        return a.getMode()==='property' && a.getHeatLayer()?.getLayers()?.length>20;
    }""", timeout=15000)
    assert not page.locator("#propertyLayers").evaluate("(e)=>e.hidden")
    assert page.locator("#violenceLayers").evaluate("(e)=>e.hidden")
    page.locator("#propertyMetric").select_option("bicycle_theft")
    page.wait_for_timeout(300)
    assert page.locator("#legend").inner_text()

    # Generic city layer must still load without producing JS errors.
    page.locator("#propertyMetric").select_option("property_total")
    page.wait_for_function("!!document.getElementById('focusCity_hamburg')",timeout=15000)
    page.click("#focusCity_hamburg")
    page.wait_for_function("""() => {
        const m=window.__CRIME_MAP__.map;
        let hasCity=false;
        m.eachLayer(l=>{
            if(l instanceof L.GeoJSON && l.getLayers()?.some(x=>x.feature?.properties?.city==='Hamburg'))
                hasCity=true;
        });
        return m.getZoom()>=8 && hasCity;
    }""",timeout=20000)
    page.screenshot(path=str(SCREENSHOT.with_name("germany-crime-map-hamburg.png")),full_page=True)

    # Regression: Munich's upstream WFS uses metre-based UTM coordinates.
    # The builder must reproject all 25 Stadtbezirke to geographic lon/lat.
    page.click("#focusCity_munich")
    page.wait_for_function("""() => {
        const m=window.__CRIME_MAP__.map;
        let rendered=false;
        m.eachLayer(l=>{
            if(!(l instanceof L.GeoJSON))return;
            const n=l.getLayers()?.filter(x=>x.feature?.properties?.city==='München').length||0;
            if(n===25 && l.getBounds().isValid() && m.getBounds().intersects(l.getBounds()))
                rendered=true;
        });
        return rendered;
    }""",timeout=25000)
    munich = page.evaluate("""() => {
        const m=window.__CRIME_MAP__.map;
        let detail=null;
        m.eachLayer(l=>{
            if(l instanceof L.GeoJSON && l.getLayers()?.some(x=>x.feature?.properties?.city==='München')) detail=l;
        });
        const coords=detail?.getBounds();
        const counties=window.__CRIME_MAP__.getCountyLayer().getLayers();
        const cityCounty=counties.find(x=>String(x.feature?.id)==='09162');
        const landkreis=counties.find(x=>String(x.feature?.id)==='09184');
        return {
            count:detail?.getLayers().length||0,
            withinViewport:!!(coords?.isValid() && m.getBounds().intersects(coords)),
            west:coords?.getWest(),east:coords?.getEast(),
            south:coords?.getSouth(),north:coords?.getNorth(),
            cityFillOpacity:cityCounty?.options?.fillOpacity,
            surroundingCountyOpacity:landkreis?.options?.fillOpacity,
        };
    }""")
    assert munich["count"]==25 and munich["withinViewport"], munich
    assert 11 < munich["west"] < munich["east"] < 12.1,munich
    assert 47.8 < munich["south"] < munich["north"] < 48.5,munich
    assert munich["cityFillOpacity"]==0, "München Stadt 09162 must be hidden under detailed districts"
    assert munich["surroundingCountyOpacity"]>0.25, "Landkreis München 09184 must remain visible"
    page.screenshot(path=str(SCREENSHOT.with_name("germany-crime-map-munich.png")),full_page=True)

    # Dresden's full municipal polygon retains a city-wide fill beneath
    # the 61 police-atlas neighbourhoods, which are not a complete city border.
    page.click("#focusCity_dresden")
    page.wait_for_timeout(1600)
    diagnostics=page.evaluate("""() => {
        const a=window.__CRIME_MAP__, m=a.map, layers=[];
        m.eachLayer(l=>{
            if(l instanceof L.GeoJSON)layers.push({
                pane:l.options?.pane,
                cities:[...new Set(l.getLayers().map(x=>x.feature?.properties?.city).filter(Boolean))],
                num:l.getLayers().length
            });
        });
        return {
            zoom:m.getZoom(),
            bounds:m.getBounds().toBBoxString(),
            mode:a.getMode(),
            metric:document.querySelector('#propertyMetric')?.value,
            layers,
            button:!!document.getElementById('focusCity_dresden')
        }
    }""")
    print("[dresden-browser-diagnostics]",json.dumps(diagnostics,ensure_ascii=False),flush=True)
    page.wait_for_function("""() => {
        const m=window.__CRIME_MAP__.map;
        let n=0;
        m.eachLayer(l=>{
            if(l instanceof L.GeoJSON && l.getLayers()?.some(x=>x.feature?.properties?.city==='Dresden'))
                n=l.getLayers().filter(x=>x.feature?.properties?.city==='Dresden').length;
        });
        return m.getZoom()>=8 && n===61;
    }""",timeout=25000)
    dresden=page.evaluate("""() => {
        const m=window.__CRIME_MAP__.map;
        const county=window.__CRIME_MAP__.getCountyLayer().getLayers()
            .find(x=>String(x.feature?.id)==='14612');
        const municipal=Array.from(m._layers ? Object.values(m._layers) : [])
            .filter(x=>x instanceof L.GeoJSON && x.options?.pane==='berlinPane'
              && x.getLayers().some(v=>String(v.feature?.id)==='14612'));
        const neighbour=window.__CRIME_MAP__.getCountyLayer().getLayers()
            .find(x=>String(x.feature?.id)==='14625');
        const styles=municipal.map(x=>x.getLayers()[0]?.options);
        return {
            cityFillOpacity:county?.options?.fillOpacity,
            municipalityLayers:municipal.length,
            hasNoDataMask:styles.some(x=>x?.fillOpacity>.25&&x?.fillOpacity<.5&&x?.fillColor==='#e7ecef'),
            hasOuterBorder:styles.some(x=>x?.fill===false&&x?.weight>=1),
            neighbourFillOpacity:neighbour?.options?.fillOpacity,
            focused:document.querySelector('.mapwrap')?.classList.contains('city-detail-focus'),
            coverageNote:document.querySelector('.generic-city-legend')?.textContent||''
        }
    }""")
    assert dresden["cityFillOpacity"] == 0, dresden
    assert dresden["municipalityLayers"]==2, dresden
    assert dresden["hasNoDataMask"] and dresden["hasOuterBorder"],dresden
    assert dresden["focused"],dresden
    assert dresden["neighbourFillOpacity"]==.12,dresden
    # A hover/mouseout on a neighbouring Kreis must restore the faded focus
    # palette rather than reverting to the full-strength orange heatmap.
    faded_after_hover=page.evaluate("""() => {
        const c=window.__CRIME_MAP__.getCountyLayer().getLayers()
            .find(x=>String(x.feature?.id)==='14625');
        if(!c)return -1;
        c.fire('mouseover');c.fire('mouseout');
        return c.options.fillOpacity;
    }""")
    assert faded_after_hover==.12, faded_after_hover
    assert "灰色市域" in dresden["coverageNote"],dresden
    page.screenshot(path=str(SCREENSHOT.with_name("germany-crime-map-dresden.png")),full_page=True)

    assert not errors, errors
    print(json.dumps({
        "result":"PASS",
        "national":initial,
        "county":county,
        "state_reopen":{"first":states["first"],"second":second},
        "berlin":True,
        "hamburg":True,
        "munich":munich,
        "dresden":dresden,
        "page_errors":errors,
    },ensure_ascii=False))
    browser.close()
