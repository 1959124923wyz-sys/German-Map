#!/usr/bin/env python3
"""Minimal runtime smoke for BahnMonitor's public red-highlight map."""
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8769/topics/railway/"
ART = Path("/tmp/railway-v15")
ART.mkdir(exist_ok=True)

def number(page, sel):
    txt = page.locator(sel).inner_text()
    return int(txt.replace(",", "").strip())

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
    errors = []
    notfound = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("response", lambda r: notfound.append((r.status, r.url)) if r.status >= 400 else None)
    response = page.goto(BASE, wait_until="domcontentloaded", timeout=60000)
    assert response.status == 200
    page.wait_for_function("document.querySelectorAll('.segment').length > 100", timeout=80000)
    re_count = number(page, "#visibleCount")
    assert re_count > 100, ("Unexpected RE count", re_count)
    assert 0 < number(page, "#redCount") <= re_count
    assert page.locator("#cities .city").count() >= 8
    assert page.locator("#detail").inner_text().find("点击彩色铁路段") >= 0
    assert page.locator(".toplinks a").count() == 6
    page.screenshot(path=str(ART / "railway-desktop.png"), full_page=True)

    # Ensure real path selection opens data, not empty simulation text.
    page.locator(".segment-hit").first.dispatch_event("click")
    assert "→" in page.locator("#detail h3").inner_text()
    assert "晚点" in page.locator("#detail").inner_text()

    page.select_option("#metric", "cancel")
    assert number(page, "#visibleCount") > 100
    page.select_option("#minimum", "500")
    assert number(page, "#visibleCount") < re_count

    # Switch service; the real data should be loaded from independent sources.
    page.select_option("#minimum", "100")
    page.select_option("#service", "RB")
    page.wait_for_function("document.querySelector('#status').textContent.includes('RB') && document.querySelectorAll('.segment').length > 100", timeout=80000)
    assert number(page, "#visibleCount") > 100
    page.select_option("#service", "ICE")
    page.wait_for_function("document.querySelector('#status').textContent.includes('ICE') && document.querySelectorAll('.segment').length > 10", timeout=80000)
    assert number(page, "#visibleCount") > 10

    # Research dashboard remains intact and reachable.
    research=page.goto(BASE + "research.html", wait_until="domcontentloaded",timeout=60000)
    assert research.status == 200
    assert "js/app.js" in page.content()
    assert not errors, ("JS errors", errors)
    assert not notfound, ("Missing assets", notfound)
    mobile=browser.new_page(viewport={"width":390,"height":844},device_scale_factor=1)
    moberrors=[]
    mobile.on("pageerror",lambda e:moberrors.append(str(e)))
    mobile.goto(BASE, wait_until="domcontentloaded",timeout=60000)
    mobile.wait_for_function("document.querySelectorAll('.segment').length > 100",timeout=80000)
    assert mobile.locator("#service").is_visible()
    assert mobile.locator("#viewport").is_visible()
    mobile.screenshot(path=str(ART / "railway-mobile.png"),full_page=True)
    assert not moberrors, moberrors
    print("PASS railway v15 RE/RB/ICE, detail, metric, sample, archived view, mobile")
    print("RE segments initially:",re_count)
    browser.close()
