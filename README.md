# 平野孤鸿 插件化修改器 smooth_game v0.1.1

专为西山居城建经营游戏《平野孤鸿》(BalladsOfHongye, Steam AppID 2656540) 开发的游戏修改工具。

**核心架构：核心壳 + 插件化** — 核心层只负责注入/通信/UI框架，所有功能以插件形式存在，新增功能无需修改核心代码。

纯内存操作 · DLL 注入 · Lua 执行引擎 · 微信三栏布局 · 插件化架构 · 6个内置插件 · 21个功能项

---

## 目录

- [软件简介](#软件简介)
- [功能大全](#功能大全)
- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [插件开发指南](#插件开发指南)
- [通信协议](#通信协议)
- [技术栈](#技术栈)
- [版本历史](#版本历史)

---

## 软件简介

本版本采用 **A方案（轻量级插件化）** 架构：

- **核心层** (`core/`)：常量、配置、日志、插件基类、插件管理器、DLL注入器、Lua执行引擎、游戏状态提供者
- **UI层** (`gui/`)：微信三栏布局主窗口（左侧导航 / 中间功能列表 / 右侧操作面板 / 底部日志）
- **插件层** (`plugins/`)：每个功能独立成插件，含 `plugin.json` 元数据 + `main.py` 插件逻辑

**设计取舍**：
- 插件是标准 Python 类，不做 import 沙箱（Python 做不到真正沙箱）
- 插件加载后常驻直到程序退出，不做热更新
- 通信协议与 woldvein_trainer.dll 兼容（文件轮询 + REQ_ID 前缀）
- 配置/日志/通信文件全部放在程序目录，**不写 C 盘**

---

## 功能大全

### 1. 资源修改（4项）
- 一键全部资源：所有资源各 +100万（人口除外）
- 资源列表：查看和修改每种资源，支持自定义数量
- 幸福度最大：幸福度设为 999
- 知名度 +1万：增加 10,000 知名度

### 2. 创造模式（3项）
- 创造模式开关：9项开关（最大鸿业/解锁全部建筑/无限资源/升级无限制/道路绕行/人口通用/GM标志/无灾害伤害/无灾害）
- 全部开启：一键开启所有创造模式
- 全部关闭：一键关闭所有创造模式

### 3. 世界系统（4项）
- 关闭所有灾害：禁用洪水/沙尘暴/龙卷风/地震等全部灾害
- 自动纳税：一键完成当前周期纳税
- 时间流速：设置游戏时间速度（0.05x ~ 60x）
- 市场价格：查看当前市场商品价格

### 4. 高级工具（4项）
- 时间跳转：跳转到指定的年/月/日
- 天气控制：设置当前天气（晴天/雨天/雪天/阴天）
- 鸿业诊断：诊断鸿业系统状态
- 天赋诊断：诊断天赋系统状态

### 5. 游戏监控（2项）
- 实时状态：实时显示品阶/人口/幸福度/金钱/时间/建筑数（2秒自动刷新）
- 资源监控：监控所有资源数值变化（2秒自动刷新）

### 6. 存档管理（4项）
- 存档列表：自动识别存档，支持备份单个存档
- 一键备份：备份整个存档目录
- 打开存档文件夹：在资源管理器中打开存档目录
- 打开备份文件夹：在资源管理器中打开备份目录

---

## 快速开始

### 环境要求
- Windows 10/11
- Python 3.10 或更高
- 游戏《平野孤鸿》已安装（默认路径 `D:\steam\steamapps\common\BalladsOfHongye_CN`）

### 运行
1. 确保 `dist/woldvein_trainer.dll` 存在
2. 双击 `启动修改器.bat`，或命令行运行 `python main.py`
3. 在主页点击「启动游戏」→「检测进程」→「注入 DLL」
4. 左侧导航切换页面，中间列表点击功能项，右侧面板操作

### 配置
配置文件 `config.json` 自动保存在程序目录（不写 C 盘）。主要配置项：
- `game_path`：游戏安装路径
- `dll_path`：DLL 路径（留空则使用 `dist/woldvein_trainer.dll`）
- `window`：窗口大小和位置（自动保存）
- `plugins.enabled`：插件启用/禁用状态
- `plugins.settings`：各插件的专属设置

---

## 项目结构

```
smooth_game0.1.1/
├── main.py                    # 程序入口
├── 启动修改器.bat               # 启动脚本
├── config.json                # 运行时配置（自动生成）
├── README.md                  # 本文件
├── requirements.txt           # Python 依赖
│
├── core/                      # 核心层
│   ├── __init__.py
│   ├── constants.py           # 全局常量（版本/路径/游戏数值）
│   ├── config.py              # 配置管理（深合并/插件设置存取）
│   ├── logger.py              # 日志系统（控制台+文件+GUI回调）
│   ├── base_plugin.py         # BasePlugin 抽象类 + MenuItem
│   ├── plugin_manager.py      # 插件管理器（扫描/加载/排序/生命周期）
│   ├── injector.py            # DLL 注入器（进程查找/注入/启动游戏）
│   ├── lua_engine.py          # Lua 执行引擎（文件轮询+请求ID竞态防护）
│   └── game_status.py         # 游戏状态提供者（单例+发布订阅+3秒刷新）
│
├── gui/                       # UI 层
│   ├── __init__.py
│   └── main_window.py         # 三栏布局主窗口
│
├── plugins/                   # 插件层
│   ├── resource_modifier/     # 资源修改
│   │   ├── plugin.json
│   │   ├── main.py
│   │   └── __init__.py
│   ├── creative_mode/         # 创造模式
│   ├── world_tools/           # 世界系统
│   ├── advanced_tools/        # 高级工具
│   ├── game_monitor/          # 游戏监控
│   └── save_manager/          # 存档管理
│
├── dist/                      # 构建产物
│   └── woldvein_trainer.dll   # 修改器 DLL
│
├── assets/                    # 资源文件
└── logs/                      # 日志文件（自动生成）
```

---

## 插件开发指南

### 第一步：创建插件目录
在 `plugins/` 下新建目录，例如 `plugins/my_plugin/`

### 第二步：编写 plugin.json
```json
{
    "plugin_id": "my_plugin",
    "name": "我的插件",
    "version": "1.0.0",
    "author": "你的名字",
    "description": "插件功能描述",
    "category": "分类名",
    "priority": 100,
    "enabled_by_default": true
}
```

### 第三步：编写 main.py
```python
import tkinter as tk
from typing import List
from core.base_plugin import BasePlugin, MenuItem

class Plugin(BasePlugin):
    plugin_id = "my_plugin"
    name = "我的插件"
    version = "1.0.0"
    category = "分类名"
    priority = 100

    def on_load(self):
        self.log("插件已加载")

    def get_menu_items(self) -> List[MenuItem]:
        return [
            MenuItem("func1", "功能一", "功能一描述", "分类名"),
        ]

    def build_ui(self, parent, item_id: str):
        if item_id == "func1":
            tk.Label(parent, text="这是功能一").pack()
            tk.Button(parent, text="执行", command=self._do_something).pack()

    def _do_something(self):
        success, result = self.execute_lua("return 1")
        self.log(f"执行结果: {result}")
```

### 第四步：重启程序
插件管理器会自动扫描并加载新插件，无需修改核心代码。

### 插件可用的核心服务
| 方法 | 说明 |
|------|------|
| `self.execute_lua(code, timeout=5.0)` | 执行 Lua 代码，返回 (success, result) |
| `self.get_game_status()` | 获取最新游戏状态快照 |
| `self.log(msg, level="INFO")` | 写日志 |
| `self.get_config()` | 获取全局配置 |
| `self.get_plugin_settings()` | 获取插件专属设置 |
| `self.save_plugin_settings(settings)` | 保存插件专属设置 |
| `self.register_hotkey(hotkey, callback)` | 注册热键 |
| `self.unregister_hotkey(hotkey)` | 注销热键 |
| `self.show_toast(msg, duration=2000)` | 显示轻量通知 |
| `self.refresh_status()` | 请求刷新游戏状态 |

### 插件生命周期
| 方法 | 时机 |
|------|------|
| `on_load()` | 插件加载时调用 |
| `on_unload()` | 插件卸载时调用 |
| `on_game_connected()` | 游戏连接成功（DLL注入完成）时调用 |
| `on_game_disconnected()` | 游戏断开时调用 |

---

## 通信协议

Python 与 DLL 通过文件轮询机制通信：

1. Python 写 `comm/lua_cmd.txt`：第一行 `REQ_ID:xxxxxxxx`，第二行起 Lua 代码
2. DLL 每 50ms 检测命令文件，读取后执行
3. DLL 写 `comm/lua_result.txt`：第一行 `REQ_ID:xxxxxxxx`，第二行起执行结果
4. Python 轮询结果文件，校验 REQ_ID 匹配后读取结果

**请求 ID 竞态防护**：每次命令生成 8 位十六进制唯一 ID，结果文件 ID 不匹配则继续等待，避免读到上一条命令的残留结果。

通信文件目录：程序目录下 `comm/` 子目录（不写 C 盘）。

---

## 技术栈

| 组件 | 技术 |
|------|------|
| 语言 | Python 3.10+ |
| GUI | tkinter（微信三栏布局） |
| DLL 注入 | CreateRemoteThread + LoadLibraryW |
| 通信 | 文件轮询 + REQ_ID 竞态防护 |
| 游戏交互 | Lua 脚本执行（DLL Hook lua_pcall） |
| 架构 | 核心壳 + 插件化（A方案轻量级） |

---

## 版本历史

### v0.1.1 (2026-09-24) — 当前版本
- 新增：A方案轻量级插件化架构
- 新增：核心层（constants/config/logger/base_plugin/plugin_manager/injector/lua_engine/game_status）
- 新增：微信三栏布局主窗口（左侧导航/中间功能列表/右侧操作面板/底部日志）
- 新增：6个内置插件（资源修改/创造模式/世界系统/高级工具/游戏监控/存档管理）
- 新增：21个功能项
- 新增：插件开发指南
- 优化：配置/日志/通信文件全部放在程序目录，不写 C 盘
- 优化：游戏状态单例 + 发布订阅，避免多插件并发查询
- 兼容：通信协议与 woldvein_trainer.dll 兼容
