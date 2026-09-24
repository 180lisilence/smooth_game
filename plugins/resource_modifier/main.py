"""
资源修改插件。

提供10种基础资源的一键增加和自定义数量修改。
"""
import tkinter as tk
from typing import List

from core.base_plugin import BasePlugin, MenuItem


# 资源定义
RESOURCES = [
    {"id": 1, "name": "金钱", "hotkey": "Ctrl+F1", "desc": "通用货币"},
    {"id": 2, "name": "矿产", "hotkey": "Ctrl+F6", "desc": "建造高级建筑所需"},
    {"id": 3, "name": "木料", "hotkey": "Ctrl+F5", "desc": "基础建造材料"},
    {"id": 4, "name": "衣物", "hotkey": "Ctrl+F4", "desc": "人口相关"},
    {"id": 5, "name": "食物", "hotkey": "Ctrl+F2", "desc": "维持人口生存"},
    {"id": 6, "name": "水", "hotkey": "Ctrl+F3", "desc": "维持人口生存"},
    {"id": 7, "name": "人口", "hotkey": "—", "desc": "劳动力来源（不建议直接修改）"},
    {"id": 19, "name": "盐", "hotkey": "Ctrl+F7", "desc": "高级资源"},
    {"id": 20, "name": "酒", "hotkey": "Ctrl+F8", "desc": "高级资源"},
    {"id": 25, "name": "精华", "hotkey": "Ctrl+F11", "desc": "高级资源（七阶目标）"},
]

DEFAULT_ADD_AMOUNT = 1000000


class Plugin(BasePlugin):
    """资源修改插件。"""

    plugin_id = "resource_modifier"
    name = "资源修改"
    version = "1.0.0"
    author = "smooth_game"
    description = "修改游戏内10种基础资源"
    category = "资源"
    priority = 10

    def on_load(self):
        self.log("资源修改插件已加载")

    def get_menu_items(self) -> List[MenuItem]:
        return [
            MenuItem("all_resources", "一键全部资源", "所有资源各 +100万", "资源"),
            MenuItem("resource_list", "资源列表", "查看和修改每种资源", "资源"),
            MenuItem("happiness", "幸福度最大", "幸福度设为999", "资源"),
            MenuItem("fame", "知名度 +1万", "增加1万知名度", "资源"),
        ]

    def build_ui(self, parent, item_id: str):
        if item_id == "all_resources":
            self._build_all_resources_ui(parent)
        elif item_id == "resource_list":
            self._build_resource_list_ui(parent)
        elif item_id == "happiness":
            self._build_happiness_ui(parent)
        elif item_id == "fame":
            self._build_fame_ui(parent)

    # ---- UI: 一键全部资源 ----

    def _build_all_resources_ui(self, parent):
        tk.Label(parent, text="一键全部资源", font=("微软雅黑", 14, "bold"),
                 bg="#ffffff", fg="#333333").pack(anchor="w", padx=16, pady=(16, 8))
        tk.Label(parent, text="所有可修改资源各 +1,000,000（人口除外）",
                 bg="#ffffff", fg="#999999", font=("微软雅黑", 10)).pack(anchor="w", padx=16)

        tk.Button(parent, text="一键全部资源 +100万", command=self._add_all_resources,
                  bg="#07C160", fg="white", bd=0, font=("微软雅黑", 12, "bold"),
                  padx=24, pady=10, cursor="hand2").pack(anchor="w", padx=16, pady=20)

        # 结果显示
        self.all_result_label = tk.Label(parent, text="", bg="#ffffff", fg="#07C160",
                                          font=("微软雅黑", 10))
        self.all_result_label.pack(anchor="w", padx=16)

    def _add_all_resources(self):
        success_count = 0
        for res in RESOURCES:
            if res["id"] == 7:  # 跳过人口
                continue
            lua = f"""
            local ok, err = pcall(function()
                if g_camp and g_camp.m_tbSource then
                    g_camp.m_tbSource[{res['id']}] = (g_camp.m_tbSource[{res['id']}] or 0) + {DEFAULT_ADD_AMOUNT}
                end
            end)
            if ok then return "[成功]" else return "[失败]:" .. tostring(err) end
            """
            success, result = self.execute_lua(lua)
            if success and "[成功]" in result:
                success_count += 1
        total = len(RESOURCES) - 1  # 减去人口
        msg = f"资源增加完成: {success_count}/{total} 项成功"
        self.all_result_label.configure(text=msg)
        self.log(msg, "SUCCESS" if success_count == total else "WARNING")

    # ---- UI: 资源列表 ----

    def _build_resource_list_ui(self, parent):
        tk.Label(parent, text="资源列表", font=("微软雅黑", 14, "bold"),
                 bg="#ffffff", fg="#333333").pack(anchor="w", padx=16, pady=(16, 8))

        # 表头
        header = tk.Frame(parent, bg="#f5f5f5")
        header.pack(fill=tk.X, padx=16, pady=(8, 0))
        tk.Label(header, text="资源", width=10, bg="#f5f5f5", font=("微软雅黑", 10, "bold")).pack(side=tk.LEFT, padx=4, pady=6)
        tk.Label(header, text="热键", width=12, bg="#f5f5f5", font=("微软雅黑", 10, "bold")).pack(side=tk.LEFT, padx=4, pady=6)
        tk.Label(header, text="数量", width=12, bg="#f5f5f5", font=("微软雅黑", 10, "bold")).pack(side=tk.LEFT, padx=4, pady=6)
        tk.Label(header, text="操作", width=12, bg="#f5f5f5", font=("微软雅黑", 10, "bold")).pack(side=tk.LEFT, padx=4, pady=6)

        self.resource_rows = {}
        for res in RESOURCES:
            row = tk.Frame(parent, bg="#ffffff")
            row.pack(fill=tk.X, padx=16, pady=2)

            tk.Label(row, text=res["name"], width=10, bg="#ffffff",
                     font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=4, pady=4)
            tk.Label(row, text=res["hotkey"], width=12, bg="#ffffff",
                     fg="#999999", font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=4, pady=4)

            amount_var = tk.StringVar(value=str(DEFAULT_ADD_AMOUNT))
            amount_entry = tk.Entry(row, textvariable=amount_var, width=12,
                                    font=("微软雅黑", 10), bd=1, relief=tk.SOLID)
            amount_entry.pack(side=tk.LEFT, padx=4, pady=4)

            if res["id"] == 7:
                tk.Label(row, text="不建议修改", bg="#ffffff", fg="#ff9800",
                         font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=4, pady=4)
            else:
                btn = tk.Button(row, text="+增加", command=lambda r=res, v=amount_var: self._add_single_resource(r, v),
                                bg="#e8f5e9", fg="#07C160", bd=0, font=("微软雅黑", 9),
                                padx=8, pady=2, cursor="hand2")
                btn.pack(side=tk.LEFT, padx=4, pady=4)

            self.resource_rows[res["id"]] = amount_var

        # 刷新按钮
        tk.Button(parent, text="刷新当前值", command=self._refresh_resource_values,
                  bg="#e0e0e0", fg="#333333", bd=0, font=("微软雅黑", 10),
                  padx=16, pady=6, cursor="hand2").pack(anchor="w", padx=16, pady=12)

    def _add_single_resource(self, res, amount_var):
        try:
            amount = int(amount_var.get())
        except ValueError:
            self.log(f"数量无效: {amount_var.get()}", "ERROR")
            return
        lua = f"""
        local ok, err = pcall(function()
            if g_camp and g_camp.m_tbSource then
                g_camp.m_tbSource[{res['id']}] = (g_camp.m_tbSource[{res['id']}] or 0) + {amount}
            end
        end)
        if ok then return "[成功]" else return "[失败]:" .. tostring(err) end
        """
        success, result = self.execute_lua(lua)
        if success:
            self.log(f"{res['name']} +{amount:,} 成功", "SUCCESS")
        else:
            self.log(f"{res['name']} 增加失败: {result}", "ERROR")

    def _refresh_resource_values(self):
        status = self.get_game_status()
        resources = status.get("resources", {})
        if not resources:
            self.log("无法获取资源状态，请确认游戏已连接", "WARNING")
            return
        for res_id, var in self.resource_rows.items():
            val = resources.get(str(res_id), resources.get(res_id, "?"))
            var.set(str(val))

    # ---- UI: 幸福度 ----

    def _build_happiness_ui(self, parent):
        tk.Label(parent, text="幸福度最大", font=("微软雅黑", 14, "bold"),
                 bg="#ffffff", fg="#333333").pack(anchor="w", padx=16, pady=(16, 8))
        tk.Label(parent, text="将幸福度设为 999（等级4，最高）",
                 bg="#ffffff", fg="#999999", font=("微软雅黑", 10)).pack(anchor="w", padx=16)

        tk.Button(parent, text="幸福度最大", command=self._set_happiness_max,
                  bg="#07C160", fg="white", bd=0, font=("微软雅黑", 12, "bold"),
                  padx=24, pady=10, cursor="hand2").pack(anchor="w", padx=16, pady=20)

        self.happiness_result = tk.Label(parent, text="", bg="#ffffff", fg="#07C160",
                                          font=("微软雅黑", 10))
        self.happiness_result.pack(anchor="w", padx=16)

    def _set_happiness_max(self):
        lua = """
        local ok, err = pcall(function()
            if g_camp then
                g_camp.m_nHappiness = 999
            end
        end)
        if ok then return "[成功]" else return "[失败]:" .. tostring(err) end
        """
        success, result = self.execute_lua(lua)
        if success:
            self.happiness_result.configure(text="幸福度已设为 999")
            self.log("幸福度最大 成功", "SUCCESS")
        else:
            self.happiness_result.configure(text=f"失败: {result}", fg="#f44336")
            self.log(f"幸福度设置失败: {result}", "ERROR")

    # ---- UI: 知名度 ----

    def _build_fame_ui(self, parent):
        tk.Label(parent, text="知名度 +1万", font=("微软雅黑", 14, "bold"),
                 bg="#ffffff", fg="#333333").pack(anchor="w", padx=16, pady=(16, 8))
        tk.Label(parent, text="增加 10,000 知名度（影响力）",
                 bg="#ffffff", fg="#999999", font=("微软雅黑", 10)).pack(anchor="w", padx=16)

        tk.Button(parent, text="知名度 +1万", command=self._add_fame,
                  bg="#07C160", fg="white", bd=0, font=("微软雅黑", 12, "bold"),
                  padx=24, pady=10, cursor="hand2").pack(anchor="w", padx=16, pady=20)

        self.fame_result = tk.Label(parent, text="", bg="#ffffff", fg="#07C160",
                                     font=("微软雅黑", 10))
        self.fame_result.pack(anchor="w", padx=16)

    def _add_fame(self):
        lua = """
        local ok, err = pcall(function()
            if g_LReputationMgr then
                g_LReputationMgr:ChangeReputation(10000)
                g_LReputationMgr:ChangeReputationBase(10000)
            end
        end)
        if ok then return "[成功]" else return "[失败]:" .. tostring(err) end
        """
        success, result = self.execute_lua(lua)
        if success:
            self.fame_result.configure(text="知名度 +10,000 成功")
            self.log("知名度 +1万 成功", "SUCCESS")
        else:
            self.fame_result.configure(text=f"失败: {result}", fg="#f44336")
            self.log(f"知名度增加失败: {result}", "ERROR")
