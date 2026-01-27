
import os
import ssl
import sqlite3
import datetime
import mimetypes
from pathlib import Path
from functools import wraps
from email.mime.text import MIMEText
from flask import (
    Flask, request, Response, abort, redirect, url_for,
    render_template_string, send_file
)
from dotenv import load_dotenv

load_dotenv("./config3.env")

# ======== 配置 ========
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads")).resolve()
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "500"))
AUTH_USERNAME = os.getenv("AUTH_USERNAME", "admin")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "ChangeMe!123")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = (UPLOAD_DIR.parent / "workstation_uploads.db").resolve()

# ======== 数据库 ========
def init_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("""
          CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename   TEXT NOT NULL,
            station    TEXT NOT NULL,
            uploaded_at TEXT NOT NULL
          )
        """)
        conn.commit()
    finally:
        conn.close()

def now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def record_upload(filename: str, station: str):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT INTO uploads (filename, station, uploaded_at) VALUES (?, ?, ?)",
            (filename, station, now_str())
        )
        conn.commit()
    finally:
        conn.close()

def get_meta(filename: str):
    """返回 (station, uploaded_at)；没有记录时返回 (None, None)"""
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(
            "SELECT station, uploaded_at FROM uploads WHERE filename = ? ORDER BY id DESC LIMIT 1",
            (filename,)
        )
        row = cur.fetchone()
        return (row[0], row[1]) if row else (None, None)
    finally:
        conn.close()

def human_size(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"

def sanitize_filename(name: str) -> str:
    base = os.path.basename(name).strip()
    if base in ("", ".", ".."):
        abort(400, "不合法的文件名")
    if any(ord(c) < 32 for c in base):
        abort(400, "文件名包含控制字符")
    return base

# ======== Flask ========
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024

# ======== 认证 ========
def check_auth(username: str, password: str) -> bool:
    return username == AUTH_USERNAME and password == AUTH_PASSWORD

def authenticate():
    return Response("需要认证（HTTP Basic Auth）。\n", 401,
                    {"WWW-Authenticate": 'Basic realm="Login Required"'} )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# ======== 页面模板（卡片视图） ========
CARDS_PAGE = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <title>工位文件卡片</title>
  <style>
    :root { --primary:#0366d6; --muted:#666; --bg:#f7f7f7; }
    body { font-family: -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, "Noto Sans", "PingFang SC", "Microsoft YaHei", sans-serif; margin: 24px; background: var(--bg);}
    h1 { margin-top: 0; }
    .toolbar { display:flex; gap:12px; align-items:center; flex-wrap:wrap; }
    .box { background:#fff; border:1px solid #e5e5e5; padding:16px; border-radius:10px; }
    input[type="text"] { padding:8px 10px; width:260px; }
    button { padding:8px 12px; cursor:pointer; }
    .grid { display:grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap:14px; margin-top:16px; }
    .card { background:#fff; border:1px solid #e8e8e8; border-radius:12px; padding:14px; transition: box-shadow .15s ease, transform .05s ease; cursor:pointer; }
    .card:hover { box-shadow: 0 6px 18px rgba(0,0,0,.06); transform: translateY(-1px); }
    .badge { display:inline-block; background:#eef4ff; color:#1f57c3; padding:2px 8px; border-radius:999px; font-size:12px; border:1px solid #d9e6ff; }
    .name { margin:8px 0 6px 0; font-weight:600; word-break:break-all; }
    .meta { color:#777; font-size:12px; }
    .empty { color:#888; font-style: italic; }
    a.link { color: var(--primary); text-decoration:none; }
    .row { display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
  </style>
</head>
<body>
  <h1>工位文件卡片</h1>

  <div class="box">
    {{ url_for(
      <input type="text" name="q" placeholder="搜索（文件名或工位）" value="{{ q|default('') }}"/>
      <button type="submit">搜索</button>
      {% if q %}{{ url_for(清空</a>{% endif %}
      <span style="color:#999;">共 {{ total }} 条</span>
    </form>
  </div>

  <div class="box" style="margin-top:14px;">
    {{ url_for(
      <label>工位：</label>
      <input type="text" name="station" placeholder="例如：A-12" required />
      <input type="file" name="file" required />
      <button type="submit">上传</button>
      <span style="color:#999;">最大 {{ max_mb }} MB</span>
    </form>
  </div>

  <div class="grid">
    {% for f in files %}
      {{ url_for(
        <span class="badge">工位：{{ f.station }}</span>
        <div class="name">{{ f.name }}</div>
        <div class="meta">上传日期：{{ f.uploaded_at }}</div>
      </div>
    {% endfor %}
    {% if files|length == 0 %}
      <div class="empty">没有匹配的文件</div>
    {% endif %}
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
  <div class="meta">工位：{{ station }}　|　上传日期：{{ uploaded_at }}　|　大小：{{ size }}</div>
  <div class="toolbar">
    {{ url_for(⬇ 下载</a>
    {{ url_for(← 返回</a>
  </div>
  <hr/>

  {% if kind == 'image' %}
    {{ raw_url }}
  {% elif kind == 'pdf' %}
    {{ raw_url }}</iframe>
  {% elif kind == 'audio' %}
    {{ raw_url }}</audio>
  {% elif kind == 'video' %}
    {{ raw_url }}</video>
  {% elif kind == 'text' %}
    <pre>{{ text_content }}</pre>
  {% else %}
    <p>该文件类型不支持在线预览，请点击“下载”。</p>
  {% endif %}
</body>
</html>
"""

# ======== 业务函数 ========
def list_files(q: str or None = None):
    """融合文件系统与数据库：按 mtime 倒序输出卡片列表"""
    items = []
    ql = (q or "").strip().lower()
    # 用文件系统作为真实来源
    paths = [p for p in UPLOAD_DIR.glob("*") if p.is_file()]
    paths.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    for p in paths:
        name = p.name
        station, uploaded_at = get_meta(name)
        # 兼容历史：没有记录时给默认值
        if not station:
            station = "未标注"
        if not uploaded_at:
            uploaded_at = datetime.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        if ql:
            if (ql not in name.lower()) and (ql not in station.lower()):
                continue
        items.append({
            "name": name,
            "station": station,
            "uploaded_at": uploaded_at,
        })
    return items

# ======== 路由 ========
@app.route("/")
def index():
    return redirect(url_for("cards"))

@app.route("/cards", methods=["GET"])
@requires_auth
def cards():
    q = request.args.get("q", "")
    files = list_files(q)
    return render_template_string(
        CARDS_PAGE,
        files=files,
        q=q,
        total=len(files),
        max_mb=MAX_UPLOAD_MB
    )

@app.route("/upload", methods=["POST"])
@requires_auth
def upload():
    if "file" not in request.files:
        abort(400, "缺少文件字段 'file'")
    f = request.files["file"]
    if not f or f.filename == "":
        abort(400, "未选择文件")
    station = (request.form.get("station") or "").strip()
    if not station:
        abort(400, "请填写工位")

    filename = sanitize_filename(f.filename)
    dest = UPLOAD_DIR / filename
    if dest.exists():
        # 重名：追加时间戳
        stem, suffix = dest.stem, dest.suffix
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = UPLOAD_DIR / f"{stem}_{ts}{suffix}"
    f.save(dest)

    record_upload(dest.name, station)
    return redirect(url_for("cards"))

@app.route("/raw/<path:filename>", methods=["GET"])
@requires_auth
def raw(filename: str):
    safe = sanitize_filename(filename)
    target = (UPLOAD_DIR / safe).resolve()
    if not target.exists() or not target.is_file():
        abort(404, "文件不存在")
    mime, _ = mimetypes.guess_type(target.name)
    mime = mime or "application/octet-stream"
    return send_file(target, mimetype=mime, as_attachment=False, conditional=True, download_name=target.name)

@app.route("/download/<path:filename>", methods=["GET"])
@requires_auth
def download(filename: str):
    safe = sanitize_filename(filename)
    target = (UPLOAD_DIR / safe).resolve()
    if not target.exists() or not target.is_file():
        abort(404, "文件不存在")
    mime, _ = mimetypes.guess_type(target.name)
    mime = mime or "application/octet-stream"
    return send_file(target, mimetype=mime, as_attachment=True, conditional=True, download_name=target.name)

@app.route("/preview/<path:filename>", methods=["GET"])
@requires_auth
def preview(filename: str):
    safe = sanitize_filename(filename)
    target = (UPLOAD_DIR / safe).resolve()
    if not target.exists() or not target.is_file():
        abort(404, "文件不存在")

    st = target.stat()
    station, uploaded_at = get_meta(target.name)
    if not station:
        station = "未标注"
    if not uploaded_at:
        uploaded_at = datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

    size = human_size(st.st_size)
    mime, _ = mimetypes.guess_type(target.name)
    mime = mime or "application/octet-stream"
    raw_url = url_for("raw", filename=target.name)

    kind = "other"
    text_content = None
    if mime.startswith("image/"):
        kind = "image"
    elif mime == "application/pdf":
        kind = "pdf"
    elif mime.startswith("audio/"):
        kind = "audio"
    elif mime.startswith("video/"):
        kind = "video"
    elif mime.startswith("text/") or mime in ("application/json",):
        kind = "text"
        # 读取文本（优先 utf-8，失败尝试 gb18030）
        try:
            text_content = target.read_text(encoding="utf-8", errors="strict")
        except Exception:
            try:
                text_content = target.read_text(encoding="gb18030", errors="replace")
            except Exception:
                text_content = "(无法以文本方式读取该文件)"

    return render_template_string(
        PREVIEW_PAGE,
        name=target.name,
        station=station,
        uploaded_at=uploaded_at,
        size=size,
        raw_url=raw_url,
        kind=kind,
        text_content=text_content
    )

# ======== 启动 ========
def main():
    from waitress import serve
    init_db()
    print(f"Serving on http://{HOST}:{PORT}  (BasicAuth 用户名: {AUTH_USERNAME})")
    serve(app, host=HOST, port=PORT)

if __name__ == "__main__":
    main()
