# -*- coding: utf-8 -*-
"""
Stock_A_ics 全局配置文件
所有配置项集中写入本文件，敏感信息从 .env 环境变量读取。
"""
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------- 基础路径
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

TEMP_DIR = BASE_DIR / ".temp"          # 临时文件目录（文件名必须以 temp_ 开头）
DATA_DIR = BASE_DIR / "data"           # 内置休市数据（兜底）
CALENDAR_DIR = BASE_DIR / "calendar"   # 生成的 ics 文件（发布到 GitHub 供订阅）
LOG_FILE = BASE_DIR / "run_log.log"    # 运行日志（单文件，最大 3M）

for _d in (TEMP_DIR, DATA_DIR, CALENDAR_DIR):
    _d.mkdir(exist_ok=True)

# ---------------------------------------------------------------- 日历配置
CALENDAR_NAME_OPEN = "A股开盘日历"
CALENDAR_NAME_CLOSED = "A股休市日历"
CALENDAR_PRODID = "-//Stock_A_ics//China Stock Market Calendar//CN"
CALENDAR_TZ = "Asia/Shanghai"

OPEN_ICS_FILE = CALENDAR_DIR / "stock_a_open.ics"      # 开盘日历（主订阅文件）
CLOSED_ICS_FILE = CALENDAR_DIR / "stock_a_closed.ics"  # 休市日历（附加文件）

# 生成年份范围（仅生成已有休市安排数据的年份，上交所公布新年度安排后自动扩展）
_YEAR_NOW = datetime.now().year
YEAR_FROM = int(os.getenv("YEAR_FROM", _YEAR_NOW))
YEAR_TO = int(os.getenv("YEAR_TO", _YEAR_NOW + 2))

# ---------------------------------------------------------------- 数据源
SSE_CLOSED_URL = "https://www.sse.com.cn/disclosure/dealinstruc/closed/"
REQUEST_TIMEOUT = 20
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://www.sse.com.cn/",
}
# 原始网页备份到临时目录（文件名带 temp_ 前缀）
SSE_RAW_HTML_FILE = TEMP_DIR / "temp_sse_closed.html"
# 内置兜底数据（网络不可用或页面改版时使用）
HOLIDAY_FALLBACK_FILE = DATA_DIR / "sse_closed_fallback.json"

# ---------------------------------------------------------------- GitHub 订阅地址
# 发布到 GitHub 后，订阅地址由 GITHUB_REPO 拼接而成（README 中展示）
GITHUB_REPO = os.getenv("GITHUB_REPO", "Wangjinyao1/Stock_A_ics")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")
RAW_SUBSCRIBE_BASE = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/calendar"
JSDELIVR_SUBSCRIBE_BASE = f"https://cdn.jsdelivr.net/gh/{GITHUB_REPO}@{GITHUB_BRANCH}/calendar"

# ---------------------------------------------------------------- 数据库配置
# 规范要求：业务数据持久化到 MySQL，表名使用项目名前缀 stock_a_
db_config = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "your_db_credential"),
    "password": os.getenv("DB_PASSWORD", "your_db_credential"),
    "database": os.getenv("DB_NAME", "your_db_credential"),
    "charset": "utf8mb4",
    "connect_timeout": 10,
    "read_timeout": 20,
    "write_timeout": 20,
}

DB_TABLE = "stock_a_calendar"          # 项目名前缀 stock_a_
DB_ENABLED = os.getenv("DB_ENABLED", "1") == "1"

# ---------------------------------------------------------------- 日志配置
LOG_MAX_BYTES = 3 * 1024 * 1024        # run_log.log 最大 3M（单文件，超出直接截断）
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
