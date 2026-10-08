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
            page.wait_for_function(
                "() => document.getElementById('region-evidence-head')?.textContent.includes('247')",
                timeout=30000)
            assert not page.locator('#region-evidence').get_attribute('open')
            page.locator('#region-evidence-head').click()
            assert '247' in page.locator('#region-evidence-body').inner_text()
            assert '214' in page.locator('#region-evidence-body').inner_text()
            assert page.locator('#region-evidence-body a[href^="https://"]').count() >= 1
            page.locator('#region-evidence-head').click()
            page.screenshot(path='/tmp/germany-drugs-evidence-bavaria.png', full_page=True)
            assert page.locator('#drug-map path[stroke="#ffffff"]').count() >= 1, 'Selected state must have a white border'
            assert page.locator('#region-county-list button').count() == 96
            assert '估算州级' in page.locator('#region-rate-label').inner_text()
            assert page.locator('#region-cases').inner_text() not in ['—','0']
            page.locator('#region-drill').click()
            page.wait_for_function('() => window.__DRUGS_PREVIEW_MAP__.getZoom() >= 8')
            page.locator('#region-county-list button').first.click()
            assert '县市详情' in page.locator('#region-heading').inner_text()
            assert page.locator('#region-change').inner_text().startswith('较2024年登记案件：')
            assert '%' in page.locator('#region-change').inner_text()
            assert page.locator('#region-original-source').is_visible()
            page.wait_for_function("() => document.querySelectorAll('#region-news-list li').length >= 1")
            assert page.locator('#region-news-all').is_visible()
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
            # Authentic drug offence codes exist in two states; other states
            # are explicitly missing, not assigned synthetic values.
            page.locator('#state-index-list button').filter(has_text='Niedersachsen').click()
            page.wait_for_function(
                "() => document.getElementById('region-evidence-head')?.textContent.includes('毒品罪名细分')")
            page.locator('#region-evidence-head').click()
            assert '3,618' in page.locator('#region-evidence-body').inner_text()
            assert '1,677' in page.locator('#region-evidence-body').inner_text()
            assert page.locator('.evidence-offence-table tbody tr:not(.evidence-code-row)').count() == 4
            page.locator('#region-home').click()
            page.locator('#state-index-list button').filter(has_text='Berlin').click()
            page.wait_for_function(
                "() => document.getElementById('region-evidence-head')?.textContent.includes('300')")
            page.locator('#region-evidence-head').click()
            assert '7.7' in page.locator('#region-evidence-body').inner_text()
            page.locator('#region-home').click()
            page.locator('#state-index-list button').filter(has_text='Saarland').click()
            page.wait_for_function(
                "() => document.getElementById('region-evidence-head')?.textContent.includes('暂无核实数字')")
            page.locator('#region-evidence-head').click()
            assert '不表示死亡人数为零' in page.locator('#region-evidence-body').inner_text()
            page.locator('#region-home').click()
            # New primary-source state metrics remain explicitly scope-labeled.
            for state,expected in [
                ('Brandenburg', ['701','404','248','27','19']),
                ('Rheinland-Pfalz', ['515','858','1,043','152','3,202']),
                ('Hessen', ['2,406','543']),
                ('Sachsen', ['2,418','263','2,785','1,669','272','175']),
                ('Hamburg', ['3,298','1,995','982','1,918','1,230']),
                ('Thüringen', ['77','50']),
                ('Sachsen-Anhalt', ['61','48']),
                ('Mecklenburg-Vorpommern', ['486','421','133','94'])
            ]:
                page.locator('#state-index-list').get_by_text(state, exact=True).click()
                page.wait_for_function(
                    "() => document.getElementById('region-evidence-head')?.textContent !== '州级补充资料 · 加载中'",
                    timeout=30000)
                page.locator('#region-evidence-head').click()
                content=page.locator('#region-evidence-body').inner_text()
                for value in expected:
                    assert value in content,(state,value,content)
                assert page.locator('#region-evidence-body a[href^="https://"]').count()>=1
                page.locator('#region-home').click()
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
            # Real clicks after a region change must update the single right
            # sidebar rather than opening a duplicate map-covering state flyout.
            assert page.locator('#state-panel').count() == 0
            click_place(page, 48.85, 11.2)
            page.locator('#region-navigator').wait_for(state='visible')
            first = page.locator('#region-current').inner_text()
            assert first == 'Bayern', first
            click_place(page, 50.72, 9.1)
            second = page.locator('#region-current').inner_text()
            assert first != second, (first, second)
            page.locator('#region-home').click()
            assert not page.locator('#region-navigator').is_visible()
            click_place(page, 48.85, 11.2)
            assert page.locator('#region-current').inner_text() == first
            # After zoom, passive state borders release county click targets.
            page.evaluate(
                "()=>window.__DRUGS_PREVIEW_MAP__.setView([50.72,9.1],9,{animate:false})")
            page.wait_for_timeout(300)
            click_place(page, 50.72, 9.1)
            assert '县市详情' in page.locator('#region-heading').inner_text()
            assert page.locator('#region-original-source').is_visible()
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
            assert '较2024年：' in page.locator('#wastewater-change').inner_text()
            # Data coverage differs by substance; cannabis lacks valid prior-year
            # values and must never show a fabricated percent change.
            page.locator('#wastewater-substance').select_option('cannabis')
            page.locator('#wastewater-rank button').first.click()
            assert '无法计算可比变化' in page.locator('#wastewater-change').inner_text()
            page.locator('#wastewater-substance').select_option('cocaine')
            page.locator('#wastewater-rank button').first.click()
            assert '较2024年：' in page.locator('#wastewater-change').inner_text()
            page.locator('#close-wastewater').click()
            assert not page.locator('#wastewater-flyout').is_visible()
            page.locator('#drugs-tab-crime').click()
            assert page.locator('#drugs-crime-content').is_visible()
            assert not page.locator('#drugs-wastewater-content').is_visible()
            assert page.locator('#legend-title').inner_text() == '毒品违法案件 / 每10万人'
            # Live police reports: visible listing, clickable markers, original URLs,
            # reliable health contextual documents, strict category and state filters.
            page.locator('#drugs-tab-news').click()
            page.wait_for_function(
                "() => Number(document.querySelector('#drug-news-count')?.textContent) >= 6",
                timeout=30000)
            assert page.locator('#drugs-news-content').is_visible()
            assert not page.locator('#drugs-crime-content').is_visible()
            assert not page.locator('#drugs-wastewater-content').is_visible()
            assert page.evaluate('() => window.GermanMapDrugNews?.active === true')
            assert page.locator('#drug-news-list .drug-news-card').count() >= 6
            assert '截至 ' in page.locator('#drug-news-updated').inner_text()
            page.locator('#drug-news-type').select_option('death')
            assert int(page.locator('#drug-news-count').inner_text()) >= 1
            assert page.locator('#drug-news-list .drug-news-card').count() >= 1
            page.locator('#drug-news-type').select_option('trade')
            assert int(page.locator('#drug-news-count').inner_text()) >= 6
            assert int(page.locator('#drug-news-mapped').inner_text()) >= 3
            page.locator('#drug-news-list .drug-news-card').first.click()
            page.locator('.leaflet-popup-content a[href^="https://"]').first.wait_for(timeout=15000)
            page.locator('#drug-news-type').select_option('all')
            assert page.locator('#drug-news-state option').count() >= 8
            page.locator('#drug-news-state').select_option('Nordrhein-Westfalen')
            assert 1 <= int(page.locator('#drug-news-count').inner_text()) <= 150
            page.locator('#drug-news-state').select_option('all')
            page.screenshot(path='/tmp/germany-crime-map-drugs-news.png',full_page=True)
            page.locator('#drugs-tab-crime').click()
            assert not page.locator('#drugs-news-content').is_visible()
            page.locator('#region-news-all').click()
            page.wait_for_function('() => document.querySelector("#drugs-tab-news")?.classList.contains("selected")')
            assert page.locator('#drugs-news-content').is_visible()
            assert page.locator('#drug-news-state').input_value() != 'all'
            page.locator('#drugs-tab-crime').click()
            assert not page.locator('#drugs-news-content').is_visible()
            assert page.locator('#drugs-crime-content').is_visible()
            page.locator('#drugs-tab-wastewater').click()
            page.wait_for_function("() => window.__DRUGS_WASTEWATER_TEST__?.isActive === true")
            assert not page.locator('#drugs-news-content').is_visible()
            page.locator('#drugs-tab-crime').click()
            page.evaluate("() => window.__DRUGS_PREVIEW_MAP__.setView([50.72,9.1],6,{animate:false})")
            page.wait_for_timeout(250)
            click_place(page, 50.72, 9.1)
            assert page.locator('#region-navigator').is_visible()
            assert page.locator('#state-panel').count() == 0
            assert not errors, errors
            print('PASS drug map smoke:', count, 'states', first, second,
                  'county click, EUDA 13 stations, 6 drugs, tab switch and return')
        finally:
            browser.close()

if __name__ == '__main__':
    main()
