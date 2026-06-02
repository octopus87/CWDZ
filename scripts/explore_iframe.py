"""探测 iframe 内结算中心页面元素。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from playwright.sync_api import Frame, Page, sync_playwright

from cwdz.crawler.captcha_ocr import recognize_captcha
from cwdz.crawler.login import LOGIN_URL, read_captcha_image, submit_with_captcha, fill_credentials, open_login_page

USERNAME = "yghtcw"
PASSWORD = "yghtcw123!"


def login(page: Page) -> None:
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


def get_iframe(page: Page) -> Frame:
    page.wait_for_selector("#iframeId", timeout=30000)
    handle = page.query_selector("#iframeId")
    assert handle is not None
    frame = handle.content_frame()
    assert frame is not None
    return frame


def dump_frame(frame: Frame, label: str) -> dict:
    data = frame.evaluate(
        """() => {
        const all = [...document.querySelectorAll('*')];
        const texts = [...new Set(all.map(el => (el.innerText||'').trim()).filter(t => t && t.length < 40))].slice(0,120);
        const clickable = [...document.querySelectorAll('button, a, span, div, li, input')]
            .map(el => ({
                tag: el.tagName,
                text: (el.innerText||el.value||el.placeholder||'').trim().slice(0,60),
                className: el.className,
                id: el.id,
                type: el.type,
            }))
            .filter(x => x.text && /项目|车场|导出|查询|下载|结算|欠费|临停|Excel|所有|选择|日期|年结|月结/.test(x.text))
            .slice(0, 60);
        return { url: location.href, title: document.title, texts: texts.slice(0,80), clickable };
    }"""
    )
    print(f"\n=== IFRAME {label} ===")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return data


def click_top(page: Page, text: str) -> None:
    page.locator(f"li:has-text('{text}')").first.click()
    page.wait_for_timeout(2500)


def click_sidebar(page: Page, text: str) -> None:
    page.locator(f".wrapper li:has-text('{text}'), .left li:has-text('{text}'), li.select ~ li:has-text('{text}')").first.click()
    page.wait_for_timeout(2500)


def main() -> None:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(accept_downloads=True)
        page.set_default_timeout(60000)

        login(page)
        page.wait_for_timeout(2000)

        click_top(page, "结算中心")
        frame = get_iframe(page)
        dump_frame(frame, "结算中心-默认")

        # 尝试侧边栏各项
        for item in ["项目年结对账", "综合信息展示", "停简单结算明细", "收费员收费减免汇总"]:
            try:
                click_sidebar(page, item)
                frame = get_iframe(page)
                dump_frame(frame, item)
            except Exception as exc:
                print(f"sidebar {item} failed: {exc}")

        # 在 iframe 内搜索项目年结对账
        frame = get_iframe(page)
        search = frame.evaluate(
            """() => {
            const html = document.documentElement.innerHTML;
            const keys = ['项目年结对账','accountIndex','yearAccount','export','导出Excel','车场选择','所有项目','临停结算','欠费追缴'];
            return keys.map(k => ({key:k, count:(html.match(new RegExp(k,'g'))||[]).length}));
        }"""
        )
        print("\n=== iframe keyword search ===")
        print(json.dumps(search, ensure_ascii=False, indent=2))

        # 下载中心 iframe
        page.locator("button.download-btn").click()
        page.wait_for_timeout(3000)
        frame = get_iframe(page)
        dump_frame(frame, "下载中心")

        browser.close()


if __name__ == "__main__":
    main()
