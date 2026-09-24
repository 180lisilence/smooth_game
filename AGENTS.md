# AGENTS.md - smooth_game 开发规范

## 项目定位
平野孤鸿 插件化修改器，A方案轻量级插件化架构。核心壳 + 插件化，核心层只负责注入/通信/UI框架，所有功能以插件形式存在。

## 硬性约束
1. **不写 C 盘**：配置、日志、通信文件、备份全部放在程序目录。`runtime_config_dir()` 是唯一路径来源。
2. **版本号唯一来源**：`core/constants.py` 的 `APP_VERSION`，其他文件不得硬编码版本号。
3. **插件不修改核心代码**：新增功能必须写插件，核心层只在必要时扩展 `BasePlugin` 的服务接口。
4. **通信协议兼容**：与 `woldvein_trainer.dll` 保持兼容（文件轮询 + REQ_ID 前缀），改协议必须同时改 DLL 端。

## 目录规范
```
core/          核心层（不依赖 gui/ 和 plugins/）
gui/           UI层（依赖 core/，不依赖具体插件）
plugins/       插件层（每个插件独立目录，依赖 core/）
dist/          构建产物（DLL/EXE）
assets/        资源文件
logs/          日志文件（自动生成，不提交）
```

## 插件开发规范
1. 每个插件目录必须包含 `plugin.json` + `main.py` + `__init__.py`
2. `main.py` 必须定义 `Plugin` 类，继承 `BasePlugin`
3. 必须实现 `get_menu_items()` 和 `build_ui(parent, item_id)`
4. 插件通过 `self.execute_lua()` 等核心服务与游戏交互，不得直接 import `core.lua_engine`
5. 插件专属设置通过 `self.save_plugin_settings()` 保存，不得直接写 config.json

## 代码规范
- Python 3.10+，使用类型注解
- 中文界面，英文代码注释
- 日志使用 `core.logger`，不得直接 print
- 错误处理：Lua 执行必须检查返回值，UI 操作必须 try/except

## 验证清单
提交前必须通过：
1. `python -m py_compile` 全部 .py 文件
2. 插件加载测试：6个插件全部加载成功
3. UI构建测试：21个菜单项全部能构建右侧面板
4. 主窗口初始化测试：创建/导航切换/销毁无异常
