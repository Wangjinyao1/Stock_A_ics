# -*- coding: utf-8 -*-
"""
数据库持久化模块（规范要求）：
  - 表名使用项目名前缀：stock_a_calendar
  - 主键自增 ID，字段包含 created_at / updated_at
数据库不可用时只记录告警，不影响 ics 生成主流程。
"""
from datetime import date
from typing import Dict, Iterable, List, Optional, Tuple

import pymysql
from pymysql.cursors import DictCursor

import config

logger = None


def _get_logger():
    global logger
    if logger is None:
        from logger_setup import setup_logger
        logger = setup_logger()
    return logger


_DDL = f"""
CREATE TABLE IF NOT EXISTS `{config.DB_TABLE}` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键',
    `trade_date` DATE NOT NULL COMMENT '日期',
    `is_open` TINYINT NOT NULL DEFAULT 1 COMMENT '是否交易日：1=开盘，0=休市',
    `trade_year` SMALLINT NOT NULL COMMENT '所属年份',
    `source` VARCHAR(32) NOT NULL DEFAULT 'sse' COMMENT '数据来源',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_{config.DB_TABLE}_date` (`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='A股交易日历'
"""


def _connect():
    return pymysql.connect(cursorclass=DictCursor, **config.db_config)


def init_schema(conn) -> None:
    with conn.cursor() as cursor:
        cursor.execute(_DDL)
    conn.commit()


def upsert_days(
    conn,
    open_days: Iterable[date],
    closed_weekdays: Iterable[date],
    source: str = "sse",
) -> int:
    """写入/更新交易日与工作日休市日记录，返回写入行数。"""
    rows: List[Tuple] = []
    for d in open_days:
        rows.append((d, 1, d.year, source))
    for d in closed_weekdays:
        rows.append((d, 0, d.year, source))
    if not rows:
        return 0

    sql = f"""
        INSERT INTO `{config.DB_TABLE}`
            (trade_date, is_open, trade_year, source)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            is_open = VALUES(is_open),
            trade_year = VALUES(trade_year),
            source = VALUES(source),
            updated_at = CURRENT_TIMESTAMP
    """
    with conn.cursor() as cursor:
        cursor.executemany(sql, rows)
    conn.commit()
    return len(rows)


def fetch_summary(conn) -> Optional[List[dict]]:
    """按年份统计交易日/休市日数量。"""
    sql = f"""
        SELECT trade_year,
               SUM(is_open = 1) AS open_days,
               SUM(is_open = 0) AS closed_weekdays,
               MAX(updated_at)  AS updated_at
        FROM `{config.DB_TABLE}`
        GROUP BY trade_year
        ORDER BY trade_year
    """
    with conn.cursor() as cursor:
        cursor.execute(sql)
        return list(cursor.fetchall())


def persist(
    open_days: Iterable[date],
    closed_weekdays: Iterable[date],
    source: str = "sse",
) -> bool:
    """持久化到 MySQL；失败返回 False，不中断主流程。"""
    log = _get_logger()
    if not config.DB_ENABLED:
        log.info("数据库持久化已禁用（DB_ENABLED=0）")
        return False

    open_list = list(open_days)
    closed_list = list(closed_weekdays)
    conn = None
    try:
        conn = _connect()
        init_schema(conn)
        written = upsert_days(conn, open_list, closed_list, source=source)
        summary = fetch_summary(conn)
        log.info("数据库写入成功：%s 条记录，表 %s", written, config.DB_TABLE)
        for row in summary or []:
            log.info(
                "  DB %s 年：开盘 %s 天，工作日休市 %s 天（更新于 %s）",
                row["trade_year"], row["open_days"],
                row["closed_weekdays"], row["updated_at"],
            )
        return True
    except pymysql.MySQLError as exc:
        log.warning("数据库操作失败（不影响 ics 生成）：%s", exc)
        return False
    finally:
        if conn is not None:
            try:
                conn.close()
            except pymysql.MySQLError:
                pass
