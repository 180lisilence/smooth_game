"""
配置管理：加载/保存/深合并。
配置文件保存在程序目录下的 config.json（不写C盘）。
"""
import os
import json
import copy
from core.constants import runtime_config_dir, DEFAULT_GAME_PATH, STEAM_APP_ID

CONFIG_PATH = os.path.join(runtime_config_dir(), "config.json")

DEFAULT_CONFIG = {
    "game_path": DEFAULT_GAME_PATH,
    "game_exe": r"bin64\BalladsOfHongye.exe",
    "steam_app_id": STEAM_APP_ID,
    "dll_path": "",
    "theme": "light",
    "window": {
        "width": 1000,
        "height": 680,
        "x": None,
        "y": None,
    },
    "auto_detect_game": True,
    "hotkeys_enabled": True,
    "plugins": {
        "enabled": {},
        "settings": {},
    },
    "hotkeys": {
        "money": "Ctrl+F1",
        "food": "Ctrl+F2",
        "water": "Ctrl+F3",
        "cloth": "Ctrl+F4",
        "wood": "Ctrl+F5",
        "mineral": "Ctrl+F6",
        "salt": "Ctrl+F7",
        "wine": "Ctrl+F8",
        "essence": "Ctrl+F11",
        "fame": "Ctrl+F9",
        "happiness": "Ctrl+F12",
        "creative_mode": "Ctrl+F10",
    },
}


def _deep_merge(base, override):
    """深合并：override 覆盖 base，缺失键用 base 补全。"""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_config():
    """加载配置，不存在则返回默认配置。"""
    if not os.path.exists(CONFIG_PATH):
        return copy.deepcopy(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            user_cfg = json.load(f)
        return _deep_merge(DEFAULT_CONFIG, user_cfg)
    except Exception as e:
        from core.logger import log_error
        log_error(f"配置文件加载失败，使用默认配置: {e}")
        return copy.deepcopy(DEFAULT_CONFIG)


def save_config(config):
    """保存配置到文件。"""
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        from core.logger import log_error
        log_error(f"配置保存失败: {e}")
        return False


def get_plugin_enabled(config, plugin_id, default=True):
    """获取插件是否启用。"""
    return config.get("plugins", {}).get("enabled", {}).get(plugin_id, default)


def set_plugin_enabled(config, plugin_id, enabled):
    """设置插件启用状态。"""
    if "plugins" not in config:
        config["plugins"] = {}
    if "enabled" not in config["plugins"]:
        config["plugins"]["enabled"] = {}
    config["plugins"]["enabled"][plugin_id] = enabled


def get_plugin_settings(config, plugin_id):
    """获取插件的自定义设置。"""
    return config.get("plugins", {}).get("settings", {}).get(plugin_id, {})


def set_plugin_settings(config, plugin_id, settings):
    """设置插件的自定义设置。"""
    if "plugins" not in config:
        config["plugins"] = {}
    if "settings" not in config["plugins"]:
        config["plugins"]["settings"] = {}
    config["plugins"]["settings"][plugin_id] = settings
