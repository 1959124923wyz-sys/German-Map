#!/usr/bin/env python3
"""Fast E2E shared city-name/white-selection regression across all three topics."""
from playwright.sync_api import sync_playwright

BASE='http://127.0.0.1:8765/'
def map_click(page, container, map_expr, lat, lon):
    point = page.evaluate(
        """([container,map_expr,lat,lon]) => {
          const map=map_expr==='main' ? window.__CRIME_MAP__.map :
            window.__DRUGS_PREVIEW_MAP__;
          const p=map.latLngToContainerPoint([lat,lon]);
          const box=document.querySelector(container).getBoundingClientRect();
          return {x:box.left+p.x,y:box.top+p.y};
        }""", [container,map_expr,lat,lon])
    page.mouse.click(point['x'], point['y'])

def assert_no_svg_focus_rectangle(page, map_selector):
    """Reproduce the black frame in Chromium by focusing a real SVG state path.

    The fix must suppress the browser's rectangular SVG bounding-box outline,
    not the geographic selection stroke itself.
    """
    outcome = page.evaluate("""sel => {
      const shapes = [...document.querySelectorAll(sel+' svg path.leaflet-interactive')];
      if (!shapes.length) return {count:0};
      const path = shapes.find(e => e.getAttribute('tabindex') !== null) || shapes[0];
      path.focus();
      const s = getComputedStyle(path);
      const result = {count:shapes.length, tag:document.activeElement?.tagName,
        outline:s.outlineStyle, outlineWidth:s.outlineWidth,
        focusVisible:path.matches(':focus-visible'), stroke:s.stroke,
        strokeWidth:s.strokeWidth};
      path.blur();
      return result;
    }""", map_selector)
    # On the national view only 16 interactive state paths may be present.
    assert outcome['count'] >= 12, outcome
    assert outcome['outline'] == 'none', (
        'Black SVG bounding-box outline remains:', map_selector, outcome)
    print('PASS SVG focus style', map_selector, outcome, flush=True)

def label_assertions(page, container, pane_expr):
    page.wait_for_function("""(c)=>document.querySelectorAll(c+' .crime-city-label').length>=8""",
                           arg=container,timeout=35000)
    assert page.locator(container + ' .crime-city-label').filter(has_text='Berlin').count()>=1
    props=page.locator(container+' .crime-city-label').first.evaluate(
        '(e)=>({size:parseFloat(getComputedStyle(e).fontSize),color:getComputedStyle(e).color})')
    assert props['size']>=11,props
    assert page.evaluate(
        '(p)=>getComputedStyle((p==="main" ? window.__CRIME_MAP__.map : window.__DRUGS_PREVIEW_MAP__).getPane(p==="main" ? "major-city-labels" : "drugs-city-labels")).pointerEvents',
        pane_expr)=='none'

def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        try:
            page=browser.new_page(viewport={'width':1440,'height':900})
            errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(BASE,wait_until='domcontentloaded',timeout=45000)
            page.wait_for_function("() => window.__CRIME_MAP__?.getCountyLayer()?.getLayers().length>300",timeout=45000)
            label_assertions(page,'#map','main')
            assert_no_svg_focus_rectangle(page, '#map')
            main_labels=page.locator('#map .crime-city-label').count()
            map_click(page,'#map','main',48.85,11.2)
            page.locator('#stateDrawer.open').wait_for(state='visible')
            assert page.locator('#map path[stroke="#ffffff"]').count()>=1
            page.locator('#stateClose').click()
            map_click(page,'#map','main',50.72,9.1)
            page.locator('#stateDrawer.open').wait_for(state='visible')
            assert_no_svg_focus_rectangle(page,'#map')
            page.locator('#stateClose').click()
            page.locator('#modeProperty').click()
            page.wait_for_function('() => window.__CRIME_MAP__?.getMode()==="property"')
            label_assertions(page,'#map','main')
            assert page.locator('#map .crime-city-label').count()==main_labels
            # Fresh state selection survives changing metric mode.
            map_click(page,'#map','main',50.72,9.1)
            page.locator('#stateDrawer.open').wait_for(state='visible')
            assert page.locator('#map path[stroke="#ffffff"]').count()>=1
            page.locator('#stateClose').click()
            page.goto(BASE+'topics/drugs/',wait_until='domcontentloaded',timeout=45000)
            page.wait_for_function("()=>document.querySelector('#county-count')?.textContent.includes('/')",timeout=45000)
            label_assertions(page,'#drug-map','drug')
            assert_no_svg_focus_rectangle(page, '#drug-map')
            map_click(page,'#drug-map','drug',48.85,11.2)
            page.locator('#region-navigator').wait_for(state='visible')
            assert page.locator('#state-panel').count()==0
            assert page.locator('#drug-map path[stroke="#ffffff"]').count()>=1
            page.screenshot(path='/tmp/shared-city-labels.png',full_page=True)
            assert not errors,errors
            print('PASS 3 map views: visible city names, no pointer interception, white selected-state outline')
        finally:
            browser.close()

if __name__=='__main__':
    main()
