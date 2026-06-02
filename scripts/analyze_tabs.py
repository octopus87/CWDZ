"""分析结算 Tab 结构与点击方式。"""

import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright
from cwdz.crawler.captcha_ocr import recognize_captcha
from cwdz.crawler.login import LOGIN_URL, read_captcha_image, submit_with_captcha, fill_credentials, open_login_page

USER, PWD = "yghtcw", "yghtcw123!"
MAIN = "https://open.tingjiandan.com/bmp-web/main?sourceType=tingjiandan_park"

def login(page):
    open_login_page(page, LOGIN_URL)
    for _ in range(5):
        c = recognize_captcha(read_captcha_image(page))
        fill_credentials(page, USER, PWD)
        try:
            submit_with_captcha(page, c); return
        except ValueError:
            page.locator("#captcha").click(); page.wait_for_timeout(800)

with sync_playwright() as pw:
    page = pw.chromium.launch(headless=True).new_page()
    page.set_default_timeout(60000)
    login(page)
    page.goto(MAIN, wait_until="networkidle")
    page.locator("li:has-text('结算中心')").first.click(); page.wait_for_timeout(2000)
    page.locator(".wrapper li:has-text('停简单结算明细')").first.click(); page.wait_for_timeout(4000)
    fr = page.query_selector("#iframeId").content_frame()
    info = fr.evaluate("""() => {
        const tabRoot = document.querySelector('.tab');
        const all = [...document.querySelectorAll('*')].filter(el => {
            const t = (el.innerText||'').trim();
            return t === '停简单临停结算' || t === 'ETC结算';
        }).slice(0,5).map(el => ({
            tag: el.tagName, text: el.innerText.trim(), className: el.className,
            parent: el.parentElement?.className, onclick: !!el.onclick
        }));
        const tabChildren = tabRoot ? [...tabRoot.children].map(el => ({
            tag: el.tagName, text: (el.innerText||'').trim(), className: el.className
        })) : [];
        return { tabChildren, all, html: tabRoot?.outerHTML?.slice(0,800) };
    }""")
    print(json.dumps(info, ensure_ascii=False, indent=2))
