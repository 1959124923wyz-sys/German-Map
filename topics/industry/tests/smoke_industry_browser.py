#!/usr/bin/env python3
"""09 Industry release smoke: all sourced events + official county polygons."""
from pathlib import Path
import base64
import json
from playwright.sync_api import sync_playwright

BASE="http://127.0.0.1:8765/topics/industry/"
LEAFLET=Path("node_modules/leaflet/dist")
PIX=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9YA0sEUAAAAASUVORK5CYII=")

def verify(browser,mobile=False):
    page=browser.new_page(viewport={"width":390 if mobile else 1440,"height":844 if mobile else 900},device_scale_factor=1)
    errors=[]
    page.on("pageerror",lambda error:errors.append(str(error)))
    page.route("https://unpkg.com/leaflet@1.9.4/dist/leaflet.js",lambda r:r.fulfill(path=str(LEAFLET/"leaflet.js"),content_type="text/javascript"))
    page.route("https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",lambda r:r.fulfill(path=str(LEAFLET/"leaflet.css"),content_type="text/css"))
    page.route("**tile.openstreetmap.org/**",lambda r:r.fulfill(status=200,body=PIX,content_type="image/png"))
    response=page.goto(BASE,wait_until="domcontentloaded",timeout=60000)
    assert response and response.status==200
    page.wait_for_function("window.GermanIndustryQA?.records===231",timeout=55000)
    result=page.evaluate("window.GermanIndustryQA")
    assert result["counties"]==400 and result["states"]==16,result
    assert result["modernCounties"]==400 and result["officialCoverage"]==0,result
    assert page.locator("#industry-map .leaflet-control-zoom-in").count()==1
    assert page.locator("#industryDossier").is_hidden()
    assert page.locator("#showMarkers").is_checked() is False
    assert page.evaluate("""() => {
      const q=GermanIndustryQA,layer=q.getStateOverlay();
      return q.getMap().hasLayer(layer)&&layer.getLayers().length===16 &&
        !!q.getMap().getPane('industryStatePane').querySelector('svg') &&
        q.getMap().getPane('industryStatePane').querySelectorAll('canvas').length===0;
    }""")

    assert page.locator("#industryNationalList .industry-row").count()==231
    # Opening a documented major event highlights one mapped factory.
    # Switching regions must immediately clear the old marker emphasis.
    first_marker_id=page.evaluate("GermanIndustryQA.getFirstMarkerId()")
    assert first_marker_id
    page.locator("#industryNationalArchive > summary").click()
    page.locator(f'#industryNationalList .industry-row[data-id="{first_marker_id}"]').click()
    assert page.evaluate("GermanIndustryQA.highlightedMarkers()")==1
    page.locator("#industryStateJump").select_option("DE-NW")
    assert page.evaluate("GermanIndustryQA.highlightedMarkers()")==0, (
        "A marker remains selected after changing the state dossier")
    page.locator("#viewGermany").click()
    assert page.evaluate("GermanIndustryQA.highlightedMarkers()")==0
    assert page.locator("#methodNote").count()==0, "Lengthy cautions should stay in collapsed research details"
    assert "底色只表示" in page.locator("#researchDetails .industry-method").text_content()
    assert page.locator(".modebar a.modebtn").count()==10
    assert page.locator(".modebar .active").inner_text()=="工业衰退"
    page.locator("#industryStateJump").select_option("DE-NW")
    oldview=page.evaluate("GermanIndustryQA.view()")
    assert page.locator("#industryDossier").is_visible()
    assert page.evaluate("GermanIndustryQA.selectedState()")=="DE-NW"
    assert "本范围可溯源" in page.locator("#industryStateMetrics").inner_text()
    page.locator('[data-dossier-tab="status"]').click()
    assert page.locator("#industryStatusSummary").is_visible()
    # A cross-state comparison should retain the selected status tab.
    page.locator("#industryStateJump").select_option("DE-HE")
    assert page.locator('[data-dossier-tab="status"]').get_attribute("aria-selected")=="true"
    assert page.locator("#industryStatusSummary").is_visible()
    page.locator("#industryStateJump").select_option("DE-NW")
    assert page.locator('[data-dossier-tab="status"]').get_attribute("aria-selected")=="true"
    oldview=page.evaluate("GermanIndustryQA.view()")
    page.locator('[data-dossier-tab="timeline"]').click()
    assert page.locator("#industryEventTimeline .industry-timeline-year").count()>0
    assert page.locator("#industryEventTimeline .industry-timeline-year").first.get_attribute("open") is not None
    page.locator("#industryEventTimeline [data-id]").first.click()
    assert page.evaluate("GermanIndustryQA.view().zoom")==oldview["zoom"]
    assert page.locator("#eventDetail").is_visible()
    assert page.locator("#eventDetail a[href^='https://']").count()>0
    assert "事件类型：" in page.locator("#eventDetail").inner_text()
    assert "资料来源类型：" in page.locator("#eventDetail").inner_text()
    assert page.locator("#eventDetail details.industry-provenance").count()==1
    page.locator("#eventDetail details.industry-provenance summary").click()
    assert page.locator("#eventDetail details.industry-provenance dt").count()>=4
    # Chronology click may enter a specific county; return to entire state
    # before testing the state-wide UPM source search.
    if page.locator("#industryBackState").is_visible():
        page.locator("#industryBackState").click()
    page.locator('[data-dossier-tab="cases"]').click()
    assert page.locator("#eventList .industry-row").count()>0
    page.locator("#industryEventSearch").fill("UPM")
    assert page.locator("#eventList .industry-row").count()>0
    page.locator("#industryEventSearch").fill("")
    page.locator("#eventList .industry-row").first.click()
    assert page.locator("#eventDetail").is_visible()
    # A multisite plan's linked files must remain distinct; never sum 280 jobs
    # into both Putzmeister factories or mistake one source for actual lay-offs.
    page.locator("#industryStateJump").select_option("DE-HE")
    page.locator('[data-dossier-tab="cases"]').click()
    page.locator("#industryEventSearch").fill("Putzmeister")
    assert page.locator("#eventList .industry-row").count()>=1
    page.locator("#eventList .industry-row").first.click()
    assert page.locator(".industry-linked-events [data-id]").count()>=2
    assert "岗位数字不能直接相加" in page.locator(".industry-linked-events").inner_text()
    page.locator(".industry-linked-events [data-id]").first.click()
    assert page.locator("#eventDetail").is_visible()
    assert page.locator("#eventDetail a[href^='https://']").count()>0
    assert page.locator("#eventDetail a[href^='https://']").count()>0
    page.locator("#viewGermany").click()
    assert page.locator("#areaName").inner_text()=="德国全国"
    assert page.locator("#industryDossier").is_hidden()
    assert page.locator("#showMarkers").is_checked() is False
    page.locator("#showMarkers").uncheck()
    assert page.locator("#showMarkers").is_checked() is False
    page.locator("#showMarkers").check()
    assert page.evaluate("""() => {
      const m=document.querySelector('#industry-map');
      return GermanIndustryQA.getMap().getPane('industryEventPane').querySelectorAll('canvas').length===0 &&
         GermanIndustryQA.getMap().getPane('industryEventPane').querySelectorAll('svg path').length>0;
    }"""),"The industrial markers must be SVG, never a full-screen Canvas"
    # The prior smoke clicked company archives, but never a real SVG factory
    # marker. Verify the browser's actual hit target before clicking it.
    page.locator("#industry-map").scroll_into_view_if_needed()
    factory=page.evaluate("""() => {
      const qa=GermanIndustryQA,map=qa.getMap();
      const b=map.getContainer().getBoundingClientRect();
      for(const [id,layer] of qa.getEventMarkers()){
        const path=layer._path;
        if(!path)continue;
        const p=path.getBoundingClientRect();
        const x=p.x+p.width/2,y=p.y+p.height/2;
        if(p.width<4||p.height<4||x<b.left+12||x>b.right-12
          ||y<b.top+15||y>b.bottom-15||y<15||y>innerHeight-15)continue;
        const node=document.elementFromPoint(x,y);
        if(node!==path)continue;
        return {id:String(id),x,y};
      }
      return null;
    }""")
    assert factory, "No industrial factory SVG marker is reachable with a real mouse"
    before_factory=page.evaluate("GermanIndustryQA.view()")
    page.mouse.click(factory['x'],factory['y'])
    assert page.evaluate("GermanIndustryQA.selectedEvent()")==factory["id"],(
        "Real factory marker click did not open its dossier",factory)
    assert page.evaluate("GermanIndustryQA.highlightedMarkers()")==1
    assert page.locator("#eventDetail").is_visible()
    assert page.evaluate("GermanIndustryQA.view()")==before_factory,(
        "Real factory marker click forced camera movement",factory)
    page.locator("#viewGermany").click()
    assert page.evaluate("GermanIndustryQA.highlightedMarkers()")==0
    page.locator("#industryStateJump").select_option("DE-NW")
    before=page.evaluate("GermanIndustryQA.view()")
    assert page.evaluate("""() => !GermanIndustryQA.getMap()
      .hasLayer(GermanIndustryQA.getStateOverlay())""")
    if not mobile:
        target=page.evaluate("""() => {
          const qa=GermanIndustryQA,map=qa.getMap();
          const rect=map.getContainer().getBoundingClientRect();
          const layers=qa.getCounties().getLayers()
             .filter(x=>String(x.feature?.id||'').startsWith('05'));
          const order=[10,9,11,8,12,7,13,6,14,5,15,4,16,3,17,2,18,1,19];
          for(const layer of layers){
             const b=layer.getBounds();
             for(const yi of order)for(const xi of order){
                const lat=b.getSouth()+(b.getNorth()-b.getSouth())*yi/20;
                const lng=b.getWest()+(b.getEast()-b.getWest())*xi/20;
                const world=map.latLngToLayerPoint([lat,lng]);
                if(!layer._containsPoint(world))continue;
                const pt=map.latLngToContainerPoint([lat,lng]);
                if(pt.x<15||pt.y<20||pt.x>rect.width-15||pt.y>rect.height-20)continue;
                const x=rect.left+pt.x,y=rect.top+pt.y;
                const node=document.elementFromPoint(x,y);
                if(node?.closest('.leaflet-pane')!==map.getPane('countyPane'))continue;
                return {x,y,id:String(layer.feature.id),tag:node.tagName};
             }
          }
          return null;
        }""")
        assert target, "No county mouse target outside industrial SVG markers"
        page.mouse.click(target["x"],target["y"])
        assert page.evaluate("GermanIndustryQA.selectedCounty()") is not None,target
        assert page.evaluate("GermanIndustryQA.selectedState()")=="DE-NW"
        assert page.evaluate("GermanIndustryQA.view()")==before,"County click moved the map unexpectedly"
        assert page.locator("#industryBackState").is_visible()
        page.locator("#industryBackState").click()
        assert page.evaluate("GermanIndustryQA.selectedCounty()") is None
    page.locator("#viewGermany").click()
    assert page.evaluate("GermanIndustryQA.selectedState()") is None
    assert page.evaluate("""() => GermanIndustryQA.getMap()
      .hasLayer(GermanIndustryQA.getStateOverlay())""")
    # NEW: manually zooming into a county while the selection is nationwide
    # must remove the transparent 16-state SVG hit shield. This is different
    # from choosing a state through the picker, which already removed it.
    page.evaluate("""() => {
      GermanIndustryQA.getMap().setView([50.72,9.1],9,{animate:false});
      return true; // Never serialize a Leaflet map (cyclic DOM references).
    }""")
    page.wait_for_function("""() => {
      const q=GermanIndustryQA,m=q.getMap();
      return m.getZoom()>=9 && !m.hasLayer(q.getStateOverlay());
    }""")
    probe=json.loads(page.evaluate("""() => {
      const qa=GermanIndustryQA,m=qa.getMap();
      const xy=m.latLngToContainerPoint([50.72,9.1]),r=m.getContainer().getBoundingClientRect();
      const world=m.latLngToLayerPoint([50.72,9.1]);
      const matches=qa.getCounties().getLayers().filter(l=>l._containsPoint?.(world));
      const x=r.left+xy.x,y=r.top+xy.y;
      const stack=document.elementsFromPoint(x,y).slice(0,7)
        .map(el=>({tag:String(el.tagName),pane:String(
          el.closest('.leaflet-pane')?.getAttribute('class')||'')}));
      // Playwright's serializer cannot safely transfer SVG className objects.
      // Flatten all diagnostics to ordinary JSON primitives.
      return JSON.stringify({x:Number(x),y:Number(y),
        matches:matches.map(l=>String(l.feature?.id||'')),stack});
    }"""))
    assert probe['matches'],f"No real 400-county polygon under high-zoom pointer: {probe}"
    assert any('leaflet-county-pane' in (item['pane'] or '') for item in probe['stack']),(
        'County renderer not reachable by actual mouse pointer',probe)
    camera_before=page.evaluate("GermanIndustryQA.view()")
    page.mouse.click(probe['x'],probe['y'])
    assert page.evaluate("GermanIndustryQA.selectedCounty()") in probe['matches'],(
        'Actual county click not dispatched to the expected polygon',probe)
    assert page.evaluate("GermanIndustryQA.view()")==camera_before,(
        'County mouse click unexpectedly moved camera')
    page.locator('#viewGermany').click()
    assert page.evaluate("GermanIndustryQA.selectedCounty()") is None
    assert page.evaluate("""() => GermanIndustryQA.getMap()
      .hasLayer(GermanIndustryQA.getStateOverlay())"""),(
        'Returning to national view must restore state click targets')

    assert not errors,errors
    page.screenshot(path="/tmp/industry-release-"+("mobile" if mobile else "desktop")+".png",full_page=True)
    if mobile:assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 6")
    page.close()

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
    try:
        verify(browser)
        verify(browser,True)
    finally:
        browser.close()
print("PASS industry R8: 231 source records / 400 BKG counties / desktop+mobile",flush=True)
