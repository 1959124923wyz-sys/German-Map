#!/usr/bin/env python3
"""Infrastructure topic smoke: real Chromium at desktop and mobile sizes with deterministic offline base tiles."""
from __future__ import annotations
import base64
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8765/topics/infrastructure/"
LEAFLET = Path("node_modules/leaflet/dist")
ONE_PX = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9YA0sEUAAAAASUVORK5CYII=")


def verify(browser, mobile: bool) -> None:
    page = browser.new_page(viewport={"width": 390 if mobile else 1460, "height": 820 if mobile else 900})
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.route("https://unpkg.com/leaflet@1.9.4/dist/leaflet.js",
               lambda route: route.fulfill(path=str(LEAFLET / "leaflet.js"), content_type="text/javascript"))
    page.route("https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
               lambda route: route.fulfill(path=str(LEAFLET / "leaflet.css"), content_type="text/css"))
    page.route("**tile.openstreetmap.org/**",
               lambda route: route.fulfill(status=200, body=ONE_PX, content_type="image/png"))
    response = page.goto(BASE, wait_until="domcontentloaded", timeout=45000)
    assert response is not None and response.status == 200
    page.wait_for_function("document.querySelectorAll('#rankList button').length===16", timeout=35000)
    assert page.locator("#infra-map .leaflet-control-zoom-in").count() == 1
    assert page.locator(".modebar a[href='../infrastructure/'].active").count() == 0  # own active href is './'
    assert page.locator(".modebar a.modebtn.active[href='./']").inner_text() == "基础设施"
    assert page.locator("#showEvents").is_checked() is False
    assert page.locator("#eventSection").is_hidden()
    assert page.locator("#areaName").inner_text() == "德国全国"
    assert "非官方" in page.locator("#legend").inner_text()
    assert page.locator("#infraDossier").is_hidden()
    assert page.locator("#stateRanking").is_visible()
    assert page.locator("#stateRanking").get_attribute("open") is None
    page.locator("#infraStateJump").select_option("DE-TH")
    assert page.locator("#areaName").inner_text() == "图林根"
    assert page.locator("#indicatorDetail").is_visible()
    assert page.locator("#indicatorDetail .metric-row").count() == 4
    page.locator('[data-dossier-tab="bridges"]').click()
    assert page.locator("#bridgeStateSummary").is_visible()
    assert "县市" in page.locator("#bridgeStateSummary").inner_text()
    page.locator("#infraStateJump").select_option("DE-SH")
    assert page.locator('[data-dossier-tab="bridges"]').get_attribute("aria-selected")=="true",(
        "Switching state reset the active bridge comparison tab")
    assert page.locator("#bridgeStateSummary").is_visible()
    page.locator("#bridgeCountySearch").fill("01002")
    assert "01002" in page.locator("#bridgeCountyList").inner_text()
    assert "85个" in page.locator("#bridgeCountyList").inner_text()
    if not mobile:
        # A five-digit AGS query belongs to the current state's bridge list,
        # not every future state. Preserve it only while this state is active.
        page.locator("#infraStateJump").select_option("DE-TH")
        assert page.locator("#bridgeCountySearch").input_value()=="", (
            "Old Schleswig-Holstein AGS search carried into Thuringia")
        assert page.locator('[data-dossier-tab="bridges"]').get_attribute("aria-selected")=="true"
        assert page.locator("#bridgeStateSummary").is_visible()
        page.locator("#infraStateJump").select_option("DE-SH")
        assert page.locator("#bridgeCountySearch").input_value()==""
    page.locator("#bridgeCountySearch").fill("")
    page.locator("#infraStateJump").select_option("DE-TH")
    assert page.locator("#eventSection").is_hidden()
    page.locator("#showEvents").check()
    assert page.locator('[data-dossier-tab="bridges"]').get_attribute("aria-selected")=="true",(
        "Toggling event markers unexpectedly switched from bridge research to project archive")
    assert page.locator("#bridgeStateSummary").is_visible()
    assert page.locator("#eventList button").count() == 1
    assert page.locator("#infra-map .infra-marker-icon").count() >= 1
    assert page.locator("#filterWrap").is_visible()
    page.locator("#showEvents").uncheck()
    assert page.locator('[data-dossier-tab="bridges"]').get_attribute("aria-selected")=="true"
    assert page.locator("#infra-map .infra-marker-icon").count()==0
    page.locator("#showEvents").check()
    assert page.locator('[data-dossier-tab="bridges"]').get_attribute("aria-selected")=="true"
    assert page.locator("#infra-map .infra-marker-icon").count()>=1
    # Explicitly opening a project is different: it may select the projects tab.
    # An actual mouse click on the site's Leaflet marker must reach its event.
    # The previous suite never clicked a map marker: only list buttons.
    page.locator("#infra-map").scroll_into_view_if_needed()
    marker=page.locator("#infra-map .infra-marker-icon").first
    assert page.evaluate("""() => {
      const qa=GermanInfrastructureQA,m=qa.getMap();
      return m.getPane('infraEventPane').querySelectorAll('.infra-marker-icon').length>0
        && m.getPane('markerPane').querySelectorAll('.infra-marker-icon').length===0;
    }"""), "Infrastructure markers escaped their dedicated z-index 530 event pane"
    box=marker.bounding_box()
    assert box and box["width"]>0 and box["height"]>0
    camera_before=page.evaluate("""() => {
      const m=GermanInfrastructureQA.getMap(),c=m.getCenter();
      return [m.getZoom(),c.lat,c.lng];
    }""")
    page.mouse.click(box["x"]+box["width"]/2,box["y"]+box["height"]/2)
    assert page.evaluate("GermanInfrastructureQA.getSelection().event") is not None, (
        "Physical marker pointer failed to open project dossier")
    assert page.locator('[data-dossier-tab="projects"]').get_attribute("aria-selected")=="true"
    assert page.locator("#eventSection").is_visible()
    assert page.evaluate("""() => {
      const m=GermanInfrastructureQA.getMap(),c=m.getCenter();
      return [m.getZoom(),c.lat,c.lng];
    }""")==camera_before, "Clicking infrastructure map marker moved the camera"
    if not mobile:
        # Verify the state's genuine SVG click target beside (but not on) the
        # project pin. This is the hit-boundary issue that list-click tests miss.
        state_target=page.evaluate("""() => {
          const qa=GermanInfrastructureQA,m=qa.getMap();
          const r=m.getContainer().getBoundingClientRect();
          const marker=m.getPane('infraEventPane').querySelector('.infra-marker-icon');
          if(!marker)return null;
          const rect=marker.getBoundingClientRect();
          const cx=rect.x+rect.width/2,cy=rect.y+rect.height/2;
          for(const d of [[24,0],[-24,0],[0,24],[0,-24],[33,12],[-33,-12],
                            [45,0],[0,45],[-45,0],[0,-45]]){
            const x=cx+d[0],y=cy+d[1];
            if(x<r.left+14||x>r.right-14||y<r.top+16||y>r.bottom-16)continue;
            const node=document.elementFromPoint(x,y);
            if(node?.closest('.leaflet-pane')!==m.getPane('infraStatePane'))continue;
            const pt=m.containerPointToLayerPoint([x-r.left,y-r.top]);
            const layer=qa.getStateLayer().getLayers()
               .find(l=>l._containsPoint?.(pt));
            if(layer)return {x,y,iso:String(layer.feature?.properties?.id)};
          }
          return null;
        }""")
        assert state_target, "No state SVG pixel reachable next to the displayed project marker"
        page.mouse.click(state_target["x"],state_target["y"])
        assert page.evaluate("GermanInfrastructureQA.getSelection().state")==state_target["iso"],(
            "Mouse click beside marker did not open the real underlying state",state_target)
        assert page.evaluate("GermanInfrastructureQA.getSelection().event") is None
        assert page.evaluate("""() => {
          const m=GermanInfrastructureQA.getMap(),c=m.getCenter();
          return [m.getZoom(),c.lat,c.lng];
        }""")==camera_before, "Clicking near a marker unexpectedly moved the viewport"
    page.locator("#eventList button").first.click()
    assert page.locator("#eventDetail").is_visible()
    assert page.locator("#eventDetail a[href^='https://']").count() >= 1
    assert "埃尔福特" in page.locator("#eventDetail").inner_text()
    assert page.locator("#locateInfraEvent").is_visible()
    if not mobile:
        # The event-list click only opened its dossier. Explicit location
        # is a separate command and must not toggle any map overlay.
        before_locate=page.evaluate("""() => {
          const m=GermanInfrastructureQA.getMap(),c=m.getCenter();
          return [m.getZoom(),c.lat,c.lng];
        }""")
        before_selection=page.evaluate("GermanInfrastructureQA.getSelection()")
        page.locator("#locateInfraEvent").click()
        after_locate=page.evaluate("""() => {
          const m=GermanInfrastructureQA.getMap(),c=m.getCenter();
          return [m.getZoom(),c.lat,c.lng];
        }""")
        assert after_locate!=before_locate, (
            "Explicit location did not move the map to project reference point")
        assert after_locate[0]>=8
        assert page.evaluate("GermanInfrastructureQA.getSelection()")==before_selection, (
            "Location changed the project or event-overlay selection")
    page.locator("#closeEventDetail").click()
    assert page.locator("#eventDetail").is_hidden()
    # User-disabled event markers must stay disabled when opening an event
    # dossier: the old selectEvent() unconditionally rechecked #showEvents
    # while leaving the actual marker layer out of sync.
    page.locator("#showEvents").uncheck()
    assert not page.locator("#showEvents").is_checked()
    assert page.locator("#infra-map .infra-marker-icon").count()==0
    assert page.locator("#filterWrap").is_hidden()
    page.locator("#eventList button").first.click()
    assert page.locator("#eventDetail").is_visible()
    assert not page.locator("#showEvents").is_checked(), (
        "Reading an infrastructure event unexpectedly restored its marker layer")
    assert page.locator("#infra-map .infra-marker-icon").count()==0
    assert page.locator("#filterWrap").is_hidden(), (
        "Opening an archive record reopened the hidden marker-filter controls")
    page.locator("#closeEventDetail").click()
    page.locator("#showEvents").check()
    assert page.locator("#showEvents").is_checked()
    assert page.locator("#filterWrap").is_visible()
    page.locator("#resetView").click()
    assert page.locator("#areaName").inner_text() == "德国全国"
    assert page.locator("#eventList button").count() == 22
    page.locator("#eventCategory").select_option("school")
    assert page.locator("#eventList button").count() == 1
    page.locator("#infraStateJump").select_option("DE-NW")
    page.locator('[data-dossier-tab="projects"]').click()
    page.locator("#eventList button").first.click()
    assert "17间教室" in page.locator("#eventDetail").inner_text()
    assert "Datteln" in page.locator("#eventDetail").inner_text()
    # Event markers must never be confused with the state polygon's condition score.
    assert page.locator("#metricValue").inner_text().endswith(" / 100")
    assert not errors, f"Browser JS errors: {errors}"
    page.screenshot(path="/tmp/infrastructure-phase1-" + ("mobile" if mobile else "desktop") + ".png", full_page=True)
    page.close()


if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        verify(browser, False)
        verify(browser, True)
        browser.close()
    print("PASS Infrastructure 16-state choropleth and 22 events, Chromium desktop/mobile")
