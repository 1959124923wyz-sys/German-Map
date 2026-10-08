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
            # Shared city labels must show above choropleths without taking clicks.
            assert page.locator('#drug-map .crime-city-label').count() >= 8
            assert page.locator('#drug-map .crime-city-label').filter(has_text='Berlin').count() >= 1
            assert page.locator('#drug-map .crime-city-label').first.evaluate(
                '(e) => parseFloat(getComputedStyle(e).fontSize)') >= 11
            assert page.evaluate("() => getComputedStyle(window.__DRUGS_PREVIEW_MAP__.getPane('drugs-city-labels')).pointerEvents") == 'none'
            # All 16 states must have a real county-backed summary and drilldown.
            assert page.locator('#state-index-list button').count() == 16
            page.locator('#state-index-list button').filter(has_text='Bayern').click()
            assert page.locator('#region-navigator').is_visible()
            assert not page.locator('#national-drug-summary').is_visible()
            assert 'Bayern' in page.locator('#region-heading').inner_text()
            assert page.locator('#drug-map path[stroke="#ffffff"]').count() >= 1, 'Selected state must have a white border'
            assert page.locator('#region-county-list button').count() == 96
            assert '估算州级' in page.locator('#region-rate-label').inner_text()
            assert page.locator('#region-cases').inner_text() not in ['—','0']
            page.locator('#region-drill').click()
            page.wait_for_function('() => window.__DRUGS_PREVIEW_MAP__.getZoom() >= 8')
            page.locator('#region-county-list button').first.click()
            assert '县市详情' in page.locator('#region-heading').inner_text()
            assert page.locator('#drug-map path[stroke="#ffffff"]').count() >= 1, 'County selection requires white border'
            assert '同比' in page.locator('#region-completeness').inner_text()
            assert page.locator('#region-state-link').is_visible()
            page.locator('#region-state-link').click()
            assert '州级汇总' in page.locator('#region-heading').inner_text()
            page.locator('#region-home').click()
            assert page.locator('#national-drug-summary').is_visible()
            assert not page.locator('#region-navigator').is_visible()
            assert page.locator('#drug-map path[stroke="#ffffff"]').count() == 0, 'National reset must clear selected border'
            assert page.locator('#state-index-list button').count() == 16
            # Visual regression: site dark shell and ascending low-to-high green palette.
            palette = page.locator('#legend-data .legend-gradient span')
            assert palette.count() == 7, f'Expected seven green intervals, got {palette.count()}'
            first = palette.first.evaluate('(e) => getComputedStyle(e).backgroundColor')
            last = palette.last.evaluate('(e) => getComputedStyle(e).backgroundColor')
            assert first == 'rgb(229, 244, 232)', first
            assert last == 'rgb(14, 81, 57)', last
            body_bg = page.locator('body').evaluate('(e) => getComputedStyle(e).backgroundColor')
            sidebar_bg = page.locator('.sidebar').evaluate('(e) => getComputedStyle(e).backgroundColor')
            assert body_bg == 'rgb(12, 17, 23)', body_bg
            assert sidebar_bg == 'rgb(19, 26, 34)', sidebar_bg
            assert page.locator('.legend-title').inner_text() == '毒品违法案件 / 每10万人'
            page.screenshot(path='/tmp/germany-crime-map-drugs-dark.png', full_page=True)
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
            # Mouse focus on an SVG polygon may not produce a large black focus bbox.
            focused_outline = page.evaluate("() => {let e=document.activeElement;return e && e.closest('#drug-map') ? getComputedStyle(e).outlineStyle : 'none';}")
            assert focused_outline == 'none', focused_outline
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
            # EUDA overlay is a separate real data layer with six substances.
            page.locator('#drugs-tab-wastewater').click()
            page.wait_for_function(
                "() => document.getElementById('wastewater-sites')?.textContent === '13'",
                timeout=30000)
            assert page.locator('#drugs-wastewater-content').is_visible()
            assert not page.locator('#drugs-crime-content').is_visible()
            assert page.locator('#wastewater-rank button').count() == 13
            assert page.evaluate('() => window.__DRUGS_WASTEWATER_TEST__.markers') == 13
            assert page.locator('#legend-title').inner_text().startswith('大麻')
            page.screenshot(path='/tmp/germany-crime-map-drugs-euda.png', full_page=True)
            page.locator('#wastewater-substance').select_option('cocaine')
            assert page.locator('#legend-title').inner_text().startswith('可卡因')
            assert page.locator('#wastewater-rank button').count() == 13
            page.locator('#wastewater-rank button').first.click()
            assert page.locator('#wastewater-flyout').is_visible()
            assert page.locator('#wastewater-value').inner_text() not in ['—','0']
            page.locator('#close-wastewater').click()
            assert not page.locator('#wastewater-flyout').is_visible()
            page.locator('#drugs-tab-crime').click()
            assert page.locator('#drugs-crime-content').is_visible()
            assert not page.locator('#drugs-wastewater-content').is_visible()
            assert page.locator('#legend-title').inner_text() == '毒品违法案件 / 每10万人'
            page.evaluate("() => window.__DRUGS_PREVIEW_MAP__.setView([50.72,9.1],6,{animate:false})")
            page.wait_for_timeout(250)
            click_place(page, 50.72, 9.1)
            page.locator('#state-panel').wait_for(state='visible')
            assert not errors, errors
            print('PASS drug map smoke:', count, 'states', first, second,
                  'county click, EUDA 13 stations, 6 drugs, tab switch and return')
        finally:
            browser.close()

if __name__ == '__main__':
    main()
