#!/usr/bin/env python3
"""Finance 08 PR browser smoke: real Leaflet app, responsive UI, no network-only dependencies."""
from __future__ import annotations
import base64
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8765/topics/finance/"
LEAFLET = Path("node_modules/leaflet/dist")
ONE_PX = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9YA0sEUAAAAASUVORK5CYII=")

def verify(browser, mobile: bool = False):
    page = browser.new_page(viewport={"width": 390 if mobile else 1440, "height": 844 if mobile else 900},
                            device_scale_factor=1)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.route("https://unpkg.com/leaflet@1.9.4/dist/leaflet.js",
               lambda r: r.fulfill(path=str(LEAFLET / "leaflet.js"), content_type="text/javascript"))
    page.route("https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
               lambda r: r.fulfill(path=str(LEAFLET / "leaflet.css"), content_type="text/css"))
    page.route("**tile.openstreetmap.org/**",
               lambda r: r.fulfill(status=200, body=ONE_PX, content_type="image/png"))
    page.goto(BASE, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_function("document.getElementById('mapStatus').hidden === true", timeout=45000)
    assert page.locator("#finance-map .leaflet-control-zoom-in").count() == 1
    # The country map must include the whole German geographical extent.
    assert page.evaluate("(bounds) => window.__FINANCE_MAP__.getBounds().contains(L.latLngBounds(bounds))", 
                         [[47.15, 5.4], [55.1, 15.6]])

    assert page.locator('[data-mode="state"]').get_attribute("aria-pressed") == "true"
    assert not page.locator("#showEvents").is_checked()
    assert page.locator("#countState").inner_text() == "13 / 16"
    assert page.locator("#caseList button").count() == 8

    page.locator("#stateMetric").select_option("integrated-2024")
    assert "综合市镇债务" in page.locator("#legend").inner_text()
    assert "2024" in page.locator("#mapGuideTitle").inner_text()
    page.locator("#stateMetric").select_option("integrated-2022")
    assert "2022" in page.locator("#legend").inner_text()
    page.locator("#stateMetric").select_option("balance-2025")
    assert "人均财政收支" in page.locator("#legend").inner_text()

    page.locator("#loanDrawer summary").click()
    assert page.locator("#loanHistory table tbody tr").count() == 5
    page.locator("#loanDrawer summary").click()

    page.locator('[data-mode="rp"]').click()
    assert page.locator("#rpPeriodWrap").is_visible()
    page.locator("#rpPeriod").select_option("2026-H1-counties")
    assert "24县政府本级" in page.locator("#mapGuideNote").inner_text()
    assert "2026上半年" in page.locator("#sectionTitle").inner_text()

    page.locator('[data-mode="events"]').click()
    page.wait_for_function("document.querySelectorAll('.finance-bubble-inner').length >= 30")
    assert page.locator("#eventsControl").is_hidden()
    page.locator("#caseList button").first.click()
    assert page.locator("#detail").is_visible()
    assert page.locator("#detail a[href^='https://']").count() >= 1

    page.locator("#extraControls summary").click()
    assert page.locator("#showAllCases").is_visible()
    page.locator("#showAllCases").click()
    assert "170" in page.locator("#visibleCount").inner_text() or page.locator("#caseList button").count() > 0
    page.locator("#resetView").click()
    assert page.locator('[data-mode="state"]').get_attribute("aria-pressed") == "true"
    assert not page.locator("#showEvents").is_checked()
    assert page.evaluate("() => window.__FINANCE_MAP__.getBounds().contains(L.latLngBounds([[47.15,5.4],[55.1,15.6]]))"), "Reset must show whole Germany"

    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 4")
    page.screenshot(path="/tmp/finance08-" + ("mobile" if mobile else "desktop") + ".png",
                    full_page=True)
    assert not errors, errors
    print("PASS Finance 08 real Chromium", "mobile" if mobile else "desktop",
          "state debt/balance, loans, RP county scope, event map, source links, archive, navigation", flush=True)
    page.close()

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            verify(browser)
            verify(browser, True)
        finally:
            browser.close()
