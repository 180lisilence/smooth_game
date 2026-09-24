@echo off
cd /d "%~dp0"
echo ============================================================
echo   平野孤鸿 插件化修改器 v0.1.1
echo ============================================================
echo.

REM 检查Python是否可用
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未找到 Python，请先安装 Python 3.10+ 并加入 PATH
    echo.
    pause
    exit /b 1
)

REM 显示Python版本
python --version
echo.

REM 运行程序
python main.py
set EXITCODE=%errorlevel%

if not "%EXITCODE%"=="0" (
    echo.
    echo ============================================================
    echo [ERROR] 程序异常退出，退出码: %EXITCODE%
    echo 请查看上方错误信息
    echo ============================================================
    echo.
    pause
)
