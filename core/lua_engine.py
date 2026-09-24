"""
Lua 执行引擎。

通过文件轮询机制与注入游戏的 DLL 通信：
    Python 写 lua_cmd.txt → DLL 检测并执行 → DLL 写 lua_result.txt → Python 读取结果

通信格式（带请求 ID 竞态防护）：
    命令文件第一行: REQ_ID:xxxxxxxx
    命令文件第二行起: Lua 代码
    结果文件第一行: REQ_ID:xxxxxxxx
    结果文件第二行起: 执行结果
"""
import os
import time
import uuid
import tempfile
from typing import Tuple, Optional

from core.logger import log_info, log_error, log_warning, log_debug
from core.constants import LUA_TIMEOUT, runtime_config_dir

# 通信文件目录（与 DLL 一致：DLL 所在目录，不写C盘）
# DLL 在 DllMain 中通过 GetModuleFileNameA 获取自身路径，通信文件放在同目录
_comm_dir = None


def _get_comm_dir() -> str:
    """获取通信文件目录，确保存在。
    与 DLL 内部逻辑一致：使用程序目录（DLL所在目录）。
    """
    global _comm_dir
    if _comm_dir:
        return _comm_dir
    # DLL 在 dist/ 目录下，通信文件与 DLL 同目录
    from core.constants import DIST_DIR
    _comm_dir = DIST_DIR
    os.makedirs(_comm_dir, exist_ok=True)
    return _comm_dir


def _get_cmd_path() -> str:
    return os.path.join(_get_comm_dir(), "lua_cmd.txt")


def _get_result_path() -> str:
    return os.path.join(_get_comm_dir(), "lua_result.txt")


def _gen_request_id() -> str:
    """生成 8 位十六进制请求 ID。"""
    return uuid.uuid4().hex[:8]


def _cleanup_files():
    """清理旧的通信文件。"""
    for path in (_get_cmd_path(), _get_result_path()):
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass


def execute_lua(code: str, timeout: float = LUA_TIMEOUT) -> Tuple[bool, str]:
    """
    执行 Lua 代码。返回 (success, result)。
    success=True 表示 DLL 成功执行并返回了结果；result 为结果字符串。
    success=False 表示超时或出错；result 为错误信息。
    """
    if not code or not code.strip():
        return False, "Lua 代码为空"

    req_id = _gen_request_id()
    cmd_path = _get_cmd_path()
    result_path = _get_result_path()

    # 1. 清理旧文件
    try:
        if os.path.exists(cmd_path):
            os.remove(cmd_path)
        if os.path.exists(result_path):
            os.remove(result_path)
    except Exception as e:
        log_warning(f"清理旧通信文件失败: {e}")

    # 2. 写入命令文件（第一行请求ID，第二行起Lua代码）
    try:
        content = f"REQ_ID:{req_id}\n{code}"
        with open(cmd_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        return False, f"写入命令文件失败: {e}"

    # 3. 轮询等待结果文件
    start_time = time.time()
    while time.time() - start_time < timeout:
        if os.path.exists(result_path):
            # 稍等一下确保 DLL 写完
            time.sleep(0.05)
            try:
                with open(result_path, "r", encoding="utf-8") as f:
                    lines = f.read().splitlines()
                if not lines:
                    time.sleep(0.1)
                    continue
                # 校验请求 ID
                result_id_line = lines[0].strip()
                if result_id_line.startswith("REQ_ID:"):
                    result_id = result_id_line[7:].strip()
                    if result_id != req_id:
                        log_debug(f"请求ID不匹配，继续等待 (期望={req_id}, 实际={result_id})")
                        time.sleep(0.1)
                        continue
                result_content = "\n".join(lines[1:]) if len(lines) > 1 else ""
                # 清理
                try:
                    os.remove(cmd_path)
                    os.remove(result_path)
                except Exception:
                    pass
                return True, result_content
            except Exception as e:
                log_warning(f"读取结果文件失败: {e}")
                time.sleep(0.1)
        time.sleep(0.05)

    # 超时
    try:
        if os.path.exists(cmd_path):
            os.remove(cmd_path)
    except Exception:
        pass
    return False, f"执行超时（{timeout}s），DLL 未返回结果。请确认游戏已连接且 DLL 已注入。"


def execute_lua_safe(code: str, timeout: float = LUA_TIMEOUT) -> Tuple[bool, str]:
    """execute_lua 的别名，语义相同。"""
    return execute_lua(code, timeout)


def execute_lua_retry(code: str, timeout: float = LUA_TIMEOUT,
                      attempts: int = 2, expect: tuple = None) -> Tuple[bool, str]:
    """
    带重试的 Lua 执行。
    expect: 结果前缀元组，如 ("[成功]", "{")，结果匹配任一前缀才算成功。
            None 表示不检查前缀，只要 DLL 返回了结果就算成功。
    """
    last_result = ""
    for i in range(attempts):
        success, result = execute_lua(code, timeout)
        last_result = result
        if success:
            if expect is None:
                return True, result
            for prefix in expect:
                if result.startswith(prefix):
                    return True, result
            log_debug(f"结果前缀不匹配，重试 ({i+1}/{attempts}): {result[:50]}")
        time.sleep(0.2)
    return False, last_result or "执行失败"


def ping_dll(timeout: float = 2.0) -> bool:
    """检测 DLL 是否可通信（发送一条简单 Lua 命令）。"""
    success, _ = execute_lua("return 1", timeout)
    return success



