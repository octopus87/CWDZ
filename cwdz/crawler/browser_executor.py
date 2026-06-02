from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Callable, TypeVar

T = TypeVar("T")

# Playwright sync API 必须在同一线程内使用
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="playwright")


def run_browser_task(func: Callable[..., T], /, *args, **kwargs) -> T:
    """在固定后台线程中执行 Playwright 操作。"""
    future = _executor.submit(func, *args, **kwargs)
    return future.result()


def shutdown_browser_executor() -> None:
    _executor.shutdown(wait=False)
