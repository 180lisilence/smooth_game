"""
世界系统插件。

灾害控制、市场、纳税、时间流速。
"""
import tkinter as tk
from typing import List

from core.base_plugin import BasePlugin, MenuItem


class Plugin(BasePlugin):
    plugin_id = "world_tools"
    name = "世界系统"
    version = "1.0.0"
    author = "smooth_game"
    description = "灾害/市场/纳税/时间工具"
    category = "世界"
    priority = 30

    def on_load(self):
        self.log("世界系统插件已加载")

    def get_menu_items(self) -> List[MenuItem]:
        return [
            MenuItem("close_disasters", "关闭所有灾害", "禁用全部灾害事件", "世界"),
            MenuItem("auto_tax", "自动纳税", "一键完成纳税", "世界"),
            MenuItem("time_speed", "时间流速", "设置游戏时间速度", "世界"),
            MenuItem("market", "市场价格", "查看/修改市场价格", "世界"),
        ]

    def build_ui(self, parent, item_id: str):
        if item_id == "close_disasters":
            self._build_disasters_ui(parent)
        elif item_id == "auto_tax":
            self._build_tax_ui(parent)
        elif item_id == "time_speed":
            self._build_time_ui(parent)
        elif item_id == "market":
            self._build_market_ui(parent)

    def _build_disasters_ui(self, parent):
        tk.Label(parent, text="关闭所有灾害", font=("微软雅黑", 14, "bold"),
                 bg="#ffffff", fg="#333333").pack(anchor="w", padx=16, pady=(16, 8))
        tk.Label(parent, text="禁用洪水/沙尘暴/龙卷风/地震等全部灾害", bg="#ffffff",
                 fg="#999999", font=("微软雅黑", 10)).pack(anchor="w", padx=16)
        tk.Button(parent, text="关闭所有灾害", command=self._close_disasters,
                  bg="#07C160", fg="white", bd=0, font=("微软雅黑", 12, "bold"),
                  padx=24, pady=10, cursor="hand2").pack(anchor="w", padx=16, pady=20)
        self.disaster_result = tk.Label(parent, text="", bg="#ffffff", fg="#07C160",
                                         font=("微软雅黑", 10))
        self.disaster_result.pack(anchor="w", padx=16)

    def _close_disasters(self):
        lua = """
        local ok, err = pcall(function()
            if g_DisasterMgr then
                g_DisasterMgr.m_bEnable = false
                g_DisasterMgr.m_nDamageRate = 0
            end
        end)
        if ok then return "[成功]" else return "[失败]:"..tostring(err) end
        """
        success, result = self.execute_lua(lua)
        if success:
            self.disaster_result.configure(text="所有灾害已关闭")
            self.log("关闭所有灾害 成功", "SUCCESS")
        else:
            self.disaster_result.configure(text=f"失败: {result}", fg="#f44336")

    def _build_tax_ui(self, parent):
        tk.Label(parent, text="自动纳税", font=("微软雅黑", 14, "bold"),
                 bg="#ffffff", fg="#333333").pack(anchor="w", padx=16, pady=(16, 8))
        tk.Label(parent, text="一键完成当前周期的纳税", bg="#ffffff",
                 fg="#999999", font=("微软雅黑", 10)).pack(anchor="w", padx=16)
        tk.Button(parent, text="立即纳税", command=self._auto_tax,
                  bg="#07C160", fg="white", bd=0, font=("微软雅黑", 12, "bold"),
                  padx=24, pady=10, cursor="hand2").pack(anchor="w", padx=16, pady=20)
        self.tax_result = tk.Label(parent, text="", bg="#ffffff", fg="#07C160",
                                    font=("微软雅黑", 10))
        self.tax_result.pack(anchor="w", padx=16)

    def _auto_tax(self):
        lua = """
        local ok, err = pcall(function()
            if g_TaxMgr then
                g_TaxMgr:PayTax()
            end
        end)
        if ok then return "[成功]" else return "[失败]:"..tostring(err) end
        """
        success, result = self.execute_lua(lua)
        if success:
            self.tax_result.configure(text="纳税完成")
            self.log("自动纳税 成功", "SUCCESS")
        else:
            self.tax_result.configure(text=f"失败: {result}", fg="#f44336")

    def _build_time_ui(self, parent):
        tk.Label(parent, text="时间流速", font=("微软雅黑", 14, "bold"),
                 bg="#ffffff", fg="#333333").pack(anchor="w", padx=16, pady=(16, 8))
        tk.Label(parent, text="设置游戏内时间流逝速度（0.05x ~ 60x）", bg="#ffffff",
                 fg="#999999", font=("微软雅黑", 10)).pack(anchor="w", padx=16)

        self.time_speed_var = tk.StringVar(value="1.0")
        entry = tk.Entry(parent, textvariable=self.time_speed_var, width=10,
                         font=("微软雅黑", 12), bd=1, relief=tk.SOLID)
        entry.pack(anchor="w", padx=16, pady=12)

        btn_frame = tk.Frame(parent, bg="#ffffff")
        btn_frame.pack(anchor="w", padx=16, pady=8)
        for speed, label in [(0.5, "0.5x"), (1.0, "1x"), (2.0, "2x"), (5.0, "5x"), (10.0, "10x")]:
            tk.Button(btn_frame, text=label, command=lambda s=speed: self._set_time_speed(s),
                      bg="#e8f5e9", fg="#07C160", bd=0, font=("微软雅黑", 10),
                      padx=10, pady=4, cursor="hand2").pack(side=tk.LEFT, padx=3)

        tk.Button(parent, text="应用自定义速度", command=lambda: self._set_time_speed(float(self.time_speed_var.get())),
                  bg="#07C160", fg="white", bd=0, font=("微软雅黑", 11),
                  padx=16, pady=6, cursor="hand2").pack(anchor="w", padx=16, pady=12)

        self.time_result = tk.Label(parent, text="", bg="#ffffff", fg="#07C160",
                                     font=("微软雅黑", 10))
        self.time_result.pack(anchor="w", padx=16)

    def _set_time_speed(self, speed: float):
        speed = max(0.05, min(60.0, speed))
        lua = f"""
        local ok, err = pcall(function()
            if g_Time then
                g_Time.m_fSpeed = {speed}
            end
        end)
        if ok then return "[成功]" else return "[失败]:"..tostring(err) end
        """
        success, result = self.execute_lua(lua)
        if success:
            self.time_result.configure(text=f"时间流速已设为 {speed}x")
            self.log(f"时间流速 {speed}x", "SUCCESS")
        else:
            self.time_result.configure(text=f"失败: {result}", fg="#f44336")

    def _build_market_ui(self, parent):
        tk.Label(parent, text="市场价格", font=("微软雅黑", 14, "bold"),
                 bg="#ffffff", fg="#333333").pack(anchor="w", padx=16, pady=(16, 8))
        tk.Label(parent, text="查看当前市场商品价格（需连接游戏）", bg="#ffffff",
                 fg="#999999", font=("微软雅黑", 10)).pack(anchor="w", padx=16)
        tk.Button(parent, text="刷新市场价格", command=self._refresh_market,
                  bg="#07C160", fg="white", bd=0, font=("微软雅黑", 11),
                  padx=16, pady=6, cursor="hand2").pack(anchor="w", padx=16, pady=12)
        self.market_text = tk.Text(parent, bg="#fafafa", fg="#333333",
                                    font=("Consolas", 10), bd=1, relief=tk.SOLID,
                                    height=12, width=60)
        self.market_text.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))

    def _refresh_market(self):
        lua = """
        local result = {}
        pcall(function()
            if g_MarketMgr and g_MarketMgr.m_tbGoods then
                for name, info in pairs(g_MarketMgr.m_tbGoods) do
                    table.insert(result, name .. ": " .. tostring(info.m_nPrice or info.price or "?"))
                end
            end
        end)
        if #result == 0 then return "无市场数据" end
        return table.concat(result, "\\n")
        """
        success, result = self.execute_lua(lua)
        self.market_text.delete(1.0, tk.END)
        self.market_text.insert(tk.END, result if success else f"获取失败: {result}")
