#!/usr/bin/env python3
"""Finance 08: fixed national balance choropleth, zoom-in state drilldown and event checkbox."""
from __future__ import annotations
import base64
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE="http://127.0.0.1:8765/topics/finance/"
LEAFLET=Path("node_modules/leaflet/dist")
ONE_PX=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9YA0sEUAAAAASUVORK5CYII=")

def verify(browser,mobile=False):
    page=browser.new_page(viewport={"width":390 if mobile else 1440,"height":844 if mobile else 900},device_scale_factor=1)
    errors=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    page.route("https://unpkg.com/leaflet@1.9.4/dist/leaflet.js",lambda r:r.fulfill(path=str(LEAFLET/"leaflet.js"),content_type="text/javascript"))
    page.route("https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",lambda r:r.fulfill(path=str(LEAFLET/"leaflet.css"),content_type="text/css"))
    page.route("**tile.openstreetmap.org/**",lambda r:r.fulfill(status=200,body=ONE_PX,content_type="image/png"))
    page.goto(BASE,wait_until="domcontentloaded",timeout=45000)
    page.wait_for_function("window.__FINANCE_UI__ && document.getElementById('mapStatus').hidden",timeout=45000)
    assert page.locator("#finance-map .leaflet-control-zoom-in").count()==1
    assert page.locator(".modebar a.modebtn").count()==7
    api="window.__FINANCE_UI__"
    assert page.evaluate(f"{api}.getMode()")=="balance-2025"
    assert page.locator("[data-mode]").count()==0
    assert page.locator("#stateMetric").count()==0
    assert not page.locator("#showEvents").is_checked()
    assert page.locator("#eventPanel").is_hidden()
    assert page.locator("#extraControls").is_hidden()
    assert page.evaluate(f"{api}.eventCount()")==0
    assert "2025" in page.locator("#legend").inner_text()
    assert page.evaluate("window.__FINANCE_MAP__.getBounds().contains(L.latLngBounds([[47.15,5.4],[55.1,15.6]]))")
    # Regression: the checkbox label must never collapse into a vertical
    # character column when a state-switcher shares the sidebar.
    toggle=page.locator(".finance-event-toggle span").bounding_box()
    controls=page.locator(".finance-controls").bounding_box()
    switcher=page.locator(".finance-state-actions").bounding_box()
    assert toggle and controls and switcher
    assert toggle["height"]<30, ("event label is wrapping vertically",toggle)
    assert switcher["y"]>=toggle["y"]+toggle["height"], (toggle,switcher)
    assert switcher["x"]+switcher["width"]<=controls["x"]+controls["width"]+2
    national_style=page.evaluate(f"{api}.stateFill('DE-RP')")
    original_zoom=page.evaluate("window.__FINANCE_MAP__.getZoom()")

    # Click a real state layer to zoom in and reveal detail without changing
    # the choropleth (no misleading mixed city budget vs state balance map).
    page.evaluate("""()=>{
      const layer=window.__FINANCE_UI__.stateLayer().getLayers()
       .find(x=>x.feature?.properties?.id==='DE-RP');
      layer.fire('click');
    }""")
    assert page.evaluate(f"{api}.getFocusState()")=="DE-RP"
    assert page.evaluate("window.__FINANCE_MAP__.getZoom()")>original_zoom
    assert page.locator("#districtPanel").is_visible()
    assert page.locator("#loanDrawer").is_visible()
    assert page.evaluate(f"{api}.stateFill('DE-RP')")==national_style
    assert page.evaluate(f"{api}.getMode()")=="balance-2025"
    assert page.evaluate(f"{api}.hasStateLayer()")
    assert page.evaluate(f"{api}.hasCountyDetail()")
    page.locator("#loanDrawer summary").click()
    assert page.locator("#loanHistory table tbody tr").count()==5
    assert "2024" in page.locator("#loanHistory").inner_text()
    page.locator("#loanDrawer summary").click()

    city=page.evaluate("window.GermanFinance08Data.cities[0]")
    page.evaluate("(id)=>window.__FINANCE_UI__.selectCounty(id)",city["id"])
    assert page.locator("#areaName").inner_text() not in ("德国 · 全国","莱茵兰-普法尔茨")
    assert "欧元/人" in page.locator("#metricValue").inner_text()
    # One contextual archive only; RP's current-year balance stays primary.
    assert page.locator("#regionalDebtDrawer").is_visible()
    assert not page.locator("#regionalDebtDrawer").get_attribute("open")
    page.locator("#regionalDebtDrawer > summary").click()
    assert "2023年县域" in page.locator("#regionalDebtInfo").inner_text()
    assert "2024年非县辖市" in page.locator("#regionalDebtInfo").inner_text()
    assert page.locator("#regionalDebtInfo a[href^='https://']").count()==2
    page.locator("#rpPeriod").select_option("2026-H1-counties")
    assert page.evaluate(f"{api}.stateFill('DE-RP')")==national_style

    # Regression for the old bug: transparent county geometries covering
    # OTHER states swallowed actual map clicks on shared Leaflet Canvas.
    assert page.evaluate(f"{api}.selectedCounties().length")>=12
    assert page.evaluate(f"{api}.selectedCounties().every(x=>String(x).startsWith('07'))")
    assert page.locator("#stateJump").input_value()=="DE-RP"
    # A user may pan and click Hessen DIRECTLY without returning nationwide.
    if not mobile:
        page.evaluate("window.__FINANCE_MAP__.panTo([50.11,8.25],{animate:false})")
        loc=page.evaluate("""()=>{
          const map=window.__FINANCE_MAP__;
          const p=map.latLngToContainerPoint([50.1109,8.6821]);
          return {x:p.x,y:p.y,w:map.getSize().x,h:map.getSize().y};
        }""")
        assert 0<loc["x"]<loc["w"] and 0<loc["y"]<loc["h"],loc
        rect=page.locator("#finance-map").bounding_box()
        page.mouse.click(rect["x"]+loc["x"],rect["y"]+loc["y"])
        assert page.evaluate(f"{api}.getFocusState()")=="DE-HE","Hessen direct click must work while RP counties are visible"
        assert page.locator("#stateJump").input_value()=="DE-HE"
        assert page.locator("#districtPanel").is_hidden()
        assert page.evaluate(f"{api}.selectedCounties().every(x=>String(x).startsWith('06'))")
        assert page.evaluate(f"{api}.stateFill('DE-RP')")==national_style
        assert page.evaluate(f"{api}.hasStateLayer()")

    # Direct state selector works even when the desired state is offscreen;
    # neither switching calls nor map colour needs a nationwide reset.
    page.locator("#stateJump").select_option("DE-NI")
    assert page.evaluate(f"{api}.getFocusState()")=="DE-NI"
    assert page.evaluate(f"{api}.selectedCounties().every(x=>String(x).startsWith('03'))")
    assert page.locator("#loanDrawer").is_visible()
    assert page.evaluate(f"{api}.stateFill('DE-RP')")==national_style
    page.locator("#stateJump").select_option("DE-RP")
    assert page.evaluate(f"{api}.getFocusState()")=="DE-RP"
    assert page.locator("#districtPanel").is_visible()
    assert page.evaluate(f"{api}.selectedCounties().every(x=>String(x).startsWith('07'))")

    # Independent test location: Kiel's two distinct real fiscal sources.
    # No national recolouring, no adding enterprise debt to county core budget.
    page.locator("#stateJump").select_option("DE-SH")
    assert page.locator("#regionalDebtDrawer").is_hidden()
    page.evaluate("()=>window.__FINANCE_UI__.selectCounty('01002')")
    assert page.locator("#regionalDebtDrawer").is_visible()
    assert page.evaluate(f"{api}.historicalCore('01002')")==2217
    assert 5165 < page.evaluate(f"{api}.historicalCity('01002')") < 5166
    assert "2023" in page.locator("#sectionTitle").inner_text()
    assert "2,217" in page.locator("#metricValue").inner_text()
    assert "2025" in page.locator("#legend").inner_text()
    page.locator("#regionalDebtDrawer > summary").click()
    facts=page.locator("#regionalDebtInfo").inner_text()
    assert "2023年县域" in facts and "2024年非县辖市" in facts
    assert "5,165.6" in facts
    # Missing city-core record remains missing, never zero.
    assert page.evaluate(f"{api}.historicalCore('08111')") is None
    page.locator("#stateJump").select_option("DE-RP")
    assert page.locator("#regionalDebtDrawer").is_hidden()
    assert page.evaluate(f"{api}.stateFill('DE-RP')")==national_style

    # R24 national data must actually be exposed as source-distinct maps.
    # Default remains the same 2025 state-balance choropleth.
    assert page.locator("#metricLayer").input_value()=="balance-2025"
    page.locator("#resetView").click()
    page.locator("#metricLayer").select_option("core-2023")
    assert page.evaluate(f"{api}.getMode()")=="core-2023"
    assert "2023" in page.locator("#legend").inner_text()
    assert page.evaluate(f"{api}.coloredCountyCount()")>=380
    assert page.evaluate(f"{api}.hasCountyDetail()")
    assert "2023" in page.locator("#mapGuideTitle").inner_text()
    page.evaluate(f"{api}.selectCounty('01002')")
    assert "2,217" in page.locator("#metricValue").inner_text()
    page.locator("#municipalDrawer").wait_for(state="visible")
    page.wait_for_function("document.getElementById('municipalCount')?.textContent.includes('个市镇')",timeout=30000)
    assert page.evaluate(f"{api}.municipalStateLoaded('01')")
    page.locator("#municipalDrawer summary").click()
    assert "Kiel" in page.locator("#municipalList").inner_text()
    assert "5,165.6" in page.locator("#municipalList").inner_text()
    page.locator("#municipalSearch").fill("01002000")
    assert page.locator("#finance-map").is_visible()
    assert page.locator("#municipalList .finance-muni-row").count()==1
    page.locator("#municipalSearch").fill("does-not-exist")
    assert "没有匹配" in page.locator("#municipalList").inner_text()
    page.locator("#municipalSearch").fill("")

    page.locator("#metricLayer").select_option("city-2024")
    assert page.evaluate(f"{api}.getMode()")=="city-2024"
    assert "2024" in page.locator("#legend").inner_text()
    assert page.evaluate(f"{api}.coloredCountyCount()")>=95
    page.evaluate(f"{api}.selectCounty('01002')")
    assert "5,165.6" in page.locator("#metricValue").inner_text()
    page.locator("#metricLayer").select_option("balance-2025")
    assert page.evaluate(f"{api}.getMode()")=="balance-2025"
    assert page.evaluate(f"{api}.stateFill('DE-RP')")==national_style
    page.locator("#resetView").click()
    assert "2025" in page.locator("#legend").inner_text()

    # Event checkbox only adds/removes geographic markers and sidebar events.
    page.locator("#showEvents").check()
    page.wait_for_function("window.__FINANCE_UI__.eventCount()>=30")
    assert page.locator("#eventPanel").is_visible()
    assert page.locator("#extraControls").is_visible()
    # Changing states does NOT turn off the independent event overlay.
    page.locator("#stateJump").select_option("DE-BY")
    assert page.evaluate(f"{api}.getFocusState()")=="DE-BY"
    assert page.locator("#showEvents").is_checked()
    assert page.evaluate(f"{api}.eventCount()")>=30
    assert page.locator("#eventPanel").is_visible()
    assert page.evaluate(f"{api}.stateFill('DE-RP')")==national_style
    assert "2025" in page.locator("#legend").inner_text()
    assert page.locator(".finance-case-preview").count()>=8
    assert page.locator("#caseList button").first.get_attribute("title")
    # A map circle's hover contains a short real event description and a
    # reminder this is a county aggregation, not a fabricated facility pin.
    page.evaluate("()=>{window.__FINANCE_UI__.eventMarkers()[0].openTooltip();return true}")
    tooltip=page.locator(".finance-event-tooltip").first
    assert tooltip.is_visible()
    assert "点击查看" in tooltip.inner_text()
    assert len(tooltip.locator("div").first.inner_text())>=8
    # Leaflet's absolutely positioned tooltip has a shrink-to-fit width.
    # A max-width alone lets Chinese text become a one-character-wide tower.
    tooltip_box=tooltip.bounding_box()
    assert tooltip_box and 210<=tooltip_box["width"]<=270,tooltip_box
    assert tooltip_box["height"]<210,tooltip_box
    page.locator("#caseList button").first.click()
    assert page.locator("#detail").is_visible()
    assert page.locator("#detail details summary").is_visible()
    page.locator("#detail details summary").click()
    assert page.locator("#detail a[href^='https://']").count()>=1
    page.locator("#extraControls summary").click()
    page.locator("#showAllCases").click()
    assert "170" in page.locator("#visibleCount").inner_text()
    page.locator("#showEvents").uncheck()
    assert page.locator("#eventPanel").is_hidden()
    assert page.evaluate(f"{api}.eventCount()")==0
    assert page.evaluate(f"{api}.hasStateLayer()")
    assert page.evaluate(f"{api}.stateFill('DE-RP')")==national_style

    page.locator("#resetView").click()
    assert page.evaluate(f"{api}.getFocusState()") is None
    assert page.locator("#districtPanel").is_hidden()
    assert page.locator("#loanDrawer").is_hidden()
    assert page.evaluate("window.__FINANCE_MAP__.getBounds().contains(L.latLngBounds([[47.15,5.4],[55.1,15.6]]))")
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+4")
    page.screenshot(path="/tmp/finance08-"+("mobile" if mobile else "desktop")+".png",full_page=True)
    assert not errors,errors
    print("PASS Finance 08 fixed national state balance, state drilldown, detail debt, county fiscal periods, independent case overlay and previews",("mobile" if mobile else "desktop"),flush=True)
    page.close()

if __name__=="__main__":
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        try:
            verify(browser)
            verify(browser,True)
        finally:
            browser.close()
