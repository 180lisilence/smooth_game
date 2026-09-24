"""
日志系统：控制台 + 文件 + GUI 回调。
"""
import os
import sys
import logging
from datetime import datetime
from core.constants import LOGS_DIR, runtime_config_dir

_log_dir = None
_log_file = None
_gui_callback = None


def _ensure_log_dir():
    global _log_dir, _log_file
    if _log_dir:
        return
    base = runtime_config_dir()
    _log_dir = os.path.join(base, "logs")
    os.makedirs(_log_dir, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    _log_file = os.path.join(_log_dir, f"trainer_{date_str}.log")


def set_gui_callback(callback):
    """设置 GUI 日志回调（主线程安全由调用方保证）。"""
    global _gui_callback
    _gui_callback = callback


def _log(level, msg):
    _ensure_log_dir()
    timestamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] [{level}] {msg}"
    # 控制台
    try:
        print(line)
    except Exception:
        pass
    # 文件
    try:
        with open(_log_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    # GUI 回调
    if _gui_callback:
        try:
            _gui_callback(msg, level)
        except Exception:
            pass


def log_info(msg):
    _log("INFO", msg)


def log_success(msg):
    _log("SUCCESS", msg)


def log_warning(msg):
    _log("WARNING", msg)


def log_error(msg):
    _log("ERROR", msg)


def log_debug(msg):
    _log("DEBUG", msg)
