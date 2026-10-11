#!/usr/bin/env python3
"""Visual-shell regression: 10 modes / 9 physical German-Map pages."""
from pathlib import Path
import base64
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8765/"
LEAFLET = Path("node_modules/leaflet/dist")
PIX = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9YA0sEUAAAAASUVORK5CYII=")
MODES = [
    ("violence","index.html","暴力犯罪"),
    ("property","index.html?mode=property","财产犯罪"),
    ("drugs","topics/drugs/","毒品问题"),
    ("immigration","topics/immigration/","移民人口"),
    ("environment","topics/environment/","环保争议"),
    ("railway","topics/railway/","铁路运行"),
    ("finance","topics/finance/","地方财政"),
    ("industry","topics/industry/","工业衰退"),
    ("infrastructure","topics/infrastructure/","基础设施"),
    ("housing","topics/housing/","住房危机"),
]
NAMES = [x[2] for x in MODES]
SCREENSHOTS = Path("/tmp/atlas-shell")
SCREENSHOTS.mkdir(parents=True,exist_ok=True)

def verify(browser, phone=False):
    context = browser.new_context(viewport={"width":390 if phone else 1440,
                                            "height":844 if phone else 900},
                                  device_scale_factor=1, reduced_motion="reduce")
    context.route("https://unpkg.com/leaflet@1.9.4/dist/leaflet.js",
                  lambda r:r.fulfill(path=str(LEAFLET/"leaflet.js"),content_type="text/javascript"))
    context.route("https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
                  lambda r:r.fulfill(path=str(LEAFLET/"leaflet.css"),content_type="text/css"))
    context.route("**tile.openstreetmap.org/**",
                  lambda r:r.fulfill(status=200,body=PIX,content_type="image/png"))
    baseline = None
    for slug,path,name in MODES:
        page=context.new_page()
        response=page.goto(BASE+path,wait_until="domcontentloaded",timeout=60000)
        assert response and response.ok, (slug,"load",response.status if response else None)
        page.wait_for_function("""() => {
           const nav=document.querySelector('header .modebar, header .toplinks');
           return nav&&nav.querySelectorAll('.modebtn').length===10 &&
              !!document.querySelector('link[href*="atlas-shared-shell.css"]');
        }""",timeout=20000)
        # The property view updates its mode via main app initialization.
        if slug=="property":
            page.wait_for_function("""() => {
              const items=[...document.querySelectorAll('header .modebar .modebtn')];
              return items.some(x=>x.textContent.trim()==='财产犯罪'&&x.classList.contains('active'));
            }""",timeout=25000)
        # Wait for genuinely loaded cartography before taking the audit image.
        if slug=="housing":
            page.wait_for_function("window.GermanHousingResearch?.state()?.validCount===400",timeout=35000)
        if slug=="railway":
            page.wait_for_function("window.__RAILWAY_OVERVIEW__?.getNetworkReady()",timeout=35000)
        if phone:
            page.wait_for_function("""() => {
               const bar=document.querySelector('header .modebar,header .toplinks');
               const active=bar?.querySelector('.modebtn.active');
               if(!active)return false;
               const a=active.getBoundingClientRect(),b=bar.getBoundingClientRect();
               return a.left>=b.left-1 && a.right<=b.right+1;
            }""",timeout=10000)
        data=page.evaluate("""() => {
          const nav=document.querySelector('header .modebar, header .toplinks');
          const anchors=[...nav.querySelectorAll('.modebtn')];
          const active=anchors.filter(a=>a.classList.contains('active'));
          const style=active.length?getComputedStyle(active[0]):null;
          const first=nav.querySelector('.modebtn');
          const ns=getComputedStyle(nav);
          const rect=nav.getBoundingClientRect();
          return {
            names:anchors.map(x=>x.textContent.trim()),active:active.map(x=>x.textContent.trim()),
            radius:style?.borderTopLeftRadius,activeBg:style?.backgroundColor,
            background:getComputedStyle(document.querySelector('header')).backgroundImage,
            display:ns.display,wrap:ns.flexWrap,
            navWidth:rect.width,viewport:innerWidth,
            firstHeight:first?.getBoundingClientRect().height,
            fullWidth:document.documentElement.scrollWidth,
            bodyScope:document.body.classList.contains('atlas-shell')
          };
        }""")
        assert data["names"]==NAMES,(slug,"nav order",data)
        assert data["active"]==[name],(slug,"active tab",data)
        assert data["radius"]=="7px",(slug,"shared radius",data)
        assert data["activeBg"]=="rgb(52, 92, 115)",(slug,"active color",data)
        assert data["wrap"]=="nowrap",(slug,"nav wrapping",data)
        assert data["bodyScope"],(slug,"CSS namespace absent")
        assert data["navWidth"]<=data["viewport"]+2,(slug,"nav clipped",data)
        assert data["firstHeight"]>=30,(slug,"too-small tap target",data)
        if phone:
            assert data["fullWidth"]<=400,(slug,"horizontal page overflow",data)
        key=(data["radius"],data["activeBg"])
        if baseline is None:baseline=key
        assert key==baseline,(slug,"inconsistent header",data)
        page.screenshot(path=str(SCREENSHOTS/(slug+("-390" if phone else "-1440")+".png")),animations="disabled")
        if phone:
            # The strip must remain user-scrollable after revealing current mode.
            page.locator("header .modebar .modebtn, header .toplinks .modebtn").last.scroll_into_view_if_needed()
            assert page.locator("header .modebar .modebtn, header .toplinks .modebtn").last.is_visible()
        print("PASS",slug,"mobile" if phone else "desktop","active",data["activeBg"],flush=True)
        page.close()
    context.close()

if __name__=="__main__":
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        try:
            verify(browser,False)
            verify(browser,True)
        finally:
            browser.close()
    print("PASS unified shell: all 10 modes, 9 pages, desktop + mobile",flush=True)
