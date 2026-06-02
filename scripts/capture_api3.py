"""抓取导出/下载 API 完整参数。"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from playwright.sync_api import sync_playwright

from cwdz.crawler.captcha_ocr import recognize_captcha
from cwdz.crawler.login import LOGIN_URL, read_captcha_image, submit_with_captcha, fill_credentials, open_login_page

USER, PWD = "yghtcw", "yghtcw123!"
MAIN = "https://open.tingjiandan.com/bmp-web/main?sourceType=tingjiandan_park"

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
    if any(x in url for x in [".js", ".css", ".png", ".jpg", ".woff", "amap", ".svg"]):
        return
    req = response.request
    if req.resource_type not in ("xhr", "fetch"):
        return
    rec = {"method": req.method, "url": url, "status": response.status}
    if req.post_data:
        rec["post_data"] = req.post_data
    try:
        ct = response.headers.get("content-type") or ""
        if "json" in ct:
            body = response.json()
            rec["response"] = body if isinstance(body, dict) else str(body)[:500]
    except Exception:
        pass
    records.append(rec)


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
    fr.locator(".ivu-select-multiple").click(force=True)
    fr.wait_for_timeout(1000)
    fr.evaluate("document.querySelector('.select-full-btn')?.click()")
    fr.wait_for_timeout(500)
    fr.evaluate("""() => [...document.querySelectorAll('button,span,div')]
        .find(el=>(el.innerText||'').trim()==='确认')?.click()""")
    fr.wait_for_timeout(2000)

    end = datetime.now()
    start = end - timedelta(days=7)
    # 日期控件 readonly，用 JS 设置或点击快捷按钮
    fr.locator("text=本周").click()
    fr.wait_for_timeout(500)

    print("=== 查询 ===", flush=True)
    fr.locator("button.select-btn").first.click()
    fr.wait_for_timeout(5000)

    print("=== 导出 ===", flush=True)
    fr.locator(".export-excel-row-btn").click()
    fr.wait_for_timeout(8000)

    print("=== 下载中心 ===", flush=True)
    page.locator("button.download-btn").click()
    page.wait_for_timeout(5000)

    browser.close()

out = Path("data/api_capture.json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

print("\n关键 API:", flush=True)
keywords = ["settle", "export", "download", "login", "excel", "file", "park", "account"]
seen = set()
for r in records:
    url_lower = r["url"].lower()
    if not any(k in url_lower for k in keywords):
        continue
    key = r["method"] + " " + r["url"]
    if key in seen:
        continue
    seen.add(key)
    print(f"\n{r['method']} {r['status']} {r['url']}")
    if r.get("post_data"):
        print(f"  POST: {r['post_data'][:600]}")
    if r.get("response") and isinstance(r["response"], dict):
        print(f"  RESP keys: {list(r['response'].keys())[:10]}")

print(f"\n保存: {out} ({len(records)} 条)", flush=True)
