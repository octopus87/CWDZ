"""测试结算中心完整导出下载流程。"""

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


def iframe(page: Page) -> Frame:
    handle = page.query_selector("#iframeId")
    assert handle
    frame = handle.content_frame()
    assert frame
    return frame


def goto_settlement(page: Page) -> Frame:
    page.goto(MAIN_URL, wait_until="networkidle")
    page.locator("li:has-text('结算中心')").first.click()
    page.wait_for_timeout(3000)
    fr = iframe(page)
    fr.wait_for_load_state("networkidle")
    print("settlement iframe:", fr.url)
    return fr


def select_all_parks(fr: Frame) -> None:
    # 打开车场下拉
    fr.locator(".ivu-select-input, .ivu-select-placeholder").first.click()
    fr.wait_for_timeout(1000)
    # 全选
    select_all = fr.locator("text=全选/不选").first
    if select_all.count():
        select_all.click()
        print("clicked 全选/不选")
    else:
        # accountIndex 可能没有全选，尝试勾选第一个 checkbox 组
        checkboxes = fr.locator(".ivu-checkbox-input")
        print("checkbox count:", checkboxes.count())
        for i in range(min(checkboxes.count(), 5)):
            checkboxes.nth(i).click(force=True)
    fr.wait_for_timeout(500)
    # 确认选择（常见按钮）
    for btn in ["确定", "确认", "完成"]:
        loc = fr.locator(f"button:has-text('{btn}')")
        if loc.count():
            loc.first.click()
            print("confirmed with", btn)
            break
    fr.wait_for_timeout(1000)


def set_dates(fr: Frame, start: str, end: str) -> None:
    inputs = fr.locator("input.ivu-input")
    print("date input count:", inputs.count())
    for i, val in enumerate([start, end]):
        if inputs.count() > i:
            inputs.nth(i).click()
            inputs.nth(i).fill(val)
            inputs.nth(i).press("Enter")
    fr.wait_for_timeout(500)


def click_query(fr: Frame) -> None:
    fr.locator("button.select-btn:has-text('查询')").first.click()
    fr.wait_for_timeout(3000)
    print("clicked 查询")


def click_export(fr: Frame) -> None:
    for sel in [
        "text=导出excel",
        "text=导出Excel",
        ".export-excel-row button",
        "button:has-text('导出')",
    ]:
        loc = fr.locator(sel)
        if loc.count():
            loc.first.click()
            print("clicked export via", sel)
            fr.wait_for_timeout(2000)
            return
    raise RuntimeError("export button not found")


def open_download_center(page: Page) -> Frame:
    page.locator("button.download-btn").click()
    page.wait_for_timeout(3000)
    fr = iframe(page)
    print("download center:", fr.url)
    return fr


def wait_and_download(fr: Frame, page: Page, out_dir: Path, timeout: int = 120) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    start = time.time()
    while time.time() - start < timeout:
        rows = fr.locator("button.info-btn:has-text('下载')")
        count = rows.count()
        if count:
            # 第一行
            status = fr.locator("text=已生成").first
            generating = fr.locator("text=生成中")
            if generating.count() and not status.count():
                print("still generating...")
            else:
                with page.expect_download(timeout=30000) as dl_info:
                    rows.first.click()
                download = dl_info.value
                path = out_dir / download.suggested_filename
                download.save_as(path)
                print("downloaded:", path)
                return path
        fr.wait_for_timeout(5000)
        page.locator("button.download-btn").click()
        page.wait_for_timeout(2000)
    raise TimeoutError("download timeout")


def main() -> None:
    end = datetime.now()
    start = end - timedelta(days=30)
    start_s = start.strftime("%Y-%m-%d")
    end_s = end.strftime("%Y-%m-%d")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.set_default_timeout(60000)

        login(page)
        fr = goto_settlement(page)
        select_all_parks(fr)
        set_dates(fr, start_s, end_s)
        click_query(fr)
        click_export(fr)
        dfr = open_download_center(page)
        path = wait_and_download(dfr, page, Path("data/downloads/test"))
        print("SUCCESS:", path)
        browser.close()


if __name__ == "__main__":
    main()
