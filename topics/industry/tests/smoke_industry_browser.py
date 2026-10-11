#!/usr/bin/env python3
"""09 Industry release smoke: all sourced events + official county polygons."""
from pathlib import Path
import base64
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
        !!document.querySelector('#industry-map .leaflet-industry-state-pane svg') &&
        document.querySelectorAll('#industry-map .leaflet-industry-state-pane canvas').length===0;
    }""")

    assert page.locator("#industryNationalList .industry-row").count()==231
    assert "不是" in page.locator("#methodNote").inner_text() or "尚非" in page.locator("#methodNote").inner_text()
    assert page.locator(".modebar a.modebtn").count()==10
    assert page.locator(".modebar .active").inner_text()=="工业衰退"
    page.locator("#industryStateJump").select_option("DE-NW")
    oldview=page.evaluate("GermanIndustryQA.view()")
    assert page.locator("#industryDossier").is_visible()
    assert page.evaluate("GermanIndustryQA.selectedState()")=="DE-NW"
    assert "本范围可溯源" in page.locator("#industryStateMetrics").inner_text()
    page.locator('[data-dossier-tab="status"]').click()
    assert page.locator("#industryStatusSummary").is_visible()
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
      return m.querySelectorAll('.leaflet-industry-event-pane canvas').length===0 &&
         m.querySelectorAll('.leaflet-industry-event-pane svg path').length>0;
    }"""),"The industrial markers must be SVG, never a full-screen Canvas"
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
                if(!node?.closest('.leaflet-county-pane'))continue;
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
