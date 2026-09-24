"""
启动器主窗口 - 干净的三栏框架。
左侧导航(80px) | 中间列表(240px) | 右侧主面板(自适应)
主页/插件/设置    插件页显示插件列表    主页:游戏连接+系统信息
                                      插件:选中插件的功能面板
                                      设置:设置表单
底部日志区
启动器只负责框架：游戏连接、插件管理、设置、日志。修改功能全部由插件提供。
"""
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional
from core.constants import APP_VERSION, APP_DISPLAY_NAME, DIST_DIR, DEFAULT_GAME_PATH
from core.logger import log_info, log_error, log_warning, set_gui_callback
from core.config import load_config, save_config
from core.plugin_manager import PluginManager
from core.game_status import GameStatusProvider
from core.injector import find_game_process, inject_dll, is_dll_injected, launch_game
from core.lua_engine import execute_lua

COLORS = {
    "bg": "#f5f5f5", "bg_sidebar": "#2e2e2e", "bg_sidebar_active": "#07C160",
    "bg_list": "#ffffff", "bg_list_hover": "#f0f0f0", "bg_list_active": "#e8f5e9",
    "bg_panel": "#ffffff", "bg_card": "#fafafa",
    "fg": "#333333", "fg_sidebar": "#ffffff", "fg_muted": "#999999",
    "border": "#e0e0e0", "accent": "#07C160", "success": "#07C160",
    "warning": "#ff9800", "error": "#f44336",
}

class MainWindow:
    def __init__(self):
        self.config = load_config()
        self.game_pid: Optional[int] = None
        self.dll_injected = False
        self.current_nav = 0
        self.current_plugin_id: Optional[str] = None
        self._plugin_buttons = []
        self.status_provider = GameStatusProvider()
        self.plugin_manager = PluginManager(self.config)
        self._core_services = self._build_core_services()
        self.plugin_manager.set_core_services(self._core_services)
        self.root = tk.Tk()
        self.root.title(f"{APP_DISPLAY_NAME} v{APP_VERSION}")
        self.root.geometry(self._get_window_geometry())
        self.root.minsize(860, 560)
        self.root.configure(bg=COLORS["bg"])
        set_gui_callback(self._on_log_message)
        self._build_ui()
        self.root.after(100, self._load_plugins)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_core_services(self):
        return {
            "execute_lua": self._service_execute_lua,
            "get_game_status": self.status_provider.get_status,
            "log": lambda msg, level="INFO": (log_info if level == "INFO" else log_warning if level == "WARNING" else log_error)(msg),
            "register_hotkey": lambda *a: None,
            "unregister_hotkey": lambda *a: None,
            "refresh_status": self.status_provider.refresh_now,
            "show_toast": lambda msg, d=2000: log_info(f"[通知] {msg}"),
            "save_plugin_settings": self._service_save_plugin_settings,
            "get_config": lambda: self.config,
        }

    def _service_execute_lua(self, code, timeout=5.0):
        if not self.dll_injected:
            return False, "DLL 未注入，请先连接游戏"
        return execute_lua(code, timeout)

    def _service_save_plugin_settings(self, plugin_id, settings):
        from core.config import set_plugin_settings
        set_plugin_settings(self.config, plugin_id, settings)
        save_config(self.config)

    def _get_window_geometry(self):
        w = self.config.get("window", {}).get("width", 960)
        h = self.config.get("window", {}).get("height", 640)
        x = self.config.get("window", {}).get("x")
        y = self.config.get("window", {}).get("y")
        if x is not None and y is not None:
            return f"{w}x{h}+{x}+{y}"
        return f"{w}x{h}"

    def _build_ui(self):
        self.main_container = tk.Frame(self.root, bg=COLORS["bg"])
        self.main_container.pack(fill=tk.BOTH, expand=True)
        self.top_frame = tk.Frame(self.main_container, bg=COLORS["bg"])
        self.top_frame.pack(fill=tk.BOTH, expand=True)
        self._build_sidebar()
        self._build_middle_list()
        self._build_right_panel()
        self._build_log_panel()
        # 初始化主页内容（current_nav=0，中间列表隐藏）
        self.middle_frame.pack_forget()
        self._build_home_panel()

    def _build_sidebar(self):
        self.sidebar = tk.Frame(self.top_frame, bg=COLORS["bg_sidebar"], width=80)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)
        self.nav_buttons = []
        for nav_id, label, icon in [(0, "主页", "⌂"), (1, "插件", "▦"), (2, "设置", "⚙")]:
            btn = tk.Button(
                self.sidebar, text=f"{icon}\n{label}",
                bg=COLORS["bg_sidebar"], fg=COLORS["fg_sidebar"],
                activebackground=COLORS["bg_sidebar_active"], activeforeground="#ffffff",
                bd=0, font=("微软雅黑", 9), width=10, height=3, cursor="hand2",
                command=lambda nid=nav_id: self._switch_nav(nid))
            btn.pack(fill=tk.X, padx=2, pady=2)
            self.nav_buttons.append(btn)
        tk.Label(self.sidebar, text=f"v{APP_VERSION}", bg=COLORS["bg_sidebar"],
                 fg=COLORS["fg_muted"], font=("微软雅黑", 8)).pack(side=tk.BOTTOM, pady=10)
        self._update_sidebar_active()

    def _build_middle_list(self):
        self.middle_frame = tk.Frame(self.top_frame, bg=COLORS["bg_list"], width=240)
        title_bar = tk.Frame(self.middle_frame, bg=COLORS["bg_list"], height=40)
        title_bar.pack(fill=tk.X)
        title_bar.pack_propagate(False)
        tk.Label(title_bar, text="已安装插件", bg=COLORS["bg_list"], fg=COLORS["fg"],
                 font=("微软雅黑", 11, "bold")).pack(side=tk.LEFT, padx=12)
        tk.Frame(self.middle_frame, bg=COLORS["border"], height=1).pack(fill=tk.X)
        self.plugin_canvas = tk.Canvas(self.middle_frame, bg=COLORS["bg_list"], bd=0, highlightthickness=0)
        self.plugin_scrollbar = ttk.Scrollbar(self.middle_frame, orient="vertical", command=self.plugin_canvas.yview)
        self.plugin_inner = tk.Frame(self.plugin_canvas, bg=COLORS["bg_list"])
        self.plugin_inner.bind("<Configure>", lambda e: self.plugin_canvas.configure(scrollregion=self.plugin_canvas.bbox("all")))
        self.plugin_canvas.create_window((0, 0), window=self.plugin_inner, anchor="nw")
        self.plugin_canvas.configure(yscrollcommand=self.plugin_scrollbar.set)
        self.plugin_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))
        self.plugin_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=8)

    def _build_right_panel(self):
        self.panel_frame = tk.Frame(self.top_frame, bg=COLORS["bg_panel"])
        self.panel_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.panel_title_bar = tk.Frame(self.panel_frame, bg=COLORS["bg_panel"], height=44)
        self.panel_title_bar.pack(fill=tk.X)
        self.panel_title_bar.pack_propagate(False)
        self.panel_title = tk.Label(self.panel_title_bar, text="主页", bg=COLORS["bg_panel"],
                                     fg=COLORS["fg"], font=("微软雅黑", 13, "bold"), anchor="w")
        self.panel_title.pack(side=tk.LEFT, padx=16, pady=8)
        self.conn_indicator = tk.Label(self.panel_title_bar, text="● 未连接", bg=COLORS["bg_panel"],
                                        fg=COLORS["fg_muted"], font=("微软雅黑", 9))
        self.conn_indicator.pack(side=tk.RIGHT, padx=16)
        tk.Frame(self.panel_frame, bg=COLORS["border"], height=1).pack(fill=tk.X)
        self.panel_canvas = tk.Canvas(self.panel_frame, bg=COLORS["bg_panel"], bd=0, highlightthickness=0)
        self.panel_scrollbar = ttk.Scrollbar(self.panel_frame, orient="vertical", command=self.panel_canvas.yview)
        self.panel_inner = tk.Frame(self.panel_canvas, bg=COLORS["bg_panel"])
        self.panel_inner.bind("<Configure>", lambda e: self.panel_canvas.configure(scrollregion=self.panel_canvas.bbox("all")))
        self.panel_canvas.create_window((0, 0), window=self.panel_inner, anchor="nw")
        self.panel_canvas.configure(yscrollcommand=self.panel_scrollbar.set)
        self.panel_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.panel_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_log_panel(self):
        self.log_frame = tk.Frame(self.main_container, bg=COLORS["bg"], height=110)
        self.log_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.log_frame.pack_propagate(False)
        lt = tk.Frame(self.log_frame, bg=COLORS["bg"])
        lt.pack(fill=tk.X, padx=8, pady=(4, 0))
        tk.Label(lt, text="运行日志", bg=COLORS["bg"], fg=COLORS["fg_muted"], font=("微软雅黑", 9)).pack(side=tk.LEFT)
        tk.Button(lt, text="清空", command=self._clear_log, bg=COLORS["bg"], fg=COLORS["fg_muted"],
                  bd=0, font=("微软雅黑", 8), cursor="hand2").pack(side=tk.RIGHT)
        self.log_text = tk.Text(self.log_frame, bg="#1e1e1e", fg="#d4d4d4", font=("Consolas", 9),
                                bd=0, wrap=tk.WORD, state=tk.DISABLED, height=5)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        for level, color in [("INFO", "#d4d4d4"), ("SUCCESS", "#07C160"), ("WARNING", "#ff9800"), ("ERROR", "#f44336")]:
            self.log_text.tag_configure(level, foreground=color)

    def _switch_nav(self, nav_id):
        self.current_nav = nav_id
        self._update_sidebar_active()
        if nav_id == 0:
            self.middle_frame.pack_forget()
            self._build_home_panel()
        elif nav_id == 1:
            self.middle_frame.pack(side=tk.LEFT, fill=tk.Y)
            self.middle_frame.pack_propagate(False)
            self._render_plugin_list()
            self._build_plugin_detail_panel()
        elif nav_id == 2:
            self.middle_frame.pack_forget()
            self._build_settings_panel()

    def _update_sidebar_active(self):
        for i, btn in enumerate(self.nav_buttons):
            btn.configure(bg=COLORS["bg_sidebar_active"] if i == self.current_nav else COLORS["bg_sidebar"],
                          fg="#ffffff" if i == self.current_nav else COLORS["fg_sidebar"])

    def _load_plugins(self):
        count = self.plugin_manager.load_all()
        log_info(f"启动器就绪，已加载 {count} 个插件")
        if self.current_nav == 1:
            self._render_plugin_list()

    def _render_plugin_list(self):
        for w in self.plugin_inner.winfo_children():
            w.destroy()
        self._plugin_buttons.clear()
        plugins = self.plugin_manager.get_all_plugins()
        if not plugins:
            tk.Label(self.plugin_inner, text="暂无已安装插件", bg=COLORS["bg_list"],
                     fg=COLORS["fg_muted"], font=("微软雅黑", 10)).pack(pady=20)
            return
        for plugin in plugins:
            btn = tk.Button(
                self.plugin_inner, text=f"{plugin.name}\nv{plugin.version}",
                bg=COLORS["bg_list"], fg=COLORS["fg"],
                activebackground=COLORS["bg_list_hover"], activeforeground=COLORS["fg"],
                bd=0, font=("微软雅黑", 10), anchor="w", justify=tk.LEFT,
                padx=12, pady=10, cursor="hand2",
                command=lambda p=plugin: self._on_plugin_select(p.plugin_id))
            btn.pack(fill=tk.X, padx=4, pady=1)
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=COLORS["bg_list_hover"]))
            btn.bind("<Leave>", lambda e, b=btn: self._restore_plugin_btn(b))
            self._plugin_buttons.append((btn, plugin.plugin_id))

    def _restore_plugin_btn(self, btn):
        for b, pid in self._plugin_buttons:
            if b is btn:
                b.configure(bg=COLORS["bg_list_active"] if self.current_plugin_id == pid else COLORS["bg_list"])
                return

    def _on_plugin_select(self, plugin_id):
        self.current_plugin_id = plugin_id
        for b, pid in self._plugin_buttons:
            b.configure(bg=COLORS["bg_list_active"] if pid == plugin_id else COLORS["bg_list"])
        self._build_plugin_detail_panel()

    def _build_plugin_detail_panel(self):
        self.panel_title.configure(text="插件管理")
        for w in self.panel_inner.winfo_children():
            w.destroy()
        if not self.current_plugin_id:
            self._build_plugin_overview()
            return
        plugin = self.plugin_manager.get_plugin(self.current_plugin_id)
        if plugin is None:
            self._build_plugin_overview()
            return
        info = tk.Frame(self.panel_inner, bg=COLORS["bg_card"], bd=1, relief=tk.SOLID)
        info.pack(fill=tk.X, padx=16, pady=12)
        hdr = tk.Frame(info, bg=COLORS["bg_card"])
        hdr.pack(fill=tk.X, padx=12, pady=(10, 2))
        tk.Label(hdr, text=plugin.name, bg=COLORS["bg_card"], fg=COLORS["fg"],
                 font=("微软雅黑", 13, "bold")).pack(side=tk.LEFT)
        tk.Label(hdr, text=f"v{plugin.version}", bg=COLORS["bg_card"], fg=COLORS["fg_muted"],
                 font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=(8, 0))
        tk.Label(info, text=f"ID: {plugin.plugin_id}  |  作者: {plugin.author or '未知'}  |  分类: {plugin.category}",
                 bg=COLORS["bg_card"], fg=COLORS["fg_muted"], font=("微软雅黑", 9)).pack(anchor="w", padx=12)
        if plugin.description:
            tk.Label(info, text=plugin.description, bg=COLORS["bg_card"], fg=COLORS["fg"],
                     font=("微软雅黑", 10), wraplength=600, justify=tk.LEFT).pack(anchor="w", padx=12, pady=(4, 10))
        try:
            items = plugin.get_menu_items()
            if items:
                tk.Label(info, text=f"提供 {len(items)} 个功能项", bg=COLORS["bg_card"],
                         fg=COLORS["fg"], font=("微软雅黑", 10, "bold")).pack(anchor="w", padx=12, pady=(6, 2))
                for it in items:
                    tk.Label(info, text=f"  • {it.label}" + (f" — {it.description}" if it.description else ""),
                             bg=COLORS["bg_card"], fg=COLORS["fg_muted"], font=("微软雅黑", 9),
                             anchor="w").pack(fill=tk.X, padx=16, pady=1)
        except Exception as e:
            tk.Label(info, text=f"获取功能项失败: {e}", bg=COLORS["bg_card"], fg=COLORS["error"],
                     font=("微软雅黑", 9)).pack(anchor="w", padx=12, pady=4)
        tk.Frame(info, bg=COLORS["bg_card"], height=8).pack()
        tk.Label(self.panel_inner, text="功能面板", bg=COLORS["bg_panel"], fg=COLORS["fg_muted"],
                 font=("微软雅黑", 10, "bold")).pack(anchor="w", padx=16, pady=(4, 6))
        try:
            items = plugin.get_menu_items()
            if len(items) > 1:
                btn_bar = tk.Frame(self.panel_inner, bg=COLORS["bg_panel"])
                btn_bar.pack(fill=tk.X, padx=16, pady=(0, 8))
                self._func_buttons = []
                for it in items:
                    b = tk.Button(btn_bar, text=it.label, command=lambda i=it: self._show_func(plugin, i),
                                  bg="#e8f5e9", fg=COLORS["accent"], bd=0, font=("微软雅黑", 9),
                                  padx=10, pady=4, cursor="hand2")
                    b.pack(side=tk.LEFT, padx=(0, 6))
                    self._func_buttons.append((b, it.item_id))
                self._show_func(plugin, items[0])
            elif len(items) == 1:
                self._func_container = tk.Frame(self.panel_inner, bg=COLORS["bg_panel"])
                self._func_container.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))
                plugin.build_ui(self._func_container, items[0].item_id)
            else:
                tk.Label(self.panel_inner, text="该插件未提供功能项", bg=COLORS["bg_panel"],
                         fg=COLORS["fg_muted"], font=("微软雅黑", 10)).pack(pady=20)
        except Exception as e:
            tk.Label(self.panel_inner, text=f"构建功能面板失败: {e}", bg=COLORS["bg_panel"],
                     fg=COLORS["error"], font=("微软雅黑", 10)).pack(pady=20)
            import traceback
            traceback.print_exc()

    def _show_func(self, plugin, item):
        for b, iid in getattr(self, '_func_buttons', []):
            b.configure(bg=COLORS["accent"] if iid == item.item_id else "#e8f5e9",
                        fg="#ffffff" if iid == item.item_id else COLORS["accent"])
        if hasattr(self, '_func_container') and self._func_container.winfo_exists():
            self._func_container.destroy()
        self._func_container = tk.Frame(self.panel_inner, bg=COLORS["bg_panel"])
        self._func_container.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))
        try:
            plugin.build_ui(self._func_container, item.item_id)
        except Exception as e:
            tk.Label(self._func_container, text=f"UI构建失败: {e}", fg=COLORS["error"],
                     bg=COLORS["bg_panel"]).pack(pady=20)
            import traceback
            traceback.print_exc()

    def _build_plugin_overview(self):
        plugins = self.plugin_manager.get_all_plugins()
        tk.Label(self.panel_inner, text=f"已安装 {len(plugins)} 个插件", bg=COLORS["bg_panel"],
                 fg=COLORS["fg"], font=("微软雅黑", 12, "bold")).pack(anchor="w", padx=16, pady=(16, 4))
        tk.Label(self.panel_inner, text="从左侧列表选择插件查看详情", bg=COLORS["bg_panel"],
                 fg=COLORS["fg_muted"], font=("微软雅黑", 10)).pack(anchor="w", padx=16, pady=(0, 8))
        for p in plugins:
            card = tk.Frame(self.panel_inner, bg=COLORS["bg_card"], bd=1, relief=tk.SOLID)
            card.pack(fill=tk.X, padx=16, pady=4)
            tk.Label(card, text=f"{p.name} v{p.version}", bg=COLORS["bg_card"], fg=COLORS["fg"],
                     font=("微软雅黑", 11, "bold")).pack(anchor="w", padx=12, pady=(6, 2))
            tk.Label(card, text=p.description or "无描述", bg=COLORS["bg_card"], fg=COLORS["fg_muted"],
                     font=("微软雅黑", 9), wraplength=600, justify=tk.LEFT).pack(anchor="w", padx=12, pady=(0, 6))

    def _build_home_panel(self):
        self.panel_title.configure(text="主页")
        for w in self.panel_inner.winfo_children():
            w.destroy()
        conn = tk.Frame(self.panel_inner, bg=COLORS["bg_card"], bd=1, relief=tk.SOLID)
        conn.pack(fill=tk.X, padx=16, pady=12)
        tk.Label(conn, text="游戏连接", bg=COLORS["bg_card"], fg=COLORS["fg"],
                 font=("微软雅黑", 12, "bold")).pack(anchor="w", padx=12, pady=(10, 4))
        self.home_status_label = tk.Label(conn, text="状态：未连接", bg=COLORS["bg_card"],
                                           fg=COLORS["fg_muted"], font=("微软雅黑", 10))
        self.home_status_label.pack(anchor="w", padx=12, pady=2)
        bf = tk.Frame(conn, bg=COLORS["bg_card"])
        bf.pack(fill=tk.X, padx=12, pady=(8, 12))
        for text, cmd, color in [("启动游戏", self._action_launch_game, COLORS["accent"]),
                                   ("检测进程", self._action_detect_process, "#e0e0e0"),
                                   ("注入 DLL", self._action_inject_dll, "#e0e0e0")]:
            fg = "#ffffff" if color == COLORS["accent"] else COLORS["fg"]
            fnt = ("微软雅黑", 10, "bold") if color == COLORS["accent"] else ("微软雅黑", 10)
            tk.Button(bf, text=text, command=cmd, bg=color, fg=fg, bd=0,
                      font=fnt, padx=16, pady=7, cursor="hand2").pack(side=tk.LEFT, padx=(0, 8))
        info = tk.Frame(self.panel_inner, bg=COLORS["bg_card"], bd=1, relief=tk.SOLID)
        info.pack(fill=tk.X, padx=16, pady=(0, 12))
        tk.Label(info, text="系统信息", bg=COLORS["bg_card"], fg=COLORS["fg"],
                 font=("微软雅黑", 12, "bold")).pack(anchor="w", padx=12, pady=(10, 4))
        for line in [f"启动器版本：{APP_VERSION}",
                     f"已加载插件：{len(self.plugin_manager.plugins)} 个",
                     f"游戏路径：{self.config.get('game_path', DEFAULT_GAME_PATH)}",
                     "配置/日志：程序目录（不写C盘）"]:
            tk.Label(info, text=line, bg=COLORS["bg_card"], fg=COLORS["fg"],
                     font=("微软雅黑", 10), anchor="w").pack(anchor="w", padx=12, pady=1)
        tk.Frame(info, bg=COLORS["bg_card"], height=8).pack()
        gs = tk.Frame(self.panel_inner, bg=COLORS["bg_card"], bd=1, relief=tk.SOLID)
        gs.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))
        tk.Label(gs, text="游戏状态", bg=COLORS["bg_card"], fg=COLORS["fg"],
                 font=("微软雅黑", 12, "bold")).pack(anchor="w", padx=12, pady=(10, 4))
        self.home_status_text = tk.Text(gs, bg=COLORS["bg_card"], fg=COLORS["fg"],
                                         font=("Consolas", 10), bd=0, height=8, wrap=tk.WORD)
        self.home_status_text.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))
        self.home_status_text.insert(tk.END, "连接游戏后显示状态...")
        self.home_status_text.config(state=tk.DISABLED)
        self._schedule_home_status()

    def _schedule_home_status(self):
        if self.current_nav == 0 and self.dll_injected:
            self._update_home_status()
        self.root.after(3000, self._schedule_home_status)

    def _update_home_status(self):
        status = self.status_provider.get_status()
        if not status:
            return
        lines = [f"城市品阶: {status.get('boom_level', '?')} / 14",
                 f"人口: {status.get('population', '?')}",
                 f"幸福度: {status.get('happiness', '?')}",
                 f"金钱: {status.get('money', '?'):,}",
                 f"时间: {status.get('year', '?')}年{status.get('month', '?')}月{status.get('day', '?')}日 ({status.get('season', '?')})",
                 f"建筑数量: {status.get('building_count', '?')}"]
        self.home_status_text.config(state=tk.NORMAL)
        self.home_status_text.delete(1.0, tk.END)
        self.home_status_text.insert(tk.END, "\n".join(lines))
        self.home_status_text.config(state=tk.DISABLED)

    def _build_settings_panel(self):
        self.panel_title.configure(text="设置")
        for w in self.panel_inner.winfo_children():
            w.destroy()
        card = tk.Frame(self.panel_inner, bg=COLORS["bg_card"], bd=1, relief=tk.SOLID)
        card.pack(fill=tk.X, padx=16, pady=12)
        tk.Label(card, text="游戏设置", bg=COLORS["bg_card"], fg=COLORS["fg"],
                 font=("微软雅黑", 12, "bold")).pack(anchor="w", padx=12, pady=(10, 8))
        pf = tk.Frame(card, bg=COLORS["bg_card"])
        pf.pack(fill=tk.X, padx=12, pady=4)
        tk.Label(pf, text="游戏路径：", bg=COLORS["bg_card"], fg=COLORS["fg"],
                 font=("微软雅黑", 10), width=10, anchor="w").pack(side=tk.LEFT)
        self.game_path_var = tk.StringVar(value=self.config.get("game_path", DEFAULT_GAME_PATH))
        tk.Entry(pf, textvariable=self.game_path_var, font=("微软雅黑", 10)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        tk.Button(pf, text="浏览", command=self._browse_game_path, bg="#e0e0e0", fg=COLORS["fg"],
                  bd=0, font=("微软雅黑", 9), padx=10, pady=3, cursor="hand2").pack(side=tk.LEFT)
        df = tk.Frame(card, bg=COLORS["bg_card"])
        df.pack(fill=tk.X, padx=12, pady=4)
        tk.Label(df, text="DLL 路径：", bg=COLORS["bg_card"], fg=COLORS["fg"],
                 font=("微软雅黑", 10), width=10, anchor="w").pack(side=tk.LEFT)
        self.dll_path_var = tk.StringVar(value=self.config.get("dll_path", "") or os.path.join(DIST_DIR, "woldvein_trainer.dll"))
        tk.Entry(df, textvariable=self.dll_path_var, font=("微软雅黑", 10)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        tk.Button(df, text="浏览", command=self._browse_dll_path, bg="#e0e0e0", fg=COLORS["fg"],
                  bd=0, font=("微软雅黑", 9), padx=10, pady=3, cursor="hand2").pack(side=tk.LEFT)
        tk.Frame(card, bg=COLORS["bg_card"], height=8).pack()
        sf = tk.Frame(card, bg=COLORS["bg_card"])
        sf.pack(fill=tk.X, padx=12, pady=(0, 12))
        tk.Button(sf, text="保存设置", command=self._action_save_settings, bg=COLORS["accent"],
                  fg="#ffffff", bd=0, font=("微软雅黑", 10, "bold"), padx=20, pady=7, cursor="hand2").pack(side=tk.LEFT)
        self.settings_result = tk.Label(sf, text="", bg=COLORS["bg_card"], fg=COLORS["success"], font=("微软雅黑", 10))
        self.settings_result.pack(side=tk.LEFT, padx=12)
        about = tk.Frame(self.panel_inner, bg=COLORS["bg_card"], bd=1, relief=tk.SOLID)
        about.pack(fill=tk.X, padx=16, pady=(0, 16))
        tk.Label(about, text=f"{APP_DISPLAY_NAME} v{APP_VERSION}", bg=COLORS["bg_card"],
                 fg=COLORS["fg"], font=("微软雅黑", 13, "bold")).pack(anchor="w", padx=12, pady=(10, 2))
        tk.Label(about, text="插件化架构 · 核心壳 + 插件 · 纯内存操作 · DLL 注入 · Lua 执行",
                 bg=COLORS["bg_card"], fg=COLORS["fg_muted"], font=("微软雅黑", 9)).pack(anchor="w", padx=12, pady=(0, 10))

    def _browse_game_path(self):
        p = filedialog.askdirectory(title="选择游戏安装目录", initialdir=self.game_path_var.get())
        if p:
            self.game_path_var.set(p)

    def _browse_dll_path(self):
        p = filedialog.askopenfilename(title="选择 DLL 文件", filetypes=[("DLL文件", "*.dll")],
                                        initialdir=os.path.dirname(self.dll_path_var.get()))
        if p:
            self.dll_path_var.set(p)

    def _action_save_settings(self):
        self.config["game_path"] = self.game_path_var.get()
        self.config["dll_path"] = self.dll_path_var.get()
        if save_config(self.config):
            self.settings_result.configure(text="设置已保存")
            log_info("设置已保存")
        else:
            self.settings_result.configure(text="保存失败", fg=COLORS["error"])

    def _action_launch_game(self):
        launch_game(self.config.get("game_path", DEFAULT_GAME_PATH))

    def _action_detect_process(self):
        pid, h_process = find_game_process()
        if pid:
            self.game_pid = pid
            if h_process:
                import ctypes
                ctypes.windll.kernel32.CloseHandle(h_process)
            injected = is_dll_injected(pid)
            self.dll_injected = injected
            msg = f"已检测到游戏 (PID={pid})"
            if injected:
                msg += "，DLL 已注入"
                self.status_provider.set_dll_ready(True)
                self.status_provider.start(interval=3.0)
                self.plugin_manager.broadcast_game_connected()
            else:
                msg += "，DLL 未注入"
            self.home_status_label.configure(text=f"状态：{msg}", fg=COLORS["success"])
            self.conn_indicator.configure(text="● 已连接", fg=COLORS["success"])
            log_info(msg)
        else:
            self.home_status_label.configure(text="状态：未检测到游戏进程", fg=COLORS["error"])
            log_warning("未检测到游戏进程")

    def _action_inject_dll(self):
        if not self.game_pid:
            messagebox.showwarning("提示", "请先点击「检测进程」")
            return
        if self.dll_injected:
            log_warning("DLL 已注入，无需重复注入")
            return
        dll_path = self.config.get("dll_path", "") or os.path.join(DIST_DIR, "woldvein_trainer.dll")
        if not os.path.exists(dll_path):
            messagebox.showerror("错误", f"DLL 文件不存在:\n{dll_path}")
            return
        if inject_dll(self.game_pid, dll_path):
            self.root.after(500, self._after_inject)
        else:
            messagebox.showerror("错误", "DLL 注入失败，请查看日志")

    def _after_inject(self):
        if is_dll_injected(self.game_pid):
            self.dll_injected = True
            self.status_provider.set_dll_ready(True)
            self.status_provider.start(interval=3.0)
            self.plugin_manager.broadcast_game_connected()
            self.home_status_label.configure(text="状态：DLL 注入成功", fg=COLORS["success"])
            self.conn_indicator.configure(text="● 已连接", fg=COLORS["success"])
            log_info("DLL 注入成功")
        else:
            log_warning("DLL 注入后检测不到，可能仍在初始化")

    def _on_log_message(self, msg, level="INFO"):
        def append():
            try:
                if not self.log_text.winfo_exists():
                    return
                self.log_text.config(state=tk.NORMAL)
                from datetime import datetime
                ts = datetime.now().strftime("%H:%M:%S")
                self.log_text.insert(tk.END, f"[{ts}] [{level}] {msg}\n", level)
                self.log_text.see(tk.END)
                line_count = int(self.log_text.index('end-1c').split('.')[0])
                if line_count > 500:
                    self.log_text.delete(1.0, f"{line_count - 500}.0")
                self.log_text.config(state=tk.DISABLED)
            except tk.TclError:
                pass
        self.root.after(0, append)

    def _clear_log(self):
        if self.log_text:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.delete(1.0, tk.END)
            self.log_text.config(state=tk.DISABLED)

    def _on_close(self):
        try:
            geom = self.root.geometry()
            parts = geom.replace("+", "x").split("x")
            if len(parts) >= 2:
                self.config.setdefault("window", {})
                self.config["window"]["width"] = int(parts[0])
                self.config["window"]["height"] = int(parts[1])
            if len(parts) >= 4:
                self.config["window"]["x"] = int(parts[2])
                self.config["window"]["y"] = int(parts[3])
            save_config(self.config)
            self.status_provider.stop()
            self.plugin_manager.unload_all()
        except Exception as e:
            print(f"关闭时异常: {e}")
        self.root.destroy()

    def run(self):
        log_info(f"{APP_DISPLAY_NAME} v{APP_VERSION} 启动")
        self.root.mainloop()

