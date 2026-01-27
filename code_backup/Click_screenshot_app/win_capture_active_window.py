
# -*- coding: utf-8 -*-
"""
Windows 截取当前活动窗口并自动保存到指定目录：
- 支持全局热键（默认：Ctrl+Alt+S）
- 支持悬浮按钮（Always on Top），点击后自动截取
- 进程优先级提升至 HIGH_PRIORITY_CLASS（可选）
"""

import os
import time
import ctypes
import threading
from datetime import datetime

import mss
from PIL import Image

# --- Windows 相关 ---
import win32gui
import win32con
import win32api
import win32process
import win32ui

# --- 全局热键 ---
from pynput import keyboard

# --- UI（可选悬浮按钮） ---
import tkinter as tk

# =========================
# 用户配置
# =========================
SAVE_DIR = r"C:\Screenshots"            # 修改为你的保存目录（不存在会自动创建）
FILENAME_PREFIX = "winshot"             # 文件名前缀
IMAGE_FMT = "png"                        # png/jpg
USE_FLOATING_BUTTON = True               # 是否显示悬浮按钮
ALWAYS_ON_TOP_BUTTON = True              # 悬浮按钮始终置顶
SET_PROCESS_HIGH_PRIORITY = True         # 是否将进程设为高优先级
GLOBAL_HOTKEY = "<ctrl>+<alt>+s"        # 全局热键（pynput格式）

# 悬浮按钮外观
BUTTON_TEXT = "截屏当前窗口"
BUTTON_OPACITY = 0.9
BUTTON_BG = "#222222"
BUTTON_FG = "#ffffff"

# =========================
# Windows API: DWM 扩展边界
# =========================
DWMWA_EXTENDED_FRAME_BOUNDS = 9

def get_extended_frame_bounds(hwnd):
    """
    使用 DwmGetWindowAttribute 获取窗口的扩展边界（更准确，不含阴影/边框误差）
    失败时回退到 GetWindowRect
    """
    try:
        rect = ctypes.wintypes.RECT()
        dwmapi = ctypes.WinDLL("dwmapi")
        res = dwmapi.DwmGetWindowAttribute(
            ctypes.wintypes.HWND(hwnd),
            ctypes.wintypes.DWORD(DWMWA_EXTENDED_FRAME_BOUNDS),
            ctypes.byref(rect),
            ctypes.sizeof(rect)
        )
        if res == 0:
            # 成功
            return rect.left, rect.top, rect.right, rect.bottom
        else:
            raise OSError("DwmGetWindowAttribute failed")
    except Exception:
        # 回退
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        return left, top, right, bottom

# =========================
# 截屏核心逻辑
# =========================
def ensure_save_dir(path: str):
    os.makedirs(path, exist_ok=True)

def timestamp_name(prefix: str, ext: str) -> str:
    now = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"{prefix}_{now}.{ext}"

def capture_active_window(save_dir: str, prefix: str, fmt: str = "png") -> str:
    """
    截取当前活动窗口并保存到 save_dir，返回文件路径。
    """
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        raise RuntimeError("未检测到活动窗口。")

    # 排除桌面/任务栏等情况
    class_name = win32gui.GetClassName(hwnd)
    title = win32gui.GetWindowText(hwnd)
    if not win32gui.IsWindowVisible(hwnd):
        raise RuntimeError("当前活动窗口不可见，截屏取消。")

    # 获取窗口边界
    left, top, right, bottom = get_extended_frame_bounds(hwnd)
    width, height = max(0, right - left), max(0, bottom - top)
    if width == 0 or height == 0:
        raise RuntimeError("窗口尺寸异常，无法截屏。")

    # 进行区域抓取
    with mss.mss() as sct:
        region = {"left": left, "top": top, "width": width, "height": height}
        img = sct.grab(region)
        # 转 PIL 保存更稳（写入元信息时可选）
        pil_img = Image.frombytes("RGB", img.size, img.rgb)

        ensure_save_dir(save_dir)
        filename = timestamp_name(prefix, fmt)
        full_path = os.path.join(save_dir, filename)
        pil_img.save(full_path, format=fmt.upper())
        return full_path

# =========================
# 进程优先级（可选）
# =========================
def set_high_priority():
    """
    将当前进程优先级设为 HIGH_PRIORITY_CLASS。
    不建议使用 REALTIME_PRIORITY_CLASS（可能导致系统无响应）。
    """
    try:
        hProc = win32api.GetCurrentProcess()
        win32process.SetPriorityClass(hProc, win32process.HIGH_PRIORITY_CLASS)
    except Exception as e:
        print("设置高优先级失败：", e)

# =========================
# 全局热键监听
# =========================
class HotkeyListener:
    def __init__(self, hotkey_str: str):
        self.hotkey_str = hotkey_str
        self._setup()

    def _setup(self):
        # 注册全局热键：Ctrl+Alt+S
        self.hk = keyboard.GlobalHotKeys({
            self.hotkey_str: self.on_trigger
        })

    def on_trigger(self):
        try:
            path = capture_active_window(SAVE_DIR, FILENAME_PREFIX, IMAGE_FMT)
            print(f"[OK] 已保存：{path}")
        except Exception as e:
            print(f"[ERR] 截屏失败：{e}")

    def start(self):
        t = threading.Thread(target=self.hk.start, daemon=True)
        t.start()

# =========================
# 悬浮按钮（可选）
# =========================
def start_floating_button():
    root = tk.Tk()
    root.title("窗口截屏")
    root.attributes("-alpha", BUTTON_OPACITY)
    root.configure(bg=BUTTON_BG)
    root.resizable(False, False)

    # 最小化边框占用：无边框/置顶
    root.overrideredirect(True)
    if ALWAYS_ON_TOP_BUTTON:
        root.attributes("-topmost", True)

    # 初始位置：屏幕右下角
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    w, h = 160, 48
    x, y = sw - w - 20, sh - h - 60
    root.geometry(f"{w}x{h}+{x}+{y}")

    # 拖拽移动
    def start_move(event):
        root._x = event.x
        root._y = event.y

    def do_move(event):
        nx = root.winfo_x() + event.x - root._x
        ny = root.winfo_y() + event.y - root._y
        root.geometry(f"+{nx}+{ny}")

    # 按钮
    btn = tk.Button(
        root,
        text=BUTTON_TEXT,
        bg=BUTTON_BG,
        fg=BUTTON_FG,
        relief="flat",
        font=("Microsoft YaHei UI", 10)
    )
    btn.pack(fill="both", expand=True)

    # 点击截屏：为了避免截到自己，点击后短暂隐藏再截屏
    def on_click():
        try:
            # 记录当前前景窗口（可能是自己），先隐藏自己，再延时
            root.withdraw()
            time.sleep(0.20)  # 给系统切换前景窗口的时间

            path = capture_active_window(SAVE_DIR, FILENAME_PREFIX, IMAGE_FMT)
            print(f"[OK] 已保存：{path}")
        except Exception as e:
            print(f"[ERR] 截屏失败：{e}")

        finally:
            # 恢复显示
            root.deiconify()
            if ALWAYS_ON_TOP_BUTTON:
                root.attributes("-topmost", True)

    btn.bind("<Button-1>", lambda e: on_click())

    # 右键关闭
    def close_app(event=None):
        root.destroy()

    root.bind("<Button-3>", close_app)
    root.bind("<Button-1>", start_move)
    root.bind("<B1-Motion>", do_move)

    root.mainloop()

# =========================
# 主入口
# =========================
def main():
    print("=== 窗口截屏工具已启动 ===")
    print(f"保存目录：{SAVE_DIR}")
    print(f"全局热键：{GLOBAL_HOTKEY}（按下即截取当前活动窗口）")
    print(f"悬浮按钮：{'开启' if USE_FLOATING_BUTTON else '关闭'}（右键按钮可退出）")

    if SET_PROCESS_HIGH_PRIORITY:
        set_high_priority()

    # 启动热键监听（后台）
    hk = HotkeyListener(GLOBAL_HOTKEY)
    hk.start()

   # 可选悬浮按钮（前台）
    if USE_FLOATING_BUTTON:
        start_floating_button()
    else:
        # 无 UI：阻塞主线程以保持进程存在
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    main()
