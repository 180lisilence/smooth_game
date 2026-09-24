"""
高级工具插件。

时间跳转、天气控制、鸿业诊断、天赋诊断。
"""
import tkinter as tk
from typing import List

from core.base_plugin import BasePlugin, MenuItem


class Plugin(BasePlugin):
    plugin_id = "advanced_tools"
    name = "高级工具"
    version = "1.0.0"
    author = "smooth_game"
    description = "时间跳转/天气/诊断工具"
    category = "高级"
    priority = 40

    def on_load(self):
        self.log("高级工具插件已加载")

    def get_menu_items(self) -> List[MenuItem]:
        return [
            MenuItem("time_skip", "时间跳转", "跳转到指定日期", "高级"),
            MenuItem("weather", "天气控制", "设置当前天气", "高级"),
            MenuItem("boom_diagnose", "鸿业诊断", "诊断鸿业系统状态", "高级"),
            MenuItem("talent_diagnose", "天赋诊断", "诊断天赋系统状态", "高级"),
        ]

    def build_ui(self, parent, item_id: str):
        if item_id == "time_skip":
            self._build_time_skip_ui(parent)
        elif item_id == "weather":
            self._build_weather_ui(parent)
        elif item_id == "boom_diagnose":
            self._build_boom_diag_ui(parent)
        elif item_id == "talent_diagnose":
            self._build_talent_diag_ui(parent)

    def _build_time_skip_ui(self, parent):
        tk.Label(parent, text="时间跳转", font=("微软雅黑", 14, "bold"),
                 bg="#ffffff", fg="#333333").pack(anchor="w", padx=16, pady=(16, 8))
        tk.Label(parent, text="跳转到指定的年/月/日", bg="#ffffff",
                 fg="#999999", font=("微软雅黑", 10)).pack(anchor="w", padx=16)

        input_frame = tk.Frame(parent, bg="#ffffff")
        input_frame.pack(anchor="w", padx=16, pady=12)
        tk.Label(input_frame, text="年:", bg="#ffffff", font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.year_var = tk.StringVar(value="1")
        tk.Entry(input_frame, textvariable=self.year_var, width=6, font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=4)
        tk.Label(input_frame, text="月:", bg="#ffffff", font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=(8, 0))
        self.month_var = tk.StringVar(value="1")
        tk.Entry(input_frame, textvariable=self.month_var, width=4, font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=4)
        tk.Label(input_frame, text="日:", bg="#ffffff", font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=(8, 0))
        self.day_var = tk.StringVar(value="1")
        tk.Entry(input_frame, textvariable=self.day_var, width=4, font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=4)

        tk.Button(parent, text="跳转", command=self._do_time_skip,
                  bg="#07C160", fg="white", bd=0, font=("微软雅黑", 11, "bold"),
                  padx=20, pady=6, cursor="hand2").pack(anchor="w", padx=16, pady=8)
        self.time_skip_result = tk.Label(parent, text="", bg="#ffffff", fg="#07C160",
                                          font=("微软雅黑", 10))
        self.time_skip_result.pack(anchor="w", padx=16)

    def _do_time_skip(self):
        try:
            y, m, d = int(self.year_var.get()), int(self.month_var.get()), int(self.day_var.get())
        except ValueError:
            self.time_skip_result.configure(text="日期格式错误", fg="#f44336")
            return
        lua = f"""
        local ok, err = pcall(function()
            if g_Time and g_Time.m_tb then
                g_Time.m_tb.m_nYear = {y}
                g_Time.m_tb.m_nMonth = {m}
                g_Time.m_tb.m_nDay = {d}
            end
        end)
        if ok then return "[成功]" else return "[失败]:"..tostring(err) end
        """
        success, result = self.execute_lua(lua)
        if success:
            self.time_skip_result.configure(text=f"已跳转到 {y}年{m}月{d}日")
            self.log(f"时间跳转到 {y}年{m}月{d}日", "SUCCESS")
            self.refresh_status()
        else:
            self.time_skip_result.configure(text=f"失败: {result}", fg="#f44336")

    def _build_weather_ui(self, parent):
        tk.Label(parent, text="天气控制", font=("微软雅黑", 14, "bold"),
                 bg="#ffffff", fg="#333333").pack(anchor="w", padx=16, pady=(16, 8))
        tk.Label(parent, text="设置当前天气状态", bg="#ffffff",
                 fg="#999999", font=("微软雅黑", 10)).pack(anchor="w", padx=16)

        btn_frame = tk.Frame(parent, bg="#ffffff")
        btn_frame.pack(anchor="w", padx=16, pady=12)
        for weather in ["晴天", "雨天", "雪天", "阴天"]:
            tk.Button(btn_frame, text=weather, command=lambda w=weather: self._set_weather(w),
                      bg="#e8f5e9", fg="#07C160", bd=0, font=("微软雅黑", 10),
                      padx=12, pady=4, cursor="hand2").pack(side=tk.LEFT, padx=4)
        self.weather_result = tk.Label(parent, text="", bg="#ffffff", fg="#07C160",
                                        font=("微软雅黑", 10))
        self.weather_result.pack(anchor="w", padx=16)

    def _set_weather(self, weather: str):
        lua = f"""
        local ok, err = pcall(function()
            if g_WeatherMgr then
                g_WeatherMgr.m_nWeatherType = {{["晴天"]=0,["雨天"]=1,["雪天"]=2,["阴天"]=3}}["{weather}"] or 0
            end
        end)
        if ok then return "[成功]" else return "[失败]:"..tostring(err) end
        """
        success, result = self.execute_lua(lua)
        msg = f"天气已设为 {weather}" if success else f"失败: {result}"
        self.weather_result.configure(text=msg, fg="#07C160" if success else "#f44336")
        self.log(msg, "SUCCESS" if success else "ERROR")

    def _build_boom_diag_ui(self, parent):
        tk.Label(parent, text="鸿业诊断", font=("微软雅黑", 14, "bold"),
                 bg="#ffffff", fg="#333333").pack(anchor="w", padx=16, pady=(16, 8))
        tk.Button(parent, text="运行诊断", command=self._run_boom_diag,
                  bg="#07C160", fg="white", bd=0, font=("微软雅黑", 11),
                  padx=16, pady=6, cursor="hand2").pack(anchor="w", padx=16, pady=12)
        self.boom_diag_text = tk.Text(parent, bg="#fafafa", fg="#333333",
                                       font=("Consolas", 10), bd=1, relief=tk.SOLID,
                                       height=15, width=60)
        self.boom_diag_text.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))

    def _run_boom_diag(self):
        lua = """
        local lines = {}
        pcall(function()
            if g_camp then
                table.insert(lines, "g_camp: 存在")
                if g_camp.GetCampBoomModule then
                    local bm = g_camp:GetCampBoomModule()
                    table.insert(lines, "BoomModule: " .. tostring(bm ~= nil))
                    if bm then
                        if bm.GetBoom then table.insert(lines, "当前鸿业: " .. tostring(bm:GetBoom())) end
                        if bm.GetProsperityLevel then table.insert(lines, "昌盛等级: " .. tostring(bm:GetProsperityLevel())) end
                    end
                end
            else
                table.insert(lines, "g_camp: 不存在")
            end
        end)
        return table.concat(lines, "\\n")
        """
        success, result = self.execute_lua(lua, timeout=5.0)
        self.boom_diag_text.delete(1.0, tk.END)
        self.boom_diag_text.insert(tk.END, result if success else f"诊断失败: {result}")

    def _build_talent_diag_ui(self, parent):
        tk.Label(parent, text="天赋诊断", font=("微软雅黑", 14, "bold"),
                 bg="#ffffff", fg="#333333").pack(anchor="w", padx=16, pady=(16, 8))
        tk.Button(parent, text="运行诊断", command=self._run_talent_diag,
                  bg="#07C160", fg="white", bd=0, font=("微软雅黑", 11),
                  padx=16, pady=6, cursor="hand2").pack(anchor="w", padx=16, pady=12)
        self.talent_diag_text = tk.Text(parent, bg="#fafafa", fg="#333333",
                                         font=("Consolas", 10), bd=1, relief=tk.SOLID,
                                         height=15, width=60)
        self.talent_diag_text.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))

    def _run_talent_diag(self):
        lua = """
        local lines = {}
        pcall(function()
            if g_TalentMgr then
                table.insert(lines, "TalentMgr: 存在")
                if g_TalentMgr.m_tbTalents then
                    local count = 0
                    for k,v in pairs(g_TalentMgr.m_tbTalents) do count = count + 1 end
                    table.insert(lines, "天赋数量: " .. count)
                end
            else
                table.insert(lines, "TalentMgr: 不存在")
            end
        end)
        return table.concat(lines, "\\n")
        """
        success, result = self.execute_lua(lua, timeout=5.0)
        self.talent_diag_text.delete(1.0, tk.END)
        self.talent_diag_text.insert(tk.END, result if success else f"诊断失败: {result}")
