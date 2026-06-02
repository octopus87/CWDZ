"""停简单平台 HTTP API 客户端。"""

from __future__ import annotations

import base64
import json
import logging
import re
import time
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import httpx

from cwdz.config import load_settings, resolve_path
from cwdz.crawler.captcha_ocr import CaptchaResult, recognize_captcha

logger = logging.getLogger(__name__)

BASE = "https://open.tingjiandan.com"
LOGIN_PAGE = f"{BASE}/bmp-web/login"
LOGIN_POST = f"{BASE}/bmp-web/loginpost"
IMG_CODE = f"{BASE}/bmp-web/code/getImgCode"
PARK_LIST = f"{BASE}/btcauthorize/funcTree/selectParkDataByFuncTreeId"
SETTLE_PAGE = f"{BASE}/tcAccountCheck/settle/getSettledInfoPage"
EXPORT_TASK = f"{BASE}/tcbstats/downTask/getOrderTask"
DOWNLOAD_LIST = f"{BASE}/tcbstats/downTask/selectDownTaskJobByPage"

# 停简单结算明细菜单 funcTreeId
FUNC_TREE_ID = "424eb20b7fb04d919a7892e1cc2ce919"

# 导出结算类型：fileName 后缀 -> businessType（与网页 Tab 一致）
EXPORT_TYPES: dict[str, str] = {
    "临停结算列表": "001",
    "长租结算列表": "002",
    "代收结算列表": "003",
    "扫码结算列表": "007",
    "补缴结算列表": "013",
    "ETC结算列表": "015",
    "欠费追缴结算列表": "010",
}

TASK_STATUS_READY = "2"
TASK_STATUS_GENERATING = "1"


@dataclass
class ParkInfo:
    park_id: str
    park_name: str


@dataclass
class DownloadTask:
    task_id: str
    file_name: str
    file_url: str
    status: str


class TingsimpleApiClient:
    """停简单 BMP HTTP API 客户端。"""

    def __init__(self, session: httpx.Client | None = None) -> None:
        self._settings = load_settings()
        self._session = session or httpx.Client(
            timeout=60.0,
            headers={"User-Agent": "Mozilla/5.0 CWDZ/1.0"},
            follow_redirects=True,
        )
        self._owns_session = session is None
        self._ctoken = ""
        self._img_code_key = ""

    def close(self) -> None:
        if self._owns_session:
            self._session.close()

    def __enter__(self) -> TingsimpleApiClient:
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def log(self, msg: str, on_progress: Callable[[str], None] | None = None) -> None:
        logger.info(msg)
        if on_progress:
            on_progress(msg)

    def fetch_captcha_result(self, *, auto_ocr: bool | None = None) -> CaptchaResult:
        """获取登录验证码图片（HTTP）。"""
        image, _ = self._fetch_captcha_image()
        self._save_login_state()
        use_ocr = (
            auto_ocr
            if auto_ocr is not None
            else bool(self._settings.get("captcha", {}).get("auto_ocr", True))
        )
        text = recognize_captcha(image) if use_ocr else ""
        return CaptchaResult(image=image, text=text)

    def _fetch_captcha_image(self) -> tuple[bytes, str]:
        resp = self._session.get(LOGIN_PAGE)
        resp.raise_for_status()
        html = resp.text

        self._ctoken = _input_value(html, "ctoken")
        img_code_key = _input_value(html, "imgCodeKey") or _input_value(html, "refer")

        img_resp = self._session.get(IMG_CODE, params={"imgCodeKey": img_code_key})
        img_resp.raise_for_status()
        payload = img_resp.json()
        self._img_code_key = payload.get("imgCodeKey") or img_code_key
        image = _decode_captcha_image(payload)
        return image, self._img_code_key

    def login(
        self,
        username: str,
        password: str,
        captcha: str | None = None,
        *,
        max_retries: int | None = None,
    ) -> None:
        """HTTP 登录（含 OCR 验证码）。"""
        retries = max_retries or int(self._settings.get("captcha", {}).get("max_retries", 3))
        auto_ocr = bool(self._settings.get("captcha", {}).get("auto_ocr", True))
        self._load_login_state()

        last_error: Exception | None = None
        code = captcha

        for attempt in range(1, retries + 1):
            if not code:
                image, _ = self._fetch_captcha_image()
                if auto_ocr:
                    code = recognize_captcha(image)
                else:
                    raise ValueError("请填写图形验证码")

            try:
                self._post_login(username, password, code)
                self._save_cookies()
                self._clear_login_state()
                return
            except ValueError as exc:
                last_error = exc
                code = None
                if attempt >= retries:
                    break
                logger.warning("HTTP 登录失败，第 %d 次重试…", attempt)
                time.sleep(0.5)

        raise ValueError(f"登录失败，已重试 {retries} 次") from last_error

    def _post_login(self, username: str, password: str, captcha: str) -> None:
        if not self._ctoken or not self._img_code_key:
            self._fetch_captcha_image()

        data = {
            "login": username,
            "password": password,
            "imgCode": captcha,
            "ReturnURL": "",
            "ctoken": self._ctoken,
            "refer": self._ctoken,
            "imgCodeKey": self._img_code_key,
        }
        login_resp = self._session.post(LOGIN_POST, data=data)
        login_resp.raise_for_status()
        result = login_resp.json()
        if not _is_success(result):
            raise ValueError(f"登录失败: {result.get('msg', result)}")

    def ensure_logged_in(
        self,
        username: str,
        password: str,
        captcha: str | None = None,
        *,
        on_progress: Callable[[str], None] | None = None,
    ) -> None:
        if self.load_cookies():
            try:
                self.get_parks()
                self.log("使用已保存 Cookie", on_progress)
                return
            except Exception:
                logger.info("Cookie 已过期，重新登录")

        self.log("HTTP 登录…", on_progress)
        self.login(username, password, captcha)

    def _login_state_path(self) -> Path:
        auth = resolve_path(
            self._settings.get("browser", {}).get("auth_state_path", "data/.auth/state.json")
        )
        return auth.with_name("login_state.json")

    def _save_login_state(self) -> None:
        path = self._login_state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"ctoken": self._ctoken, "imgCodeKey": self._img_code_key}, ensure_ascii=False),
            encoding="utf-8",
        )

    def _load_login_state(self) -> None:
        path = self._login_state_path()
        if not path.exists():
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        self._ctoken = data.get("ctoken", "")
        self._img_code_key = data.get("imgCodeKey", "")

    def _clear_login_state(self) -> None:
        path = self._login_state_path()
        if path.exists():
            path.unlink()

    def load_cookies(self) -> bool:
        cookie_path = self._cookie_path()
        if not cookie_path.exists():
            return False
        for item in json.loads(cookie_path.read_text(encoding="utf-8")):
            self._session.cookies.set(item["name"], item["value"], domain=item.get("domain"))
        return True

    def _save_cookies(self) -> None:
        path = self._cookie_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        cookies = []
        for c in self._session.cookies.jar:
            cookies.append({"name": c.name, "value": c.value, "domain": c.domain})
        path.write_text(json.dumps(cookies, ensure_ascii=False), encoding="utf-8")

    def _cookie_path(self) -> Path:
        return resolve_path(
            self._settings.get("browser", {}).get("auth_state_path", "data/.auth/state.json")
        ).with_suffix(".cookies.json")

    def get_parks(self) -> list[ParkInfo]:
        url = f"{PARK_LIST}/{FUNC_TREE_ID}"
        resp = self._session.post(url, json={})
        resp.raise_for_status()
        data = resp.json()
        if not _is_success(data):
            raise RuntimeError(f"获取车场列表失败: {data.get('msg')}")
        parks: list[ParkInfo] = []
        for item in data.get("body") or []:
            pid = item.get("pmParkId") or item.get("id") or item.get("parkId")
            name = item.get("parkName") or item.get("name") or ""
            if pid:
                parks.append(ParkInfo(park_id=str(pid), park_name=str(name)))
        return parks

    def get_all_park_ids(self) -> list[str]:
        return [p.park_id for p in self.get_parks()]

    def _date_str(self, date: str) -> str:
        return date.replace("-", "")

    def _build_file_name(self, parks: list[ParkInfo], type_suffix: str) -> str:
        names = [p.park_name for p in parks if p.park_name]
        if len(names) >= 2:
            prefix = f"{names[0]},{names[1]},..."
        elif names:
            prefix = f"{names[0]},..."
        else:
            prefix = "所有项目,..."
        return f"{prefix}{type_suffix}"

    def export_settlement(
        self,
        parks: list[ParkInfo],
        start_date: str,
        end_date: str,
        *,
        on_progress: Callable[[str], None] | None = None,
    ) -> list[str]:
        """提交全部结算类型导出任务，返回 taskId 列表。"""
        park_list = ",".join(p.park_id for p in parks)
        task_ids: list[str] = []

        for type_suffix, business_type in EXPORT_TYPES.items():
            file_name = self._build_file_name(parks, type_suffix)
            payload = {
                "pmParkId": "",
                "pmParkIdList": park_list,
                "businessType": business_type,
                "startDate": self._date_str(start_date),
                "endDate": self._date_str(end_date),
                "fileName": file_name,
                "downType": "getSettledInfoExcel",
            }
            self.log(f"提交导出任务: {type_suffix} (businessType={business_type})", on_progress)
            resp = self._session.post(EXPORT_TASK, json=payload)
            resp.raise_for_status()
            data = resp.json()
            if not data.get("taskId"):
                raise RuntimeError(f"导出失败 [{type_suffix}]: {data.get('msg', data)}")
            task_id = data["taskId"]
            task_ids.append(task_id)
            self.log(f"  taskId={task_id} ({data.get('msg', '')})", on_progress)
            time.sleep(0.5)
        return task_ids

    def list_download_tasks(self) -> list[DownloadTask]:
        resp = self._session.post(DOWNLOAD_LIST, json={"start": 0, "limit": 20})
        resp.raise_for_status()
        data = resp.json()
        tasks: list[DownloadTask] = []
        for block in data.get("resultData") or []:
            for item in block.get("message") or []:
                tasks.append(
                    DownloadTask(
                        task_id=item.get("downTaskJobId", ""),
                        file_name=item.get("fileName", ""),
                        file_url=_decode_file_url(item.get("fileUrl", "")),
                        status=str(item.get("status", "")),
                    )
                )
        return tasks

    def wait_tasks_ready(
        self,
        task_ids: list[str],
        *,
        timeout: int = 300,
        on_progress: Callable[[str], None] | None = None,
    ) -> list[DownloadTask]:
        pending = set(task_ids)
        ready: list[DownloadTask] = []
        start = time.time()

        while pending and time.time() - start < timeout:
            tasks = self.list_download_tasks()
            for task in tasks:
                if task.task_id not in pending:
                    continue
                if task.status == TASK_STATUS_READY:
                    ready.append(task)
                    pending.discard(task.task_id)
                    self.log(f"文件已生成: {task.file_name}", on_progress)
                elif task.status == TASK_STATUS_GENERATING:
                    self.log(f"生成中: {task.file_name}", on_progress)
            if pending:
                self.log(f"等待 {len(pending)} 个文件生成…", on_progress)
                time.sleep(5)
        if pending:
            raise TimeoutError(f"以下任务超时未生成: {pending}")
        return ready

    def download_file(self, task: DownloadTask, download_dir: Path) -> Path:
        download_dir.mkdir(parents=True, exist_ok=True)
        safe_name = task.file_name.replace("/", "_") + ".xls"
        save_path = download_dir / safe_name
        resp = self._session.get(task.file_url)
        resp.raise_for_status()
        save_path.write_bytes(resp.content)
        return save_path

    def download_reconciliation(
        self,
        start_date: str,
        end_date: str,
        *,
        username: str | None = None,
        password: str | None = None,
        captcha: str | None = None,
        download_dir: str | Path | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> Path:
        """完整 API 下载流程。"""
        ts = self._settings.get("tingsimple", {})
        user = username or ts.get("username", "")
        pwd = password or ts.get("password", "")
        if download_dir:
            target_dir = Path(download_dir).expanduser()
        else:
            target_dir = resolve_path(ts.get("download_dir", "data/downloads"))

        self.ensure_logged_in(user, pwd, captcha, on_progress=on_progress)

        self.log("获取车场列表…", on_progress)
        parks = self.get_parks()
        self.log(f"共 {len(parks)} 个车场", on_progress)

        self.log(f"提交导出 {start_date} ~ {end_date}", on_progress)
        task_ids = self.export_settlement(
            parks, start_date, end_date, on_progress=on_progress
        )

        self.log("等待文件生成…", on_progress)
        tasks = self.wait_tasks_ready(task_ids, on_progress=on_progress)

        self.log(f"下载 {len(tasks)} 个文件…", on_progress)
        saved: list[Path] = []
        for task in tasks:
            path = self.download_file(task, target_dir)
            saved.append(path)
            self.log(f"已保存: {path.name}", on_progress)

        # 返回第一个文件路径；全部文件在同一目录
        if not saved:
            raise RuntimeError("未下载到任何文件")
        return saved[0]


def _input_value(html: str, name: str) -> str:
    m = re.search(rf'name="{name}"[^>]*value="([^"]*)"', html)
    if m:
        return m.group(1)
    m = re.search(rf'value="([^"]*)"[^>]*name="{name}"', html)
    return m.group(1) if m else ""


def _is_success(data: dict) -> bool:
    val = data.get("isSuccess")
    return val in (0, "0", True, "true")


def _decode_file_url(url: str) -> str:
    return urllib.parse.unquote(url.replace("%2dcn%2d", "-cn-"))


def _decode_captcha_image(payload: dict) -> bytes:
    data = payload.get("data") or payload.get("img") or ""
    if isinstance(data, bytes):
        return data
    if not isinstance(data, str):
        raise ValueError(f"无法解析验证码响应: {payload}")
    if data.startswith("data:"):
        _, encoded = data.split(",", 1)
        return base64.b64decode(encoded)
    return base64.b64decode(data)
