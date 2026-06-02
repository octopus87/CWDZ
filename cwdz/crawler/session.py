from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from cwdz.config import load_settings, resolve_path
from cwdz.crawler.api_client import TingsimpleApiClient
from cwdz.crawler.browser_executor import run_browser_task
from cwdz.crawler.captcha import CaptchaResult, CaptchaSession, fetch_captcha
from cwdz.crawler.download import download_reconciliation
from cwdz.crawler.login import HOME_URL, is_logged_in

logger = logging.getLogger(__name__)


def _use_api_mode() -> bool:
    settings = load_settings()
    return settings.get("download", {}).get("mode", "browser") == "api"


class TingsimpleClient:
    """停简单 BMP 平台客户端。"""

    def __init__(self) -> None:
        self._settings = load_settings()
        self._ts = self._settings.get("tingsimple", {})
        self._browser_cfg = self._settings.get("browser", {})
        self._use_api = _use_api_mode()

    def fetch_captcha(
        self,
        *,
        refresh: bool = False,
        on_progress: Callable[[str], None] | None = None,
    ) -> CaptchaResult:
        if self._use_api:
            return _fetch_captcha_api(on_progress=on_progress)
        return fetch_captcha(refresh=refresh, on_progress=on_progress)

    def fetch_reconciliation(
        self,
        start_date: str,
        end_date: str,
        *,
        username: str,
        password: str,
        captcha: str,
        download_dir: str | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> Path:
        if not username or not password:
            raise ValueError("请填写停简单用户名和密码")
        if not captcha.strip():
            raise ValueError("请填写图形验证码")

        if self._use_api:
            return _fetch_reconciliation_api(
                start_date,
                end_date,
                username=username,
                password=password,
                captcha=captcha.strip(),
                download_dir=download_dir,
                on_progress=on_progress,
            )

        return run_browser_task(
            _fetch_reconciliation_sync,
            start_date,
            end_date,
            username=username,
            password=password,
            captcha=captcha.strip(),
            download_dir=download_dir,
            on_progress=on_progress,
            ts=self._ts,
            browser_cfg=self._browser_cfg,
        )


def _fetch_captcha_api(
    *,
    on_progress: Callable[[str], None] | None = None,
) -> CaptchaResult:
    def report(msg: str) -> None:
        logger.info(msg)
        if on_progress:
            on_progress(msg)

    report("正在获取验证码…")
    with TingsimpleApiClient() as client:
        result = client.fetch_captcha_result()
    if result.text:
        report(f"验证码已自动识别: {result.text}")
    else:
        report("验证码已获取，请手动输入")
    return result


def _fetch_reconciliation_api(
    start_date: str,
    end_date: str,
    *,
    username: str,
    password: str,
    captcha: str,
    download_dir: str | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> Path:
    with TingsimpleApiClient() as client:
        return client.download_reconciliation(
            start_date,
            end_date,
            username=username,
            password=password,
            captcha=captcha,
            download_dir=download_dir,
            on_progress=on_progress,
        )


def _fetch_reconciliation_sync(
    start_date: str,
    end_date: str,
    *,
    username: str,
    password: str,
    captcha: str,
    on_progress: Callable[[str], None] | None,
    ts: dict,
    browser_cfg: dict,
    download_dir: str | None = None,
) -> Path:
    if download_dir:
        save_dir = Path(download_dir).expanduser()
    else:
        save_dir = resolve_path(ts.get("download_dir", "data/downloads"))
    auth_state = resolve_path(
        browser_cfg.get("auth_state_path", "data/.auth/state.json")
    )

    def report(msg: str) -> None:
        logger.info(msg)
        if on_progress:
            on_progress(msg)

    saved = _try_download_with_saved_session(
        start_date,
        end_date,
        save_dir,
        auth_state,
        browser_cfg,
        report,
    )
    if saved is not None:
        return saved

    report("正在登录停简单…")
    try:
        session = CaptchaSession.current()
        used_captcha = session.login_with_auto_retry(username, password, captcha)
        report(f"登录成功，验证码: {used_captcha}")
        session.save_auth_state()

        report(f"正在下载 {start_date} ~ {end_date} 对账数据…")
        save_path = download_reconciliation(
            session.page(),
            session.context,
            save_dir,
            start_date=start_date,
            end_date=end_date,
        )
        report(f"下载完成: {save_path.name}")
        return save_path
    finally:
        CaptchaSession.reset()


def _try_download_with_saved_session(
    start_date: str,
    end_date: str,
    download_dir: Path,
    auth_state: Path,
    browser_cfg: dict,
    report: Callable[[str], None],
) -> Path | None:
    if not auth_state.exists():
        return None

    report("检测到已保存登录状态，正在验证…")
    with sync_playwright() as pw:
        browser: Browser = pw.chromium.launch(
            headless=browser_cfg.get("headless", True)
        )
        context: BrowserContext = browser.new_context(
            accept_downloads=True,
            storage_state=str(auth_state),
        )
        page: Page = context.new_page()
        page.set_default_timeout(browser_cfg.get("timeout_ms", 60000))
        try:
            page.goto(HOME_URL, wait_until="networkidle")
            if not is_logged_in(page):
                report("登录状态已过期，需要重新登录")
                return None

            report("已使用保存的登录状态")
            report(f"正在下载 {start_date} ~ {end_date} 对账数据…")
            save_path = download_reconciliation(
                page,
                context,
                download_dir,
                start_date=start_date,
                end_date=end_date,
            )
            report(f"下载完成: {save_path.name}")
            return save_path
        finally:
            browser.close()
