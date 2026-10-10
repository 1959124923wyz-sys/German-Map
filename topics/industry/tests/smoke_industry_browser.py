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
    assert page.locator("#eventList .industry-row").count()==30
    assert "不是" in page.locator("#methodNote").inner_text() or "尚非" in page.locator("#methodNote").inner_text()
    assert page.locator(".modebar a.modebtn").count()==10
    assert page.locator(".modebar .active").inner_text()=="工业衰退"
    page.locator("#eventList .industry-row").first.click()
    assert page.locator("#eventDetail").is_visible()
    assert page.locator("#eventDetail a[href^='https://']").count()>0
    page.locator("#viewGermany").click()
    assert page.locator("#areaName").inner_text()=="德国全国"
    page.locator("#showMarkers").uncheck()
    assert page.locator("#showMarkers").is_checked() is False
    page.locator("#showMarkers").check()
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
