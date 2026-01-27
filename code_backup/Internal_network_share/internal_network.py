# -*- coding: utf-8 -*-
"""
内网培训文档服务器 + 实时新增监控 + 邮件通知
- Flask 提供目录浏览与下载
- watchdog 监听 DOCS_DIR 新增文件，聚合后邮件提醒
- psutil 设置高优先级（安全）
- 可选基本认证保护访问
"""

import os
import sys
import time
import socket
import threading
import mimetypes
from datetime import datetime
from urllib.parse import quote

from flask import Flask, request, Response, abort, send_from_directory, render_template_string
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from email.message import EmailMessage
import smtplib
import psutil

from dotenv import load_dotenv

# ============ 加载配置 ============
load_dotenv(dotenv_path="./config.env")
# load_dotenv()

DOCS_DIR       = os.getenv("DOCS_DIR", os.path.abspath("./training_docs"))
SERVER_HOST    = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT    = int(os.getenv("SERVER_PORT", "8000"))
SERVER_PUBLIC_URL = os.getenv("SERVER_PUBLIC_URL", "").strip()

BASIC_AUTH_USER = os.getenv("BASIC_AUTH_USER", "").strip()
BASIC_AUTH_PASS = os.getenv("BASIC_AUTH_PASS", "").strip()

SMTP_SERVER   = os.getenv("SMTP_SERVER", "")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM    = os.getenv("EMAIL_FROM", SMTP_USERNAME)
EMAIL_TO      = [e.strip() for e in os.getenv("EMAIL_TO", "").split(",") if e.strip()]
USE_TLS       = os.getenv("USE_TLS", "true").lower() == "true"
USE_SSL       = os.getenv("USE_SSL", "false").lower() == "true"

AGGREGATE_SECONDS = int(os.getenv("AGGREGATE_SECONDS", "15"))
PRIORITY_LEVEL    = os.getenv("PRIORITY_LEVEL", "high").lower()

# ============ 初始化目录 ============
os.makedirs(DOCS_DIR, exist_ok=True)

# ============ 提升进程优先级（安全） ============
def set_process_priority():
    try:
        p = psutil.Process(os.getpid())
        if os.name == "nt":
            # Windows：HIGH_PRIORITY_CLASS
            if PRIORITY_LEVEL == "high":
                p.nice(psutil.HIGH_PRIORITY_CLASS)
        else:
            # POSIX：nice 值越低优先级越高（-20 ~ 19）
            if PRIORITY_LEVEL == "high":
                try:
                    os.nice(-10)  # 适度提升；若有权限可到 -20
                except PermissionError:
                    pass
    except Exception as e:
        print("[WARN] 设置优先级失败：", e)

set_process_priority()

# ============ 辅助：认证 ============
def check_auth():
    if not BASIC_AUTH_USER or not BASIC_AUTH_PASS:
        return True
    auth = request.authorization
    return auth and auth.username == BASIC_AUTH_USER and auth.password == BASIC_AUTH_PASS

def require_auth():
    if not check_auth():
        return Response("需要认证", 401, {"WWW-Authenticate": 'Basic realm="TrainingDocs"'})

# ============ 辅助：服务器 URL ============
def get_base_url():
    if SERVER_PUBLIC_URL:
        return SERVER_PUBLIC_URL.rstrip("/")
    # 自动推测本机内网 IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        ip = socket.gethostbyname(socket.gethostname())
    return f"http://{ip}:{SERVER_PORT}"

# ============ 网页模板 ============
INDEX_HTML = """
<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>培训文档索引</title>
<style>
body { font-family: "Microsoft YaHei UI", Arial, sans-serif; margin: 20px; }
h1 { margin-bottom: 6px; }
small { color: #777; }
table { border-collapse: collapse; width: 100%; }
th, td { border-bottom: 1px solid #eee; padding: 8px; text-align: left; }
tr:hover { background: #fafafa; }
.path { color: #555; margin-bottom: 10px; }
.footer { color: #888; margin-top: 20px; font-size: 12px; }
</style>
</head>
<body>
<h1>培训文档空间</h1>
<table>
<thead><tr><th>文件/目录</th><th>大小</th><th>最后修改时间</th></tr></thead>
<tbody>
{% for item in items %}
<tr>
  <td>
    {% if item.is_dir %}
      📁 /list/{{ item.rel_path | urlencode }}{{ item.name }}</a>
    {% else %}
      📄 <a href="/docs/{{ item.rel_path | urlencode }}" target="_    {% endif %}
  </td>
  <td>{{ item.size }}</td>
  <td>{{ item.mtime }}</td>
</tr>
{% endfor %}
</tbody>
</table>

<div class="footer">
  本页自动生成。访问保护：{{ '启用' if auth_enabled else '关闭' }}。
</div>
</body>
</html>
"""

# ============ Flask 应用 ============
app = Flask(__name__)

def human_size(bytes_):
    try:
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(bytes_)
        for u in units:
            if size < 1024:
                return f"{size:.1f} {u}"
            size /= 1024
        return f"{size:.1f} PB"
    except Exception:
        return str(bytes_)

def list_dir(rel=""):
    base = os.path.join(DOCS_DIR, rel)
    if not os.path.isdir(base):
        abort(404)
    items = []
    for name in sorted(os.listdir(base)):
        full = os.path.join(base, name)
        st = os.stat(full)
        items.append({
            "name": name,
            "rel_path": os.path.relpath(full, DOCS_DIR).replace("\\", "/"),
            "is_dir": os.path.isdir(full),
            # "is_dir": True,
            "size": "" if os.path.isdir(full) else human_size(st.st_size),
            "mtime": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        })
    return items

@app.route("/")
def index():
    ra = require_auth()
    if isinstance(ra, Response):
        return ra
    items = list_dir("")
    print(items)
    return render_template_string(
        INDEX_HTML,
        items=items,
        docs_dir=DOCS_DIR,
        auth_enabled=bool(BASIC_AUTH_USER and BASIC_AUTH_PASS)
    )

@app.route("/list/<path:rel>")
def list_sub(rel):
    ra = require_auth()
    if isinstance(ra, Response):
        return ra
    items = list_dir(rel)
    return render_template_string(
        INDEX_HTML,
        items=items,
        docs_dir=os.path.join(DOCS_DIR, rel),
        auth_enabled=bool(BASIC_AUTH_USER and BASIC_AUTH_PASS)
    )

@app.route("/docs/<path:rel>")
def serve_file(rel):
    ra = require_auth()
    if isinstance(ra, Response):
        return ra
    directory = DOCS_DIR
    rel = rel.replace("\\", "/")
    # 禁止越权访问
    full = os.path.abspath(os.path.join(directory, rel))
    if not full.startswith(os.path.abspath(directory)):
        abort(403)
    if not os.path.isfile(full):
        abort(404)
    return send_from_directory(directory, rel, as_attachment=False)

# ============ 邮件发送 ============
def send_mail_new_files(file_paths):
    # if not SMTP_SERVER or not EMAIL_TO:
    if not EMAIL_TO:
        print("[WARN] 邮件未配置，跳过通知。")
        return

    msg = EmailMessage()
    msg["Subject"] = f"[培训文档] 新增 {len(file_paths)} 个文件"
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(EMAIL_TO)

    base_url = get_base_url()
    lines = []
    for p in file_paths:
        rel = os.path.relpath(p, DOCS_DIR).replace("\\", "/")
        url = f"{base_url}/docs/{quote(rel)}"
        lines.append(f"- {rel}\n  查看链接：{url}")
    body = (
        f"您好，培训文档空间有新增文件（共 {len(file_paths)} 个）：\n\n"
        + "\n\n".join(lines)
        + "\n\n访问主页："
        + f"{base_url}/"
        + "\n\n此邮件由系统自动发送。"
    )
    msg.set_content(body)
    print(body)
    try:
        if USE_SSL:
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as s:
                s.login(SMTP_USERNAME, SMTP_PASSWORD)
                s.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
                s.ehlo()
                if USE_TLS:
                    s.starttls()
                if SMTP_USERNAME:
                    s.login(SMTP_USERNAME, SMTP_PASSWORD)
                s.send_message(msg)
        print(f"[OK] 已发送通知邮件给：{EMAIL_TO}")
    except Exception as e:
        print("[ERR] 发送邮件失败：", e)

# ============ 监控：聚合新增事件 ============
class NewFileAggregator:
    def __init__(self, window_seconds=AGGREGATE_SECONDS):
        self.lock = threading.Lock()
        self.window_seconds = window_seconds
        self.pending = set()
        self.timer = None

    def add(self, path):
        with self.lock:
            self.pending.add(path)
            if self.timer:
                self.timer.cancel()
            self.timer = threading.Timer(self.window_seconds, self.flush)
            self.timer.daemon = True
            self.timer.start()

    def flush(self):
        with self.lock:
            files = sorted(self.pending)
            self.pending.clear()
            self.timer = None
        if files:
            send_mail_new_files(files)

aggregator = NewFileAggregator()

class Handler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and os.path.isfile(event.src_path):
            print("[NEW] 文件：", event.src_path)
            aggregator.add(event.src_path)

    def on_moved(self, event):
        # 迁移到目录内也视为新增
        if not event.is_directory and os.path.isfile(event.dest_path):
            if os.path.commonpath([os.path.abspath(event.dest_path), os.path.abspath(DOCS_DIR)]) == os.path.abspath(DOCS_DIR):
                print("[NEW] 文件(移动)：", event.dest_path)
                aggregator.add(event.dest_path)

def start_watchdog():
    obs = Observer()
    obs.schedule(Handler(), DOCS_DIR, recursive=True)
    obs.start()
    print(f"[MONITOR] 正在监控新增：{DOCS_DIR}")

# ============ 启动 ============
def main():
    print("=== 培训文档内网服务启动 ===")
    print(f"目录：{DOCS_DIR}")
    print(f"地址：{get_base_url()}/")
    # 启动监控线程
    t = threading.Thread(target=start_watchdog, daemon=True)
    t.start()
    # 启动 Web 服务
    app.run(host=SERVER_HOST, port=SERVER_PORT, threaded=True)

if __name__ == "__main__":
    main()
