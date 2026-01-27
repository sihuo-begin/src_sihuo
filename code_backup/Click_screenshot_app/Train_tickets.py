
import time

from pynput import mouse

print("开始监听鼠标点击事件，按 Ctrl+C 退出")
time.sleep(10)
def on_click(x, y, button, pressed):
    if pressed:
        print(f"点击位置: ({x}, {y})  按钮: {button}")

with mouse.Listener(on_click=on_click) as listener:
    listener.join()


# import time
# import random
# import pyautogui
# def click_positions_loop(
#     positions,
#     interval=1,          # 每次点击后等待的秒数
#     total_duration=None,   # 总持续时间（秒），None 表示无限循环直到触发 fail-safe 或 Ctrl+C
#     clicks_per_pos=1,      # 每个位置连续点击次数
#     button='left',         # 鼠标按钮：'left'、'right'、'middle'
#     jitter=0,              # 每次点击时在坐标附近的随机抖动像素范围，例如 3 表示在 ±3 像素内随机
#     move_duration=0.001,    # 鼠标移动到目标点所用时间（秒）
#     pause_between_positions=0.0 # 从一个坐标到下一个坐标的附加间隔
# ):
#     """
#     在给定 positions 列表中循环点击。
#     - positions: [(x1,y1), (x2,y2), ...]
#     - interval: 每次点击后等待的时间（影响节奏）
#     - total_duration: 总运行时长（秒）；None 为无限循环
#     - clicks_per_pos: 每个坐标点击次数（比如双击可设为2，也可直接用 pyautogui.doubleClick）
#     - button: 'left'/'right'/'middle'
#     - jitter: 每次点击时在坐标附近随机偏移的像素数，0 表示不偏移
#     - move_duration: 移动到目标点所用时间
#     - pause_between_positions: 从当前坐标到下一个坐标前的额外等待
#     """
#     # 开启 pyautogui 的 fail-safe（默认左上角(0,0)触发）
#     time.sleep(10)
#     pyautogui.FAILSAFE = True
#     # 每个 pyautogui 动作后全局暂停（可不设或设更小）
#     pyautogui.PAUSE = 0.000001
#     if not positions:
#         raise ValueError("positions 不能为空。请提供至少一个坐标点。")
#
#     start_time = time.time()
#     print("开始循环点击。将鼠标快速移至屏幕左上角可安全退出。按 Ctrl+C 也可终止。")
#
#     try:
#         while True:
#
#             for (x, y) in positions:
#                 # 若设置了总时长，到点就退出
#                 if total_duration is not None and (time.time() - start_time) >= total_duration:
#                     print("\n已到达设定总时长，停止。")
#                     return
#
#                 # 随机抖动（可选）
#                 if jitter and jitter > 0:
#                     dx = random.randint(-jitter, jitter)
#                     dy = random.randint(-jitter, jitter)
#                 else:
#                     dx = dy = 0
#
#                 target_x = x + dx
#                 target_y = y + dy
#                 # 平滑移动到目标
#                 pyautogui.moveTo(target_x, target_y, duration=move_duration)
#
#                 # 点击（可多次）
#                 for _ in range(clicks_per_pos):
#                     pyautogui.click(x=target_x, y=target_y, button=button)
#                     time.sleep(interval)
#
#                 if pause_between_positions > 0:
#                     time.sleep(pause_between_positions)
#             continue
#     except pyautogui.FailSafeException:
#         print("\n检测到 Fail-Safe 触发（鼠标到左上角），已安全退出。")
#     except KeyboardInterrupt:
#         print("\n收到 Ctrl+C，已退出。")
#
# if __name__ == "__main__":
#     # 这里替换成你自己记录下来的坐标
#     target_positions = [
#         (897, 599),  # 位置1
#         (1000, 500), # 位置2
#         (900, 600)   # 位置3
#     ]
#
#     click_positions_loop(
#         positions=target_positions,
#         interval=0.000001,             # 每次点击之间 0.5s
#         total_duration=20,       # 总共点击 120 秒；如需无限循环，设为 None
#         clicks_per_pos=1,         # 每个位置点击一次
#         button='left',            # 左键
#         jitter=2,                 # 每次点击在 ±2 像素内随机抖动
#         move_duration=0.000001,       # 移动到目标的时间
#         pause_between_positions=0 # 坐标之间不额外停顿
#     )
