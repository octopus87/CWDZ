from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def validate(df: pd.DataFrame, required_columns: list[str] | None = None) -> list[str]:
    """校验对账数据，返回错误信息列表（空列表表示通过）。"""
    errors: list[str] = []

    if df.empty:
        errors.append("数据为空")
        return errors

    if required_columns:
        missing = [c for c in required_columns if c not in df.columns]
        if missing:
            errors.append(f"缺少必要列: {', '.join(missing)}")

    # 占位：检查金额列是否存在空值
    amount_cols = [c for c in df.columns if "金额" in str(c) or "amount" in str(c).lower()]
    for col in amount_cols:
        null_count = df[col].isna().sum()
        if null_count:
            errors.append(f"列「{col}」存在 {null_count} 个空值")

    if errors:
        logger.warning("数据校验未通过: %s", "; ".join(errors))
    else:
        logger.info("数据校验通过")

    return errors
