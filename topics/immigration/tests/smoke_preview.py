#!/usr/bin/env python3
"""Chromium smoke test for standalone immigration Leaflet preview.

Only the feature-branch standalone page is served; never touches the production page.
Requires: pip install playwright; playwright install chromium; npm install leaflet@1.9.4
"""
from __future__ import annotations

import base64
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[3]
DIST = ROOT / "topics" / "immigration" / "node_modules" / "leaflet" / "dist"
PIXEL = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScL/nwAAAABJRU5ErkJggg==")


def main() -> None:
    if not (DIST / "leaflet.js").is_file() or not (DIST / "leaflet.css").is_file():
        raise RuntimeError("Install local Leaflet test dependency first: npm install --prefix topics/immigration --no-save leaflet@1.9.4")

    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/topics/immigration/"
    try:
        with sync_playwright() as runner:
            browser = runner.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1366, "height": 880}, device_scale_factor=1)
            page_errors = []
            page.on("pageerror", lambda err: page_errors.append(str(err)))
            # Browser test reproducible without external CDN/network dependencies.
            page.route("https://unpkg.com/leaflet@1.9.4/dist/leaflet.js",
                       lambda route: route.fulfill(path=str(DIST / "leaflet.js"), content_type="application/javascript"))
            page.route("https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
                       lambda route: route.fulfill(path=str(DIST / "leaflet.css"), content_type="text/css"))
            page.route("https://unpkg.com/leaflet@1.9.4/dist/images/**",
                       lambda route: route.fulfill(status=404))
            page.route("https://tile.openstreetmap.org/**",
                       lambda route: route.fulfill(body=PIXEL, content_type="image/png"))

            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_function("window.GermanMapTopics?.immigration?.getViewState().active === true")
            assert not page.locator("#status").count(), "Standalone page reports a load error"
            assert page.locator(".immigration-topic").count() == 1
            try:
                page.wait_for_function(
                    "() => document.querySelectorAll('.leaflet-immigrationDataPane-pane path').length >= 16",
                    timeout=8000)
            except Exception:
                diagnostics = page.evaluate("""() => ({
                    status: document.querySelector('#status')?.innerText,
                    svgPaths: document.querySelectorAll('svg path').length,
                    topicPaths: document.querySelectorAll('.leaflet-immigrationDataPane-pane path').length,
                    panes: Array.from(document.querySelectorAll('.leaflet-pane')).map(x => x.className),
                    active: window.GermanMapTopics?.immigration?.getViewState().active
                })""")
                raise AssertionError(f"Missing state map polygons: {diagnostics}")
            assert page.locator(".leaflet-immigrationDataPane-pane").evaluate(
                "(node) => node.style.pointerEvents") == "none"
            assert page.locator(".im-national-value").inner_text().strip() == "232,067"

            values = [
                ("其中持有暂缓遣返证明", "190,974"),
                ("其中未持暂缓遣返证明", "41,093"),
                ("全年实际遣返", "22,787"),
                ("负有离境义务", "232,067"),
            ]
            for title, expected in values:
                page.get_by_role("button", name=title, exact=True).click()
                assert page.locator(".im-national-value").inner_text().strip() == expected

            page.get_by_role("combobox", name="选择德国联邦州").select_option("DE-HH")
            page.wait_for_function("window.GermanMapTopics.immigration.getViewState().state === 'DE-HH'")
            assert "11,477" in page.locator(".im-mini-stats").inner_text()

            # Real browser click inside Berlin's geographic bounds. Geographical
            # picking is owned by the *standalone harness*, not the topic module.
            point = page.evaluate("""() => {
              const m = window.__immigrationStandaloneMap;
              if (!m) return null;
              const p = m.latLngToContainerPoint([52.52,13.405]);
              return {x:p.x,y:p.y};
            }""")
            assert point is not None, "Preview map API is unavailable"
            page.locator("#map").click(position=point, force=True)
            page.wait_for_function("window.GermanMapTopics.immigration.getViewState().state === 'DE-BE'")

            for _ in range(3):
                page.get_by_role("button", name="测试退出 / 重新进入").click()
                assert page.locator(".immigration-topic").count() == 1
                page.wait_for_function(
                    "() => document.querySelectorAll('.leaflet-immigrationDataPane-pane path').length >= 16",
                    timeout=8000)
                assert page.locator(".leaflet-immigrationDataPane-pane").evaluate(
                    "(node) => node.style.pointerEvents") == "none"
                page.get_by_role("combobox", name="选择德国联邦州").select_option("DE-SN")
                page.wait_for_function("window.GermanMapTopics.immigration.getViewState().state === 'DE-SN'")
                page.get_by_role("combobox", name="选择德国联邦州").select_option("DE-BE")
            assert not page_errors, f"JavaScript runtime errors: {page_errors}"
            print("PASS: Leaflet state polygons, four metrics, Berlin map click, three re-entries, no pointer overlay.")
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
