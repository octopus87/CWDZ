from __future__ import annotations

import logging
import time
from pathlib import Path

from playwright.sync_api import BrowserContext, Page, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)

# 停简单结算中心与下载中心路径（基于平台结构，必要时可通过配置覆盖）
SETTLEMENT_CENTER_URL = "https://open.tingjiandan.com/bmp-web/settlement-center"
DOWNLOAD_CENTER_URL = "https://open.tingjiandan.com/bmp-web/download-center"


def _select_all_projects(page: Page) -> None:
    """选择「所有项目」进行查询。"""
    # 尝试点击项目下拉并选择所有项目
    try:
        # 常见下拉触发器
        page.click('text=所有项目', timeout=3000)
    except PlaywrightTimeout:
        # 尝试更通用的项目选择器
        selectors = [
            'text=项目',
            '[placeholder*="项目"]',
            'text=全部项目',
        ]
        for sel in selectors:
            try:
                page.click(sel, timeout=2000)
                break
            except PlaywrightTimeout:
                continue
    # 选择所有
    try:
        page.click('text=所有项目', timeout=2000)
    except PlaywrightTimeout:
        logger.warning("未能定位「所有项目」选项，尝试继续导出")


def _set_date_range(page: Page, start_date: str, end_date: str) -> None:
    """设置结算日期范围。"""
    # 基于截图中的日期选择器，尝试常见输入框
    date_inputs = page.locator('input[type="text"], input[placeholder*="日期"]')
    count = date_inputs.count()
    if count >= 2:
        # 假设前两个是开始和结束日期
        date_inputs.nth(0).fill(start_date)
        date_inputs.nth(1).fill(end_date)
    else:
        # 回退：尝试特定 placeholder
        for placeholder in ["开始日期", "开始时间", "开始"]:
            try:
                page.fill(f'input[placeholder*="{placeholder}"]', start_date, timeout=2000)
                break
            except PlaywrightTimeout:
                continue
        for placeholder in ["结束日期", "结束时间", "结束"]:
            try:
                page.fill(f'input[placeholder*="{placeholder}"]', end_date, timeout=2000)
                break
            except PlaywrightTimeout:
                continue

    # 有些页面需要点击「查询」按钮应用筛选
    try:
        page.click('text=查询', timeout=3000)
        page.wait_for_load_state("networkidle")
    except PlaywrightTimeout:
        pass


def _trigger_export(page: Page) -> None:
    """点击导出按钮（支持「导出」或「导出详情」）。"""
    export_texts = ["导出", "导出Excel", "导出详情"]
    for text in export_texts:
        try:
            page.click(f'text={text}', timeout=5000)
            logger.info("已点击导出按钮: %s", text)
            return
        except PlaywrightTimeout:
            continue
    raise RuntimeError("未能找到导出按钮，请确认页面元素")


def _go_to_download_center(page: Page) -> None:
    """导航到下载中心页面。"""
    page.goto(DOWNLOAD_CENTER_URL, wait_until="networkidle")
    # 等待下载任务列表加载
    page.wait_for_timeout(1000)


def _wait_and_download_from_center(
    page: Page,
    context: BrowserContext,
    download_dir: Path,
    timeout_seconds: int = 300,
) -> Path:
    """在下载中心等待最新任务完成并下载文件。"""
    logger.info("进入下载中心，等待文件生成…")
    start_time = time.time()
    last_file: Path | None = None

    while time.time() - start_time < timeout_seconds:
        # 查找最新的下载任务行（通常第一行是最新）
        # 尝试点击「下载」或文件链接
        try:
            # 常见：列表中第一行的下载按钮
            download_btn = page.locator('text=下载').first
            if download_btn.is_visible():
                with page.expect_download(timeout=10000) as download_info:
                    download_btn.click()
                download = download_info.value
                filename = download.suggested_filename
                last_file = download_dir / filename
                download.save_as(last_file)
                logger.info("从下载中心下载完成: %s", last_file)
                return last_file
        except PlaywrightTimeout:
            pass

        # 刷新列表或等待
        try:
            page.click('text=刷新', timeout=2000)
        except PlaywrightTimeout:
            page.wait_for_timeout(5000)

        page.wait_for_timeout(3000)

    if last_file:
        return last_file
    raise TimeoutError(f"下载中心等待超时（{timeout_seconds}s），未找到可下载文件")


def download_reconciliation(
    page: Page,
    context: BrowserContext,
    download_dir: Path,
    *,
    start_date: str,
    end_date: str,
) -> Path:
    """从停简单平台下载对账数据。

    流程：
    1. 进入结算中心，选择所有项目，设置日期范围
    2. 点击导出（覆盖临停结算、欠费追缴结算等所有数据）
    3. 跳转下载中心，等待文件生成后下载到本地
    """
    download_dir.mkdir(parents=True, exist_ok=True)
    logger.info("准备下载对账数据: %s ~ %s", start_date, end_date)

    # 1. 进入结算中心
    page.goto(SETTLEMENT_CENTER_URL, wait_until="networkidle")
    page.wait_for_timeout(1500)

    # 2. 选择所有项目 + 设置日期范围
    _select_all_projects(page)
    _set_date_range(page, start_date, end_date)

    # 3. 触发导出
    _trigger_export(page)

    # 4. 跳转下载中心等待并下载
    _go_to_download_center(page)
    saved_path = _wait_and_download_from_center(page, context, download_dir)

    logger.info("对账文件已保存: %s", saved_path)
    return saved_path

