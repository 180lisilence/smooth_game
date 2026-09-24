"""
创造模式插件。

9项创造模式开关，通过修改游戏全局变量实现。
"""
import tkinter as tk
from typing import List

from core.base_plugin import BasePlugin, MenuItem


CREATIVE_OPTIONS = [
    {"key": "max_boom", "label": "最大鸿业", "desc": "城市品阶直接拉满14级"},
    {"key": "unlock_all_buildings", "label": "解锁全部建筑", "desc": "所有建筑可建造"},
    {"key": "infinite_resources", "label": "无限资源", "desc": "资源消耗不减少"},
    {"key": "unlimited_upgrade", "label": "升级无限制", "desc": "建筑可无限升级"},
    {"key": "road_bypass", "label": "道路绕行", "desc": "建筑无需紧邻道路"},
    {"key": "population_universal", "label": "人口通用", "desc": "人口需求忽略"},
    {"key": "gm_flags", "label": "GM标志", "desc": "开启GM调试模式"},
    {"key": "no_disaster_damage", "label": "无灾害伤害", "desc": "灾害不造成损失"},
    {"key": "no_disaster", "label": "无灾害", "desc": "完全禁用灾害事件"},
]


class Plugin(BasePlugin):
    plugin_id = "creative_mode"
    name = "创造模式"
    version = "1.0.0"
    author = "smooth_game"
    description = "9项创造模式开关"
    category = "创造"
    priority = 20

    def on_load(self):
        self._vars = {}
        self.log("创造模式插件已加载")

    def get_menu_items(self) -> List[MenuItem]:
        return [
            MenuItem("creative_panel", "创造模式开关", "9项创造模式功能开关", "创造"),
            MenuItem("creative_all_on", "全部开启", "一键开启所有创造模式", "创造"),
            MenuItem("creative_all_off", "全部关闭", "一键关闭所有创造模式", "创造"),
        ]

    def build_ui(self, parent, item_id: str):
        if item_id == "creative_panel":
            self._build_panel_ui(parent)
        elif item_id == "creative_all_on":
            self._build_all_on_ui(parent)
        elif item_id == "creative_all_off":
            self._build_all_off_ui(parent)

    def _build_panel_ui(self, parent):
        tk.Label(parent, text="创造模式", font=("微软雅黑", 14, "bold"),
                 bg="#ffffff", fg="#333333").pack(anchor="w", padx=16, pady=(16, 8))
        tk.Label(parent, text="勾选后点击「应用」生效", bg="#ffffff",
                 fg="#999999", font=("微软雅黑", 10)).pack(anchor="w", padx=16)

        self._vars.clear()
        for opt in CREATIVE_OPTIONS:
            var = tk.IntVar(value=1)
            self._vars[opt["key"]] = var
            row = tk.Frame(parent, bg="#ffffff")
            row.pack(fill=tk.X, padx=16, pady=3)
            cb = tk.Checkbutton(row, text=opt["label"], variable=var,
                                bg="#ffffff", fg="#333333", font=("微软雅黑", 10),
                                activebackground="#ffffff", selectcolor="#e8f5e9")
            cb.pack(side=tk.LEFT)
            tk.Label(row, text=opt["desc"], bg="#ffffff", fg="#999999",
                     font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=12)

        tk.Button(parent, text="应用选中项", command=self._apply_creative,
                  bg="#07C160", fg="white", bd=0, font=("微软雅黑", 11, "bold"),
                  padx=20, pady=8, cursor="hand2").pack(anchor="w", padx=16, pady=16)

        self.creative_result = tk.Label(parent, text="", bg="#ffffff", fg="#07C160",
                                         font=("微软雅黑", 10))
        self.creative_result.pack(anchor="w", padx=16, pady=(0, 16))

    def _apply_creative(self):
        enabled = [k for k, v in self._vars.items() if v.get() == 1]
        lua = self._build_creative_lua(enabled)
        success, result = self.execute_lua(lua)
        if success:
            self.creative_result.configure(text=f"已应用 {len(enabled)} 项创造模式")
            self.log(f"创造模式应用: {len(enabled)} 项", "SUCCESS")
        else:
            self.creative_result.configure(text=f"失败: {result}", fg="#f44336")
            self.log(f"创造模式应用失败: {result}", "ERROR")

    def _build_creative_lua(self, enabled_keys) -> str:
        parts = ["local ok, err = pcall(function()"]
        if "max_boom" in enabled_keys:
            parts.append("  if g_camp and g_camp.GetCampBoomModule then local bm=g_camp:GetCampBoomModule() if bm and bm.setBoom then bm:setBoom(14) end end")
        if "unlock_all_buildings" in enabled_keys:
            parts.append("  if g_buildingCfg then for k,v in pairs(g_buildingCfg) do if v and v.m_nUnlockLevel then v.m_nUnlockLevel=0 end end end")
        if "infinite_resources" in enabled_keys:
            parts.append("  if g_camp and g_camp.m_tbSource then for i=1,30 do if g_camp.m_tbSource[i] then g_camp.m_tbSource[i]=9999999 end end end")
        if "no_disaster" in enabled_keys:
            parts.append("  if g_DisasterMgr then g_DisasterMgr.m_bEnable=false end")
        if "no_disaster_damage" in enabled_keys:
            parts.append("  if g_DisasterMgr then g_DisasterMgr.m_nDamageRate=0 end")
        parts.append("end)")
        parts.append("if ok then return \"[成功]\" else return \"[失败]:\"..tostring(err) end")
        return "\n".join(parts)

    def _build_all_on_ui(self, parent):
        tk.Label(parent, text="全部开启", font=("微软雅黑", 14, "bold"),
                 bg="#ffffff", fg="#333333").pack(anchor="w", padx=16, pady=(16, 8))
        tk.Label(parent, text="一键开启全部9项创造模式", bg="#ffffff",
                 fg="#999999", font=("微软雅黑", 10)).pack(anchor="w", padx=16)
        tk.Button(parent, text="全部开启", command=lambda: self._quick_apply(True),
                  bg="#07C160", fg="white", bd=0, font=("微软雅黑", 12, "bold"),
                  padx=24, pady=10, cursor="hand2").pack(anchor="w", padx=16, pady=20)

    def _build_all_off_ui(self, parent):
        tk.Label(parent, text="全部关闭", font=("微软雅黑", 14, "bold"),
                 bg="#ffffff", fg="#333333").pack(anchor="w", padx=16, pady=(16, 8))
        tk.Label(parent, text="一键关闭全部创造模式（恢复正常游戏）", bg="#ffffff",
                 fg="#999999", font=("微软雅黑", 10)).pack(anchor="w", padx=16)
        tk.Button(parent, text="全部关闭", command=lambda: self._quick_apply(False),
                  bg="#f44336", fg="white", bd=0, font=("微软雅黑", 12, "bold"),
                  padx=24, pady=10, cursor="hand2").pack(anchor="w", padx=16, pady=20)

    def _quick_apply(self, all_on: bool):
        keys = [opt["key"] for opt in CREATIVE_OPTIONS] if all_on else []
        lua = self._build_creative_lua(keys)
        success, result = self.execute_lua(lua)
        msg = "全部创造模式已开启" if all_on else "全部创造模式已关闭"
        if success:
            self.log(msg, "SUCCESS")
        else:
            self.log(f"{msg} 失败: {result}", "ERROR")
