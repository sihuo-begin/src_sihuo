import tkinter as tk

class InfoWindow:
    def __init__(self, master, title, pid, sn, status):
        self.master = master
        master.title(title)

        self.label_pid = tk.Label(master, text=f"PID: {pid}")
        self.label_pid.pack()

        self.label_sn = tk.Label(master, text=f"SN: {sn}")
        self.label_sn.pack()

        self.label_status = tk.Label(master, text=f"状态: {status}")
        self.label_status.pack()

def create_new_window(title, pid, sn, status):
    new_window = tk.Toplevel(root)
    InfoWindow(new_window, title, pid, sn, status)

if __name__ == "__main__":
    root = tk.Tk()
    root.title("主窗口")

    # 创建多个信息窗口
    # create_new_window("窗口 1", "1234", "ABCD1234", "正常")
    # create_new_window("窗口 2", "5678", "EFGH5678", "故障")
    # create_new_window("窗口 3", "91011", "IJKL91011", "待处理")
    # create_new_window("窗口 4", "1213", "MNOP1213", "正常")
    # create_new_window("窗口 5", "1415", "QRST1415", "正常")

    root.mainloop()
