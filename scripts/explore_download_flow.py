"""探测停简单结算中心下载流程，输出页面结构与关键元素。"""

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


def dump_page_info(page, label: str) -> dict:
    info = page.evaluate(
        """() => {
        const texts = [...document.querySelectorAll('a, button, span, li, div, input')]
            .map(el => (el.innerText || el.value || el.placeholder || '').trim())
            .filter(t => t && t.length < 30);
        const links = [...document.querySelectorAll('a[href]')]
            .map(a => ({text: (a.innerText||'').trim(), href: a.getAttribute('href')}))
            .filter(x => x.text || x.href);
        const buttons = [...document.querySelectorAll('button, input[type=button], input[type=submit], .submit')]
            .map(b => ({tag: b.tagName, text: (b.innerText||b.value||'').trim(), id: b.id, className: b.className}));
        const inputs = [...document.querySelectorAll('input, select, textarea')]
            .map(i => ({tag: i.tagName, type: i.type, name: i.name, id: i.id, placeholder: i.placeholder, className: i.className}));
        return {
            url: location.href,
            title: document.title,
            texts: [...new Set(texts)].slice(0, 80),
            links: links.slice(0, 40),
            buttons: buttons.slice(0, 30),
            inputs: inputs.slice(0, 30),
        };
    }"""
    )
    print(f"\n=== {label} ===")
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return info


def login(page) -> None:
    open_login_page(page, LOGIN_URL)
    for attempt in range(5):
        image = read_captcha_image(page)
        captcha = recognize_captcha(image)
        print(f"attempt {attempt + 1}, captcha={captcha}")
        fill_credentials(page, USERNAME, PASSWORD)
        try:
            submit_with_captcha(page, captcha)
            print("login ok:", page.url)
            return
        except ValueError as exc:
            print("login failed:", exc)
            page.locator("#captcha").click()
            page.wait_for_timeout(800)
    raise RuntimeError("login failed after retries")


def find_and_click(page, keywords: list[str]) -> bool:
    for kw in keywords:
        loc = page.get_by_text(kw, exact=False)
        if loc.count() > 0:
            try:
                loc.first.click(timeout=3000)
                page.wait_for_load_state("networkidle")
                print(f"clicked: {kw} -> {page.url}")
                return True
            except Exception as exc:
                print(f"click failed {kw}: {exc}")
    return False


def main() -> None:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.set_default_timeout(60000)

        login(page)
        home = dump_page_info(page, "HOME after login")

        # 尝试进入结算中心
        clicked = find_and_click(page, ["结算中心", "项目年结对账", "对账"])
        if clicked:
            dump_page_info(page, "SETTLEMENT PAGE")

        # 尝试常见 URL
        candidates = [
            "https://open.tingjiandan.com/bmp-web/settlement-center",
            "https://open.tingjiandan.com/bmp-web/#/settlement-center",
            "https://open.tingjiandan.com/bmp-web/settlement",
            "https://open.tingjiandan.com/bmp-web/download-center",
            "https://open.tingjiandan.com/bmp-web/#/download-center",
        ]
        for url in candidates:
            try:
                resp = page.goto(url, wait_until="networkidle", timeout=15000)
                status = resp.status if resp else "?"
                print(f"\nURL probe: {url} status={status} final={page.url}")
                if "/login" not in page.url.lower():
                    dump_page_info(page, f"URL {url}")
            except Exception as exc:
                print(f"URL probe failed {url}: {exc}")

        # 从首页链接里找结算/下载相关
        settlement_links = [
            l for l in home.get("links", [])
            if any(k in (l.get("text", "") + l.get("href", "")) for k in ["结算", "对账", "下载"])
        ]
        print("\n=== settlement related links ===")
        print(json.dumps(settlement_links, ensure_ascii=False, indent=2))

        browser.close()


if __name__ == "__main__":
    main()
