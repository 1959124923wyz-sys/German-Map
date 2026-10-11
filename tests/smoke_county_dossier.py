#!/usr/bin/env python3
"""Browser QA: all published PKS categories of a pinned county, both viewport sizes."""
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8765/"

def verify(browser,mobile=False):
    page=browser.new_page(viewport={"width":390 if mobile else 1440,"height":844 if mobile else 900})
    errors=[]
    page.on("pageerror",lambda e: errors.append(str(e)))
    page.route("**/tile.openstreetmap.org/**",lambda r:r.abort())
    page.goto(BASE,wait_until="domcontentloaded",timeout=45000)
    page.wait_for_function("""() => {
      const m=window.__CRIME_MAP__;
      return m?.getPksData()?.records?.['10041']?.homicide
        && m?.getPropertyData()?.records?.['10041']?.property_total
        && m?.getCountyLayer()?.getLayers()?.length>=395
        && window.__CRIME_COUNTY_DOSSIER__;
    }""",timeout=40000)
    assert page.locator("#crimeCountyDossier").is_hidden()
    assert page.evaluate("window.__CRIME_COUNTY_DOSSIER__.entries('violence')")==0
    # Hovering the map must remain transient; only pinned counties get the archive.
    page.evaluate("""() => {
      const layer=window.__CRIME_MAP__.getCountyLayer().getLayers()
        .find(l=>String(l.feature?.id||l.feature?.properties?.AGS)==='10041');
      layer.fire('mouseover');
      return true;
    }""")
    assert page.locator("#crimeCountyDossier").is_hidden()
    page.evaluate("""() => {
      const layer=window.__CRIME_MAP__.getCountyLayer().getLayers()
        .find(l=>String(l.feature?.id||l.feature?.properties?.AGS)==='10041');
      layer.fire('click');
      return true;
    }""")
    assert page.locator("#crimeCountyDossier").is_visible()
    # Pinning an actual county automatically reveals its parent state's official
    # numbers, while preserving the complete county dossier on the right.
    assert page.locator("#stateDrawer").evaluate("(e)=>e.classList.contains('open')")
    assert page.locator("#stateCountyBrowse").is_visible()
    page.locator("#stateCountyDirectory > summary").click()
    assert page.locator("#stateCountyList .state-county-row").count()>0
    page.locator("#stateCountySearch").fill("10041")
    assert page.locator("#stateCountyList .state-county-row").count()==1
    before_view=page.evaluate("({z:__CRIME_MAP__.map.getZoom(),lat:__CRIME_MAP__.map.getCenter().lat})")
    page.locator("#stateCountyList .state-county-row").click()
    after_view=page.evaluate("({z:__CRIME_MAP__.map.getZoom(),lat:__CRIME_MAP__.map.getCenter().lat})")
    assert before_view==after_view,"county directory must not auto-pan"
    assert page.evaluate("__CRIME_COUNTY_DOSSIER__.selected()")=="10041|violence"
    page.locator("#stateCountyBrowse").click()
    assert page.evaluate("__CRIME_MAP__.isCountyBrowse()") is True
    assert page.evaluate("__CRIME_MAP__.getStateLayer()") is None
    page.locator("#stateCountyBrowse").click()
    assert page.evaluate("__CRIME_MAP__.isCountyBrowse()") is False
    assert page.locator("#crimeCountyExpand").get_attribute("open") is None
    assert page.locator("#crimeCountyExpand > summary").is_visible()
    page.locator("#crimeCountyExpand > summary").click()
    assert page.locator("#crimeCountyExpand").get_attribute("open") is not None
    assert page.evaluate("window.__CRIME_COUNTY_DOSSIER__.selected()")== "10041|violence"
    assert page.evaluate("window.__CRIME_COUNTY_DOSSIER__.active()")=="violence"
    assert page.locator("#crimeCountyViolence .crime-county-metric").count()==5
    assert page.locator("#crimeCountyProperty .crime-county-metric").count()==5
    assert "1,234 起" in page.locator("[data-metric='violence'] .crime-county-facts").inner_text()
    assert "19 起" in page.locator("[data-metric='homicide'] .crime-county-facts").inner_text()
    assert "+46 %" in page.locator("[data-metric='homicide']").inner_text()
    assert "9,725 起" in page.locator("[data-metric='property_total']").inner_text()
    assert page.locator("#crimeCountyViolenceSource[href^='https://']").count()==1
    assert page.locator("#crimeCountyPropertySource[href^='https://']").count()==1
    page.locator('[data-dossier-tab="property"]').click()
    assert page.locator('[data-dossier-pane="property"]').is_visible()
    assert page.locator('[data-dossier-pane="violence"]').is_hidden()
    assert "类别有包含与重叠关系" in page.locator("#crimeCountyDossier").inner_text()
    before=page.evaluate("window.__CRIME_COUNTY_DOSSIER__.renders()")
    page.evaluate("""() => {
      const layer=window.__CRIME_MAP__.getCountyLayer().getLayers()
        .find(l=>String(l.feature?.id||l.feature?.properties?.AGS)==='10041');
      layer.fire('mouseover');
      return true;
    }""")
    assert page.evaluate("window.__CRIME_COUNTY_DOSSIER__.renders()")==before,"hover should not reset tabs"
    page.locator("#crimeCountyBackState").click()
    assert page.locator("#crimeCountyDossier").is_hidden()
    assert page.locator("#stateDrawer").evaluate("(e)=>e.classList.contains('open')"),"state data remains available"
    page.evaluate("""() => {
      const layer=window.__CRIME_MAP__.getCountyLayer().getLayers()
        .find(l=>String(l.feature?.id||l.feature?.properties?.AGS)==='10041');
      layer.fire('click');
      return true;
    }""")
    assert page.locator("#crimeCountyDossier").is_visible()
    page.locator("#viewGermany").click()
    assert page.locator("#crimeCountyDossier").is_hidden()
    assert page.locator("#crimeCountyExpand").get_attribute("open") is None
    page.locator("#modeProperty").click()
    page.wait_for_function("window.__CRIME_MAP__.getMode()==='property'")
    page.evaluate("""() => {
      const layer=window.__CRIME_MAP__.getCountyLayer().getLayers()
        .find(l=>String(l.feature?.id||l.feature?.properties?.AGS)==='10041');
      layer.fire('click');
      return true;
    }""")
    assert page.locator("#crimeCountyDossier").is_visible()
    assert page.locator("#crimeCountyExpand").get_attribute("open") is None
    page.locator("#crimeCountyExpand > summary").click()
    assert page.evaluate("window.__CRIME_COUNTY_DOSSIER__.active()")=="property"
    assert page.evaluate("window.__CRIME_COUNTY_DOSSIER__.selected()")=="10041|property"
    assert "2,919 /10万人" in page.locator("[data-metric='property_total']").inner_text()
    assert "4 %" in page.locator("[data-metric='property_total']").inner_text()
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+4")
    assert not errors,errors
    print("PASS source-specific county archive 5+5 categories", "mobile" if mobile else "desktop",flush=True)
    page.close()

with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True)
    try:
        verify(browser)
        verify(browser,True)
    finally:
        browser.close()
