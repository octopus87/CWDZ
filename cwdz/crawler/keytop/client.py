"""科拓（Keytop）平台客户端。"""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

import httpx

from cwdz.config import load_settings, resolve_path

logger = logging.getLogger(__name__)

BASE = "https://park.keytop.cn"
QR_CODE_API = f"{BASE}/unity/service/open/login/qrcode/app"
POLL_API = f"{BASE}/unity/service/open/pollingLoginResult"
TOKEN_API = f"{BASE}/unity/service/open/login/getUserTokenByUUID"
USER_INFO_API = f"{BASE}/unity/user/getMyBaseInfo"
FIND_MY_LOTS_API = f"{BASE}/unity/lot/findMyLots"
SET_LOT_CACHE_API = f"{BASE}/unity/user/setLotCache"
PAGE_ACCOUNT_FLOW_API = f"{BASE}/as-kos-web/service/account/pageAccountFlow"
EXPORT_ACCOUNT_FLOW_API = f"{BASE}/as-kos-web/service/account/exportAccountFlow"
EXPORT_PROGRESS_API = f"{BASE}/as-kos-web/service/excel/getExportProgress"
EXPORT_DOWNLOAD_API = f"{BASE}/as-kos-web/service/excel/downloadExcel"

STATE_WAITING = "QRCODE_SCAN_NEVER"
STATE_POLL_AGAIN = {"QRCODE_SCAN_NEVER", "QRCODE_SCAN_ING"}
STATE_SCAN_SUCCESS = "QRCODE_SCAN_SUCC"
STATE_SCAN_FAIL = "QRCODE_SCAN_FAIL"


@dataclass
class QrCodeResult:
    image: bytes
    uuid: str
    image_url: str


@dataclass
class KeytopUserProfile:
    lot_name: str = ""
    user_name: str = ""
    current_lot_id: str = ""


class KeytopClient:
    """科拓 UnityP 客户端（扫码登录）。"""

    def __init__(self, session: httpx.Client | None = None) -> None:
        self._settings = load_settings()
        self._kt = self._settings.get("keytop", {})
        self._session = session or httpx.Client(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 CWDZ/1.0",
                "client-flag": "PC",
            },
            follow_redirects=True,
        )
        self._owns_session = session is None
        self._lot_id = ""
        self._load_auth()

    def close(self) -> None:
        if self._owns_session:
            self._session.close()

    def __enter__(self) -> KeytopClient:
        return self

    def __exit__(self, *args) -> None:
        self.close()

    @property
    def kt_token(self) -> str:
        return self._session.headers.get("kt-token", "")

    def is_logged_in(self) -> bool:
        return bool(self.kt_token) or self._auth_path().exists()

    def fetch_qr_code(self, *, expire_day: int | None = None) -> QrCodeResult:
        """获取登录二维码。"""
        days = expire_day or int(self._kt.get("qr_expire_days", 30))
        resp = self._session.get(QR_CODE_API, params={"expireDay": days})
        resp.raise_for_status()
        payload = resp.json()
        data = payload.get("data") or {}
        uuid = data.get("uuid", "")
        image_url = data.get("img", "")
        if not uuid or not image_url:
            raise RuntimeError(f"获取二维码失败: {payload}")

        img_resp = self._session.get(image_url)
        img_resp.raise_for_status()
        return QrCodeResult(image=img_resp.content, uuid=uuid, image_url=image_url)

    def poll_login_state(self, uuid: str) -> str:
        resp = self._session.get(POLL_API, params={"uuid": uuid, "type": "app"})
        resp.raise_for_status()
        data = resp.json().get("data") or {}
        return str(data.get("state", ""))

    def fetch_token(self, uuid: str) -> str:
        resp = self._session.post(TOKEN_API, json={"uuid": uuid})
        resp.raise_for_status()
        payload = resp.json()
        code = payload.get("code", payload.get("resultCode"))
        if code not in (200, "200", None):
            if payload.get("key") != "common.success":
                raise RuntimeError(payload.get("resultMsg") or payload.get("message") or str(payload))

        data = payload.get("data") or {}
        token = (
            data.get("ktToken")
            or data.get("token")
            or data.get("userToken")
            or data.get("accessToken")
        )
        if not token and isinstance(data, str):
            token = data
        if not token or token in {"1", "null", "undefined"}:
            raise RuntimeError(f"未获取到有效登录 token: {payload}")
        return str(token)

    def fetch_user_profile(
        self,
        *,
        on_progress: Callable[[str], None] | None = None,
    ) -> KeytopUserProfile:
        """获取当前登录用户与车场信息。"""
        self.ensure_logged_in(on_progress=on_progress)
        profile = self._read_user_profile()
        self._save_auth(
            {
                "kt_token": self.kt_token,
                **profile.__dict__,
            }
        )
        return profile

    def wait_for_login(
        self,
        uuid: str,
        *,
        timeout: int | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> None:
        """轮询扫码结果直至登录成功。"""
        limit = timeout or int(self._kt.get("login_timeout", 180))
        start = time.time()
        last_state = ""

        while time.time() - start < limit:
            state = self.poll_login_state(uuid)
            if state != last_state:
                last_state = state
                if state == STATE_SCAN_SUCCESS:
                    self._report("扫码成功，请在手机点击确认登录", on_progress)
                else:
                    self._report(f"扫码状态: {state}", on_progress)

            if state == STATE_SCAN_FAIL:
                raise RuntimeError("扫码失败，请刷新二维码后重试")

            if state == STATE_SCAN_SUCCESS:
                token = self.fetch_token(uuid)
                self._apply_token(token, uuid)
                self._report("科拓登录成功", on_progress)
                return

            if state in STATE_POLL_AGAIN:
                time.sleep(2)
                continue

            time.sleep(2)

        raise TimeoutError("扫码登录超时，请刷新二维码后重试")

    def ensure_logged_in(
        self,
        *,
        on_progress: Callable[[str], None] | None = None,
    ) -> None:
        if not self.kt_token and not self._load_auth():
            raise ValueError("请先扫码登录科拓平台")
        self._sync_session_headers()
        resp = self._session.post(USER_INFO_API, json={})
        resp.raise_for_status()
        payload = resp.json()
        code = payload.get("code", payload.get("resultCode"))
        if code not in (200, "200", None):
            raise ValueError(
                payload.get("resultMsg") or payload.get("message") or "科拓登录已失效，请重新扫码"
            )
        self._report("使用已保存的科拓登录状态", on_progress)

    def download_reconciliation(
        self,
        start_date: str,
        end_date: str,
        *,
        download_dir: str | Path | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> Path:
        """下载科拓账户资金流水（报表中心 → 结算中心 → 账户资金）。"""
        self.ensure_logged_in(on_progress=on_progress)
        target = Path(download_dir or self._kt.get("download_dir", "data/downloads/keytop"))
        target.mkdir(parents=True, exist_ok=True)

        flow_start = self._to_flow_date(start_date)
        flow_end = self._to_flow_date(end_date)
        self._report(
            f"提交账户资金导出任务 ({start_date} ~ {end_date})…",
            on_progress,
        )
        resp = self._session.post(
            EXPORT_ACCOUNT_FLOW_API,
            json={
                "flowDateStart": flow_start,
                "flowDateEnd": flow_end,
                "subjectCode": "",
                "subjectType": "",
            },
        )
        resp.raise_for_status()
        task_id = self._parse_kos_data(resp.json())
        if not task_id:
            raise RuntimeError(f"未获取到导出任务 ID: {resp.text}")

        self._report("等待导出文件生成…", on_progress)
        self._wait_export_task(str(task_id), on_progress=on_progress)

        self._report("下载导出文件…", on_progress)
        download_resp = self._session.get(
            EXPORT_DOWNLOAD_API,
            params={"taskId": task_id},
        )
        download_resp.raise_for_status()
        content_type = download_resp.headers.get("content-type", "")
        if "json" in content_type or download_resp.content[:1] == b"{":
            payload = download_resp.json()
            raise RuntimeError(payload.get("message") or str(payload))

        filename = self._filename_from_disposition(
            download_resp.headers.get("content-disposition", "")
        )
        if not filename:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"账户流水_{flow_start}_{flow_end}_{stamp}.xlsx"

        out_path = target / filename
        out_path.write_bytes(download_resp.content)
        self._report(f"已保存: {out_path.name}", on_progress)
        return out_path

    def list_my_lots(
        self,
        *,
        on_progress: Callable[[str], None] | None = None,
    ) -> list[dict]:
        """获取当前账号可见车场列表。"""
        resp = self._session.post(FIND_MY_LOTS_API, json={})
        resp.raise_for_status()
        data = self._parse_unity_data(resp.json())
        if not isinstance(data, list):
            return []
        self._report(f"获取到 {len(data)} 个可见车场", on_progress)
        return data

    def switch_lot(
        self,
        lot_id: str,
        *,
        lot_name: str = "",
        on_progress: Callable[[str], None] | None = None,
    ) -> KeytopUserProfile:
        """切换当前操作车场，确认切换成功后再返回。"""
        label = lot_name or lot_id
        self._report(f"正在切换车场至「{label}」…", on_progress)
        resp = self._session.post(SET_LOT_CACHE_API, json={"lotId": lot_id})
        resp.raise_for_status()
        self._parse_unity_data(resp.json())
        self._lot_id = str(lot_id)
        self._sync_session_headers()

        profile = self._read_user_profile()
        if profile.current_lot_id != str(lot_id):
            raise RuntimeError(
                f"车场切换失败: 期望 {lot_id}，当前 {profile.current_lot_id or '未知'}"
            )
        self._report(
            f"车场切换完成: {profile.lot_name} (ID: {profile.current_lot_id})",
            on_progress,
        )
        return profile

    def switch_lot_by_sheet_name(
        self,
        sheet_name: str,
        lots: list[dict],
        *,
        on_progress: Callable[[str], None] | None = None,
    ) -> KeytopUserProfile | None:
        """按页签车场名匹配并切换；无权限时返回 None。"""
        from cwdz.processor.keytop_workbook import match_lot

        lot = match_lot(sheet_name, lots)
        if not lot:
            return None
        lot_id = str(lot.get("lotId") or "")
        lot_name = str(lot.get("name") or sheet_name)
        return self.switch_lot(lot_id, lot_name=lot_name, on_progress=on_progress)

    def fetch_account_flow_all(
        self,
        start_date: str,
        end_date: str,
        *,
        page_size: int = 500,
        on_progress: Callable[[str], None] | None = None,
    ) -> list[dict]:
        """分页拉取账户资金流水。"""
        flow_start = self._to_flow_date(start_date)
        flow_end = self._to_flow_date(end_date)
        items: list[dict] = []
        page = 1
        total = 0

        while True:
            resp = self._session.post(
                PAGE_ACCOUNT_FLOW_API,
                json={
                    "flowDateStart": flow_start,
                    "flowDateEnd": flow_end,
                    "subjectCode": "",
                    "subjectType": "",
                    "pageNum": page,
                    "pageSize": page_size,
                },
            )
            resp.raise_for_status()
            data = self._parse_kos_data(resp.json()) or {}
            batch = data.get("items") or []
            if page == 1:
                total = int(data.get("total") or 0)
                self._report(f"账户流水共 {total} 条", on_progress)
            items.extend(batch)
            if not batch or len(items) >= total:
                break
            page += 1

        return items

    def _read_user_profile(self) -> KeytopUserProfile:
        resp = self._session.post(USER_INFO_API, json={})
        resp.raise_for_status()
        payload = resp.json()
        code = payload.get("code", payload.get("resultCode"))
        if code not in (200, "200", None):
            raise RuntimeError(payload.get("resultMsg") or payload.get("message") or str(payload))

        data = payload.get("data") or {}
        profile = KeytopUserProfile(
            lot_name=str(data.get("lotName") or ""),
            user_name=str(data.get("name") or data.get("loginName") or ""),
            current_lot_id=str(data.get("currentLotId") or ""),
        )
        self._lot_id = profile.current_lot_id
        self._sync_session_headers()
        return profile

    def _apply_token(self, token: str, uuid: str = "") -> None:
        existing = {}
        path = self._auth_path()
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
        existing.update({"kt_token": token, "uuid": uuid})
        self._save_auth(existing)

    def _sync_session_headers(self) -> None:
        lot_id = self._lot_id or str(self._kt.get("default_lot_id", ""))
        if lot_id:
            self._session.headers["KT_LOT_ID"] = lot_id
            self._session.headers["kt-lotcodes"] = lot_id
        self._session.headers["client-flag"] = "PC"
        self._session.headers["op-source"] = "3000"
        self._session.headers["accept-language"] = "zh-CN"

    def _wait_export_task(
        self,
        task_id: str,
        *,
        timeout: int | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> None:
        limit = timeout or int(self._kt.get("export_timeout", 120))
        start = time.time()
        while time.time() - start < limit:
            resp = self._session.get(EXPORT_PROGRESS_API, params={"taskId": task_id})
            resp.raise_for_status()
            data = self._parse_kos_data(resp.json()) or {}
            if isinstance(data, dict) and data.get("result"):
                msg = str(data.get("msg") or "导出完成")
                self._report(msg, on_progress)
                return
            if isinstance(data, dict) and data.get("result") is False:
                raise RuntimeError(str(data.get("msg") or "导出失败"))
            time.sleep(1)
        raise TimeoutError("账户资金导出超时，请稍后重试")

    @staticmethod
    def _to_flow_date(date_str: str) -> str:
        cleaned = date_str.strip().replace("/", "-")
        if re.fullmatch(r"\d{8}", cleaned):
            return cleaned
        return datetime.strptime(cleaned, "%Y-%m-%d").strftime("%Y%m%d")

    @staticmethod
    def _parse_kos_data(payload: dict):
        code = payload.get("code")
        if code not in (2000, "2000", None):
            raise RuntimeError(payload.get("message") or payload.get("resultMsg") or str(payload))
        return payload.get("data")

    @staticmethod
    def _parse_unity_data(payload: dict):
        code = payload.get("resultCode", payload.get("code"))
        if code not in (200, "200", None):
            raise RuntimeError(payload.get("resultMsg") or payload.get("message") or str(payload))
        return payload.get("data")

    @staticmethod
    def _filename_from_disposition(header: str) -> str:
        if not header:
            return ""
        match = re.search(r"filename\*?=(?:UTF-8''|\"?)([^\";]+)", header, re.I)
        if not match:
            return ""
        return unquote(match.group(1).strip()).strip('"')

    def _auth_path(self) -> Path:
        return resolve_path(
            self._kt.get("auth_state_path", "data/.auth/keytop.json")
        )

    def _save_auth(self, data: dict) -> None:
        path = self._auth_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        token = data.get("kt_token", "")
        if token:
            self._session.headers["kt-token"] = token
        lot_id = data.get("current_lot_id")
        if lot_id:
            self._lot_id = str(lot_id)
        self._sync_session_headers()

    def _load_auth(self) -> bool:
        path = self._auth_path()
        if not path.exists():
            return False
        data = json.loads(path.read_text(encoding="utf-8"))
        token = data.get("kt_token", "")
        self._lot_id = str(data.get("current_lot_id") or "")
        if token:
            self._session.headers["kt-token"] = token
            self._sync_session_headers()
            return True
        return False

    def saved_profile(self) -> KeytopUserProfile:
        path = self._auth_path()
        if not path.exists():
            return KeytopUserProfile()
        data = json.loads(path.read_text(encoding="utf-8"))
        return KeytopUserProfile(
            lot_name=str(data.get("lot_name") or ""),
            user_name=str(data.get("user_name") or ""),
            current_lot_id=str(data.get("current_lot_id") or ""),
        )

    @staticmethod
    def _report(msg: str, on_progress: Callable[[str], None] | None) -> None:
        logger.info(msg)
        if on_progress:
            on_progress(msg)
