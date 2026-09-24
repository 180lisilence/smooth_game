"""
BasePlugin - 插件基类（A方案轻量级插件化的核心）。

所有插件必须继承此类并实现抽象方法。
插件管理器通过统一接口加载、排序、挂载 UI。

插件生命周期：
    扫描 → 读取 plugin.json → 动态导入 → 实例化 → on_load()
    → get_menu_items() 挂到中间列表
    → 用户点击 → build_ui() 构建右侧面板
    → 插件通过 self.execute_lua() 与游戏通信
    → 程序退出 → on_unload()
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable, Any


class MenuItem:
    """中间功能列表的菜单项。"""

    def __init__(self, item_id: str, label: str, description: str = "",
                 category: str = "", icon: str = ""):
        self.item_id = item_id
        self.label = label
        self.description = description
        self.category = category
        self.icon = icon

    def __repr__(self):
        return f"<MenuItem {self.item_id}: {self.label}>"


class BasePlugin(ABC):
    """
    插件基类。子类必须实现：
        - get_menu_items()  返回该插件提供的菜单项列表
        - build_ui(parent, item_id)  点击菜单项后构建右侧操作面板

    可选重写：
        - on_load()      插件加载时调用
        - on_unload()    插件卸载时调用
        - on_game_connected()   游戏连接成功时调用
        - on_game_disconnected() 游戏断开时调用
    """

    # ---- 元数据（子类可覆盖，或从 plugin.json 读取） ----
    plugin_id: str = ""
    name: str = ""
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    category: str = "功能"
    priority: int = 100  # 数字越小越靠前
    icon: str = ""

    def __init__(self):
        # 核心服务引用，由插件管理器注入
        self._core = None
        self._config = None
        self._plugin_settings = {}
        self._hotkeys: Dict[str, Callable] = {}
        self._loaded = False

    # ---- 核心服务注入（由插件管理器调用，插件不要重写） ----

    def _inject_core(self, core_services: dict):
        """注入核心服务。core_services 包含：
            execute_lua, get_game_status, log, config, register_hotkey,
            refresh_status, show_toast
        """
        self._core = core_services

    def _inject_config(self, config: dict, plugin_settings: dict):
        """注入全局配置和插件专属设置。"""
        self._config = config
        self._plugin_settings = plugin_settings

    # ---- 插件可调用的核心服务 ----

    def execute_lua(self, code: str, timeout: float = 5.0) -> tuple:
        """执行 Lua 代码。返回 (success, result)。"""
        if self._core and "execute_lua" in self._core:
            return self._core["execute_lua"](code, timeout)
        return False, "核心服务未注入"

    def get_game_status(self) -> dict:
        """获取当前游戏状态快照。"""
        if self._core and "get_game_status" in self._core:
            return self._core["get_game_status"]()
        return {}

    def log(self, msg: str, level: str = "INFO"):
        """写日志。"""
        if self._core and "log" in self._core:
            self._core["log"](msg, level)

    def get_config(self) -> dict:
        """获取全局配置（只读，修改请用 save_config）。"""
        return self._config or {}

    def get_plugin_settings(self) -> dict:
        """获取插件专属设置。"""
        return self._plugin_settings

    def save_plugin_settings(self, settings: dict):
        """保存插件专属设置（会触发全局配置保存）。"""
        self._plugin_settings = settings
        if self._core and "save_plugin_settings" in self._core:
            self._core["save_plugin_settings"](self.plugin_id, settings)

    def register_hotkey(self, hotkey: str, callback: Callable):
        """注册全局热键。"""
        self._hotkeys[hotkey] = callback
        if self._core and "register_hotkey" in self._core:
            self._core["register_hotkey"](hotkey, callback, self.plugin_id)

    def unregister_hotkey(self, hotkey: str):
        """注销热键。"""
        self._hotkeys.pop(hotkey, None)
        if self._core and "unregister_hotkey" in self._core:
            self._core["unregister_hotkey"](hotkey, self.plugin_id)

    def show_toast(self, msg: str, duration: int = 2000):
        """显示轻量通知。"""
        if self._core and "show_toast" in self._core:
            self._core["show_toast"](msg, duration)

    def refresh_status(self):
        """请求刷新游戏状态。"""
        if self._core and "refresh_status" in self._core:
            self._core["refresh_status"]()

    # ---- 生命周期（子类可选重写） ----

    def on_load(self):
        """插件加载时调用。可在此初始化资源、读取设置。"""
        pass

    def on_unload(self):
        """插件卸载时调用。可在此清理资源、保存设置。"""
        pass

    def on_game_connected(self):
        """游戏连接成功（DLL注入完成）时调用。"""
        pass

    def on_game_disconnected(self):
        """游戏断开时调用。"""
        pass

    # ---- 抽象方法（子类必须实现） ----

    @abstractmethod
    def get_menu_items(self) -> List[MenuItem]:
        """
        返回该插件提供的菜单项列表，将显示在中间功能列表中。
        每个 MenuItem 对应一个可点击的功能入口。
        """
        ...

    @abstractmethod
    def build_ui(self, parent, item_id: str):
        """
        用户点击菜单项后，在右侧操作面板构建 UI。
        parent: tkinter 容器（右侧面板的 Frame）
        item_id: 被点击的 MenuItem.item_id
        注意：每次调用前 parent 会被清空，插件只需往里面 pack/grid 控件。
        """
        ...
