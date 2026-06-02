"""带详细步骤输出的停简单下载流程测试。"""

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


def log(step: int, msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] 步骤{step}: {msg}", flush=True)


def login(page: Page) -> None:
    log(1, "打开登录页…")
    open_login_page(page, LOGIN_URL)
    for attempt in range(1, 6):
        captcha = recognize_captcha(read_captcha_image(page))
        log(1, f"第{attempt}次识别验证码: {captcha}")
        fill_credentials(page, USERNAME, PASSWORD)
        try:
            submit_with_captcha(page, captcha)
            log(1, f"登录成功 → {page.url}")
            return
        except ValueError as exc:
            log(1, f"登录失败: {exc}，刷新验证码重试…")
            page.locator("#captcha").click()
            page.wait_for_timeout(800)
    raise RuntimeError("登录失败")


def get_iframe(page: Page) -> Frame:
    handle = page.query_selector("#iframeId")
    if not handle:
        raise RuntimeError("未找到 iframe #iframeId")
    frame = handle.content_frame()
    if not frame:
        raise RuntimeError("iframe 未加载")
    return frame


def goto_settlement_detail(page: Page) -> Frame:
    log(2, f"进入主页 {MAIN_URL}")
    page.goto(MAIN_URL, wait_until="networkidle")

    log(3, "点击顶部导航「结算中心」")
    page.locator("li:has-text('结算中心')").first.click()
    page.wait_for_timeout(2500)

    log(4, "点击左侧菜单「停简单结算明细」（含临停~欠费追缴结算 Tab）")
    page.locator(".wrapper li:has-text('停简单结算明细')").first.click()
    page.wait_for_timeout(4000)

    frame = get_iframe(page)
    log(4, f"iframe 已加载 → {frame.url}")
    return frame


def select_all_parks(frame: Frame) -> None:
    log(5, "打开「车场选择」多选下拉框")
    frame.locator(".ivu-select-multiple").click(force=True)
    frame.wait_for_timeout(1200)

    log(5, "点击「全选/不选」")
    clicked = frame.evaluate(
        """() => {
        const btn = document.querySelector('.select-full-btn');
        if (!btn) return false;
        btn.click();
        return true;
    }"""
    )
    if not clicked:
        raise RuntimeError("未找到「全选/不选」按钮")
    frame.wait_for_timeout(800)

    log(5, "点击「确认」")
    frame.evaluate(
        """() => {
        const btn = [...document.querySelectorAll('button, span, div')]
            .find(el => (el.innerText || '').trim() === '确认');
        btn?.click();
    }"""
    )
    frame.wait_for_timeout(1000)

    selected = frame.evaluate(
        "() => (document.querySelector('.ivu-select-multiple')?.innerText || '').slice(0, 120)"
    )
    log(5, f"已选车场: {selected or '(空)'}")


def set_date_range(frame: Frame, start_date: str, end_date: str) -> None:
    log(6, f"设置查询日期: {start_date} ~ {end_date}")
    inputs = frame.locator('input.ivu-input[placeholder="选择日期"]')
    count = inputs.count()
    log(6, f"找到 {count} 个日期输入框")
    if count < 2:
        raise RuntimeError("日期输入框不足")
    inputs.nth(0).fill(start_date)
    inputs.nth(1).fill(end_date)
    frame.wait_for_timeout(500)


def click_query(frame: Frame) -> None:
    log(7, "点击「查询」")
    frame.locator("button.select-btn:has-text('查询')").first.click()
    frame.wait_for_timeout(5000)
    has_data = "暂无数据" not in frame.inner_text("body")
    log(7, f"查询完成，页面{'有' if has_data else '无'}数据")


def click_export(frame: Frame) -> None:
    tabs = frame.evaluate(
        """() => [...document.querySelectorAll('.tab, .ivu-tabs-tab')]
            .map(el => el.innerText.trim()).filter(Boolean).slice(0, 10)"""
    )
    log(8, f"当前结算 Tab: {tabs}")

    log(8, "点击「导出excel」（包含临停~欠费追缴全部类型）")
    frame.locator(".export-excel-row-btn").click()
    frame.wait_for_timeout(3000)
    log(8, "导出任务已提交")


def open_download_center(page: Page) -> Frame:
    log(9, "点击右上角「下载中心」按钮")
    page.locator("button.download-btn").click()
    page.wait_for_timeout(3000)
    frame = get_iframe(page)
    log(9, f"下载中心 iframe → {frame.url}")
    return frame


def wait_and_download(page: Page, frame: Frame, out_dir: Path, timeout: int = 180) -> Path:
    log(10, "等待文件生成并下载…")
    out_dir.mkdir(parents=True, exist_ok=True)
    start = time.time()

    for i in range(timeout // 5):
        body = frame.inner_text("body")
        filenames = frame.evaluate(
            """() => [...document.querySelectorAll('.filename')]
                .map(el => el.innerText.trim()).slice(0, 3)"""
        )
        statuses = frame.evaluate(
            """() => [...document.querySelectorAll('tr, .ivu-table-row')]
                .slice(0, 3).map(el => el.innerText.replace(/\\s+/g,' ').trim()).filter(Boolean)"""
        )

        elapsed = int(time.time() - start)
        log(10, f"轮询 #{i + 1}（{elapsed}s）最新文件: {filenames[:1]}")
        if statuses:
            log(10, f"  状态摘要: {statuses[0][:80]}")

        if "生成中" in body:
            log(10, "  → 文件生成中，继续等待…")
        elif frame.locator("button.info-btn:has-text('下载')").count():
            fname = filenames[0] if filenames else "unknown.xlsx"
            log(10, f"  → 文件已就绪，开始下载: {fname}")
            with page.expect_download(timeout=30000) as dl_info:
                frame.locator("button.info-btn:has-text('下载')").first.click()
            download = dl_info.value
            save_path = out_dir / download.suggested_filename
            download.save_as(save_path)
            log(10, f"下载完成 → {save_path}")
            return save_path

        time.sleep(5)
        page.locator("button.download-btn").click()
        page.wait_for_timeout(2000)
        frame = get_iframe(page)

    raise TimeoutError(f"等待超时（{timeout}s）")


def main() -> None:
    end = datetime.now()
    start = end - timedelta(days=7)
    start_s = start.strftime("%Y-%m-%d")
    end_s = end.strftime("%Y-%m-%d")

    print("=" * 60, flush=True)
    print("停简单对账下载流程测试（详细日志）", flush=True)
    print("=" * 60, flush=True)

    with sync_playwright() as pw:
        log(0, "启动浏览器（headless）")
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(accept_downloads=True)
        page.set_default_timeout(60000)

        try:
            login(page)
            frame = goto_settlement_detail(page)
            select_all_parks(frame)
            set_date_range(frame, start_s, end_s)
            click_query(frame)
            click_export(frame)
            frame = open_download_center(page)
            path = wait_and_download(page, frame, Path("data/downloads/test"))

            print("=" * 60, flush=True)
            print(f"✓ 全流程成功，文件: {path}", flush=True)
            print("=" * 60, flush=True)
        except Exception as exc:
            print("=" * 60, flush=True)
            print(f"✗ 失败: {exc}", flush=True)
            print("=" * 60, flush=True)
            raise
        finally:
            browser.close()
            log(0, "浏览器已关闭")


if __name__ == "__main__":
    main()
