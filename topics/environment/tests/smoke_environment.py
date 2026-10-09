#!/usr/bin/env python3
"""06 environmental controversies: data integrity + desktop/mobile interaction smoke."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE=os.getenv("GERMAN_MAP_TEST_BASE","http://127.0.0.1:8765/")
EXPECTED={"overview":64,"focus":21,"policy":10,"organization":10,"facility":92,"archive":41}
def test_page(browser,width,height,mobile=False):
    page=browser.new_page(viewport={"width":width,"height":height},device_scale_factor=1)
    errors=[]
    page.on("pageerror",lambda e: errors.append(str(e)))
    r=page.goto(BASE+"topics/environment/",wait_until="load",timeout=30000)
    assert r and r.ok, ("HTTP environment",r.status if r else None)
    page.wait_for_function("""() => window.GermanEnvironment06Data?.length===154 &&
         document.querySelectorAll('#entries .entry').length>0 &&
         document.querySelectorAll('#points .mark').length>0""",timeout=20000)
    assert page.locator(".site-nav a").count()==5
    assert page.locator(".site-nav a.active").inner_text()=="环保争议"
    assert page.locator('#mapSvg').is_visible()
    check=page.evaluate("""() => {
      const rows=window.GermanEnvironment06Data;
      const count=(kind)=>rows.filter(x=>x.kind===kind).length;
      const allGood=rows.every(x=>/^\\d{4}-\\d{2}-\\d{2}$/.test(x.date)
       && Number.isFinite(x.coordinates?.lat)&&Number.isFinite(x.coordinates?.lon)
       && x.sources?.length>0 && x.sources.every(s=>/^https:\\/\\//.test(s.url)));
      const phases={}; for(const x of rows.filter(x=>x.kind==='facility'))
        phases[x.facility_phase]=(phases[x.facility_phase]||0)+1;
      return {n:rows.length,archive:count('archive'),policy:count('policy'),
        organization:count('organization'),facility:count('facility'),
        facility_story:count('facility_story'),phases,allGood};
    }""")
    assert check["allGood"] and check["n"]==154,check
    assert [check[k] for k in ("archive","policy","organization","facility","facility_story")]==[41,10,10,92,1],check
    assert check["phases"]=={"retired":32,"awarded":36,"ordered":3,"scheduled":21},check
    for mode,expected in EXPECTED.items():
        page.locator(f'[data-mode="{mode}"]').click()
        count=int(page.locator("#count").inner_text())
        assert count==expected,(mode,count,expected)
        assert page.locator("#entries .entry").count()==expected,mode
        assert page.locator("#points .mark").count()==expected,mode
    # Future schedules are clearly distinguished from retired facilities.
    page.locator('[data-mode="facility"]').click()
    page.locator('[data-phase="scheduled"]').click()
    assert int(page.locator("#count").inner_text())==21
    assert "计划" in page.locator("#listHint").inner_text() or "退出" in page.locator("#listHint").inner_text()
    page.locator('[data-phase="retired"]').click()
    assert int(page.locator("#count").inner_text())==32
    # Actual disruptive actions including airport blockage, spray paint, roads.
    page.locator('[data-mode="archive"]').click()
    page.locator("#search").fill("机场")
    assert 1<=int(page.locator("#count").inner_text())<=41
    page.locator("#search").fill("")
    page.locator('[data-action="traffic"]').click()
    assert int(page.locator("#count").inner_text())==21
    page.locator('[data-action="all"]').click()
    page.locator("#entries .entry").first.click()
    assert page.locator("#detail h2").count()==1
    assert page.locator("#detail .sources a[href^='https://']").count()>=1
    # Real SVG action marker interactive rather than decoration.
    page.locator("#points .mark").last.dispatch_event("click")
    assert page.locator("#detail h2").count()==1
    page.locator("#zin").click()
    assert "scale(" in page.locator("#geoLayer").get_attribute("transform")
    page.locator("#reset").click()
    assert "scale(1)" in page.locator("#geoLayer").get_attribute("transform")
    if mobile:
        page.screenshot(path="/tmp/environment-06-mobile.png",full_page=True)
        assert page.locator(".site-nav").is_visible()
        assert page.locator('#entries').is_visible()
    else:
        page.screenshot(path="/tmp/environment-06-desktop.png",full_page=True)
    assert not errors,errors
    print("PASS environment 06",width,"x",height,check["n"],"records; tabs, event groups, statuses, links, SVG actions",flush=True)
    page.close()

if __name__=="__main__":
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        try:
            test_page(browser,1440,900)
            test_page(browser,390,844,True)
        finally:
            browser.close()
