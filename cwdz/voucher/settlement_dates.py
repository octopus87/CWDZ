"""停简单到账推算：工作日 T+1（含中国法定节假日）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from cwdz.voucher.chinese_workday import is_workday


@dataclass(frozen=True)
class UnsettledRangeResult:
    dates: tuple[date, ...]
    period_start: date
    period_end: date
    last_business_day: date

    @property
    def start(self) -> date | None:
        return self.dates[0] if self.dates else None

    @property
    def end(self) -> date | None:
        return self.dates[-1] if self.dates else None


def is_business_day(value: date) -> bool:
    """工作日：排除周末及国家法定节假日（含调休上班日）。"""
    return is_workday(value)


def parse_period_range(period: str) -> tuple[date, date]:
    text = period.strip().replace("/", "-").replace(".", "-")
    parts = text.split("-")
    if len(parts) < 2:
        raise ValueError(f"账期格式无效: {period}")
    year = int(parts[0])
    month = int(parts[1])
    if month < 1 or month > 12:
        raise ValueError(f"账期月份无效: {period}")
    period_start = date(year, month, 1)
    if month == 12:
        period_end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        period_end = date(year, month + 1, 1) - timedelta(days=1)
    return period_start, period_end


def last_business_day_of_month(period_start: date, period_end: date) -> date:
    """账期月份内最后一个工作日。"""
    current = period_end
    while current >= period_start:
        if is_business_day(current):
            return current
        current -= timedelta(days=1)
    raise ValueError("账期内未找到工作日")


def compute_unsettled_dates(period: str) -> UnsettledRangeResult:
    """推算未到账期间：月末最后一个工作日 ~ 月末最后一天（结算 T+1）。"""
    period_start, period_end = parse_period_range(period)
    last_workday = last_business_day_of_month(period_start, period_end)
    unsettled: list[date] = []
    current = last_workday
    while current <= period_end:
        unsettled.append(current)
        current += timedelta(days=1)
    return UnsettledRangeResult(
        dates=tuple(unsettled),
        period_start=period_start,
        period_end=period_end,
        last_business_day=last_workday,
    )


def format_unsettled_summary(result: UnsettledRangeResult) -> str:
    last = _display_date(result.last_business_day)
    if not result.dates:
        return f"月末最后工作日 {last}，无未到账期间"
    if len(result.dates) == 1:
        return f"月末最后工作日 {last}，未到账日期：{_display_date(result.start)}"
    if len(result.dates) <= 12:
        return (
            f"月末最后工作日 {last}，未到账日期："
            + "、".join(_display_date(d) for d in result.dates)
        )
    return (
        f"月末最后工作日 {last}，未到账日期："
        f"{_display_date(result.start)} ~ {_display_date(result.end)}"
        f"（共 {len(result.dates)} 天）"
    )


def _display_date(value: date) -> str:
    return f"{value.month}/{value.day}"
