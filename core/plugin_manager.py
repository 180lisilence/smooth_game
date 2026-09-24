"""
PluginManager - 插件管理器。

职责：
    1. 扫描 plugins/ 目录
    2. 读取每个插件的 plugin.json 元数据
    3. 动态导入 main.py，实例化 Plugin 类
    4. 注入核心服务和配置
    5. 按 priority 排序
    6. 管理启用/禁用状态
    7. 调用生命周期方法（on_load / on_unload / on_game_connected）

A方案不做沙箱、不做热更新，插件加载后常驻直到程序退出。
"""
import os
import sys
import json
import importlib
import importlib.util
from typing import Dict, List, Optional, Callable

from core.constants import PLUGINS_DIR, PLUGIN_META_FILE, PLUGIN_ENTRY_MODULE, PLUGIN_ENTRY_CLASS
from core.base_plugin import BasePlugin, MenuItem
from core.logger import log_info, log_error, log_warning
from core.config import get_plugin_enabled, set_plugin_enabled, get_plugin_settings


class PluginManager:
    """插件管理器。"""

    def __init__(self, config: dict):
        self.config = config
        self.plugins: Dict[str, BasePlugin] = {}
        self.plugin_meta: Dict[str, dict] = {}
        self._core_services: dict = {}
        self._loaded = False

    # ---- 核心服务注入 ----

    def set_core_services(self, services: dict):
        """设置核心服务字典，将在加载插件时注入到每个插件。"""
        self._core_services = services

    # ---- 扫描与加载 ----

    def scan_plugins(self) -> List[str]:
        """扫描 plugins/ 目录，返回找到的插件目录名列表。"""
        if not os.path.isdir(PLUGINS_DIR):
            log_warning(f"插件目录不存在: {PLUGINS_DIR}")
            return []
        plugin_dirs = []
        for name in os.listdir(PLUGINS_DIR):
            full_path = os.path.join(PLUGINS_DIR, name)
            if not os.path.isdir(full_path):
                continue
            meta_path = os.path.join(full_path, PLUGIN_META_FILE)
            main_path = os.path.join(full_path, f"{PLUGIN_ENTRY_MODULE}.py")
            if os.path.exists(meta_path) and os.path.exists(main_path):
                plugin_dirs.append(name)
            else:
                log_warning(f"跳过无效插件目录: {name}（缺少 plugin.json 或 main.py）")
        return plugin_dirs

    def _load_plugin_meta(self, plugin_dir: str) -> Optional[dict]:
        """读取插件的 plugin.json。"""
        meta_path = os.path.join(PLUGINS_DIR, plugin_dir, PLUGIN_META_FILE)
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            # 补全缺省字段
            meta.setdefault("plugin_id", plugin_dir)
            meta.setdefault("name", plugin_dir)
            meta.setdefault("version", "1.0.0")
            meta.setdefault("author", "")
            meta.setdefault("description", "")
            meta.setdefault("category", "功能")
            meta.setdefault("priority", 100)
            meta.setdefault("icon", "")
            meta.setdefault("enabled_by_default", True)
            return meta
        except Exception as e:
            log_error(f"读取插件元数据失败 [{plugin_dir}]: {e}")
            return None

    def _load_plugin_class(self, plugin_dir: str) -> Optional[type]:
        """动态导入插件的 main.py，返回 Plugin 类。"""
        main_path = os.path.join(PLUGINS_DIR, plugin_dir, f"{PLUGIN_ENTRY_MODULE}.py")
        module_name = f"plugins.{plugin_dir}.{PLUGIN_ENTRY_MODULE}"
        try:
            # 确保 plugins 包路径在 sys.path 中
            if PLUGINS_DIR not in sys.path:
                sys.path.insert(0, os.path.dirname(PLUGINS_DIR))
            spec = importlib.util.spec_from_file_location(module_name, main_path)
            if spec is None or spec.loader is None:
                log_error(f"无法创建模块规范: {main_path}")
                return None
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            plugin_class = getattr(module, PLUGIN_ENTRY_CLASS, None)
            if plugin_class is None:
                log_error(f"插件 [{plugin_dir}] 的 main.py 中未找到 {PLUGIN_ENTRY_CLASS} 类")
                return None
            if not issubclass(plugin_class, BasePlugin):
                log_error(f"插件 [{plugin_dir}] 的 {PLUGIN_ENTRY_CLASS} 类未继承 BasePlugin")
                return None
            return plugin_class
        except Exception as e:
            log_error(f"加载插件类失败 [{plugin_dir}]: {e}")
            import traceback
            traceback.print_exc()
            return None

    def load_all(self) -> int:
        """
        扫描并加载所有插件。返回成功加载的插件数量。
        流程：扫描 → 读元数据 → 检查启用状态 → 动态导入 → 实例化 → 注入服务 → on_load
        """
        if self._loaded:
            log_warning("插件已加载，跳过重复加载")
            return len(self.plugins)

        plugin_dirs = self.scan_plugins()
        log_info(f"扫描到 {len(plugin_dirs)} 个插件目录")

        loaded_count = 0
        for plugin_dir in plugin_dirs:
            # 1. 读元数据
            meta = self._load_plugin_meta(plugin_dir)
            if meta is None:
                continue
            plugin_id = meta["plugin_id"]
            self.plugin_meta[plugin_id] = meta

            # 2. 检查启用状态
            enabled = get_plugin_enabled(self.config, plugin_id, meta.get("enabled_by_default", True))
            if not enabled:
                log_info(f"插件已禁用，跳过: {plugin_id}")
                continue

            # 3. 动态导入
            plugin_class = self._load_plugin_class(plugin_dir)
            if plugin_class is None:
                continue

            # 4. 实例化
            try:
                plugin = plugin_class()
            except Exception as e:
                log_error(f"实例化插件失败 [{plugin_id}]: {e}")
                continue

            # 5. 从元数据覆盖插件属性（如果插件类没设置）
            if not plugin.plugin_id:
                plugin.plugin_id = meta["plugin_id"]
            if not plugin.name:
                plugin.name = meta["name"]
            if not plugin.version:
                plugin.version = meta["version"]
            if not plugin.author:
                plugin.author = meta["author"]
            if not plugin.description:
                plugin.description = meta["description"]
            if not plugin.category:
                plugin.category = meta["category"]
            if plugin.priority == 100 and meta.get("priority") != 100:
                plugin.priority = meta["priority"]
            if not plugin.icon:
                plugin.icon = meta.get("icon", "")

            # 6. 注入核心服务和配置
            plugin._inject_core(self._core_services)
            plugin_settings = get_plugin_settings(self.config, plugin_id)
            plugin._inject_config(self.config, plugin_settings)

            # 7. 调用 on_load
            try:
                plugin.on_load()
                plugin._loaded = True
            except Exception as e:
                log_error(f"插件 on_load 失败 [{plugin_id}]: {e}")
                continue

            self.plugins[plugin_id] = plugin
            loaded_count += 1
            log_info(f"插件加载成功: {plugin_id} v{plugin.version} - {plugin.name}")

        self._loaded = True
        log_info(f"插件加载完成: {loaded_count}/{len(plugin_dirs)} 个成功")
        return loaded_count

    # ---- 查询 ----

    def get_all_plugins(self) -> List[BasePlugin]:
        """返回所有已加载插件，按 priority 排序。"""
        return sorted(self.plugins.values(), key=lambda p: p.priority)

    def get_plugin(self, plugin_id: str) -> Optional[BasePlugin]:
        """按 ID 获取插件。"""
        return self.plugins.get(plugin_id)

    def get_all_menu_items(self) -> List[MenuItem]:
        """
        获取所有插件的所有菜单项，按插件 priority + 菜单项顺序排列。
        返回的 MenuItem 会附加 plugin_id 属性，便于点击时路由。
        """
        items = []
        for plugin in self.get_all_plugins():
            try:
                plugin_items = plugin.get_menu_items()
                for item in plugin_items:
                    # 附加 plugin_id 供路由使用
                    item.plugin_id = plugin.plugin_id
                    item.plugin_name = plugin.name
                    if not item.category:
                        item.category = plugin.category
                    items.append(item)
            except Exception as e:
                log_error(f"获取插件菜单项失败 [{plugin.plugin_id}]: {e}")
        return items

    def get_menu_items_by_category(self) -> Dict[str, List[MenuItem]]:
        """按分类分组返回菜单项。"""
        result = {}
        for item in self.get_all_menu_items():
            cat = item.category or "其他"
            if cat not in result:
                result[cat] = []
            result[cat].append(item)
        return result

    # ---- 生命周期广播 ----

    def broadcast_game_connected(self):
        """广播游戏连接事件到所有插件。"""
        for plugin in self.plugins.values():
            try:
                plugin.on_game_connected()
            except Exception as e:
                log_error(f"插件 on_game_connected 失败 [{plugin.plugin_id}]: {e}")

    def broadcast_game_disconnected(self):
        """广播游戏断开事件到所有插件。"""
        for plugin in self.plugins.values():
            try:
                plugin.on_game_disconnected()
            except Exception as e:
                log_error(f"插件 on_game_disconnected 失败 [{plugin.plugin_id}]: {e}")

    def unload_all(self):
        """卸载所有插件，调用 on_unload。"""
        for plugin_id, plugin in list(self.plugins.items()):
            try:
                plugin.on_unload()
                log_info(f"插件已卸载: {plugin_id}")
            except Exception as e:
                log_error(f"插件 on_unload 失败 [{plugin_id}]: {e}")
        self.plugins.clear()
        self._loaded = False
