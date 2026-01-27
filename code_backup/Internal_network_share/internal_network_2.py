
import os
import ssl
import smtplib
import threading
import datetime
import mimetypes
import sqlite3
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from functools import wraps

from flask import (
    Flask, request, Response, abort, redirect, url_for,
    render_template_string, send_file
)
from dotenv import load_dotenv

load_dotenv("./config2.env")

# ========= 配置 =========
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads")).resolve()
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "500"))

AUTH_USERNAME = os.getenv("AUTH_USERNAME", "admin")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "123")

BASE_URL = os.getenv("BASE_URL", "").strip().rstrip("/")

SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASS = os.getenv("SMTP_PASS", "").strip()
SMTP_FROM = os.getenv("SMTP_FROM", "").strip()
SMTP_TO = [x.strip() for x in os.getenv("SMTP_TO", "").split(",") if x.strip()]
EMAIL_ATTACH_FILE = os.getenv("EMAIL_ATTACH_FILE", "false").lower() == "true"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# SQLite 记录上传元数据（文件名、上传时间）
DB_PATH = (UPLOAD_DIR.parent / "uploads_meta.db").resolve()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                uploaded_at TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()

init_db()

# ========= Flask 初始化 =========
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024

# ========= 认证 =========
def check_auth(username: str, password: str) -> bool:
    return username == AUTH_USERNAME and password == AUTH_PASSWORD

def authenticate():
    return Response(
        "需要认证（HTTP Basic Auth）。\n",
        401,
        {"WWW-Authenticate": 'Basic realm="Login Required"'},
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# ========= 工具函数 =========
def human_size(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"

def now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def sanitize_filename(name: str) -> str:
    # 保留中文等字符，但禁止路径穿越
    base = os.path.basename(name).strip()
    if base in ("", ".", ".."):
        abort(400, "不合法的文件名")
    # 可选：限制非常规控制字符
    if any(ord(c) < 32 for c in base):
        abort(400, "文件名包含控制字符")
    return base

def record_upload(filename: str):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT INTO uploads (filename, uploaded_at) VALUES (?, ?)",
            (filename, now_str())
        )
        conn.commit()
    finally:
        conn.close()

def get_upload_time(filename: str):
# def get_upload_time(filename: str) -> str | None:
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            "SELECT uploaded_at FROM uploads WHERE filename = ? ORDER BY id DESC LIMIT 1",
            (filename,),
        )
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        conn.close()

def list_files(filter_q: str):
# def list_files(filter_q: str | None = None):
    items = []
    q = (filter_q or "").lower()
    for p in sorted(UPLOAD_DIR.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True):
        if not p.is_file():
            continue
        name = p.name
        if q and q not in name.lower():
            continue
        st = p.stat()
        uploaded_at = get_upload_time(name)
        if not uploaded_at:
            uploaded_at = datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        items.append({
            "name": name,
            "size": human_size(st.st_size),
            "mtime": datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "uploaded_at": uploaded_at,
        })
    return items

# def send_email_async(subject: str, body: str, attach_path: Path | None):
def send_email_async(subject: str, body: str, attach_path: Path):
    # 未配置邮件则不发送
    if not (SMTP_HOST and SMTP_FROM and SMTP_TO and (SMTP_USER and SMTP_PASS)):
        return

    def _send():
        try:
            msg = MIMEMultipart()
            msg["From"] = SMTP_FROM
            msg["To"] = ", ".join(SMTP_TO)
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain", "utf-8"))

            if attach_path and EMAIL_ATTACH_FILE and attach_path.exists():
                part = MIMEBase("application", "octet-stream")
                with open(attach_path, "rb") as f:
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f'attachment; filename="{attach_path.name}"')
                msg.attach(part)

            context = ssl.create_default_context()
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                if SMTP_USE_TLS:
                    server.starttls(context=context)
                server.login(SMTP_USER, SMTP_PASS)
                server.sendmail(SMTP_FROM, SMTP_TO, msg.as_string())
        except Exception as e:
            print(f"[Mail] 发送失败: {e}")

    threading.Thread(target=_send, daemon=True).start()

# ========= 页面模板 =========
FILES_PAGE = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <title>文件中心</title>
  <style>
    body { font-family: -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, "Noto Sans", "PingFang SC", "Microsoft YaHei", sans-serif; margin: 24px;}
    h1 { margin-top: 0; }
    .box { border: 1px solid #ddd; padding: 16px; border-radius: 8px; }
    table { width: 100%; border-collapse: collapse; margin-top: 12px; }
    th, td { border-bottom: 1px solid #eee; padding: 8px; text-align: left; }
    a { color: #0366d6; text-decoration: none; }
    .meta { color: #666; font-size: 12px; }
    .row { display: flex; gap: 12px; flex-wrap: wrap; }
    input[type="text"] { padding: 6px 10px; width: 260px; }
    button { padding: 6px 12px; }
    .muted { color: #777; }
  </style>
</head>
<body>
  <h1>文件中心</h1>

  <div class="box">
    {{ url_for(
      <input type="text" name="q" placeholder="搜索文件名（支持模糊匹配）" value="{{ q|default('') }}"/>
      <button type="submit">搜索</button>
      {% if q %}
        <a href="{{ url_for('files endif %}
    </form>
    <div class="meta">共 {{ total }} 个结果</div>
  </div>

  <div class="box">
    <form method="post" action="{{ url_for('upload') }}" enctype="multipart/form-datared />
      <button type="submit">上传</button>
      <span class="muted">最大 {{ max_mb }} MB</span>
    </form>
  </div>

  <h2>文件列表</h2>
  <div class="box">
    <table>
      <thead>
        <tr><th>文件名</th><th>大小</th><th>上传日期</th><th>操作</th></tr>
      </thead>
      <tbody>
        {% for f in files %}
          <tr>
            <td>{{ f.name }}</td>
            <td>{{ f.size }}</td>
            <td>{{ f.uploaded_at }}</td>
            <td>
              {{ url_for(预览</a> |
              {{ url_for(下载</a>
            </td>
          </tr>
        {% endfor %}
        {% if files|length == 0 %}
          <tr><td colspan="4"><em>没有匹配的文件</em></td></tr>
        {% endif %}
      </tbody>
    </table>
  </div>
</body>
</html>
"""

PREVIEW_PAGE = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <title>预览：{{ name }}</title>
  <style>
    body { font-family: -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, "Noto Sans", "PingFang SC", "Microsoft YaHei", sans-serif; margin: 24px;}
    .meta { color:#555; margin-bottom: 12px; }
    .toolbar a { margin-right: 12px; }
    pre { background: #f8f8f8; padding: 12px; overflow: auto; border-radius: 6px; }
    img, video, audio, iframe { max-width: 100%; }
  </style>
</head>
<body>
  <h1>{{ name }}</h1>
  <div class="meta">上传日期：{{ uploaded_at }}　|　大小：{{ size }}</div>
  <div class="toolbar">
    <a url_for(⬇ 下载</a>
    {{ url_for(← 返回列表</a>
  </div>
  <hr/>

  {% if kind == 'image' %}
    <img src="{{ raw_urllif kind == 'pdf' %}
    <iframe src="{{ raw_url }}" width="100%" height="800px" style="border:1px solid #ddd;border-radius:6px' %}
    {{ raw_url }}</video>
  {% elif kind == 'text' %}
    <pre>{{ text_content }}</pre>
  {% else %}
    <p>该文件类型不支持在线预览。请点击“下载”。</p>
  {% endif %}
</body>
</html>
"""

# ========= 路由 =========
@app.route("/")
def index():
    return redirect(url_for("files"))

# 列表 + 搜索 + 上传入口
@app.route("/files", methods=["GET"])
@requires_auth
def files():
    q = request.args.get("q", "").strip()
    items = list_files(q)
    return render_template_string(
        FILES_PAGE,
        files=items,
        q=q,
        total=len(items),
        max_mb=MAX_UPLOAD_MB
    )

# 上传
@app.route("/upload", methods=["POST"])
@requires_auth
def upload():
    if "file" not in request.files:
        abort(400, "缺少文件字段 'file'")
    f = request.files["file"]
    if f.filename == "":
        abort(400, "未选择文件")

    filename = sanitize_filename(f.filename)
    dest = UPLOAD_DIR / filename
    if dest.exists():
        stem = dest.stem
        suffix = dest.suffix
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = UPLOAD_DIR / f"{stem}_{timestamp}{suffix}"

    f.save(dest)
    record_upload(dest.name)

    # 邮件通知
    link_preview = f"/preview/{dest.name}"
    link_download = f"/download/{dest.name}"
    full_preview = (f"{BASE_URL}{link_preview}" if BASE_URL else link_preview)
    full_download = (f"{BASE_URL}{link_download}" if BASE_URL else link_download)

    subject = f"[文件中心] 新文件上传：{dest.name}"
    body = (
        f"文件名: {dest.name}\n"
        f"大小: {human_size(dest.stat().st_size)}\n"
        f"上传时间: {now_str()}\n"
        f"预览链接: {full_preview}\n"
        f"下载链接: {full_download}\n"
        f"存储路径: {dest}\n"
    )
    send_email_async(subject, body, dest)

    return redirect(url_for("files"))

# 原始内容（inline 使用）
@app.route("/raw/<path:filename>", methods=["GET"])
@requires_auth
def raw(filename: str):
    safe_name = sanitize_filename(filename)
    target = (UPLOAD_DIR / safe_name).resolve()
    if not target.exists() or not target.is_file():
        abort(404, "文件不存在")
    mime, _ = mimetypes.guess_type(target.name)
    mime = mime or "application/octet-stream"
    return send_file(target, mimetype=mime, as_attachment=False, conditional=True, download_name=target.name)

# 下载
@app.route("/download/<path:filename>", methods=["GET"])
@requires_auth
def download(filename: str):
    safe_name = sanitize_filename(filename)
    target = (UPLOAD_DIR / safe_name).resolve()
    if not target.exists() or not target.is_file():
        abort(404, "文件不存在")
    mime, _ = mimetypes.guess_type(target.name)
    mime = mime or "application/octet-stream"
    return send_file(target, mimetype=mime, as_attachment=True, conditional=True, download_name=target.name)

# 预览（展示文件名 + 上传日期 + 内嵌预览）
@app.route("/preview/<path:filename>", methods=["GET"])
@requires_auth
def preview(filename: str):
    safe_name = sanitize_filename(filename)
    target = (UPLOAD_DIR / safe_name).resolve()
    if not target.exists() or not target.is_file():
        abort(404, "文件不存在")

    st = target.stat()
    uploaded_at = get_upload_time(target.name) or datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    size = human_size(st.st_size)

    mime, _ = mimetypes.guess_type(target.name)
    mime = mime or "application/octet-stream"
    raw_url = url_for("raw", filename=target.name)

    kind = "other"
    if mime.startswith("image/"):
        kind = "image"
        text_content = None
    elif mime == "application/pdf":
        kind = "pdf"
        text_content = None
    elif mime.startswith("audio/"):
        kind = "audio"
        text_content = None
    elif mime.startswith("video/"):
        kind = "video"
        text_content = None
    elif mime.startswith("text/") or mime in ("application/json",):
        kind = "text"
        # 尝试读取文本（编码优先 utf-8，失败再 gb18030）
        try:
            text_content = target.read_text(encoding="utf-8", errors="strict")
        except Exception:
            try:
                text_content = target.read_text(encoding="gb18030", errors="replace")
            except Exception:
                text_content = "(无法以文本方式读取该文件)"
    else:
        text_content = None

    return render_template_string(
        PREVIEW_PAGE,
        name=target.name,
        uploaded_at=uploaded_at,
        size=size,
        raw_url=raw_url,
        kind=kind,
        text_content=text_content
    )

# ========= 启动入口 =========
def main():
    from waitress import serve
    print(f"Serving on http://{HOST}:{PORT}  (BasicAuth 用户名: {AUTH_USERNAME})")
    serve(app, host=HOST, port=PORT)

if __name__ == "__main__":
    main()
