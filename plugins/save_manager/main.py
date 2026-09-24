"""
存档管理插件。

自动识别存档列表、备份存档、恢复存档、打开存档文件夹。
"""
import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import List

from core.base_plugin import BasePlugin, MenuItem
from core.constants import runtime_config_dir, DEFAULT_GAME_PATH


class Plugin(BasePlugin):
    plugin_id = "save_manager"
    name = "存档管理"
    version = "1.0.0"
    author = "smooth_game"
    description = "存档备份/恢复/管理"
    category = "存档"
    priority = 60

    def on_load(self):
        # 优先读取用户保存的存档目录，没有或路径不存在时再自动检测
        saved = self.get_plugin_settings()
        saved_dir = saved.get("save_dir") if saved else None
        if saved_dir and os.path.isdir(saved_dir):
            self._save_dir = saved_dir
        else:
            self._save_dir = self._detect_save_dir()
        self._backup_dir = os.path.join(runtime_config_dir(), "backups")
        os.makedirs(self._backup_dir, exist_ok=True)
        self.log(f"存档管理插件已加载，存档目录: {self._save_dir}")

    def _detect_save_dir(self) -> str:
        """自动检测存档目录。"""
        candidates = [
            os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "LocalLow", "西山居", "BalladsOfHongye", "Save"),
            os.path.join(os.environ.get("APPDATA", ""), "BalladsOfHongye", "Save"),
            os.path.join(DEFAULT_GAME_PATH, "Save"),
        ]
        for path in candidates:
            if os.path.isdir(path):
                return path
        return candidates[0]

    def get_menu_items(self) -> List[MenuItem]:
        return [
            MenuItem("save_list", "存档列表", "查看和管理游戏存档", "存档"),
            MenuItem("backup_all", "一键备份", "备份全部存档", "存档"),
            MenuItem("open_save_dir", "打开存档文件夹", "在资源管理器中打开存档目录", "存档"),
            MenuItem("open_backup_dir", "打开备份文件夹", "在资源管理器中打开备份目录", "存档"),
        ]

    def build_ui(self, parent, item_id: str):
        if item_id == "save_list":
            self._build_save_list_ui(parent)
        elif item_id == "backup_all":
            self._build_backup_all_ui(parent)
        elif item_id == "open_save_dir":
            self._open_dir(self._save_dir)
            tk.Label(parent, text=f"已打开存档文件夹:\n{self._save_dir}",
                     bg="#ffffff", fg="#333333", font=("微软雅黑", 11)).pack(pady=40)
        elif item_id == "open_backup_dir":
            self._open_dir(self._backup_dir)
            tk.Label(parent, text=f"已打开备份文件夹:\n{self._backup_dir}",
                     bg="#ffffff", fg="#333333", font=("微软雅黑", 11)).pack(pady=40)

    def _build_save_list_ui(self, parent):
        tk.Label(parent, text="存档列表", font=("微软雅黑", 14, "bold"),
                 bg="#ffffff", fg="#333333").pack(anchor="w", padx=16, pady=(16, 8))

        # 存档目录显示
        dir_frame = tk.Frame(parent, bg="#fafafa", bd=1, relief=tk.SOLID)
        dir_frame.pack(fill=tk.X, padx=16, pady=(0, 8))
        tk.Label(dir_frame, text=f"存档目录: {self._save_dir}", bg="#fafafa",
                 fg="#666666", font=("微软雅黑", 9), wraplength=500,
                 justify=tk.LEFT).pack(anchor="w", padx=8, pady=6)

        # 刷新按钮
        btn_frame = tk.Frame(parent, bg="#ffffff")
        btn_frame.pack(fill=tk.X, padx=16, pady=(0, 8))
        tk.Button(btn_frame, text="刷新列表", command=lambda: self._refresh_save_list(parent),
                  bg="#e0e0e0", fg="#333333", bd=0, font=("微软雅黑", 10),
                  padx=12, pady=4, cursor="hand2").pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(btn_frame, text="更改存档目录", command=self._change_save_dir,
                  bg="#e0e0e0", fg="#333333", bd=0, font=("微软雅黑", 10),
                  padx=12, pady=4, cursor="hand2").pack(side=tk.LEFT)

        # 存档列表容器
        self.save_list_container = tk.Frame(parent, bg="#ffffff")
        self.save_list_container.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))

        self._refresh_save_list(parent)

    def _refresh_save_list(self, parent):
        for widget in self.save_list_container.winfo_children():
            widget.destroy()

        if not os.path.isdir(self._save_dir):
            tk.Label(self.save_list_container, text="存档目录不存在", bg="#ffffff",
                     fg="#f44336", font=("微软雅黑", 11)).pack(pady=20)
            return

        saves = []
        for name in os.listdir(self._save_dir):
            full_path = os.path.join(self._save_dir, name)
            if os.path.isfile(full_path) or os.path.isdir(full_path):
                stat = os.stat(full_path)
                saves.append((name, full_path, stat.st_mtime, stat.st_size))

        if not saves:
            tk.Label(self.save_list_container, text="暂无存档", bg="#ffffff",
                     fg="#999999", font=("微软雅黑", 11)).pack(pady=20)
            return

        saves.sort(key=lambda x: x[2], reverse=True)

        for name, full_path, mtime, size in saves[:20]:
            row = tk.Frame(self.save_list_container, bg="#fafafa", bd=1, relief=tk.SOLID)
            row.pack(fill=tk.X, pady=3)

            info_frame = tk.Frame(row, bg="#fafafa")
            info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8, pady=6)
            tk.Label(info_frame, text=name, bg="#fafafa", fg="#333333",
                     font=("微软雅黑", 10, "bold"), anchor="w").pack(anchor="w")
            from datetime import datetime
            time_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.2f} MB"
            tk.Label(info_frame, text=f"{time_str} | {size_str}", bg="#fafafa",
                     fg="#999999", font=("微软雅黑", 9)).pack(anchor="w")

            btn_frame = tk.Frame(row, bg="#fafafa")
            btn_frame.pack(side=tk.RIGHT, padx=8, pady=6)
            tk.Button(btn_frame, text="备份", command=lambda p=full_path, n=name: self._backup_single(p, n),
                      bg="#e8f5e9", fg="#07C160", bd=0, font=("微软雅黑", 9),
                      padx=8, pady=2, cursor="hand2").pack(side=tk.LEFT, padx=2)

    def _backup_single(self, src_path: str, name: str):
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{name}_{timestamp}"
        dst_path = os.path.join(self._backup_dir, backup_name)
        try:
            if os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path)
            else:
                shutil.copy2(src_path, dst_path)
            self.log(f"存档备份成功: {name} -> {backup_name}", "SUCCESS")
            messagebox.showinfo("成功", f"存档已备份到:\n{dst_path}")
        except Exception as e:
            self.log(f"存档备份失败: {e}", "ERROR")
            messagebox.showerror("失败", f"备份失败:\n{e}")

    def _build_backup_all_ui(self, parent):
        tk.Label(parent, text="一键备份", font=("微软雅黑", 14, "bold"),
                 bg="#ffffff", fg="#333333").pack(anchor="w", padx=16, pady=(16, 8))
        tk.Label(parent, text=f"将备份整个存档目录到:\n{self._backup_dir}",
                 bg="#ffffff", fg="#999999", font=("微软雅黑", 10),
                 justify=tk.LEFT).pack(anchor="w", padx=16)
        tk.Button(parent, text="一键备份全部存档", command=self._backup_all,
                  bg="#07C160", fg="white", bd=0, font=("微软雅黑", 12, "bold"),
                  padx=24, pady=10, cursor="hand2").pack(anchor="w", padx=16, pady=20)
        self.backup_all_result = tk.Label(parent, text="", bg="#ffffff", fg="#07C160",
                                           font=("微软雅黑", 10))
        self.backup_all_result.pack(anchor="w", padx=16)

    def _backup_all(self):
        if not os.path.isdir(self._save_dir):
            self.backup_all_result.configure(text="存档目录不存在", fg="#f44336")
            return
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"full_backup_{timestamp}"
        dst_path = os.path.join(self._backup_dir, backup_name)
        try:
            shutil.copytree(self._save_dir, dst_path)
            self.backup_all_result.configure(text=f"全部存档已备份到: {backup_name}")
            self.log(f"全部存档备份成功: {backup_name}", "SUCCESS")
        except Exception as e:
            self.backup_all_result.configure(text=f"备份失败: {e}", fg="#f44336")
            self.log(f"全部存档备份失败: {e}", "ERROR")

    def _change_save_dir(self):
        new_dir = filedialog.askdirectory(title="选择存档目录", initialdir=self._save_dir)
        if new_dir:
            self._save_dir = new_dir
            self.save_plugin_settings({"save_dir": new_dir})
            self.log(f"存档目录已更改为: {new_dir}")

    def _open_dir(self, path: str):
        try:
            if os.path.isdir(path):
                os.startfile(path)
            else:
                os.makedirs(path, exist_ok=True)
                os.startfile(path)
        except Exception as e:
            self.log(f"打开文件夹失败: {e}", "ERROR")
            messagebox.showerror("错误", f"打开文件夹失败:\n{e}")
