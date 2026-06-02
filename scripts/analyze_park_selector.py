"""分析 accountIndex 车场选择控件。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from playwright.sync_api import sync_playwright

from cwdz.crawler.captcha_ocr import recognize_captcha
from cwdz.crawler.login import LOGIN_URL, read_captcha_image, submit_with_captcha, fill_credentials, open_login_page

USERNAME = "yghtcw"
PASSWORD = "yghtcw123!"


def login(page):
    open_login_page(page, LOGIN_URL)
    for _ in range(5):
        captcha = recognize_captcha(read_captcha_image(page))
        fill_credentials(page, USERNAME, PASSWORD)
        try:
            submit_with_captcha(page, captcha)
            return
        except ValueError:
            page.locator("#captcha").click()
            page.wait_for_timeout(800)


with sync_playwright() as pw:
    page = pw.chromium.launch(headless=True).new_page()
    page.set_default_timeout(60000)
    login(page)
    page.goto("https://open.tingjiandan.com/bmp-web/main?sourceType=tingjiandan_park", wait_until="networkidle")
    page.locator("li:has-text('结算中心')").first.click()
    page.wait_for_timeout(4000)
    fr = page.query_selector("#iframeId").content_frame()
    data = fr.evaluate(
        """() => {
        const visible = el => {
            const r = el.getBoundingClientRect();
            return r.width > 0 && r.height > 0;
        };
        return [...document.querySelectorAll('*')]
            .filter(el => visible(el))
            .map(el => ({
                tag: el.tagName,
                text: (el.innerText||'').trim().slice(0,100),
                className: el.className,
                id: el.id,
            }))
            .filter(x => x.text && /车场|项目|全选|所有|选择|282|查询时间|导出/.test(x.text))
            .slice(0, 80);
    }"""
    )
    print(json.dumps(data, ensure_ascii=False, indent=2))

    # 尝试点击各种 opener
    for sel in [
        ".search-test",
        ".title-bar",
        ".ivu-select",
        ".ivu-select-selection",
        "div[class*='park']",
        "span:has-text('请选择停车场')",
    ]:
        loc = fr.locator(sel)
        print(sel, "count=", loc.count(), "visible=", loc.first.is_visible() if loc.count() else False)

    page.wait_for_timeout(1000)
    fr.locator(".ivu-select").first.click(force=True)
    page.wait_for_timeout(2000)
    after = fr.evaluate(
        """() => [...document.querySelectorAll('*')]
            .map(el => (el.innerText||'').trim())
            .filter(t => t && /全选|所有|已选择|282|项目/.test(t))
            .slice(0,30)"""
    )
    print("after click:", after)
