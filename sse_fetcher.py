# -*- coding: utf-8 -*-
"""
上交所休市安排数据抓取与解析。

数据来源：上海证券交易所 休市安排
        https://www.sse.com.cn/disclosure/dealinstruc/closed/

页面以自然语言描述年度休市区间，例如：
    2026年休市安排
    春节：2月15日（星期日）至2月23日（星期一）休市，2月24日（星期二）起照常开市。
解析策略：
    1. 定位“XXXX年休市安排”标题，作为后续日期区间的年份上下文；
    2. 正则提取“X月X日（星期X）至X月X日（星期X）休市”区间；
    3. 清除已匹配区间后再提取单日休市“X月X日（星期X）休市”；
    4. 网络失败或解析结果为空时，回退到 data/sse_closed_fallback.json。
"""
import html as html_lib
import json
import re
from datetime import date, timedelta
from typing import Dict, Optional, Set

import requests

import config

logger = None


def _get_logger():
    global logger
    if logger is None:
        from logger_setup import setup_logger
        logger = setup_logger()
    return logger


# 年份标题：如“2026年休市安排”
_YEAR_HEADING_RE = re.compile(r"(\d{4})年休市安排")
# 兜底年份标题：如“2026年”（页面结构变化时使用）
_YEAR_FALLBACK_RE = re.compile(r"(\d{4})年")
# 休市区间：如“2月15日（星期日）至2月23日（星期一）休市”
_RANGE_RE = re.compile(
    r"(\d{1,2})月(\d{1,2})日(?:（星期[一二三四五六日]）)?\s*至\s*"
    r"(\d{1,2})月(\d{1,2})日(?:（星期[一二三四五六日]）)?休市"
)
# 单日休市：如“1月1日（星期四）休市”
_SINGLE_RE = re.compile(r"(\d{1,2})月(\d{1,2})日(?:（星期[一二三四五六日]）)?休市")


def fetch_sse_page() -> str:
    """抓取上交所休市安排页面，原始 HTML 备份到 .temp/temp_sse_closed.html。"""
    log = _get_logger()
    resp = requests.get(
        config.SSE_CLOSED_URL,
        headers=config.REQUEST_HEADERS,
        timeout=config.REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    html_text = resp.text

    try:
        config.SSE_RAW_HTML_FILE.write_text(html_text, encoding="utf-8")
        log.info("原始页面已备份到 %s", config.SSE_RAW_HTML_FILE.name)
    except OSError as exc:
        log.warning("原始页面备份失败：%s", exc)
    return html_text


def html_to_text(html_text: str) -> str:
    """去除脚本/样式与标签，得到可解析的纯文本。"""
    text = re.sub(r"(?is)<script.*?</script>", " ", html_text)
    text = re.sub(r"(?is)<style.*?</style>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|tr|td|th|li|h\d)>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html_lib.unescape(text)
    text = text.replace("\u3000", " ")
    # 压缩空白，保留换行
    text = re.sub(r"[ \t\xa0]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text


def _year_for_position(position: int, headings, text: str) -> Optional[int]:
    """取匹配位置之前最近的年份标题。"""
    year = None
    for pos, y in headings:
        if pos < position:
            year = y
        else:
            break
    if year is None:
        m = _YEAR_FALLBACK_RE.search(text, 0, position)
        if m:
            year = int(m.group(1))
    return year


def _make_date(year: int, month: int, day: int) -> Optional[date]:
    try:
        return date(year, month, day)
    except ValueError:
        _get_logger().warning("非法日期被忽略：%d-%02d-%02d", year, month, day)
        return None


def parse_closed_text(text: str) -> Dict[int, Set[date]]:
    """从页面文本解析各年度休市日期，返回 {年份: {date, ...}}。"""
    log = _get_logger()
    result: Dict[int, Set[date]] = {}

    headings = [(m.start(), int(m.group(1))) for m in _YEAR_HEADING_RE.finditer(text)]

    # 1) 先提取休市区间
    work_text = list(text)
    for m in _RANGE_RE.finditer(text):
        year = _year_for_position(m.start(), headings, text)
        if year is None:
            log.warning("无法确定年份，跳过区间：%s", m.group(0)[:40])
            continue
        sm, sd, em, ed = (int(m.group(i)) for i in range(1, 5))
        start = _make_date(year, sm, sd)
        end = _make_date(year, em, ed)
        if start is None or end is None:
            continue
        if end < start:  # 跨年区间（如 12月30日至1月2日）
            end = _make_date(year + 1, em, ed)
            if end is None:
                continue
        days = result.setdefault(year, set())
        cur = start
        while cur <= end:
            days.add(cur)
            cur += timedelta(days=1)
        # 标记已处理，避免单日正则重复匹配
        for i in range(m.start(), m.end()):
            work_text[i] = " "

    log.info("解析到休市区间 %d 段", len(list(_RANGE_RE.finditer(text))))

    # 2) 再提取单日休市（已处理的区间已置空）
    remaining = "".join(work_text)
    single_count = 0
    for m in _SINGLE_RE.finditer(remaining):
        year = _year_for_position(m.start(), headings, remaining)
        if year is None:
            continue
        d = _make_date(year, int(m.group(1)), int(m.group(2)))
        if d is None:
            continue
        result.setdefault(year, set()).add(d)
        single_count += 1
    log.info("解析到单日休市 %d 天", single_count)

    for year in sorted(result):
        log.info("解析到 %d 年休市 %d 天（含周末）", year, len(result[year]))
    return result


def load_local_fallback() -> Dict[int, Set[date]]:
    """读取内置兜底数据 data/sse_closed_fallback.json。"""
    log = _get_logger()
    path = config.HOLIDAY_FALLBACK_FILE
    if not path.exists():
        log.warning("兜底数据文件不存在：%s", path)
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        result: Dict[int, Set[date]] = {}
        for year_str, day_list in raw.get("holidays", {}).items():
            days = set()
            for s in day_list:
                try:
                    days.add(date.fromisoformat(s))
                except ValueError:
                    log.warning("兜底数据存在非法日期：%s", s)
            if days:
                result[int(year_str)] = days
        log.info("兜底数据：%s", ", ".join(
            f"{y}年{len(d)}天" for y, d in sorted(result.items())) or "无")
        return result
    except (OSError, json.JSONDecodeError) as exc:
        log.error("读取兜底数据失败：%s", exc)
        return {}


def get_holidays(offline: bool = False) -> Dict[int, Set[date]]:
    """
    获取各年度休市日期：优先线上解析，失败则使用兜底数据；
    两者按年份合并（线上数据优先覆盖同一年份）。
    """
    log = _get_logger()
    fallback = load_local_fallback()
    if offline:
        log.info("离线模式：跳过网络抓取，仅使用内置兜底数据")
        return fallback

    parsed: Dict[int, Set[date]] = {}
    try:
        html_text = fetch_sse_page()
        parsed = parse_closed_text(html_to_text(html_text))
        if not parsed:
            log.warning("页面解析结果为空，可能是页面结构变化，使用兜底数据")
    except requests.RequestException as exc:
        log.warning("抓取上交所页面失败（%s），使用兜底数据", exc)
    except Exception as exc:  # noqa: BLE001 - 解析异常不应中断主流程
        log.warning("解析上交所页面异常（%s），使用兜底数据", exc)

    merged = dict(fallback)
    merged.update(parsed)
    if not merged:
        log.error("线上与兜底数据均为空，无法生成日历")
    return merged
