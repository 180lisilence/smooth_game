"""
DLL 注入器。

使用标准 Windows 远程线程注入法（CreateRemoteThread + LoadLibraryW）。
职责：查找游戏进程、注入 DLL、检测注入状态、启动游戏。
"""
import os
import ctypes
import ctypes.wintypes
import time
from typing import Optional, Tuple

from core.logger import log_info, log_error, log_warning
from core.constants import DEFAULT_GAME_PATH, GAME_EXE_REL, STEAM_RUN_URL

# Windows API
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)

PROCESS_ALL_ACCESS = 0x1F0FFF
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
PAGE_READWRITE = 0x04


def find_game_process(game_exe_name: str = "BalladsOfHongye.exe") -> Tuple[Optional[int], Optional[int]]:
    """
    查找游戏进程。返回 (pid, process_handle) 或 (None, None)。
    process_handle 用完需 CloseHandle。
    """
    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_READ = 0x0010

    class PROCESSENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", ctypes.wintypes.DWORD),
            ("cntUsage", ctypes.wintypes.DWORD),
            ("th32ProcessID", ctypes.wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
            ("th32ModuleID", ctypes.wintypes.DWORD),
            ("cntThreads", ctypes.wintypes.DWORD),
            ("th32ParentProcessID", ctypes.wintypes.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", ctypes.wintypes.DWORD),
            ("szExeFile", ctypes.c_char * 260),
        ]

    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)  # TH32CS_SNAPPROCESS
    if snapshot == -1:
        log_error("CreateToolhelp32Snapshot 失败")
        return None, None

    entry = PROCESSENTRY32()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32)

    found_pid = None
    if kernel32.Process32First(snapshot, ctypes.byref(entry)):
        while True:
            exe_name = entry.szExeFile.decode("gbk", errors="ignore")
            if exe_name.lower() == game_exe_name.lower():
                found_pid = entry.th32ProcessID
                break
            if not kernel32.Process32Next(snapshot, ctypes.byref(entry)):
                break

    kernel32.CloseHandle(snapshot)

    if found_pid is None:
        return None, None

    h_process = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, found_pid)
    if h_process == 0:
        log_error(f"OpenProcess 失败 (PID={found_pid})")
        return found_pid, None

    return found_pid, h_process


def is_dll_injected(pid: int, dll_name: str = "woldvein_trainer.dll") -> bool:
    """检查指定进程是否已注入指定 DLL。"""
    if pid is None:
        return False

    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_READ = 0x0010

    h_process = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if h_process == 0:
        return False

    class MODULEENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", ctypes.wintypes.DWORD),
            ("th32ModuleID", ctypes.wintypes.DWORD),
            ("th32ProcessID", ctypes.wintypes.DWORD),
            ("GlblcntUsage", ctypes.wintypes.DWORD),
            ("ProccntUsage", ctypes.wintypes.DWORD),
            ("modBaseAddr", ctypes.POINTER(ctypes.c_byte)),
            ("modBaseSize", ctypes.wintypes.DWORD),
            ("hModule", ctypes.wintypes.HMODULE),
            ("szModule", ctypes.c_char * 256),
            ("szExePath", ctypes.c_char * 260),
        ]

    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000018, pid)  # TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32
    if snapshot == -1:
        kernel32.CloseHandle(h_process)
        return False

    entry = MODULEENTRY32()
    entry.dwSize = ctypes.sizeof(MODULEENTRY32)
    found = False

    if kernel32.Module32First(snapshot, ctypes.byref(entry)):
        while True:
            mod_name = entry.szModule.decode("gbk", errors="ignore")
            if mod_name.lower() == dll_name.lower():
                found = True
                break
            if not kernel32.Module32Next(snapshot, ctypes.byref(entry)):
                break

    kernel32.CloseHandle(snapshot)
    kernel32.CloseHandle(h_process)
    return found


def inject_dll(pid: int, dll_path: str) -> bool:
    """
    向指定进程注入 DLL。
    使用 CreateRemoteThread + LoadLibraryW 标准方法。
    """
    if not os.path.exists(dll_path):
        log_error(f"DLL 文件不存在: {dll_path}")
        return False

    h_process = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    if h_process == 0:
        log_error(f"OpenProcess 失败 (PID={pid})")
        return False

    try:
        # 1. 在游戏进程中分配内存，存放 DLL 路径
        dll_path_w = ctypes.create_unicode_buffer(dll_path)
        path_size = ctypes.sizeof(dll_path_w)
        remote_mem = kernel32.VirtualAllocEx(
            h_process, None, path_size,
            MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE
        )
        if remote_mem is None or remote_mem == 0:
            log_error("VirtualAllocEx 失败")
            return False

        # 2. 写入 DLL 路径
        written = ctypes.c_size_t(0)
        if not kernel32.WriteProcessMemory(
            h_process, remote_mem, dll_path_w, path_size, ctypes.byref(written)
        ):
            log_error("WriteProcessMemory 失败")
            kernel32.VirtualFreeEx(h_process, remote_mem, 0, 0x8000)  # MEM_RELEASE
            return False

        # 3. 获取 LoadLibraryW 地址
        # kernel32.dll 在所有 Windows 进程中加载地址相同，直接从当前进程获取即可
        try:
            load_lib_addr = ctypes.cast(kernel32.LoadLibraryW, ctypes.c_void_p).value
        except Exception:
            # 备用方式：通过 GetModuleHandleW + GetProcAddress
            h_kernel32 = kernel32.GetModuleHandleW("kernel32.dll")
            load_lib_addr = kernel32.GetProcAddress(h_kernel32, b"LoadLibraryW")
        if not load_lib_addr:
            log_error("获取 LoadLibraryW 地址失败")
            kernel32.VirtualFreeEx(h_process, remote_mem, 0, 0x8000)
            return False

        # 4. 创建远程线程
        h_thread = kernel32.CreateRemoteThread(
            h_process, None, 0, load_lib_addr, remote_mem, 0, None
        )
        if h_thread is None or h_thread == 0:
            log_error("CreateRemoteThread 失败")
            kernel32.VirtualFreeEx(h_process, remote_mem, 0, 0x8000)
            return False

        # 5. 等待线程完成（超时 10 秒）
        wait_result = kernel32.WaitForSingleObject(h_thread, 10000)
        if wait_result != 0:  # WAIT_OBJECT_0
            log_error(f"等待远程线程超时或失败 (result={wait_result})")
            kernel32.CloseHandle(h_thread)
            kernel32.VirtualFreeEx(h_process, remote_mem, 0, 0x8000)
            return False

        # 6. 获取线程退出码（即 LoadLibraryW 返回值，DLL 模块句柄）
        exit_code = ctypes.c_ulong(0)
        kernel32.GetExitCodeThread(h_thread, ctypes.byref(exit_code))

        kernel32.CloseHandle(h_thread)
        kernel32.VirtualFreeEx(h_process, remote_mem, 0, 0x8000)

        if exit_code.value == 0:
            log_error("LoadLibraryW 返回 NULL，DLL 加载失败")
            return False

        log_info(f"DLL 注入成功 (PID={pid}, module=0x{exit_code.value:X})")
        return True

    finally:
        kernel32.CloseHandle(h_process)


def launch_game(game_path: str = DEFAULT_GAME_PATH) -> bool:
    """通过 Steam 协议启动游戏。"""
    try:
        os.startfile(STEAM_RUN_URL)
        log_info(f"已通过 Steam 启动游戏: {STEAM_RUN_URL}")
        return True
    except Exception as e:
        log_error(f"启动游戏失败: {e}")
        return False


def wait_for_game(timeout: int = 30, game_exe_name: str = "BalladsOfHongye.exe") -> Optional[int]:
    """等待游戏进程出现，超时返回 None。"""
    log_info(f"等待游戏启动（超时 {timeout}s）...")
    start = time.time()
    while time.time() - start < timeout:
        pid, _ = find_game_process(game_exe_name)
        if pid:
            log_info(f"游戏进程已启动 (PID={pid})")
            return pid
        time.sleep(1)
    log_warning("等待游戏启动超时")
    return None

