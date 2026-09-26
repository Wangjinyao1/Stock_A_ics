# -*- coding: utf-8 -*-
"""
Stock_A_ics 主入口：中国股市开盘日历生成器。

流程：
  1. 抓取上交所休市安排页面并解析（失败时使用内置兜底数据）；
  2. 按规则计算交易日（周末不开市 + 节假日休市）；
  3. 持久化到 MySQL 表 stock_a_calendar；
  4. 生成可发布的 ics 文件（calendar/stock_a_open.ics、calendar/stock_a_closed.ics）。

用法：
  python main.py                 # 在线抓取 + 生成
  python main.py --offline       # 仅使用内置兜底数据
  python main.py --no-db         # 跳过数据库持久化
  python main.py --year-from 2026 --year-to 2028
"""
import argparse
import sys
from datetime import date

import config
import db
import ics_generator
import sse_fetcher
import trading_calendar
from logger_setup import setup_logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成中国股市开盘日历 ics 文件")
    parser.add_argument("--offline", action="store_true", help="不访问网络，仅使用内置兜底数据")
    parser.add_argument("--no-db", action="store_true", help="跳过数据库持久化")
    parser.add_argument("--year-from", type=int, default=None, help="起始年份（默认取 config）")
    parser.add_argument("--year-to", type=int, default=None, help="结束年份（默认取 config）")
    return parser.parse_args()


def main() -> int:
    log = setup_logger()
    args = parse_args()
    year_from, year_to = trading_calendar.resolve_years(args.year_from, args.year_to)

    log.info("=" * 60)
    log.info("Stock_A_ics 启动：生成 %s ~ %s 年 A股日历", year_from, year_to)

    # 1. 获取休市数据（线上优先，兜底）
    holidays = sse_fetcher.get_holidays(offline=args.offline)
    if not holidays:
        log.error("没有任何休市数据，终止")
        return 1

    # 2. 计算交易日
    open_days, closed_weekdays, skipped = trading_calendar.build_trading_days(
        year_from, year_to, holidays
    )
    if skipped:
        log.warning(
            "以下年份上交所尚未公布休市安排，已跳过：%s（公布后重新运行即可补充）",
            "、".join(map(str, skipped)),
        )
    if not open_days:
        log.error("计算结果为空，终止")
        return 1

    # 3. 数据持久化
    if not args.no_db:
        db.persist(open_days, closed_weekdays, source="sse")

    # 4. 生成 ics 文件
    open_count = ics_generator.generate_open_ics(open_days)
    closed_count = ics_generator.generate_closed_ics(closed_weekdays)
    log.info("生成完成：%s（交易日 %d 个）", config.OPEN_ICS_FILE.name, open_count)
    log.info("生成完成：%s（工作日休市 %d 个）", config.CLOSED_ICS_FILE.name, closed_count)

    # 5. 汇总统计
    years = sorted({d.year for d in open_days})
    for y in years:
        y_open = sum(1 for d in open_days if d.year == y)
        y_closed = sum(1 for d in closed_weekdays if d.year == y)
        log.info("  %d 年：交易日 %d 天，工作日休市 %d 天", y, y_open, y_closed)

    first, last = min(open_days), max(open_days)
    log.info("覆盖区间：%s ~ %s", first.isoformat(), last.isoformat())
    log.info("订阅地址（README 中已列出）：")
    log.info("  jsDelivr : %s/%s", config.JSDELIVR_SUBSCRIBE_BASE, config.OPEN_ICS_FILE.name)
    log.info("  GitHub   : %s/%s", config.RAW_SUBSCRIBE_BASE, config.OPEN_ICS_FILE.name)
    log.info("Stock_A_ics 运行结束")
    return 0


if __name__ == "__main__":
    sys.exit(main())
