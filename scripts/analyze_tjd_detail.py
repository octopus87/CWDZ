"""分析 tjdAccountDetail 页面控件。"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from playwright.sync_api import sync_playwright
from cwdz.crawler.captcha_ocr import recognize_captcha
from cwdz.crawler.login import LOGIN_URL, read_captcha_image, submit_with_captcha, fill_credentials, open_login_page

USERNAME, PASSWORD = "yghtcw", "yghtcw123!"

def login(page):
    open_login_page(page, LOGIN_URL)
    for _ in range(5):
        c = recognize_captcha(read_captcha_image(page))
        fill_credentials(page, USERNAME, PASSWORD)
        try:
            submit_with_captcha(page, c); return
        except ValueError:
            page.locator("#captcha").click(); page.wait_for_timeout(800)

with sync_playwright() as pw:
    page = pw.chromium.launch(headless=True).new_page()
    page.set_default_timeout(60000)
    login(page)
    page.goto("https://open.tingjiandan.com/bmp-web/main?sourceType=tingjiandan_park", wait_until="networkidle")
    page.locator("li:has-text('结算中心')").first.click()
    page.wait_for_timeout(2000)
    page.locator(".wrapper li:has-text('停简单结算明细')").first.click()
    page.wait_for_timeout(4000)
    fr = page.query_selector("#iframeId").content_frame()

    info = fr.evaluate("""() => ({
        selects: [...document.querySelectorAll('.ivu-select')].map((el,i)=>({i, className: el.className, text: el.innerText.slice(0,80)})),
        fullBtn: [...document.querySelectorAll('.select-full-btn, .select-all, [class*=full]')].map(el=>({text:el.innerText, className:el.className, visible: el.offsetParent!==null})),
        export: [...document.querySelectorAll('button, span, div')].filter(el=>/导出/i.test(el.innerText||'')).map(el=>({tag:el.tagName,text:el.innerText.trim(),className:el.className})),
        tabs: [...document.querySelectorAll('[class*=tab], .ivu-tabs-tab')].map(el=>({text:el.innerText.trim(),className:el.className})),
        dateInputs: [...document.querySelectorAll('input.ivu-input')].map((el,i)=>({i, value:el.value, placeholder:el.placeholder})),
    })""")
    import json; print(json.dumps(info, ensure_ascii=False, indent=2))

    # open first select
    fr.locator(".ivu-select").first.click(force=True)
    fr.wait_for_timeout(1500)
    fr.locator(".select-full-btn").click(force=True)
    fr.wait_for_timeout(1000)
    after = fr.evaluate("""() => ({
        selectedText: document.querySelector('.ivu-select-selected-value, .ivu-select-selection')?.innerText?.slice(0,200),
        checked: document.querySelectorAll('.ivu-checkbox-checked').length,
    })""")
    print("after force select all:", after)
