"""
游戏状态提供者。

统一管理游戏状态的刷新，采用发布-订阅模式：
    - 单一 worker 线程定时刷新状态
    - 插件/UI 通过 get_status() 获取最新快照
    - 避免多个插件各自定时查询导致的并发和竞态问题
"""
import threading
import time
import json
from typing import Dict, Optional, Callable, List

from core.logger import log_info, log_error, log_warning
from core.lua_engine import execute_lua_safe

# 获取游戏状态的 Lua 脚本（返回 JSON 字符串）
LUA_GET_STATUS = r"""
local function safe_get(t, k, default)
    local ok, v = pcall(function() return t[k] end)
    if ok and v ~= nil then return v end
    return default
end

local status = {}
status.connected = true

-- 城市品阶
local boom = 1
pcall(function()
    local camp = g_camp
    if camp and camp.GetCampBoomModule then
        local bm = camp:GetCampBoomModule()
        if bm and bm.GetBoom then boom = bm:GetBoom() end
    end
end)
status.boom_level = boom

-- 人口
local population = 0
pcall(function()
    if g_camp and g_camp.m_nPopulation then population = g_camp.m_nPopulation end
end)
status.population = population

-- 幸福度
local happiness = 0
pcall(function()
    if g_camp and g_camp.m_nHappiness then happiness = g_camp.m_nHappiness end
end)
status.happiness = happiness

-- 金钱
local money = 0
pcall(function()
    if g_camp and g_camp.m_tbSource and g_camp.m_tbSource[1] then
        money = g_camp.m_tbSource[1]
    end
end)
status.money = money

-- 时间
local year, month, day = 1, 1, 1
local season = "春"
pcall(function()
    if g_Time and g_Time.m_tb then
        year = g_Time.m_tb.m_nYear or 1
        month = g_Time.m_tb.m_nMonth or 1
        day = g_Time.m_tb.m_nDay or 1
        local s = g_Time.m_tb.m_nSeason or 0
        local seasons = {"春", "夏", "秋", "冬"}
        season = seasons[(s % 4) + 1] or "春"
    end
end)
status.year = year
status.month = month
status.day = day
status.season = season

-- 建筑数量
local building_count = 0
pcall(function()
    if g_camp and g_camp.m_lsBuilding then
        building_count = #g_camp.m_lsBuilding
    end
end)
status.building_count = building_count

-- 资源表
local resources = {}
pcall(function()
    if g_camp and g_camp.m_tbSource then
        for i = 1, 30 do
            if g_camp.m_tbSource[i] ~= nil then
                resources[i] = g_camp.m_tbSource[i]
            end
        end
    end
end)
status.resources = resources

local cjson = require("cjson.safe")
if cjson then
    return cjson.encode(status)
end
-- 降级：手动拼 JSON
local function esc(s) return tostring(s):gsub("\\", "\\\\"):gsub('"', '\\"') end
local parts = {}
table.insert(parts, '"connected":true')
table.insert(parts, '"boom_level":' .. boom)
table.insert(parts, '"population":' .. population)
table.insert(parts, '"happiness":' .. happiness)
table.insert(parts, '"money":' .. money)
table.insert(parts, '"year":' .. year)
table.insert(parts, '"month":' .. month)
table.insert(parts, '"day":' .. day)
table.insert(parts, '"season":"' .. esc(season) .. '"')
table.insert(parts, '"building_count":' .. building_count)
return "{" .. table.concat(parts, ",") .. "}"
"""


class GameStatusProvider:
    """
    游戏状态提供者（单例模式）。
    单一 worker 线程定时刷新，所有插件共享同一份状态快照。
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._status: Dict = {}
        self._status_lock = threading.Lock()
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False
        self._interval = 3.0  # 刷新间隔（秒）
        self._subscribers: List[Callable] = []
        self._consecutive_failures = 0
        self._dll_ready = False

    def start(self, interval: float = 3.0):
        """启动状态刷新 worker。"""
        if self._running:
            return
        self._interval = interval
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()
        log_info(f"游戏状态刷新已启动（间隔 {interval}s）")

    def stop(self):
        """停止状态刷新。"""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=2.0)
        log_info("游戏状态刷新已停止")

    def set_dll_ready(self, ready: bool):
        """设置 DLL 是否就绪（未就绪时不查询）。"""
        self._dll_ready = ready
        if not ready:
            with self._status_lock:
                self._status = {}

    def get_status(self) -> Dict:
        """获取最新状态快照。"""
        with self._status_lock:
            return dict(self._status)

    def subscribe(self, callback: Callable[[Dict], None]):
        """订阅状态更新，每次刷新后调用 callback(status)。"""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable):
        """取消订阅。"""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def refresh_now(self):
        """请求立即刷新一次（在 worker 线程中执行）。"""
        # 简单实现：设置一个标志，worker 下一轮立即刷新
        self._refresh_requested = True

    def _worker(self):
        """worker 线程主循环。"""
        while self._running:
            try:
                if self._dll_ready:
                    success, result = execute_lua_safe(LUA_GET_STATUS, timeout=3.0)
                    if success and result:
                        self._parse_and_update(result)
                        self._consecutive_failures = 0
                    else:
                        self._consecutive_failures += 1
                        if self._consecutive_failures % 5 == 0:
                            log_warning(f"游戏状态查询连续失败 {self._consecutive_failures} 次")
            except Exception as e:
                log_error(f"状态刷新 worker 异常: {e}")

            # 等待间隔，支持立即刷新请求
            waited = 0
            while waited < self._interval and self._running:
                if getattr(self, "_refresh_requested", False):
                    self._refresh_requested = False
                    break
                time.sleep(0.2)
                waited += 0.2

    def _parse_and_update(self, result: str):
        """解析 Lua 返回的 JSON 字符串并更新状态。"""
        try:
            status = json.loads(result)
            with self._status_lock:
                self._status = status
            # 通知订阅者
            for callback in self._subscribers:
                try:
                    callback(dict(status))
                except Exception as e:
                    log_error(f"状态订阅者回调异常: {e}")
        except json.JSONDecodeError as e:
            log_warning(f"游戏状态 JSON 解析失败: {e}, 原始内容: {result[:100]}")
        except Exception as e:
            log_error(f"更新游戏状态异常: {e}")
