from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright

from cwdz.config import load_settings, resolve_path
from cwdz.crawler.browser_executor import run_browser_task
from cwdz.crawler.captcha_ocr import CaptchaResult, recognize_captcha
from cwdz.crawler.login import (
    LOGIN_URL,
    fill_credentials,
    open_login_page,
    read_captcha_image,
    refresh_captcha_image,
    submit_with_captcha,
)

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


class CaptchaSession:
    """保持浏览器会话，确保验证码与登录提交在同一会话中。"""

    _active: CaptchaSession | None = None

    def __init__(self) -> None:
        self._settings = load_settings()
        self._ts = self._settings.get("tingsimple", {})
        self._browser_cfg = self._settings.get("browser", {})
        self._captcha_cfg = self._settings.get("captcha", {})
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    @classmethod
    def current(cls) -> CaptchaSession:
        if cls._active is None:
            cls._active = CaptchaSession()
        return cls._active

    @classmethod
    def reset(cls) -> None:
        if cls._active is not None:
            cls._active.close()
            cls._active = None

    @property
    def login_url(self) -> str:
        return self._ts.get("login_url") or self._ts.get("base_url") or LOGIN_URL

    @property
    def auto_ocr(self) -> bool:
        return bool(self._captcha_cfg.get("auto_ocr", True))

    @property
    def max_retries(self) -> int:
        return int(self._captcha_cfg.get("max_retries", 3))

    def _ensure_browser(self) -> Page:
        if self._page is not None:
            return self._page

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self._browser_cfg.get("headless", True)
        )
        self._context = self._browser.new_context(accept_downloads=True)
        self._page = self._context.new_page()
        self._page.set_default_timeout(self._browser_cfg.get("timeout_ms", 60000))
        return self._page

    def page(self) -> Page:
        return self._ensure_browser()

    @property
    def context(self) -> BrowserContext:
        if self._context is None:
            self._ensure_browser()
        assert self._context is not None
        return self._context

    def prepare_captcha(self) -> bytes:
        page = self._ensure_browser()
        open_login_page(page, self.login_url)
        return read_captcha_image(page)

    def refresh_captcha(self) -> bytes:
        page = self._ensure_browser()
        if "/login" not in page.url.lower():
            open_login_page(page, self.login_url)
        return refresh_captcha_image(page)

    def fetch_captcha_result(self, *, refresh: bool = False) -> CaptchaResult:
        image = self.refresh_captcha() if refresh else self.prepare_captcha()
        text = recognize_captcha(image) if self.auto_ocr else ""
        return CaptchaResult(image=image, text=text)

    def login(self, username: str, password: str, captcha: str) -> None:
        page = self._ensure_browser()
        if "/login" not in page.url.lower():
            raise RuntimeError("当前不在登录页，请先获取验证码")
        fill_credentials(page, username, password)
        submit_with_captcha(page, captcha)
        logger.info("登录成功: %s", page.url)

    def login_with_auto_retry(self, username: str, password: str, captcha: str) -> str:
        """登录失败时自动刷新验证码并重试 OCR。"""
        last_error: Exception | None = None
        current_captcha = captcha

        for attempt in range(1, self.max_retries + 1):
            try:
                self.login(username, password, current_captcha)
                return current_captcha
            except ValueError as exc:
                last_error = exc
                if attempt >= self.max_retries or not self.auto_ocr:
                    break
                logger.warning("登录失败，第 %d 次重试…", attempt)
                result = self.fetch_captcha_result(refresh=True)
                current_captcha = result.text

        raise ValueError(
            f"登录失败，已重试 {self.max_retries} 次。"
            f"最后验证码: {current_captcha}"
        ) from last_error

    def save_auth_state(self) -> None:
        if self._context is None:
            return
        auth_state = resolve_path(
            self._browser_cfg.get("auth_state_path", "data/.auth/state.json")
        )
        auth_state.parent.mkdir(parents=True, exist_ok=True)
        self._context.storage_state(path=str(auth_state))

    def close(self) -> None:
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
        self._page = None
        self._context = None


def _fetch_captcha_sync(
    *,
    refresh: bool = False,
    on_progress: Callable[[str], None] | None = None,
) -> CaptchaResult:
    def report(msg: str) -> None:
        logger.info(msg)
        if on_progress:
            on_progress(msg)

    session = CaptchaSession.current()
    report("正在获取验证码…")
    try:
        result = session.fetch_captcha_result(refresh=refresh)
    except Exception:
        CaptchaSession.reset()
        raise

    if result.text:
        report(f"验证码已自动识别: {result.text}")
    else:
        report("验证码已获取，请手动输入")
    return result


def fetch_captcha(
    *,
    refresh: bool = False,
    on_progress: Callable[[str], None] | None = None,
) -> CaptchaResult:
    """获取登录页图形验证码（在固定浏览器线程中执行）。"""
    return run_browser_task(
        _fetch_captcha_sync,
        refresh=refresh,
        on_progress=on_progress,
    )


def reset_captcha_session() -> None:
    """关闭验证码浏览器会话（在固定浏览器线程中执行）。"""
    run_browser_task(CaptchaSession.reset)
