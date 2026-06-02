"""深入探测停简单结算中心页面结构与下载流程。"""

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


def login(page) -> None:
    open_login_page(page, LOGIN_URL)
    for attempt in range(5):
        captcha = recognize_captcha(read_captcha_image(page))
        fill_credentials(page, USERNAME, PASSWORD)
        try:
            submit_with_captcha(page, captcha)
            return
        except ValueError:
            page.locator("#captcha").click()
            page.wait_for_timeout(800)
    raise RuntimeError("login failed")


def dump(page, label: str) -> None:
    data = page.evaluate(
        """() => {
        const pick = sel => [...document.querySelectorAll(sel)].map(el => ({
            tag: el.tagName,
            text: (el.innerText||el.textContent||'').trim().slice(0,80),
            className: el.className,
            id: el.id,
            href: el.getAttribute && el.getAttribute('href'),
            onclick: el.getAttribute && el.getAttribute('onclick'),
        })).filter(x => x.text || x.id || x.className);
        return {
            url: location.href,
            title: document.title,
            iframes: [...document.querySelectorAll('iframe')].map(f => ({src: f.src, id: f.id, name: f.name})),
            nav: pick('.nav li, .menu li, .sidebar li, .left-menu li, [class*=menu] li, [class*=nav] li').slice(0,50),
            tabs: pick('[class*=tab], .el-tabs__item, .nav-tabs li').slice(0,30),
            buttons: pick('button, .btn, input[type=button], a.btn').slice(0,40),
            exportBtns: pick('a, button, span, div').filter(x => /导出|下载|Excel|查询|所有项目|车场/.test(x.text)).slice(0,40),
            scripts: [...document.scripts].map(s => s.src).filter(Boolean).slice(0,20),
        };
    }"""
    )
    print(f"\n=== {label} ===")
    print(json.dumps(data, ensure_ascii=False, indent=2))


def click_text(page, text: str) -> bool:
    locators = [
        page.locator(f"text={text}").first,
        page.locator(f"a:has-text('{text}')").first,
        page.locator(f"li:has-text('{text}')").first,
        page.locator(f"span:has-text('{text}')").first,
        page.locator(f"div:has-text('{text}')").first,
    ]
    for loc in locators:
        try:
            if loc.count() and loc.is_visible(timeout=1000):
                loc.click(timeout=5000)
                page.wait_for_timeout(2000)
                print(f"clicked '{text}' -> {page.url}")
                return True
        except Exception:
            continue
    print(f"NOT clicked: {text}")
    return False


def main() -> None:
    requests_log: list[str] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.set_default_timeout(60000)

        page.on("request", lambda r: requests_log.append(f"{r.method} {r.url}") if any(
            k in r.url for k in ["settle", "download", "export", "account", "reconcil", "bill", "settlement", "excel"]
        ) else None)

        login(page)
        page.wait_for_timeout(2000)
        dump(page, "after login")

        # 顶部导航
        for item in ["结算中心", "下载中心"]:
            click_text(page, item)
            dump(page, f"after top nav {item}")

        # 左侧菜单（结算中心子菜单）
        for item in ["项目年结对账", "项目月结对账", "停简单临停结算", "停简单结算明细"]:
            click_text(page, item)
            dump(page, f"after sidebar {item}")

        # 下载中心按钮
        try:
            page.locator("button.download-btn, .download-btn").first.click(timeout=5000)
            page.wait_for_timeout(2000)
            dump(page, "after download-btn")
        except Exception as exc:
            print("download-btn click failed:", exc)

        # 搜索页面脚本中的路由关键字
        routes = page.evaluate(
            """() => {
            const html = document.documentElement.innerHTML;
            const keys = ['项目年结对账','settlement','download','export','accountCheck','reconcile','settle'];
            return keys.map(k => ({key:k, count:(html.match(new RegExp(k,'g'))||[]).length}));
        }"""
        )
        print("\n=== route keyword counts ===")
        print(json.dumps(routes, ensure_ascii=False, indent=2))

        print("\n=== interesting network requests ===")
        for r in requests_log[:50]:
            print(r)

        browser.close()


if __name__ == "__main__":
    main()
