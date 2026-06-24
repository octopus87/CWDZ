"""科拓 Excel 页签合并（第二步整理）。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from cwdz.processor.keytop_workbook import ACCOUNT_FLOW_HEADERS, NO_PERMISSION_MSG
from cwdz.processor.parser import EXCEL_SUFFIXES

logger = logging.getLogger(__name__)

SHEET_NAME_COLUMN = "页签名称"
MERGE_OUTPUT_SUFFIX = "_合并"

ERROR_PREFIXES = ("下载失败", "车场切换失败")


@dataclass
class KeytopMergeResult:
    dataframe: pd.DataFrame
    source_file: Path
    processed_sheets: list[str]
    skipped_sheets: list[str]


def merge_keytop_workbook(input_path: Path) -> KeytopMergeResult:
    """读取单个 Excel，将其全部页签合并为一表，首列写入页签名称。"""
    file_path = Path(input_path)
    if not file_path.is_file():
        raise ValueError(f"文件不存在: {file_path}")
    if file_path.suffix.lower() not in EXCEL_SUFFIXES:
        raise ValueError(f"不支持的文件格式: {file_path.suffix}")

    frames: list[pd.DataFrame] = []
    processed: list[str] = []
    skipped: list[str] = []

    sheets = pd.read_excel(file_path, sheet_name=None, header=0)
    for sheet_name, raw in sheets.items():
        name = str(sheet_name)
        df = _clean_keytop_sheet(name, raw)
        if df.empty:
            skipped.append(name)
            logger.info("跳过无有效数据页签: %s", name)
            continue
        frames.append(df)
        processed.append(name)
        logger.info("已读取页签: %s (%d 行)", name, len(df))

    if not frames:
        raise ValueError("文件中没有可合并的有效页签数据")

    merged = pd.concat(frames, ignore_index=True)
    logger.info(
        "科拓页签合并完成: %s, %d 个页签, %d 行 (跳过 %d 个页签)",
        file_path.name,
        len(processed),
        len(merged),
        len(skipped),
    )
    return KeytopMergeResult(
        dataframe=merged,
        source_file=file_path,
        processed_sheets=processed,
        skipped_sheets=skipped,
    )


def build_merge_output_path(source_file: Path, stamp: str) -> Path:
    return source_file.with_name(f"{source_file.stem}{MERGE_OUTPUT_SUFFIX}_{stamp}.xlsx")


def _clean_keytop_sheet(sheet_name: str, df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.iloc[0:0].copy()

    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    date_col = ACCOUNT_FLOW_HEADERS[0]
    if date_col not in df.columns:
        return df.iloc[0:0].copy()

    values = df[date_col].astype(str).str.strip()
    valid = (
        df[date_col].notna()
        & (values != "")
        & (values != "nan")
        & ~values.str.contains(NO_PERMISSION_MSG, regex=False)
        & ~values.str.startswith(ERROR_PREFIXES)
    )
    df = df.loc[valid].reset_index(drop=True)
    if df.empty:
        return df

    columns = [SHEET_NAME_COLUMN, *ACCOUNT_FLOW_HEADERS]
    for col in ACCOUNT_FLOW_HEADERS:
        if col not in df.columns:
            df[col] = ""
    df = df[ACCOUNT_FLOW_HEADERS]
    df.insert(0, SHEET_NAME_COLUMN, sheet_name)
    return df[columns]
