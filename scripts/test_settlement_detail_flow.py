"""测试停简单结算明细页导出下载。"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from playwright.sync_api import Frame, Page, sync_playwright

from cwdz.crawler.captcha_ocr import recognize_captcha
from cwdz.crawler.login import LOGIN_URL, read_captcha_image, submit_with_captcha, fill_credentials, open_login_page

USERNAME = "yghtcw"
PASSWORD = "yghtcw123!"
MAIN_URL = "https://open.tingjiandan.com/bmp-web/main?sourceType=tingjiandan_park"


def login(page: Page) -> None:
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


def iframe(page: Page) -> Frame:
    h = page.query_selector("#iframeId")
    assert h
    f = h.content_frame()
    assert f
    return f


def goto_settlement_detail(page: Page) -> Frame:
    page.goto(MAIN_URL, wait_until="networkidle")
    page.locator("li:has-text('结算中心')").first.click()
    page.wait_for_timeout(2000)
    page.locator(".wrapper li:has-text('停简单结算明细')").first.click()
    page.wait_for_timeout(4000)
    fr = iframe(page)
    print("iframe url:", fr.url)
    return fr


def select_all_parks(fr: Frame) -> None:
    fr.locator(".ivu-select").first.click(force=True)
    fr.wait_for_timeout(1000)
    sel = fr.locator("text=全选/不选").first
    if sel.count():
        sel.click()
        print("selected 全选/不选")
    fr.wait_for_timeout(500)


def set_dates(fr: Frame, start: str, end: str) -> None:
    inputs = fr.locator("input.ivu-input")
    n = inputs.count()
    print("date inputs:", n)
    if n >= 2:
        inputs.nth(0).click()
        inputs.nth(0).fill(start)
        inputs.nth(1).click()
        inputs.nth(1).fill(end)


def query(fr: Frame) -> None:
    fr.locator("button.select-btn:has-text('查询')").first.click()
    fr.wait_for_timeout(4000)


def export_excel(fr: Frame) -> None:
    for sel in ["text=导出excel", "text=导出Excel", ".export-excel-row button", "button:has-text('导出')"]:
        loc = fr.locator(sel)
        if loc.count():
            loc.first.click()
            print("export via", sel)
            fr.wait_for_timeout(3000)
            return
    raise RuntimeError("no export")


def download_from_center(page: Page, out: Path) -> Path:
    page.locator("button.download-btn").click()
    page.wait_for_timeout(3000)
    fr = iframe(page)
    for _ in range(24):
        btn = fr.locator("button.info-btn:has-text('下载')").first
        row = fr.locator(".filename").first
        if btn.count() and row.count():
            fname = row.inner_text()
            print("latest file:", fname)
            if "生成中" in fr.inner_text("body"):
                print("generating...")
            else:
                with page.expect_download(timeout=30000) as dl:
                    btn.click()
                path = out / dl.value.suggested_filename
                dl.value.save_as(path)
                return path
        page.wait_for_timeout(5000)
        page.locator("button.download-btn").click()
        page.wait_for_timeout(2000)
    raise TimeoutError("download timeout")


def main():
    end = datetime.now()
    start = end - timedelta(days=7)
    out = Path("data/downloads/test")
    out.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        page = pw.chromium.launch(headless=True).new_page(accept_downloads=True)
        page.set_default_timeout(60000)
        login(page)
        fr = goto_settlement_detail(page)
        select_all_parks(fr)
        set_dates(fr, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        query(fr)
        export_excel(fr)
        path = download_from_center(page, out)
        print("SUCCESS", path)


if __name__ == "__main__":
    main()
