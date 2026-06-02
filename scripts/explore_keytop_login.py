"""探索科拓平台登录页与二维码。"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from playwright.sync_api import sync_playwright

LOGIN_URL = "https://park.keytop.cn/unityp/login"
records = []


def on_response(response):
    url = response.url
    if "keytop" not in url.lower():
        return
    req = response.request
    if req.resource_type not in ("xhr", "fetch", "image"):
        return
    rec = {"url": url, "method": req.method, "type": req.resource_type}
    if req.post_data:
        rec["post"] = req.post_data[:500]
    try:
        ct = response.headers.get("content-type") or ""
        if "json" in ct:
            rec["json"] = response.json()
    except Exception:
        pass
    records.append(rec)


with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    page = browser.new_page()
    page.on("response", on_response)
    page.goto(LOGIN_URL, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(3000)

    info = page.evaluate("""() => ({
        title: document.title,
        imgs: [...document.querySelectorAll('img')].map(el => ({
            src: el.src?.slice(0,200),
            alt: el.alt,
            className: el.className,
            w: el.width, h: el.height
        })),
        canvases: document.querySelectorAll('canvas').length,
        qrTexts: [...document.querySelectorAll('*')].filter(el =>
            /二维码|扫码|微信/.test(el.innerText||'')).slice(0,5).map(el => el.innerText.trim().slice(0,50)),
        bodySnippet: document.body.innerText.slice(0,500)
    })""")
    print("PAGE INFO:", json.dumps(info, ensure_ascii=False, indent=2))

    qr = page.locator("img").first
    if qr.count():
        qr.screenshot(path="data/keytop_qr_sample.png")
        print("saved data/keytop_qr_sample.png")

    print("\nAPI calls:")
    seen = set()
    for r in records:
        key = r["url"].split("?")[0]
        if key in seen:
            continue
        seen.add(key)
        if any(k in r["url"].lower() for k in ["login", "qr", "code", "scan", "auth", "token", "user"]):
            print(r["method"], r["url"][:120])
            if r.get("json"):
                print(" ", str(r["json"])[:200])

    browser.close()
