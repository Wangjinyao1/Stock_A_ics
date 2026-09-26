# -*- coding: utf-8 -*-
"""
日志模块：控制台 + run_log.log（单文件，最大 3M，超出直接截断，不产生轮转备份文件）。
"""
import logging
from logging.handlers import RotatingFileHandler

import config


class SingleFileRotatingHandler(RotatingFileHandler):
    """超过 maxBytes 时直接截断原文件，保证 run_log.log 始终只有一个且 <= 3M。"""

    def _doRollover(self) -> None:
        if self.stream:
            self.stream.close()
            self.stream = None
        # 直接清空，而非轮转出 .1 文件（规范：日志只需一个文件）
        with open(self.baseFilename, "w", encoding="utf-8", errors="replace"):
            pass
        self.stream = self._open()


def setup_logger(name: str = "stock_a_ics") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:  # 幂等，避免重复添加 handler
        return logger

    logger.setLevel(getattr(logging, config.LOG_LEVEL, logging.INFO))
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台输出
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    # 本地运行日志（单文件最大 3M）
    try:
        file_handler = SingleFileRotatingHandler(
            filename=str(config.LOG_FILE),
            maxBytes=config.LOG_MAX_BYTES,
            backupCount=0,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError as exc:  # 日志文件不可写时不影响主流程
        logger.warning("无法创建日志文件 %s：%s", config.LOG_FILE, exc)

    return logger
