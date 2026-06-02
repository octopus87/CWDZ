from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_ocr = None


@dataclass
class CaptchaResult:
    image: bytes
    text: str


def _get_ocr():
    global _ocr
    if _ocr is None:
        import ddddocr

        _ocr = ddddocr.DdddOcr(show_ad=False)
    return _ocr


def recognize_captcha(image: bytes) -> str:
    """识别图形验证码。"""
    text = _get_ocr().classification(image)
    cleaned = re.sub(r"[^a-zA-Z0-9]", "", text or "").strip()
    logger.info("验证码识别结果: %s", cleaned or "(空)")
    if not cleaned:
        raise ValueError("验证码识别失败，请手动输入或刷新重试")
    return cleaned


def recognize_captcha_result(image: bytes) -> CaptchaResult:
    return CaptchaResult(image=image, text=recognize_captcha(image))
