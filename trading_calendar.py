# -*- coding: utf-8 -*-
"""
交易日历计算规则（中国 A 股）：
  1. 周末（周六、周日）不开市 —— 即使因节假日调休补班，周末也休市；
  2. 上交所公布的年度休市安排中的日期不开市（含其中的周末，规则 1 已覆盖）；
  3. 其余工作日（周一至周五）为交易日（开盘日）。
"""
from datetime import date
from typing import Dict, Iterable, List, Set, Tuple

import config


def build_trading_days(
    year_from: int,
    year_to: int,
    holidays_by_year: Dict[int, Set[date]],
) -> Tuple[List[date], List[date], List[int]]:
    """
    计算交易日与节假日休市日。

    返回：
        open_days        交易日（开盘日）列表
        closed_weekdays  仅工作日的休市日列表（周末不重复列出）
        skipped_years    因缺少休市安排数据而跳过的年份
    """
    open_days: List[date] = []
    closed_weekdays: List[date] = []
    skipped_years: List[int] = []

    for year in range(year_from, year_to + 1):
        holidays = holidays_by_year.get(year)
        if not holidays:
            skipped_years.append(year)
            continue
        d = date(year, 1, 1)
        while d.year == year:
            if d.weekday() >= 5:          # 周末不开市（规则 1）
                pass
            elif d in holidays:           # 节假日休市（规则 2）
                closed_weekdays.append(d)
            else:                         # 交易日（规则 3）
                open_days.append(d)
            d = date.fromordinal(d.toordinal() + 1)

    return open_days, closed_weekdays, skipped_years


def iter_year_ranges(days: Iterable[date]) -> List[Tuple[date, date]]:
    """把连续日期合并为区间（供调试/统计使用）。"""
    days = sorted(days)
    ranges: List[Tuple[date, date]] = []
    for d in days:
        if ranges and (d.toordinal() - ranges[-1][1].toordinal()) == 1:
            ranges[-1] = (ranges[-1][0], d)
        else:
            ranges.append((d, d))
    return ranges


def resolve_years(year_from: int | None, year_to: int | None) -> Tuple[int, int]:
    """解析生成年份范围（命令行参数优先，其次 .env，最后默认值）。"""
    y_from = year_from if year_from is not None else config.YEAR_FROM
    y_to = year_to if year_to is not None else config.YEAR_TO
    if y_to < y_from:
        y_to = y_from
    return y_from, y_to
