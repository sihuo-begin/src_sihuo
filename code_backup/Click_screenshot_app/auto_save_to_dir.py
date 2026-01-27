
# -*- coding: utf-8 -*-
"""
Windows 自动保存文件到指定目录（Ctrl+S / 鼠标点击触发），并设置程序高优先级 & 悬浮置顶控制按钮。

功能：
- 全局热键（默认：Ctrl+Alt+S）触发：对当前前台窗口发送 Ctrl+S
- 捕获标准“另存为”对话框，自动填写目录 & 文件名，点击保存
- 非标准对话框则回退到 pyautogui 的鼠标/键盘策略
- 进程优先级提升到 HIGH_PRIORITY_CLASS（安全）
- 悬浮控制按钮（Always on Top），支持点击进行保存

注意：
- 某些应用自定义了保存面板（如 Adobe 系列），建议配置回退策略的坐标或改用应用自身的自动化接口。
"""

import os
import time
import threading
from datetime import datetime

# 自动化库
from pynput import keyboard
import pyautogui as pag

# Windows API
import win32api
import win32process
import win32con

# UI
import tkinter as tk

# pywinauto（标准保存对话框）
from pywinauto import Desktop, Application

# =========================
# 用户配置
# =========================
SAVE_DIR = r"C:\AutoSaves"  # 指定保存目录（不存在会自动创建）
FILENAME_PREFIX = "autosave"  # 文件名的前缀
FILENAME_SUFFIX_DATETIME = True  # 是否在文件名后添加时间戳
DEFAULT_EXT = ".pdf"  # 默认扩展名（若应用没自动补全扩展名时可用）

GLOBAL_HOTKEY = "<ctrl>+<alt>+s"  # 全局热键
USE_FLOATING_BUTTON = True        # 是否显示悬浮按钮
ALWAYS_ON_TOP_BUTTON = True       # 悬浮按钮永远置顶
SET_PROCESS_HIGH_PRIORITY = True  # 设置高优先级

# 回退策略（非标准保存对话框时）——鼠标点击/键盘输入
FALLBACK_USE_MOUSE = True
# 如果使用 FALLBACK_USE_MOUSE=True，你需要提供保存按钮、大致坐标；或使用 TAB 导航。
FALLBACK_COORDS = {
    # 这些坐标需要你在实际使用中调整为“保存按钮”的屏幕坐标
    "save_button": (1200, 800),  # 示例坐标：右下角“保存”按钮
}
FALLBACK_TYPING_DELAY = 0.002  # 键入速度

# 悬浮按钮 UI
BUTTON_TEXT = "自动保存到指定目录"
BUTTON_OPACITY = 0.92
BUTTON_BG = "#202020"
BUTTON_FG = "#ffffff"
positions = {"enter_file": ((43, 31)),
             "enter_save": (203, 267),
             "select_folder": (915, 347),
             # "enter_file_name": (723, 552),
             "confirm_save": (761, 559)}
# =========================
# 工具函数
# =========================
def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def build_filename(prefix: str, ext: str = None) -> str:
    base = prefix
    if FILENAME_SUFFIX_DATETIME:
        base += "_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    if ext and not base.lower().endswith(ext.lower()):
        base += ext
    return base

def set_high_priority():
    """
    设置为 HIGH_PRIORITY_CLASS。不要使用 REALTIME_PRIORITY_CLASS（可能让系统无响应）。
    """
    try:
        hProc = win32api.GetCurrentProcess()
        win32process.SetPriorityClass(hProc, win32process.HIGH_PRIORITY_CLASS)
    except Exception as e:
        print("[WARN] 设置高优先级失败：", e)

def send_ctrl_s():
    """向当前前台窗口发送 Ctrl+S（用 pyautogui，兼容性好）。"""
    pag.hotkey("ctrl", "s")

# =========================
# 主逻辑：尝试标准“另存为”对话框
# =========================
def try_save_via_common_dialog(save_dir: str, filename: str, timeout: float = 5.0) -> bool:
    """
    通过标准“另存为”对话框进行保存：
    - 定位 '#32770' 类（Windows 通用对话框），或 'Save As' 标题
    - 设置文件名输入框为 'save_dir\\filename'
    - 点击保存按钮
    返回 True/False
    """
    t0 = time.time()
    dlg = None
    while time.time() - t0 < timeout:
        # Desktop(backend="uia") 对一些应用更稳；先尝试 uia，再 fallback 到 win32
        try:
            desktop = Desktop(backend="uia")
            # 常见标题包含 '另存为', 'Save As', 或本地化变体
            dlg_candidates = desktop.windows(class_name="#32770")
            # 如果找不到，尝试通过控件类型过滤
            if not dlg_candidates:
                dlg_candidates = [w for w in desktop.windows() if "另存为" in (w.window_text() or "") or "Save As" in (w.window_text() or "")]
            if dlg_candidates:
                # 选择最近出现的一个（通常是前台）
                dlg = sorted(dlg_candidates, key=lambda w: w.handle, reverse=True)[0]
                break
        except Exception:
            pass
        time.sleep(0.2)

    if not dlg:
        return False

    try:
        # 激活对话框
        dlg.set_focus()

        # 在“文件名”编辑框输入完整路径
        # 常见名称：'文件名(&N):'、'File name:'，使用 uia 的控件类型过滤更稳
        edit = None
        for c in dlg.descendants():
            # Edit 控件通常是文件名输入框
            if getattr(c, "friendly_class_name", "") == "Edit":
                edit = c
                break

        full_path = os.path.join(save_dir, filename)
        ensure_dir(save_dir)

        if edit is not None:
            edit.set_edit_text(full_path)
        else:
            # 回退：尝试通过 TAB 导航
            pag.typewrite(full_path, interval=FALLBACK_TYPING_DELAY)

        # 点击“保存”按钮（常见控件类型：Button，文本可能为 '保存' / 'Save'）
        save_btn = None
        for c in dlg.descendants():
            if getattr(c, "friendly_class_name", "") == "Button":
                txt = (c.window_text() or "").lower()
                if "save" in txt or "保存" in txt:
                    save_btn = c
                    break

        if save_btn:
            save_btn.click_input()
        else:
            # 回退：按下 Enter
            pag.press("enter")

        # 等待保存完成（简单等待）
        time.sleep(0.5)
        return True
    except Exception as e:
        print("[WARN] 标准对话框自动化失败：", e)
        return False

# =========================
# 回退策略：鼠标/键盘
# =========================
def fallback_save_via_mouse(save_dir: str, filename: str):
    """
    非标准对话框时：
    - 键入完整路径（目录+文件名）
    - 点击保存按钮（需要坐标）
    """
    full_path = os.path.join(save_dir, filename)
    ensure_dir(save_dir)

    # 将路径打到焦点处（确保焦点在“文件名”输入框）
    # pag.typewrite(full_path, interval=FALLBACK_TYPING_DELAY)
    # time.sleep(0.2)

    # 点击“保存”按钮坐标（需要你调整）
    # time.sleep(1)
    for i in list(positions):
        if i in ["enter_save", "confirm_save"]:
            time.sleep(0.2)
        else:
            time.sleep(1)
        x, y = positions[i]
        pag.moveTo(x, y, duration=0.1)
        pag.click()
        if "select_folder" in i:
            time.sleep(1)
            pag.typewrite(full_path, interval=FALLBACK_TYPING_DELAY)
    # if "save_button" in FALLBACK_COORDS:
    #     x, y = FALLBACK_COORDS["save_button"]
    #     pag.moveTo(x, y, duration=0.1)
    #     pag.click()
    # else:
    #     # 如果没配置坐标，就直接 Enter
    #     pag.press("enter")

    time.sleep(0.5)

# =========================
# 触发流程
# =========================
def perform_auto_save():
    """
    触发一次自动保存流程：
    1) 发送 Ctrl+S
    2) 优先用标准“另存为”对话框保存
    3) 不行则回退到鼠标策略
    """
    try:
        # 生成文件名
        filename = build_filename(FILENAME_PREFIX, DEFAULT_EXT)
        #
        # 发送保存快捷键
        # send_ctrl_s()
        # time.sleep(0.3)  # 给应用弹窗时间
        #
        # # 首选：通用对话框
        # ok = try_save_via_common_dialog(SAVE_DIR, filename, timeout=6.0)
        # if ok:
        #     print(f"[OK] 已保存：{os.path.join(SAVE_DIR, filename)}")
        #     return

        # 回退：鼠标/键盘策略
        if FALLBACK_USE_MOUSE:
            fallback_save_via_mouse(SAVE_DIR, filename)
            print(f"[OK]（回退策略）已保存：{os.path.join(SAVE_DIR, filename)}")
        else:
            print("[ERR] 未捕获到标准对话框，且未启用回退策略。")
    except Exception as e:
        print(f"[ERR] 自动保存失败：{e}")

# =========================
# 全局热键监听
# =========================
class HotkeyListener:
    def __init__(self, hotkey_str: str):
        self.hotkey_str = hotkey_str
        self.hk = keyboard.GlobalHotKeys({hotkey_str: perform_auto_save})

    def start(self):
        t = threading.Thread(target=self.hk.start, daemon=True)
        t.start()

# =========================
# 悬浮按钮（Always on Top）
# =========================
def start_floating_button():
    root = tk.Tk()
    root.title("自动保存控制")
    root.attributes("-alpha", BUTTON_OPACITY)
    root.configure(bg=BUTTON_BG)
    root.resizable(False, False)
    root.overrideredirect(True)
    if ALWAYS_ON_TOP_BUTTON:
        root.attributes("-topmost", True)

    # 放置到右下
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    w, h = 220, 50
    # x, y = sw - w - 20, sh - h - 60
    x, y = sw - w - 20, sh - h - 800
    root.geometry(f"{w}x{h}+{x}+{y}")

    def start_move(event):
        root._x, root._y = event.x, event.y
    def do_move(event):
        nx = root.winfo_x() + event.x - root._x
        ny = root.winfo_y() + event.y - root._y
        root.geometry(f"+{nx}+{ny}")

    btn = tk.Button(root, text=BUTTON_TEXT, bg=BUTTON_BG, fg=BUTTON_FG,
                    relief="flat", font=("Microsoft YaHei UI", 10))
    btn.pack(fill="both", expand=True)

    def on_click():
        # 防止截到自己或影响前台：短暂降低可见性
        root.withdraw()
        time.sleep(0.15)
        perform_auto_save()
        root.deiconify()
        if ALWAYS_ON_TOP_BUTTON:
            root.attributes("-topmost", True)

    btn.bind("<Button-1>", lambda e: on_click())
    root.bind("<Button-3>", lambda e: root.destroy())
    root.bind("<Button-1>", start_move)
    root.bind("<B1-Motion>", do_move)

    root.mainloop()

# =========================
# 主入口
# =========================
def main():
    print("=== 自动保存工具已启动 ===")
    print(f"保存目录：{SAVE_DIR}")
    print(f"全局热键：{GLOBAL_HOTKEY}（按下即自动保存到指定目录）")
    print(f"悬浮按钮：{'开启' if USE_FLOATING_BUTTON else '关闭'}（右键退出）")

    if SET_PROCESS_HIGH_PRIORITY:
        set_high_priority()

    hk = HotkeyListener(GLOBAL_HOTKEY)
    hk.start()

    if USE_FLOATING_BUTTON:
        start_floating_button()
    else:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    main()
