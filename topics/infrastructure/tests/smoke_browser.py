#!/usr/bin/env python3
"""Infrastructure topic smoke: real Chromium at desktop and mobile sizes with deterministic offline base tiles."""
from __future__ import annotations
import base64
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8765/topics/infrastructure/"
LEAFLET = Path("node_modules/leaflet/dist")
ONE_PX = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9YA0sEUAAAAASUVORK5CYII=")


def verify(browser, mobile: bool) -> None:
    page = browser.new_page(viewport={"width": 390 if mobile else 1460, "height": 820 if mobile else 900})
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.route("https://unpkg.com/leaflet@1.9.4/dist/leaflet.js",
               lambda route: route.fulfill(path=str(LEAFLET / "leaflet.js"), content_type="text/javascript"))
    page.route("https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
               lambda route: route.fulfill(path=str(LEAFLET / "leaflet.css"), content_type="text/css"))
    page.route("**tile.openstreetmap.org/**",
               lambda route: route.fulfill(status=200, body=ONE_PX, content_type="image/png"))
    response = page.goto(BASE, wait_until="domcontentloaded", timeout=45000)
    assert response is not None and response.status == 200
    page.wait_for_function("document.querySelectorAll('#rankList button').length===16", timeout=35000)
    assert page.locator("#infra-map .leaflet-control-zoom-in").count() == 1
    assert page.locator(".modebar a[href='../infrastructure/'].active").count() == 0  # own active href is './'
    assert page.locator(".modebar a.modebtn.active[href='./']").inner_text() == "基础设施"
    assert page.locator("#showEvents").is_checked() is False
    assert page.locator("#eventSection").is_hidden()
    assert page.locator("#areaName").inner_text() == "德国全国"
    assert "非官方" in page.locator("#legend").inner_text()
    page.locator("#rankList button").first.click()
    assert page.locator("#areaName").inner_text() == "图林根"
    assert page.locator("#indicatorDetail").is_visible()
    assert page.locator("#indicatorDetail .metric-row").count() == 4
    assert page.locator("#eventSection").is_hidden()
    page.locator("#showEvents").check()
    assert page.locator("#eventSection").is_visible()
    assert page.locator("#eventList button").count() == 1
    page.locator("#eventList button").first.click()
    assert page.locator("#eventDetail").is_visible()
    assert page.locator("#eventDetail a[href^='https://']").count() >= 1
    assert "埃尔福特" in page.locator("#eventDetail").inner_text()
    page.locator("#closeEventDetail").click()
    assert page.locator("#eventDetail").is_hidden()
    page.locator("#resetView").click()
    assert page.locator("#areaName").inner_text() == "德国全国"
    assert page.locator("#eventList button").count() == 22
    page.locator("#eventCategory").select_option("school")
    assert page.locator("#eventList button").count() == 1
    page.locator("#eventList button").first.click()
    assert "17间教室" in page.locator("#eventDetail").inner_text()
    assert "Datteln" in page.locator("#eventDetail").inner_text()
    # Event markers must never be confused with the state polygon's condition score.
    assert page.locator("#metricValue").inner_text().endswith(" / 100")
    assert not errors, f"Browser JS errors: {errors}"
    page.screenshot(path="/tmp/infrastructure-phase1-" + ("mobile" if mobile else "desktop") + ".png", full_page=True)
    page.close()


if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        verify(browser, False)
        verify(browser, True)
        browser.close()
    print("PASS Infrastructure 16-state choropleth and 22 events, Chromium desktop/mobile")
