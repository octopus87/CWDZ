from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

HEADER_ROW_OFFSET = 6
NAME_COLUMN = "停车场名称"
EXCEL_SUFFIXES = (".xlsx", ".xls")
ORDER_COUNT_PATTERN = re.compile(r"订单数量\s*:\s*(\d+)")


@dataclass
class MergeResult:
    dataframe: pd.DataFrame
    processed_files: list[str]
    skipped_files: list[str]


def parse_tingsimple_export(file_path: Path) -> pd.DataFrame:
    """解析单个停简单导出文件（跳过前 6 行汇总区）。"""
    df = _read_export_sheet(file_path)
    df = _clean_data_rows(df)
    logger.info("解析文件 %s: %d 行", file_path.name, len(df))
    return df


def merge_tingsimple_exports(input_dir: Path) -> MergeResult:
    """合并目录下全部停简单 Excel 导出文件。"""
    if not input_dir.is_dir():
        raise ValueError(f"目录不存在: {input_dir}")

    files = sorted(
        p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in EXCEL_SUFFIXES
    )
    if not files:
        raise ValueError(f"目录中没有 Excel 文件: {input_dir}")

    frames: list[pd.DataFrame] = []
    processed: list[str] = []
    skipped: list[str] = []

    for file_path in files:
        if not _file_has_data(file_path):
            skipped.append(file_path.name)
            logger.info("跳过无数据文件: %s", file_path.name)
            continue

        df = parse_tingsimple_export(file_path)
        if df.empty:
            skipped.append(file_path.name)
            logger.info("跳过空数据文件: %s", file_path.name)
            continue

        frames.append(df)
        processed.append(file_path.name)
        logger.info("已读取: %s (%d 行)", file_path.name, len(df))

    if not frames:
        raise ValueError("目录中没有可合并的有效数据文件")

    merged = pd.concat(frames, ignore_index=True)
    logger.info(
        "合并完成: %d 个文件, %d 行 (跳过 %d 个)",
        len(processed),
        len(merged),
        len(skipped),
    )
    return MergeResult(dataframe=merged, processed_files=processed, skipped_files=skipped)


def _read_export_sheet(file_path: Path) -> pd.DataFrame:
    suffix = file_path.suffix.lower()
    if suffix in EXCEL_SUFFIXES:
        df = pd.read_excel(file_path, skiprows=HEADER_ROW_OFFSET, header=0)
    elif suffix == ".csv":
        df = pd.read_csv(file_path, encoding="utf-8-sig", skiprows=HEADER_ROW_OFFSET)
    else:
        raise ValueError(f"不支持的文件格式: {suffix}")

    df.columns = [str(c).strip() for c in df.columns]
    return df


def _file_has_data(file_path: Path) -> bool:
    """根据汇总区「订单数量」判断文件是否有明细数据。"""
    try:
        summary = pd.read_excel(file_path, header=None, nrows=5)
    except Exception:
        return True

    for value in summary.iloc[:, 0].dropna().astype(str):
        match = ORDER_COUNT_PATTERN.search(value)
        if match and int(match.group(1)) > 0:
            return True
    return False


def _clean_data_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or NAME_COLUMN not in df.columns:
        return df.iloc[0:0].copy()

    name = df[NAME_COLUMN].astype(str).str.strip()
    valid = (
        df[NAME_COLUMN].notna()
        & (name != "")
        & (name != "nan")
        & ~name.str.contains(r"^-+$", regex=True)
        & ~name.str.contains("报表导出时间", regex=False)
    )
    return df.loc[valid].reset_index(drop=True)
