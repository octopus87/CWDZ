"""科拓批量下载账户资金并生成新 Excel。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from cwdz.crawler.keytop.client import KeytopClient
from cwdz.processor.keytop_workbook import (
    NO_PERMISSION_MSG,
    load_task_workbook,
    mark_sheet_no_permission,
    save_task_workbook,
    write_sheet_message,
    write_sheet_rows,
)

SUBJECT_TYPE_MAP = {"00": "入账", "01": "出账"}


@dataclass
class BatchSheetResult:
    sheet_name: str
    status: str
    row_count: int = 0
    message: str = ""


@dataclass
class BatchDownloadResult:
    workbook_path: Path
    sheets: list[BatchSheetResult] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        return sum(1 for s in self.sheets if s.status == "ok")

    @property
    def no_permission_count(self) -> int:
        return sum(1 for s in self.sheets if s.status == "no_permission")

    @property
    def error_count(self) -> int:
        return sum(1 for s in self.sheets if s.status == "error")


def flow_item_to_row(item: dict) -> list:
    subject_type = str(item.get("subjectType") or "")
    type_text = SUBJECT_TYPE_MAP.get(subject_type, subject_type)
    return [
        item.get("flowDate"),
        item.get("tranDate"),
        item.get("totalAmount"),
        item.get("fee"),
        item.get("inAccountAmount"),
        item.get("outAccountAmount"),
        item.get("afterBalance"),
        type_text,
        item.get("operateDesc"),
    ]


def build_output_path(
    template_path: str | Path,
    output_dir: str | Path,
    start_date: str,
    end_date: str,
) -> Path:
    template = Path(template_path)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    start = start_date.replace("-", "").replace("/", "")
    end = end_date.replace("-", "").replace("/", "")
    return target_dir / f"{template.stem}_{start}_{end}_{stamp}.xlsx"


def download_batch_workbook(
    client: KeytopClient,
    workbook_path: str | Path,
    start_date: str,
    end_date: str,
    *,
    output_dir: str | Path | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> BatchDownloadResult:
    """按任务 Excel 每个页签切换车场、下载账户资金，并生成新文件。"""
    template_path = Path(workbook_path)
    out_path = build_output_path(
        template_path,
        output_dir or template_path.parent,
        start_date,
        end_date,
    )
    client.ensure_logged_in(on_progress=on_progress)
    client._report(f"读取任务模板: {template_path.name}", on_progress)
    client._report(f"输出文件: {out_path}", on_progress)

    lots = client.list_my_lots(on_progress=on_progress)
    lot_names = ", ".join(str(lot.get("name", "")) for lot in lots) or "无"
    client._report(f"当前账号可见车场 ({len(lots)}): {lot_names}", on_progress)

    wb = load_task_workbook(template_path)
    result = BatchDownloadResult(workbook_path=out_path)
    total = len(wb.sheetnames)

    for index, sheet_name in enumerate(wb.sheetnames, start=1):
        ws = wb[sheet_name]
        client._report(f"[{index}/{total}] 页签「{sheet_name}」", on_progress)

        try:
            profile = client.switch_lot_by_sheet_name(
                sheet_name,
                lots,
                on_progress=on_progress,
            )
        except Exception as exc:
            msg = f"车场切换失败: {exc}"
            write_sheet_message(ws, msg)
            result.sheets.append(
                BatchSheetResult(
                    sheet_name=sheet_name,
                    status="error",
                    message=msg,
                )
            )
            client._report(f"  → {msg}", on_progress)
            continue

        if not profile:
            mark_sheet_no_permission(ws)
            result.sheets.append(
                BatchSheetResult(
                    sheet_name=sheet_name,
                    status="no_permission",
                    message=NO_PERMISSION_MSG,
                )
            )
            client._report("  → 无车场权限，页签已标红", on_progress)
            continue

        lot_name = profile.lot_name or sheet_name
        try:
            client._report(f"  → 切换完成，开始下载「{lot_name}」账户资金…", on_progress)
            items = client.fetch_account_flow_all(
                start_date,
                end_date,
                on_progress=on_progress,
            )
            rows = [flow_item_to_row(item) for item in items]
            write_sheet_rows(ws, rows)
            result.sheets.append(
                BatchSheetResult(
                    sheet_name=sheet_name,
                    status="ok",
                    row_count=len(rows),
                    message=f"{lot_name} {len(rows)} 条",
                )
            )
            client._report(f"  → {lot_name} 下载 {len(rows)} 条", on_progress)
        except Exception as exc:
            msg = f"下载失败: {exc}"
            write_sheet_message(ws, msg)
            result.sheets.append(
                BatchSheetResult(
                    sheet_name=sheet_name,
                    status="error",
                    message=msg,
                )
            )
            client._report(f"  → {msg}", on_progress)

    save_task_workbook(wb, out_path)
    client._report(f"已生成新文件: {out_path}", on_progress)
    client._report(
        f"批量任务完成: 成功 {result.success_count}，无权限 {result.no_permission_count}，失败 {result.error_count}",
        on_progress,
    )
    return result
