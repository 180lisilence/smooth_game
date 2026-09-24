"""
smooth_game - 全局常量

集中存放跨模块共享的常量，杜绝散落各处的硬编码。
注意：本模块不得 import 项目内其它模块（避免循环依赖）。
"""
import os
import sys

# ---------------------------------------------------------------- 版本（唯一版本源）
APP_NAME = "smooth_game"
APP_VERSION = "0.1.1"
APP_DISPLAY_NAME = "平野孤鸿 插件化修改器"

# ---------------------------------------------------------------- 游戏环境
STEAM_APP_ID = "2656540"
STEAM_RUN_URL = "steam://run/" + STEAM_APP_ID
DEFAULT_GAME_PATH = r"D:\steam\steamapps\common\BalladsOfHongye_CN"
GAME_EXE_REL = r"bin64\BalladsOfHongye.exe"
SIM_COMMON_REL = "sim_common"

# ---------------------------------------------------------------- 项目路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
PLUGINS_DIR = os.path.join(PROJECT_ROOT, "plugins")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")


def runtime_config_dir():
    """运行期可写目录：统一用程序所在目录，不写C盘。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return PROJECT_ROOT


# ---------------------------------------------------------------- 游戏数值
BOOM_MAX_LEVEL = 14
ACHIEVEMENT_ID_SCAN_LIMIT = 400
MAX_SKIP_DAYS = 3600

# 时间系统
DAY_TIME_REAL = 5
DAY_TICK_COUNT = 2
TICK_DELTA_BASE = float(DAY_TIME_REAL) / float(DAY_TICK_COUNT)
TIME_SPEED_MIN = 0.05
TIME_SPEED_MAX = 60.0

# 历法
DAYS_PER_MONTH = 30
MONTHS_PER_YEAR = 12
DAYS_PER_YEAR = DAYS_PER_MONTH * MONTHS_PER_YEAR

# 一键增加资源默认数值
RESOURCE_ADD_AMOUNT = 1000000
FAME_ADD_AMOUNT = 10000

# ---------------------------------------------------------------- 执行
LUA_TIMEOUT = 5.0
LUA_TIMEOUT_LONG = 10.0

# ---------------------------------------------------------------- 插件
PLUGIN_META_FILE = "plugin.json"
PLUGIN_ENTRY_MODULE = "main"
PLUGIN_ENTRY_CLASS = "Plugin"
