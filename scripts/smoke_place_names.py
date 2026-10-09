#!/usr/bin/env python3
"""Regression: Chinese toponyms must match across all four public maps."""
import re
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
ASSET=ROOT/"node_modules/leaflet/dist"
BASE="http://127.0.0.1:8765/"
def test_one(browser,url,mode=None):
    page=browser.new_page(viewport={"width":1460,"height":940})
    errors=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    page.route(re.compile(r"https://unpkg\.com/leaflet@1\.9\.4/dist/leaflet\.(?:css|js)"),lambda r:r.fulfill(path=str(ASSET/("leaflet.css" if ".css" in r.request.url else "leaflet.js")),content_type="text/css" if ".css" in r.request.url else "application/javascript"))
    page.route(re.compile(r"https://basemaps\.cartocdn\.com/.*"),lambda r:r.abort())
    page.route(re.compile(r"https://tile\.openstreetmap\.org/.*"),lambda r:r.abort())
    page.goto(BASE+url,wait_until="domcontentloaded",timeout=45000)
    page.wait_for_function("()=>window.GermanPlaceNames && window.GermanPlaceNames.coverage.counties===400",timeout=30000)
    assert page.evaluate("()=>window.GermanPlaceNames.translate('Berlin')")=="柏林"
    assert page.evaluate("()=>window.GermanPlaceNames.translate('Nordrhein-Westfalen')")=="北莱茵－威斯特法伦州"
    assert page.evaluate("()=>window.GermanPlaceNames.byAGS('01001','Flensburg')")=="弗伦斯堡"
    if mode=="property":
        page.locator("#modeProperty").click()
        page.wait_for_function("()=>document.getElementById('modeProperty').classList.contains('active')",timeout=20000)
    if url.startswith("index.html"):
        target="#map"
        page.wait_for_function("()=>document.querySelectorAll('#map .crime-city-label').length>=4",timeout=45000)
    elif "drugs" in url:
        target="#drug-map"
        page.wait_for_function("()=>document.querySelectorAll('#state-index-list button').length===16",timeout=45000)
        page.locator("#state-index-list button").filter(has_text="巴伐利亚州").click()
        assert "巴伐利亚州" in page.locator("#region-heading").inner_text()
    else:
        target="#immigration-map"
        page.wait_for_function("()=>window.__IMMIGRATION_READY__===true",timeout=45000)
        page.locator("#state-list button").filter(has_text="柏林").click()
        assert "柏林" in page.locator("#region-name").inner_text()
        page.locator("#back-country").click()
    assert page.locator(target+" .crime-city-label").filter(has_text="柏林").count()>=1
    assert page.locator(target+" .crime-city-label").filter(has_text="Berlin").count()==0
    page.wait_for_function("()=>document.querySelectorAll('.leaflet-tile-pane img.leaflet-tile').length>0",timeout=12000)
    tile_urls=page.evaluate("()=>[...document.querySelectorAll('.leaflet-tile-pane img.leaflet-tile')].map(e=>e.src)")
    assert tile_urls and all('https://tile.openstreetmap.org/' in src for src in tile_urls),tile_urls[:4]
    assert not any('cartocdn' in src or 'API_KEY' in src for src in tile_urls),tile_urls[:4]
    tile_filter=page.evaluate("()=>getComputedStyle(document.querySelector('.leaflet-tile-pane')).filter")
    if 'drugs' in url or 'immigration' in url:
        assert 'invert(' not in tile_filter and 'grayscale(' not in tile_filter, ('Road basemap filter inverted/greyed',url,tile_filter)
    if 'immigration' in url:
        label_style=page.locator('#immigration-map .crime-city-label').first.evaluate("(e)=>({whiteSpace:getComputedStyle(e).whiteSpace,overflow:getComputedStyle(e.parentElement).overflow,color:getComputedStyle(e).color})")
        assert label_style['whiteSpace']=='nowrap' and label_style['overflow']=='visible',label_style
        assert page.evaluate("()=>+window.__IMMIGRATION_MAP_V13__.getPane('immigrationStatePane').querySelector('path').getAttribute('fill-opacity')") <= 0.65
    if 'drugs' in url:
        page.wait_for_function("()=>window.__DRUGS_PREVIEW_MAP__?.getPane('drugsCountyPane')?.querySelector('path')",timeout=30000)
        assert page.evaluate("()=>+window.__DRUGS_PREVIEW_MAP__.getPane('drugsCountyPane').querySelector('path').getAttribute('fill-opacity')") <= 0.72
    assert not errors,errors
    page.close()
with sync_playwright() as p:
    b=p.chromium.launch(headless=True)
    try:
        for path,mode in [("index.html",None),("index.html","property"),("topics/drugs/",None),("topics/immigration/",None)]:
            test_one(b,path,mode)
            print("PASS: shared Chinese names, "+path+" "+(mode or ""),flush=True)
    finally:
        b.close()
