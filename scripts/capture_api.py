"""抓取停简单导出流程中的 API 请求。"""

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

api_calls: list[dict] = []


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
    if not any(k in url for k in ["tingjiandan", "bmweb", "bmp-web"]):
        return
    if any(skip in url for skip in [".js", ".css", ".png", ".jpg", ".woff", "amap.com"]):
        return
    req = response.request
    if req.resource_type not in ("xhr", "fetch", "document"):
        return
    entry = {
        "method": req.method,
        "url": url,
        "status": response.status,
        "type": req.resource_type,
    }
    if req.method == "POST":
        try:
            entry["post_data"] = req.post_data[:500] if req.post_data else None
        except Exception:
            pass
    api_calls.append(entry)
    print(f"  API → {req.method} {response.status} {url[:120]}", flush=True)


with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page()
    page.on("response", on_response)
    page.set_default_timeout(60000)

    print("=== 登录 ===", flush=True)
    login(page)

    print("\n=== 进入结算明细 ===", flush=True)
    page.goto(MAIN, wait_until="networkidle")
    page.locator("li:has-text('结算中心')").first.click()
    page.wait_for_timeout(2000)
    page.locator(".wrapper li:has-text('停简单结算明细')").first.click()
    page.wait_for_timeout(5000)

    fr = page.query_selector("#iframeId").content_frame()
    print(f"\n=== iframe: {fr.url} ===", flush=True)

    print("\n=== 全选车场 ===", flush=True)
    fr.locator(".ivu-select-multiple").click(force=True)
    fr.wait_for_timeout(1000)
    fr.evaluate("document.querySelector('.select-full-btn')?.click()")
    fr.wait_for_timeout(500)
    fr.evaluate("""() => {
        [...document.querySelectorAll('button,span,div')]
            .find(el => (el.innerText||'').trim()==='确认')?.click();
    }""")
    fr.wait_for_timeout(2000)

    print("\n=== 点击查询 ===", flush=True)
    fr.locator("button.select-btn:has-text('查询')").click()
    fr.wait_for_timeout(5000)

    print("\n=== 点击导出excel ===", flush=True)
    fr.locator(".export-excel-row-btn").click()
    fr.wait_for_timeout(5000)

    print("\n=== 打开下载中心 ===", flush=True)
    page.locator("button.download-btn").click()
    page.wait_for_timeout(5000)

    browser.close()

print("\n" + "=" * 60, flush=True)
print(f"共捕获 {len(api_calls)} 个 API 请求", flush=True)
print("=" * 60, flush=True)

# 按 URL 去重输出
seen = set()
for c in api_calls:
    key = f"{c['method']} {c['url']}"
    if key in seen:
        continue
    seen.add(key)
    print(f"\n{c['method']} {c['status']} {c['url']}")
    if c.get("post_data"):
        print(f"  POST: {c['post_data'][:300]}")

out = Path("data/api_capture.json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(api_calls, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n完整记录已保存: {out}", flush=True)
