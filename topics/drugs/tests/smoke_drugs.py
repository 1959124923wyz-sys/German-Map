#!/usr/bin/env python3
"""Real pointer regression for the independent drug map preview."""
from pathlib import Path
import re

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8765/topics/drugs/"

def click_place(page, lat, lon):
    point = page.evaluate(
        "([lat,lon]) => { const p=window.__DRUGS_PREVIEW_MAP__.latLngToContainerPoint([lat,lon]);"
        "const b=document.getElementById('drug-map').getBoundingClientRect();"
        "return {x:b.left+p.x,y:b.top+p.y}; }", [lat, lon])
    page.mouse.click(point["x"], point["y"])

def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 920})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(URL, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_function(
                "() => document.getElementById('county-count').textContent.includes('/')",
                timeout=45000)
            count = page.locator('#county-count').inner_text()
            assert not errors, errors
            assert re.search(r'\d+ / \d+', count), count
            assert page.locator('.leaflet-pane svg path').count() > 200, ('SVG paths:', page.locator('.leaflet-pane svg path').count())
            # Large, non-overlapping southern / central states: real pointer events.
            click_place(page, 48.85, 11.2)
            page.locator('#state-panel').wait_for(state='visible')
            first = page.locator('#state-name').inner_text()
            assert first, first
            click_place(page, 50.72, 9.1)
            second = page.locator('#state-name').inner_text()
            assert first != second, (first, second)
            page.locator('#close-state').click()
            assert not page.locator('#state-panel').is_visible()
            click_place(page, 48.85, 11.2)
            page.locator('#state-panel').wait_for(state='visible')
            assert page.locator('#state-name').inner_text() == first
            # After zoom, state fills must release county hit targets.
            page.evaluate(
                "()=>window.__DRUGS_PREVIEW_MAP__.setView([50.72,9.1],9,{animate:false})")
            page.wait_for_timeout(300)
            click_place(page, 50.72, 9.1)
            page.locator('#state-panel').wait_for(state='visible')
            assert '每10万人登记案件' in page.locator('#state-rate-label').inner_text()
            assert not errors, errors
            print('PASS drug map smoke:', count, 'states', first, second, 'county click at zoom 9')
        finally:
            browser.close()

if __name__ == '__main__':
    main()
