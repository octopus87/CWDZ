from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def reconcile(df: pd.DataFrame) -> pd.DataFrame:
    """执行对账整理逻辑。

    TODO: 按财务对账规则补充：去重、汇总、差异标记等。
    """
    logger.info("开始对账整理，原始行数: %d", len(df))
    result = df.copy()

    # 占位：去除完全重复行
    result = result.drop_duplicates()

    logger.info("整理完成，输出行数: %d", len(result))
    return result


def save_reconciled(df: pd.DataFrame, output_path: Path) -> Path:
    """将对账结果保存为 Excel。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(output_path, index=False)
    logger.info("对账结果已保存: %s", output_path)
    return output_path
