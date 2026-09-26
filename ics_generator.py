# -*- coding: utf-8 -*-
"""
ICS（iCalendar）文件生成。

遵循 RFC 5545：
  - 行结束符为 CRLF；
  - 每行（按 UTF-8 字节计）不超过 75 octets，超出需折行（空格续行）；
  - 文本值需转义反斜杠、分号、逗号与换行。
生成两个日历：
  - stock_a_open.ics   A股开盘日历（交易日，主订阅文件）
  - stock_a_closed.ics A股休市日历（工作日节假日）
"""
from datetime import date, datetime, timedelta, timezone
from typing import Iterable, List

import config

CRLF = "\r\n"
UID_DOMAIN = "stock-a-ics"
MAX_OCTETS = 75


def _escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _fold(line: str) -> List[str]:
    """按 75 octets（UTF-8 字节）折行，续行以单个空格开头。"""
    encoded = line.encode("utf-8")
    if len(encoded) <= MAX_OCTETS:
        return [line]

    pieces: List[str] = []
    current = ""
    current_bytes = 0
    limit = MAX_OCTETS - 1  # 续行前导空格占用 1 字节
    for ch in line:
        ch_len = len(ch.encode("utf-8"))
        budget = limit if pieces else MAX_OCTETS
        if current_bytes + ch_len > budget:
            pieces.append(current)
            current = " " + ch
            current_bytes = 1 + ch_len
        else:
            current += ch
            current_bytes += ch_len
    if current:
        pieces.append(current)
    return pieces


def _dtstamp(now: datetime) -> str:
    return now.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _date_str(d: date) -> str:
    return d.strftime("%Y%m%d")


def _build_event(
    day: date,
    summary: str,
    description: str,
    categories: str,
    uid_prefix: str,
    dtstamp: str,
) -> List[str]:
    next_day = day + timedelta(days=1)
    return [
        "BEGIN:VEVENT",
        f"UID:{uid_prefix}-{_date_str(day)}@{UID_DOMAIN}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART;VALUE=DATE:{_date_str(day)}",
        f"DTEND;VALUE=DATE:{_date_str(next_day)}",
        f"SUMMARY:{_escape(summary)}",
        f"DESCRIPTION:{_escape(description)}",
        f"CATEGORIES:{_escape(categories)}",
        "TRANSP:TRANSPARENT",
        "STATUS:CONFIRMED",
        "SEQUENCE:0",
        "END:VEVENT",
    ]


def _build_calendar(name: str, description: str, events: List[List[str]], dtstamp: str) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{config.CALENDAR_PRODID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape(name)}",
        f"X-WR-CALDESC:{_escape(description)}",
        f"X-WR-TIMEZONE:{config.CALENDAR_TZ}",
        "X-PUBLISHED-TTL:P1W",
    ]
    for event in events:
        lines.extend(event)
    lines.append("END:VCALENDAR")

    folded: List[str] = []
    for line in lines:
        folded.extend(_fold(line))
    return CRLF.join(folded) + CRLF


def _write(path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="")


def generate_open_ics(open_days: Iterable[date]) -> int:
    """生成开盘日历，返回事件数。"""
    now = datetime.now(timezone.utc)
    desc = (
        "中国 A 股交易日（开盘日）。数据来源：上海证券交易所休市安排 "
        f"{config.SSE_CLOSED_URL} ；周末及法定节假日休市。由 Stock_A_ics 自动生成。"
    )
    events = [
        _build_event(d, "A股开盘", desc, "开盘,交易日", "stocka-open", _dtstamp(now))
        for d in sorted(open_days)
    ]
    content = _build_calendar(config.CALENDAR_NAME_OPEN, desc, events, _dtstamp(now))
    _write(config.OPEN_ICS_FILE, content)
    return len(events)


def generate_closed_ics(closed_days: Iterable[date]) -> int:
    """生成休市日历（仅工作日节假日），返回事件数。"""
    now = datetime.now(timezone.utc)
    desc = (
        "中国 A 股节假日休市（周末休市未列出）。数据来源：上海证券交易所休市安排 "
        f"{config.SSE_CLOSED_URL} 。由 Stock_A_ics 自动生成。"
    )
    events = [
        _build_event(d, "A股休市", desc, "休市,节假日", "stocka-closed", _dtstamp(now))
        for d in sorted(closed_days)
    ]
    content = _build_calendar(config.CALENDAR_NAME_CLOSED, desc, events, _dtstamp(now))
    _write(config.CLOSED_ICS_FILE, content)
    return len(events)
