"""
游戏监控插件。

实时显示游戏状态，自动刷新。
"""
import tkinter as tk
from typing import List

from core.base_plugin import BasePlugin, MenuItem


class Plugin(BasePlugin):
    plugin_id = "game_monitor"
    name = "游戏监控"
    version = "1.0.0"
    author = "smooth_game"
    description = "实时监控游戏状态"
    category = "监控"
    priority = 50

    def on_load(self):
        self._monitor_running = False
        self.log("游戏监控插件已加载")

    def on_game_connected(self):
        self.log("游戏已连接，监控可用")

    def get_menu_items(self) -> List[MenuItem]:
        return [
            MenuItem("realtime_status", "实时状态", "实时显示游戏核心数值", "监控"),
            MenuItem("resource_watch", "资源监控", "监控所有资源数值变化", "监控"),
        ]

    def build_ui(self, parent, item_id: str):
        if item_id == "realtime_status":
            self._build_realtime_ui(parent)
        elif item_id == "resource_watch":
            self._build_resource_watch_ui(parent)

    def _build_realtime_ui(self, parent):
        tk.Label(parent, text="实时状态", font=("微软雅黑", 14, "bold"),
                 bg="#ffffff", fg="#333333").pack(anchor="w", padx=16, pady=(16, 8))

        self.status_frame = tk.Frame(parent, bg="#ffffff")
        self.status_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)

        self.status_labels = {}
        fields = [
            ("boom_level", "城市品阶"),
            ("population", "人口"),
            ("happiness", "幸福度"),
            ("money", "金钱"),
            ("year", "年份"),
            ("month", "月份"),
            ("day", "日期"),
            ("season", "季节"),
            ("building_count", "建筑数量"),
        ]
        for i, (key, label) in enumerate(fields):
            row = tk.Frame(self.status_frame, bg="#fafafa", bd=1, relief=tk.SOLID)
            row.grid(row=i // 3, column=i % 3, padx=4, pady=4, sticky="nsew")
            tk.Label(row, text=label, bg="#fafafa", fg="#999999",
                     font=("微软雅黑", 9)).pack(anchor="w", padx=8, pady=(4, 0))
            val_label = tk.Label(row, text="—", bg="#fafafa", fg="#333333",
                                 font=("微软雅黑", 12, "bold"))
            val_label.pack(anchor="w", padx=8, pady=(0, 4))
            self.status_labels[key] = val_label

        # 配置网格权重
        for i in range(3):
            self.status_frame.grid_columnconfigure(i, weight=1)

        # 自动刷新
        self._monitor_running = True
        self._schedule_refresh(parent)

    def _schedule_refresh(self, parent):
        if not self._monitor_running:
            return
        self._update_status()
        # 保存 parent 引用用于 after
        if hasattr(parent, 'after'):
            parent.after(2000, lambda: self._schedule_refresh(parent))

    def _update_status(self):
        status = self.get_game_status()
        if not status:
            return
        for key, label in self.status_labels.items():
            val = status.get(key, "—")
            if key == "money" and isinstance(val, (int, float)):
                val = f"{val:,}"
            label.configure(text=str(val))

    def _build_resource_watch_ui(self, parent):
        tk.Label(parent, text="资源监控", font=("微软雅黑", 14, "bold"),
                 bg="#ffffff", fg="#333333").pack(anchor="w", padx=16, pady=(16, 8))

        self.resource_frame = tk.Frame(parent, bg="#ffffff")
        self.resource_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)

        self.resource_labels = {}
        resource_names = {
            1: "金钱", 2: "矿产", 3: "木料", 4: "衣物",
            5: "食物", 6: "水", 19: "盐", 20: "酒", 25: "精华",
        }
        for i, (res_id, name) in enumerate(resource_names.items()):
            row = tk.Frame(self.resource_frame, bg="#fafafa", bd=1, relief=tk.SOLID)
            row.grid(row=i // 2, column=i % 2, padx=4, pady=4, sticky="nsew")
            tk.Label(row, text=name, bg="#fafafa", fg="#999999",
                     font=("微软雅黑", 9)).pack(anchor="w", padx=8, pady=(4, 0))
            val_label = tk.Label(row, text="—", bg="#fafafa", fg="#07C160",
                                 font=("微软雅黑", 11, "bold"))
            val_label.pack(anchor="w", padx=8, pady=(0, 4))
            self.resource_labels[res_id] = val_label

        for i in range(2):
            self.resource_frame.grid_columnconfigure(i, weight=1)

        self._resource_monitor_running = True
        self._schedule_resource_refresh(parent)

    def _schedule_resource_refresh(self, parent):
        if not getattr(self, "_resource_monitor_running", False):
            return
        self._update_resources()
        if hasattr(parent, 'after'):
            parent.after(2000, lambda: self._schedule_resource_refresh(parent))

    def _update_resources(self):
        status = self.get_game_status()
        resources = status.get("resources", {})
        if not resources:
            return
        for res_id, label in self.resource_labels.items():
            val = resources.get(str(res_id), resources.get(res_id, "—"))
            if isinstance(val, (int, float)):
                val = f"{val:,}"
            label.configure(text=str(val))

    def on_unload(self):
        self._monitor_running = False
        self._resource_monitor_running = False
