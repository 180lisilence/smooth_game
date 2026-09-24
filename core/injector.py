"""
DLL 注入器。

使用标准 Windows 远程线程注入法（CreateRemoteThread + LoadLibraryW）。
职责：查找游戏进程、注入 DLL、检测注入状态、启动游戏。

技术要点：
- 所有 Windows API 显式设置 argtypes/restype，防止64位句柄/指针被截断
- 使用 LoadLibraryW（Unicode），支持中文路径
- kernel32.dll 在所有进程中加载地址相同，直接从当前进程获取函数地址
"""
import os
import ctypes
from ctypes import wintypes
import time
from typing import Optional, Tuple

from core.logger import log_info, log_error, log_warning
from core.constants import DEFAULT_GAME_PATH, GAME_EXE_REL, STEAM_RUN_URL

# Windows API
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)

# === 显式设置 ctypes 函数原型（64位下防止句柄/指针被截断为c_int）===
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE

kernel32.VirtualAllocEx.argtypes = [wintypes.HANDLE, wintypes.LPVOID, ctypes.c_size_t, wintypes.DWORD, wintypes.DWORD]
kernel32.VirtualAllocEx.restype = wintypes.LPVOID

kernel32.VirtualFreeEx.argtypes = [wintypes.HANDLE, wintypes.LPVOID, ctypes.c_size_t, wintypes.DWORD]
kernel32.VirtualFreeEx.restype = wintypes.BOOL

kernel32.WriteProcessMemory.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.LPCVOID, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
kernel32.WriteProcessMemory.restype = wintypes.BOOL

kernel32.CreateRemoteThread.argtypes = [wintypes.HANDLE, wintypes.LPVOID, ctypes.c_size_t, wintypes.LPVOID, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
kernel32.CreateRemoteThread.restype = wintypes.HANDLE

kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel32.WaitForSingleObject.restype = wintypes.DWORD

kernel32.GetExitCodeThread.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
kernel32.GetExitCodeThread.restype = wintypes.BOOL

kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL

kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE

kernel32.GetProcAddress.argtypes = [wintypes.HMODULE, wintypes.LPCSTR]
kernel32.GetProcAddress.restype = wintypes.LPVOID

kernel32.LoadLibraryW.argtypes = [wintypes.LPCWSTR]
kernel32.LoadLibraryW.restype = wintypes.HMODULE

kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE

kernel32.Process32First.argtypes = [wintypes.HANDLE, wintypes.LPVOID]
kernel32.Process32First.restype = wintypes.BOOL

kernel32.Process32Next.argtypes = [wintypes.HANDLE, wintypes.LPVOID]
kernel32.Process32Next.restype = wintypes.BOOL

kernel32.Module32First.argtypes = [wintypes.HANDLE, wintypes.LPVOID]
kernel32.Module32First.restype = wintypes.BOOL

kernel32.Module32Next.argtypes = [wintypes.HANDLE, wintypes.LPVOID]
kernel32.Module32Next.restype = wintypes.BOOL

# 常量
PROCESS_ALL_ACCESS = 0x1F0FFF
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
MEM_RELEASE = 0x8000
PAGE_READWRITE = 0x04
WAIT_OBJECT_0 = 0x00000000
WAIT_TIMEOUT = 0x00000102
STILL_ACTIVE = 259

def find_game_process(game_exe_name: str = "BalladsOfHongye.exe") -> Tuple[Optional[int], Optional[int]]:
    """
    查找游戏进程。返回 (pid, process_handle) 或 (None, None)。
    process_handle 用完需 CloseHandle。
    """
    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_READ = 0x0010

    class PROCESSENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", ctypes.c_char * 260),
        ]

    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)  # TH32CS_SNAPPROCESS
    if snapshot == -1 or snapshot is None:
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
    if not h_process:
        error = ctypes.get_last_error()
        log_error(f"OpenProcess 失败 (PID={found_pid}, error={error})")
        return found_pid, None

    return found_pid, h_process


def is_dll_injected(pid: int, dll_name: str = "woldvein_trainer.dll") -> bool:
    """检查指定进程是否已注入指定 DLL。"""
    if pid is None:
        return False

    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_VM_READ = 0x0010

    h_process = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h_process:
        return False

    class MODULEENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("th32ModuleID", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("GlblcntUsage", wintypes.DWORD),
            ("ProccntUsage", wintypes.DWORD),
            ("modBaseAddr", ctypes.POINTER(ctypes.c_byte)),
            ("modBaseSize", wintypes.DWORD),
            ("hModule", wintypes.HMODULE),
            ("szModule", ctypes.c_char * 256),
            ("szExePath", ctypes.c_char * 260),
        ]

    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000018, pid)  # TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32
    if snapshot == -1 or snapshot is None:
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
    dll_path = os.path.abspath(dll_path)
    if not os.path.exists(dll_path):
        log_error(f"DLL 文件不存在: {dll_path}")
        return False

    dll_name = os.path.basename(dll_path)

    # 检查是否已注入
    if is_dll_injected(pid, dll_name):
        log_info(f"DLL 已注入: {dll_name}")
        return True

    log_info(f"开始注入 DLL: {dll_path} -> PID={pid}")

    h_process = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    if not h_process:
        error = ctypes.get_last_error()
        log_error(f"OpenProcess 失败 (PID={pid}, error={error})")
        return False

    try:
        # 1. 在游戏进程中分配内存，存放 DLL 路径（UTF-16-LE，支持中文路径）
        dll_path_bytes = dll_path.encode("utf-16-le") + b"\x00\x00"
        path_size = len(dll_path_bytes)
        remote_mem = kernel32.VirtualAllocEx(
            h_process, None, path_size,
            MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE
        )
        if not remote_mem:
            error = ctypes.get_last_error()
            log_error(f"VirtualAllocEx 失败 (error={error})")
            return False

        # 2. 写入 DLL 路径
        dll_path_buf = ctypes.create_string_buffer(dll_path_bytes)
        written = ctypes.c_size_t(0)
        if not kernel32.WriteProcessMemory(
            h_process, remote_mem, dll_path_buf, path_size, ctypes.byref(written)
        ) or written.value != path_size:
            error = ctypes.get_last_error()
            log_error(f"WriteProcessMemory 失败 (error={error})")
            kernel32.VirtualFreeEx(h_process, remote_mem, 0, MEM_RELEASE)
            return False

        # 3. 获取 LoadLibraryW 地址
        # kernel32.dll 在所有 Windows 进程中加载地址相同，直接从当前进程获取
        try:
            load_lib_addr = ctypes.cast(kernel32.LoadLibraryW, ctypes.c_void_p).value
        except Exception:
            h_kernel32 = kernel32.GetModuleHandleW("kernel32.dll")
            load_lib_addr = kernel32.GetProcAddress(h_kernel32, b"LoadLibraryW")
        if not load_lib_addr:
            error = ctypes.get_last_error()
            log_error(f"获取 LoadLibraryW 地址失败 (error={error})")
            kernel32.VirtualFreeEx(h_process, remote_mem, 0, MEM_RELEASE)
            return False

        # 4. 创建远程线程
        thread_id = wintypes.DWORD(0)
        h_thread = kernel32.CreateRemoteThread(
            h_process, None, 0,
            load_lib_addr,
            remote_mem, 0, ctypes.byref(thread_id)
        )
        if not h_thread:
            error = ctypes.get_last_error()
            log_error(f"CreateRemoteThread 失败 (error={error})")
            kernel32.VirtualFreeEx(h_process, remote_mem, 0, MEM_RELEASE)
            return False

        # 5. 等待线程完成（超时 10 秒）
        wait_result = kernel32.WaitForSingleObject(h_thread, 10000)
        if wait_result == WAIT_TIMEOUT:
            log_warning("等待远程线程超时（10秒），DLL可能仍在加载中")
            kernel32.CloseHandle(h_thread)
            # 不释放远程内存，否则DLL加载会崩溃
            return False
        elif wait_result != WAIT_OBJECT_0:
            error = ctypes.get_last_error()
            log_error(f"WaitForSingleObject 失败 (result={wait_result}, error={error})")
            kernel32.CloseHandle(h_thread)
            kernel32.VirtualFreeEx(h_process, remote_mem, 0, MEM_RELEASE)
            return False

        # 6. 获取线程退出码（即 LoadLibraryW 返回值，DLL 模块句柄）
        exit_code = wintypes.DWORD(0)
        if not kernel32.GetExitCodeThread(h_thread, ctypes.byref(exit_code)):
            error = ctypes.get_last_error()
            log_error(f"GetExitCodeThread 失败 (error={error})")
            kernel32.CloseHandle(h_thread)
            kernel32.VirtualFreeEx(h_process, remote_mem, 0, MEM_RELEASE)
            return False

        kernel32.CloseHandle(h_thread)
        kernel32.VirtualFreeEx(h_process, remote_mem, 0, MEM_RELEASE)

        if exit_code.value == 0:
            log_error("LoadLibraryW 返回 NULL，DLL 加载失败（可能DLL依赖缺失或版本不匹配）")
            return False
        if exit_code.value == STILL_ACTIVE:
            log_warning("远程线程仍在运行中，DLL加载未完成")
            return False

        # 7. 验证 DLL 是否加载
        if is_dll_injected(pid, dll_name):
            log_info(f"DLL 注入成功 (PID={pid}, module=0x{exit_code.value:X})")
            return True
        else:
            log_warning("DLL注入后未在进程模块列表中找到")
            return False

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
