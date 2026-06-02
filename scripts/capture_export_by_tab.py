"""抓取各结算 Tab 导出时的 API 参数。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from playwright.sync_api import sync_playwright

from cwdz.crawler.captcha_ocr import recognize_captcha
from cwdz.crawler.login import LOGIN_URL, read_captcha_image, submit_with_captcha, fill_credentials, open_login_page

USER, PWD = "yghtcw", "yghtcw123!"
MAIN = "https://open.tingjiandan.com/bmp-web/main?sourceType=tingjiandan_park"

TAB_NAMES = [
    "停简单临停结算",
    "停简单长租结算",
    "停简单代收结算",
    "停简单扫码结算",
    "停简单补缴结算",
    "ETC结算",
    "停简单欠费追缴结算",
]

records: list[dict] = []


def login(page):
    open_login_page(page, LOGIN_URL)
    for _ in range(5):
        c = recognize_captcha(read_captcha_image(page))
        fill_credentials(page, USER, PWD)
        try:
            submit_with_captcha(page, c)
            return
        except ValueError:
            page.locator("#captcha").click()
            page.wait_for_timeout(800)


def on_response(response):
    url = response.url
    if "tingjiandan.com" not in url:
        return
    req = response.request
    if req.resource_type not in ("xhr", "fetch"):
        return
    if not any(k in url for k in ["getSettledInfoPage", "getOrderTask"]):
        return
    rec = {"method": req.method, "url": url.split("/")[-1], "status": response.status}
    if req.post_data:
        rec["post_data"] = req.post_data
    records.append(rec)


def setup_page(fr):
    fr.locator(".ivu-select-multiple").click(force=True)
    fr.wait_for_timeout(1000)
    fr.evaluate("document.querySelector('.select-full-btn')?.click()")
    fr.wait_for_timeout(500)
    fr.evaluate(
        """() => [...document.querySelectorAll('button,span,div')]
            .find(el => (el.innerText || '').trim() === '确认')?.click()"""
    )
    fr.wait_for_timeout(1500)
    # 日期控件 readonly，用「本月」快捷按钮
    try:
        fr.locator("text=本月").click(timeout=3000)
        fr.wait_for_timeout(500)
    except Exception:
        pass


results = []
with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page()
    page.on("response", on_response)
    page.set_default_timeout(60000)

    login(page)
    page.goto(MAIN, wait_until="networkidle")
    page.locator("li:has-text('结算中心')").first.click()
    page.wait_for_timeout(2000)
    page.locator(".wrapper li:has-text('停简单结算明细')").first.click()
    page.wait_for_timeout(4000)

    fr = page.query_selector("#iframeId").content_frame()
    setup_page(fr)

    for tab_name in TAB_NAMES:
        records.clear()
        print(f"\n=== {tab_name} ===", flush=True)
        fr.locator(f".tab li:has-text('{tab_name}')").click()
        fr.wait_for_timeout(1500)

        selected = fr.evaluate(
            "() => document.querySelector('.tab li.selected')?.innerText?.trim()"
        )
        print(f"  selected tab: {selected}", flush=True)

        fr.locator("button.select-btn:has-text('查询')").first.click()
        fr.wait_for_timeout(4000)

        fr.locator(".export-excel-row-btn").click()
        fr.wait_for_timeout(3000)

        query = export = None
        for r in records:
            if r["url"] == "getSettledInfoPage":
                query = json.loads(r["post_data"])
            if r["url"] == "getOrderTask":
                export = json.loads(r["post_data"])

        item = {"tab": tab_name, "query": query, "export": export}
        results.append(item)
        if export:
            print(
                "  export:",
                {k: export.get(k) for k in ["businessType", "downType", "fileName"]},
                flush=True,
            )
        if query:
            print(
                "  query:",
                {k: query.get(k) for k in ["businessType", "startDate", "endDate"]},
                flush=True,
            )

    browser.close()

out = Path("data/export_by_tab.json")
out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nSaved {out}", flush=True)
