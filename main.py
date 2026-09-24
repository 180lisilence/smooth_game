"""
平野孤鸿 插件化修改器 - 主入口

A方案轻量级插件化架构：
    - core/       核心层（常量/配置/日志/插件基类/插件管理器/注入器/Lua引擎/游戏状态）
    - gui/        UI层（三栏布局主窗口）
    - plugins/    插件层（每个插件独立目录，含 plugin.json + main.py）
    - dist/       构建产物（DLL/EXE）
    - assets/     资源文件
    - logs/       日志文件

启动流程：
    1. 初始化日志和配置
    2. 创建主窗口
    3. 初始化插件管理器，注入核心服务
    4. 扫描并加载所有插件
    5. 启动游戏状态刷新（连接游戏后）
    6. 进入主循环
"""
import sys
import os
import traceback


def main():
    try:
        # 确保项目根目录在 sys.path 中
        project_root = os.path.dirname(os.path.abspath(__file__))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        from core.constants import APP_NAME, APP_VERSION, APP_DISPLAY_NAME
        from core.logger import log_info, log_error

        log_info("=" * 60)
        log_info(f"{APP_DISPLAY_NAME} v{APP_VERSION} 启动")
        log_info("=" * 60)

        from gui.main_window import MainWindow
        app = MainWindow()
        app.run()

    except Exception as e:
        error_msg = f"程序启动失败: {e}\n{traceback.format_exc()}"
        print(error_msg)
        try:
            from core.logger import log_error
            log_error(error_msg)
        except Exception:
            pass
        # 尝试显示错误对话框
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("启动失败", f"程序启动失败:\n{e}")
            root.destroy()
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
