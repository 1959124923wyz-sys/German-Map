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
    assert page.locator("#stateLocate").is_visible()
    page.evaluate("""() => {
       const state=__CRIME_MAP__.getStateLayer().getLayers()
         .find(l=>l.feature.properties.name==='Saarland');
       window.__QA_STATE_CENTER__=state.getBounds().getCenter();
       return true;
    }""")
    if mobile:
        # Compact, scrollable overlay leaves room for the actual map.
        drawer=page.locator("#stateDrawer").bounding_box()
        map_box=page.locator("#map").bounding_box()
        assert drawer and map_box
        assert drawer["height"]<=188, drawer
        assert drawer["width"]<=map_box["width"]-10
        assert page.locator("#stateDrawerExpand").is_visible()
        assert page.locator("#stateDrawerExpand").get_attribute("aria-expanded")=="false"
        page.locator("#stateDrawerExpand").click()
        expanded=page.locator("#stateDrawer").bounding_box()
        assert expanded["height"]>drawer["height"]+50, (drawer,expanded)
        assert page.locator("#stateDrawerExpand").get_attribute("aria-expanded")=="true"
        page.locator("#stateDrawerExpand").click()
        assert page.locator("#stateDrawerExpand").get_attribute("aria-expanded")=="false"
    else:
        assert page.locator("#stateDrawerExpand").is_hidden()
    state_targets=page.evaluate("""() => (__CRIME_MAP__.getStateLayer()
      ?.getLayers()||[]).map(l=>({name:l.feature?.properties?.name,
        interactive:l.options.interactive!==false}))""")
    assert len(state_targets)==16,state_targets
    assert [s for s in state_targets if s["name"]=="Saarland"]==[
        {"name":"Saarland","interactive":False}],state_targets
    assert sum(s["interactive"] for s in state_targets)==15,state_targets
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
    assert page.evaluate("""() => {
      const layer=__CRIME_MAP__.getStateLayer();
      return layer && layer.getLayers().length===16 &&
        layer.getLayers().every(l=>l.options.interactive===false);
    }""")
    page.locator("#stateCountyBrowse").click()
    assert page.evaluate("__CRIME_MAP__.isCountyBrowse()") is False
    assert page.evaluate("""() => __CRIME_MAP__.getStateLayer()
      .getLayers().filter(l=>l.options.interactive!==false).length===15""")
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
    # Actual pointer regression (not synthetic layer.fire): selected-state SVG
    # must allow a real mouse click to reach the underlying county polygon.
    if not mobile:
        page.locator("#viewGermany").click()
        page.evaluate("""() => {
          const state=__CRIME_MAP__.getStateLayer().getLayers()
            .find(l=>l.feature?.properties?.name==='Saarland');
          state.fire('click');
          return true;
        }""")
        # Force a deliberate user selection (not a no-op same-value select).
        page.locator("#stateJump").select_option("Berlin")
        page.locator("#stateJump").select_option("Saarland")
        pointer=page.evaluate("""() => {
          const model=__CRIME_MAP__, map=model.map;
          const candidates=model.getCountyLayer().getLayers().filter(l=>
            String(l.feature?.id||l.feature?.properties?.AGS).startsWith('10'));
          const r=map.getContainer().getBoundingClientRect();
          const inside=window.CrimeMapUtils.pointInGeometry;
          const diag={zoom:map.getZoom(),map:[r.width,r.height],counties:candidates.length,
            center:[map.getCenter().lat,map.getCenter().lng],inside:0,within:0,samples:[]};
          for(const county of candidates){
            const b=county.getBounds();
            // Test interior points before boundary-adjacent grid cells:
            // Leaflet Canvas click targets may be simplified at high zoom.
            const order=[10,9,11,8,12,7,13,6,14,5,15,4,16,3,17,2,18,1,19];
            for(const yi of order)for(const xi of order){
              const lat=b.getSouth()+(b.getNorth()-b.getSouth())*yi/20;
              const lng=b.getWest()+(b.getEast()-b.getWest())*xi/20;
              if(!inside(lng,lat,county.feature.geometry))continue;
              diag.inside++;
              // Source geometry and Canvas' simplified hit path can differ
              // near boundaries at larger zoom. Check the actual hit path.
              const layerPoint=map.latLngToLayerPoint([lat,lng]);
              if(!county._containsPoint(layerPoint))continue;
              const pt=map.latLngToContainerPoint([lat,lng]);
              const x=r.left+pt.x,y=r.top+pt.y;
              const node=document.elementFromPoint(x,y);
              if(diag.samples.length<8)diag.samples.push({
                id:String(county.feature.id),pt:[pt.x,pt.y],
                node:node?.tagName,cls:node?.className?.baseVal||node?.className,
                blocked:!!node?.closest('#stateDrawer,.legend,.leaflet-control')});
              if(pt.x<15||pt.x>r.width-20||pt.y<25||pt.y>r.height-50)continue;
              diag.within++;
              if(!node||node.closest('#stateDrawer,.legend,.leaflet-control'))continue;
              return {x,y,id:String(county.feature.id),hit:node.tagName,
                hitPane:node.closest('.leaflet-pane')?.className||'none'};
            }
          }
          return {debug:diag};
        }""")
        assert pointer and "x" in pointer, pointer
        page.mouse.click(pointer["x"],pointer["y"])
        assert page.evaluate("__CRIME_MAP__.getPinnedArea()?.ags")==pointer["id"], {"target":pointer,"pinned":page.evaluate("__CRIME_MAP__.getPinnedArea()?.ags"),"zoom":page.evaluate("__CRIME_MAP__.map.getZoom()")}
        assert page.locator("#crimeCountyDossier").is_visible()
        assert page.locator("#stateDrawer").evaluate("(e)=>e.classList.contains('open')")
    # A deliberate state locator may move the camera; a normal county click never does.
    # Check actual screen visibility, accounting for maxBounds at the western edge.
    assert page.evaluate("Boolean(window.__QA_STATE_CENTER__)")
    page.locator("#stateLocate").click()
    focus=page.evaluate("""() => {
       const m=__CRIME_MAP__.map;
       const at=m.latLngToContainerPoint(window.__QA_STATE_CENTER__);
       const mr=m.getContainer().getBoundingClientRect();
       const dr=document.querySelector('#stateDrawer').getBoundingClientRect();
       const x=mr.left+at.x,y=mr.top+at.y;
       return {x,y,zoom:m.getZoom(),map:{left:mr.left,top:mr.top,right:mr.right,bottom:mr.bottom},
         blocked:x>=dr.left&&x<=dr.right&&y>=dr.top&&y<=dr.bottom};
    }""")
    assert focus["zoom"]<=8.01, focus
    assert not focus["blocked"], focus
    assert focus["map"]["left"]<=focus["x"]<=focus["map"]["right"], focus
    assert focus["map"]["top"]<=focus["y"]<=focus["map"]["bottom"], focus
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
