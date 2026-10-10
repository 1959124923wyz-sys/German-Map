#!/usr/bin/env python3
"""Railway browser regression: grouped measured services, thin lines, Chinese stations and hotspots."""
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE="http://127.0.0.1:8769/topics/railway/"
ART=Path("/tmp/railway-v16")
ART.mkdir(exist_ok=True)
def n(page,s): return int(page.locator(s).inner_text().replace(",","").strip())
def loaded(page,service,min_count=20):
    page.wait_for_function("""args => window.__RAILWAY_OVERVIEW__?.getService()===args[0]
      && document.querySelector('#visibleCount')?.textContent!=='—'
      && Number(document.querySelector('#visibleCount').textContent.replaceAll(',',''))>args[1]""",
      arg=[service,min_count],timeout=160000)

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    page=browser.new_page(viewport={"width":1440,"height":900},device_scale_factor=1)
    errors=[];bad=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    page.on("response",lambda r:bad.append((r.status,r.url)) if r.status>=400 else None)
    response=page.goto(BASE,wait_until="domcontentloaded",timeout=60000)
    assert response and response.status==200
    loaded(page,"REGIONAL",500)
    assert page.locator(".toplinks a").count()>=7 and page.locator('a[href="../finance/"]').count()==1
    assert page.locator("#service [data-service]").count()==3
    assert page.locator("#metric [data-metric]").count()==3
    assert page.locator("#cities .city").count()>=8
    assert page.locator(".hot-row").count()==10
    regional=n(page,"#visibleCount")
    # Each sufficiently observed line must be visible even below the warning
    # threshold. Source-missing rails are on the separate dark canvas.
    page.wait_for_function("""() => document.querySelectorAll('.segment.normal').length>100""")
    assert page.locator(".segment").count()==regional
    assert page.locator(".segment.normal").first.get_attribute("stroke")=="#5cad91"
    assert page.locator(".rail-legend b").inner_text().startswith("综合关注")
    assert "晚点 <25% 且取消 <4%" in page.locator("#railLegend").inner_text()
    assert "晚点 ≥40% 或取消 ≥8%" in page.locator("#railLegend").inner_text()
    assert "无匹配或样本不足" in page.locator("#railLegend").inner_text()
    assert page.locator(".map-panel #railLegend").count()==1
    # A green observed section must be selectable with its real observations.
    page.locator(".segment.normal").first.dispatch_event("click")
    assert "低于关注门槛" in page.locator("#detail .grade").inner_text()
    assert "→" in page.locator("#detail h3").inner_text()
    assert 0<n(page,"#redCount")<=regional
    assert page.locator("#redShare").inner_text().endswith("%")
    styles=page.locator(".segment.hot").first.evaluate("""e=>{
      const s=getComputedStyle(e);
      return {width:parseFloat(s.strokeWidth),cap:s.strokeLinecap,filter:s.filter};
    }""")
    assert styles["width"]<=2.1 and styles["cap"]=="butt" and styles["filter"]=="none",styles
    assert page.evaluate("window.__RAILWAY_OVERVIEW__.stationZh('Berlin Hbf')")=="柏林中央火车站"
    assert page.evaluate("window.__RAILWAY_OVERVIEW__.stationZh('Köln Messe/Deutz')")=="科隆会展／道依茨站"
    assert page.evaluate("window.__RAILWAY_OVERVIEW__.stationZh('Unknown Village 27')")=="Unknown Village 27"
    page.screenshot(path=str(ART/"railway-desktop.png"),full_page=True)
    page.locator(".segment-hit").first.dispatch_event("click")
    assert "→" in page.locator("#detail h3").inner_text()
    assert page.locator(".original-stations").is_visible()
    assert "有效到站观测" in page.locator("#detail").inner_text()
    page.locator(".hot-row").first.click()
    assert page.evaluate("window.__RAILWAY_OVERVIEW__.getSelected()!==null")
    assert "→" in page.locator("#detail h3").inner_text()
    page.locator('[data-metric="cancel"]').click()
    assert page.locator('[data-metric="cancel"]').get_attribute("aria-pressed")=="true"
    assert n(page,"#visibleCount")>100
    assert "4%–<8%" in page.locator("#railLegend").inner_text()
    assert "≥8%" in page.locator("#railLegend").inner_text()
    assert page.locator(".segment.normal").count()>0
    page.select_option("#minimum","500")
    assert n(page,"#visibleCount")<regional
    page.select_option("#minimum","100")
    page.locator('[data-metric="late"]').click()
    assert "25%–<40%" in page.locator("#railLegend").inner_text()
    assert "≥40%" in page.locator("#railLegend").inner_text()
    page.locator('[data-metric="both"]').click()
    assert "晚点 <25% 且取消 <4%" in page.locator("#railLegend").inner_text()
    page.locator('[data-service="LONG"]').click()
    loaded(page,"LONG",10)
    page.locator('[data-service="OTHER"]').click()
    loaded(page,"OTHER",100)
    page.locator('[data-service="REGIONAL"]').click()
    loaded(page,"REGIONAL",500)
    assert n(page,"#visibleCount")==regional
    research=page.goto(BASE+"research.html",wait_until="domcontentloaded",timeout=60000)
    assert research.status==200 and "js/app.js" in page.content()
    assert not errors,errors
    assert not bad,bad
    mobile=browser.new_page(viewport={"width":390,"height":844},device_scale_factor=1)
    mobile_errors=[]
    mobile.on("pageerror",lambda e:mobile_errors.append(str(e)))
    mobile.goto(BASE,wait_until="domcontentloaded",timeout=60000)
    loaded(mobile,"REGIONAL",500)
    assert mobile.locator("#viewport").is_visible()
    assert mobile.locator(".hot-row").count()==10
    assert mobile.locator(".segment.normal").count()>100
    assert mobile.locator(".sidebar #railLegend").count()==1
    assert mobile.locator(".map-panel #railLegend").count()==0
    assert mobile.evaluate("document.documentElement.scrollWidth <= innerWidth+3")
    mobile.screenshot(path=str(ART/"railway-mobile.png"),full_page=True)
    assert not mobile_errors,mobile_errors
    print("PASS railway 07: observed green links, numeric dynamic legend, grey no-data, existing routes, mobile and filters")
    print("Regional grouped sections:",regional)
    browser.close()
