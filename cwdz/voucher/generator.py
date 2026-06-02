from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

logger = logging.getLogger(__name__)

# 凭证模板中数据起始行（1-based），按财务模板调整
DATA_START_ROW = 2


def generate_voucher(
    df: pd.DataFrame,
    template_path: Path,
    output_dir: Path,
    *,
    period: str | None = None,
) -> Path:
    """基于 Excel 模板生成凭证文件。

    Args:
        df: 对账整理后的数据
        template_path: 财务提供的 Excel 模板路径
        output_dir: 凭证输出目录
        period: 账期标识，如 2026-05

    Returns:
        生成的凭证文件路径
    """
    if not template_path.exists():
        raise FileNotFoundError(
            f"凭证模板不存在: {template_path}\n"
            "请将财务提供的 Excel 模板放到 voucher/template.xlsx"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    period = period or datetime.now().strftime("%Y-%m")
    output_path = output_dir / f"凭证_{period}.xlsx"

    shutil.copy(template_path, output_path)
    wb = load_workbook(output_path)
    ws = wb.active

    # TODO: 按财务模板列映射关系填写数据
    for i, row in df.iterrows():
        excel_row = DATA_START_ROW + i
        ws.cell(row=excel_row, column=1, value=row.iloc[0] if len(row) > 0 else "")
        ws.cell(row=excel_row, column=2, value=row.iloc[1] if len(row) > 1 else "")

    wb.save(output_path)
    logger.info("凭证已生成: %s", output_path)
    return output_path
