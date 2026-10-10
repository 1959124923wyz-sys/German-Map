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
            count = page.locator('#county-count').text_content()
            assert not errors, errors
            assert re.search(r'\d+ / \d+', count), count
            assert page.locator('.leaflet-pane svg path').count() > 200, ('SVG paths:', page.locator('.leaflet-pane svg path').count())
            # Shared city labels must show above choropleths without taking clicks.
            assert page.locator('#drug-map .crime-city-label').count() >= 8
            assert page.locator('#drug-map .crime-city-label').filter(has_text='柏林').count() >= 1
            assert page.locator('#drug-map .crime-city-label').first.evaluate(
                '(e) => parseFloat(getComputedStyle(e).fontSize)') >= 11
            assert page.evaluate("() => getComputedStyle(window.__DRUGS_PREVIEW_MAP__.getPane('drugs-city-labels')).pointerEvents") == 'none'
            # All 16 states must have a real county-backed summary and drilldown.
            assert page.locator('#state-index-list button').count() == 16
            # First-screen contract: only one headline metric, all auxiliary
            # national statistics, rankings and methods closed by default.
            assert page.locator('#national-drug-summary .metricbox.wide').is_visible()
            for drawer in ('national-extras','national-states','national-counties','national-method'):
                assert not page.locator('#'+drawer).get_attribute('open'), drawer
            assert not page.locator('#national-extras .national-health-summary').is_visible()
            assert not page.locator('#state-index-list').is_visible()
            page.locator('#national-states > summary').click()
            page.locator('#state-index-list button').filter(has_text='巴伐利亚州').click()
            assert page.locator('#region-navigator').is_visible()
            assert not page.locator('#national-drug-summary').is_visible()
            assert '巴伐利亚州' in page.locator('#region-heading').inner_text()
            page.wait_for_function(
                "() => document.getElementById('region-evidence-head')?.textContent.includes('247')",
                timeout=30000)
            assert not page.locator('#region-evidence').get_attribute('open')
            page.locator('#region-evidence-head').click()
            assert '247' in page.locator('#region-evidence-body').inner_text()
            assert '214' in page.locator('#region-evidence-body').inner_text()
            bavaria_details = page.locator('#region-evidence-body').inner_text()
            for expected in ('7,164', '4,440', '1,308', '15,270', '3,972', '823'):
                assert expected in bavaria_details, ('Bayern 2025 PKS', expected, bavaria_details)
            assert '大麻法' in bavaria_details or '2024年4月' in bavaria_details
            assert page.locator('#region-evidence-body a[href^="https://"]').count() >= 1
            page.locator('#region-evidence-head').click()
            page.screenshot(path='/tmp/germany-drugs-evidence-bavaria.png', full_page=True)
            assert page.locator('#drug-map path[stroke="#ffffff"]').count() >= 1, 'Selected state must have a white border'
            assert page.locator('#region-county-list button').count() == 96
            assert not page.locator('#region-county-details').get_attribute('open')
            assert not page.locator('#region-news').get_attribute('open')
            assert '估算州级' in page.locator('#region-rate-label').inner_text()
            assert page.locator('#region-cases').inner_text() not in ['—','0']
            page.locator('#region-drill').click()
            page.wait_for_function('() => window.__DRUGS_PREVIEW_MAP__.getZoom() >= 8')
            page.locator('#region-county-details > summary').click()
            page.locator('#region-county-list button').first.click()
            assert '县市详情' in page.locator('#region-heading').inner_text()
            assert page.locator('#region-change').inner_text().startswith('较2024年登记案件：')
            assert '%' in page.locator('#region-change').inner_text()
            page.locator('#region-interpretation > summary').click()
            assert page.locator('#region-original-source').is_visible()
            page.wait_for_function("() => document.querySelectorAll('#region-news-list li').length >= 1")
            page.locator('#region-news > summary').click()
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
            page.locator('#state-index-list button').filter(has_text='下萨克森州').click()
            page.wait_for_function(
                "() => document.getElementById('region-evidence-head')?.textContent.includes('毒品罪名细分')")
            page.locator('#region-evidence-head').click()
            assert '3,618' in page.locator('#region-evidence-body').inner_text()
            assert '1,677' in page.locator('#region-evidence-body').inner_text()
            assert page.locator('.evidence-offence-table tbody tr:not(.evidence-code-row)').count() == 4
            page.locator('#region-home').click()
            page.locator('#state-index-list button').filter(has_text='柏林').click()
            page.wait_for_function(
                "() => document.getElementById('region-evidence-head')?.textContent.includes('300')")
            page.locator('#region-evidence-head').click()
            assert '7.7' in page.locator('#region-evidence-body').inner_text()
            berlin_details = page.locator('#region-evidence-body').inner_text()
            for expected in ('2,218', '1,432', '2,343', '1,309', '731200', '732200'):
                assert expected in berlin_details, ('Berlin 2025 PKS', expected, berlin_details)
            assert '子项' in berlin_details or '其中' in berlin_details
            page.locator('#region-home').click()
            page.locator('#state-index-list button').filter(has_text='萨尔州').click()
            page.wait_for_function(
                "() => document.getElementById('region-evidence-head')?.textContent.includes('暂无核实数字')")
            page.locator('#region-evidence-head').click()
            assert '不表示死亡人数为零' in page.locator('#region-evidence-body').inner_text()
            page.locator('#region-home').click()
            # New primary-source state metrics remain explicitly scope-labeled.
            for state,expected in [
                ('Brandenburg', ['701','404','248','27','19']),
                ('Rheinland-Pfalz', ['34','515','858','1,043','152','3,202','2,319','495','316','86','47','173','178']),
                ('Hessen', ['2,406','543','153','157','263']),
                ('Baden-Württemberg', ['156','61','NpSG','BtMG']),
                ('Nordrhein-Westfalen', ['7,507', '6,433', '可卡因／快克']),
                ('Sachsen', ['2,418','263','2,785','1,669','272','175']),
                ('Hamburg', ['3,298','1,995','982','1,918','1,230']),
                ('Thüringen', ['77','50']),
                ('Sachsen-Anhalt', ['61','48','1,222','1,080','839','788','4,544','5,887','379','598']),
                ('Mecklenburg-Vorpommern', ['24','15','486','421','133','94'])
            ]:
                page.locator('#state-index-list').get_by_text({'Brandenburg':'勃兰登堡州','Rheinland-Pfalz':'莱茵兰－普法尔茨州','Hessen':'黑森州','Baden-Württemberg':'巴登－符腾堡州','Nordrhein-Westfalen':'北莱茵－威斯特法伦州','Sachsen':'萨克森州','Hamburg':'汉堡','Thüringen':'图林根州','Sachsen-Anhalt':'萨克森－安哈尔特州','Mecklenburg-Vorpommern':'梅克伦堡－前波美拉尼亚州'}.get(state,state), exact=True).click()
                page.wait_for_function(
                    "() => document.getElementById('region-evidence-head')?.textContent !== '州级补充资料 · 加载中'",
                    timeout=30000)
                page.locator('#region-evidence-head').click()
                content=page.locator('#region-evidence-body').inner_text()
                for value in expected:
                    assert value in content,(state,value,content)
                assert page.locator('#region-evidence-body a[href^="https://"]').count()>=1
                if state == 'Rheinland-Pfalz':
                    assert '2025年毒品相关死亡' in content
                    assert '34 人' in content
                    assert '2024年可比死亡人数：未核实' in content
                    assert page.locator('#region-evidence-body .evidence-source a[href*="mainz.de"]').count()>=1
                assert page.locator('#region-evidence-body svg.evidence-mini-trend').count()==0
                if state == 'Sachsen-Anhalt':
                    assert '此数值由公共媒体或专业机构引述' not in content
                    assert '毒品非法交易与走私（多物质）' in content
                if state == 'Mecklenburg-Vorpommern':
                    assert '媒体或专业机构' in content
                    assert '州级' in page.locator('#region-evidence-head').inner_text()
                    assert 'NaN' not in content
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
            assert first == '巴伐利亚州', first
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
            page.locator('#region-interpretation > summary').click()
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
            assert not page.locator('#wastewater-rank-details').get_attribute('open')
            page.locator('#wastewater-rank-details > summary').click()
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
            if not page.locator('#region-news').get_attribute('open'):
                page.locator('#region-news > summary').click()
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
            # Mobile first viewport: maps/legend and one headline metric,
            # while the long lists remain accessible but not expanded.
            mobile = browser.new_page(viewport={"width":390,"height":844}, device_scale_factor=1)
            mobile_errors=[]
            mobile.on("pageerror",lambda e:mobile_errors.append(str(e)))
            mobile.goto(URL,wait_until="domcontentloaded",timeout=45000)
            mobile.wait_for_function("() => document.querySelector('#county-count')?.textContent.includes('/')",timeout=45000)
            assert mobile.locator('#national-drug-summary .metricbox.wide').is_visible()
            assert not mobile.locator('#national-states').get_attribute('open')
            assert not mobile.locator('#national-extras').get_attribute('open')
            assert mobile.locator('#drug-map .leaflet-control-zoom-in').count()==1
            assert mobile.evaluate("document.documentElement.scrollWidth <= innerWidth + 3"), 'mobile must not scroll horizontally'
            mobile.locator('#national-states > summary').click()
            assert mobile.locator('#state-index-list button').count()==16
            mobile.screenshot(path='/tmp/germany-crime-map-drugs-mobile-clean.png',full_page=True)
            assert not mobile_errors,mobile_errors
            mobile.close()
            print('PASS drug map smoke:', count, 'states', first, second,
                  'county click, clean collapsed overview, mobile, EUDA 13 stations, 6 drugs, tab switch and return')
        finally:
            browser.close()

if __name__ == '__main__':
    main()
