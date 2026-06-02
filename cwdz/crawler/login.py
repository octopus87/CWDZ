from __future__ import annotations

import base64
import logging

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)

LOGIN_URL = "https://open.tingjiandan.com/bmp-web/login"
HOME_URL = "https://open.tingjiandan.com/bmp-web/"


def read_captcha_image(page: Page) -> bytes:
    """从登录页读取图形验证码图片。"""
    src = page.locator("#captcha").get_attribute("src")
    if not src:
        raise ValueError("未找到验证码图片")
    if src.startswith("data:"):
        _, encoded = src.split(",", 1)
        return base64.b64decode(encoded)
    raise ValueError("验证码图片格式不支持")


def refresh_captcha_image(page: Page) -> bytes:
    """点击验证码图片刷新并返回新图片。"""
    page.locator("#captcha").click()
    page.wait_for_timeout(800)
    return read_captcha_image(page)


def login_on_page(page: Page, username: str, password: str, captcha: str) -> None:
    """在已打开登录页的会话中提交登录。"""
    fill_credentials(page, username, password)
    submit_with_captcha(page, captcha)
    logger.info("登录完成")


def open_login_page(page: Page, login_url: str | None = None) -> None:
    """打开停简单登录页。"""
    url = login_url or LOGIN_URL
    logger.info("正在打开登录页: %s", url)
    page.goto(url, wait_until="networkidle")


def fill_credentials(page: Page, username: str, password: str) -> None:
    """填写用户名和密码（验证码需另行处理）。"""
    page.fill('input[name="login"]', username)
    page.fill('input[name="password"]', password)
    logger.info("已填写账号密码，等待验证码")


def submit_with_captcha(page: Page, captcha: str) -> None:
    """填写图形验证码并点击登录。"""
    page.fill('input[name="imgCode"]', captcha)
    page.click("#submit")
    _wait_login_success(page)


def login_with_manual_captcha(
    page: Page,
    username: str,
    password: str,
    login_url: str | None = None,
    *,
    manual_wait_ms: int = 120_000,
) -> None:
    """自动填账号密码，用户在可见浏览器中手动输入验证码并登录。"""
    open_login_page(page, login_url)
    fill_credentials(page, username, password)
    logger.info("请在浏览器窗口中输入图形验证码并点击「登录」")
    try:
        page.wait_for_url(
            lambda url: "/login" not in url.lower(),
            timeout=manual_wait_ms,
        )
    except PlaywrightTimeout as exc:
        raise TimeoutError("登录超时，请确认已在浏览器中完成验证码输入并登录") from exc
    page.wait_for_load_state("networkidle")
    logger.info("登录成功，当前页面: %s", page.url)


def login(
    page: Page,
    username: str,
    password: str,
    login_url: str | None = None,
    *,
    captcha: str | None = None,
    manual_captcha: bool = True,
) -> None:
    """登录停简单 BMP 平台。

    Args:
        captcha: 图形验证码；若提供则自动提交
        manual_captcha: 为 True 时等待用户在浏览器中手动完成验证码与登录
    """
    if captcha:
        open_login_page(page, login_url)
        login_on_page(page, username, password, captcha)
        return

    if manual_captcha:
        login_with_manual_captcha(page, username, password, login_url)
        return

    raise ValueError("停简单登录需要图形验证码，请使用 manual_captcha 或在界面填写验证码")


def _wait_login_success(page: Page, timeout_ms: int = 30_000) -> None:
    try:
        page.wait_for_url(
            lambda url: "/login" not in url.lower(),
            timeout=timeout_ms,
        )
    except PlaywrightTimeout as exc:
        raise ValueError("登录失败，请检查账号、密码或验证码是否正确") from exc
    page.wait_for_load_state("networkidle")


def is_logged_in(page: Page) -> bool:
    """检查当前是否已登录。"""
    return "/login" not in page.url.lower()
