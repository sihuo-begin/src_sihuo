
import os
import smtplib
import ssl
import threading
import datetime
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from functools import wraps
from pathlib import Path

from flask import (
    Flask, request, send_from_directory, Response,
    render_template_string, redirect, url_for, abort
)
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv('./config1.env')

# ===================== 配置 =====================
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "200"))
ROOT_DIR = Path(os.getenv("ROOT_DIR", "uploads"))

AUTH_USERNAME = os.getenv("AUTH_USERNAME", "admin")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "ChangeMe123!")

SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASS = os.getenv("SMTP_PASS", "").strip()
SMTP_FROM = os.getenv("SMTP_FROM", "").strip()
SMTP_TO = [x.strip() for x in os.getenv("SMTP_TO", "").split(",") if x.strip()]
EMAIL_ATTACH_FILE = os.getenv("EMAIL_ATTACH_FILE", "false").lower() == "true"

# Flask 基本设置
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ===================== 认证 =====================
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

# ===================== 工具函数 =====================
def human_size(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"

# def send_email_async(subject: str, body: str, attach_path: Path | None):
def send_email_async(subject: str, body: str, attach_path: Path):
    if not (SMTP_HOST and SMTP_FROM and SMTP_TO and (SMTP_USER and SMTP_PASS)):
        # 未配置邮件，直接返回
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
                part.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{attach_path.name}"',
                )
                msg.attach(part)

            context = ssl.create_default_context()
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                if SMTP_USE_TLS:
                    server.starttls(context=context)
                server.login(SMTP_USER, SMTP_PASS)
                server.sendmail(SMTP_FROM, SMTP_TO, msg.as_string())
        except Exception as e:
            # 简易日志
            print(f"[Mail] 发送失败: {e}")

    threading.Thread(target=_send, daemon=True).start()

# ===================== 页面模板 =====================
# BROWSE_PAGE = """
# <!doctype html>
# <html lang="zh-CN">
# <head>
#   <meta charset="utf-8"/>
#   <title>内网文件浏览</title>
#   <style>
#     body { font-family: -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, "Noto Sans", "PingFang SC", "Microsoft YaHei", sans-serif; margin: 24px;}
#     h1 { margin-top: 0; }
#     .box { border: 1px solid #ddd; padding: 16px; border-radius: 8px; }
#     table { width: 100%; border-collapse: collapse; margin-top: 12px; }
#     th, td { border-bottom: 1px solid #eee; padding: 8px; text-align: left; }
#     a { text-decoration: none; color: #0366d6; }
#     small { color: #666; }
#     .muted { color: #777; }
#   </style>
# </head>
# <body>
#   <h1>内网文件浏览</h1>
#   <div class="box">
#     <div>
#       <div><strong>根目录：</strong><code>{{ root }}</code></div>
#       <div><strong>当前位置：</strong><code>{{ subpath if subpath else "/" }}</code></div>
#       {% if subpath %}
#         <div><a href="{{ url_for('browse', subpath=lse %}
#         <div class="muted">（已经是根目录）</div>
#       {% endif %}
#     </div>
#
#     <table>
#       <thead>
#         <tr><th>名称</th><th>大小</th><th>修改时间</th></tr>
#       </thead>
#       <tbody>
#       {% for e in entries %}
#         <tr>
#           <td>
#             {% if e.is_dir %}
#               📁 <a href="{{ url_for('browse', subpath=e.rel)lse %}
#               📄 <a href="{{ url_for('viewa>
#             {% endif %}
#           </td>
#           <td>{{ e.size }}</td>
#           <td>{{ e.mtime }}</td>
#         </tr>
#       {% endfor %}
#       {% if entries|length == 0 %}
#         <tr><td colspan="3"><em>该目录为空</em></td></tr>
#       {% endif %}
#       </tbody>
#     </table>
#
#     <p class="muted"><small>提示：图片/文本/PDF/音视频可在线预览，其他类型将下载。</small></p>
#   </div>
# </body>
# </html>
# """
PAGE = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <title>文件服务</title>
  <style>
    body { font-family: -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, "Noto Sans", "PingFang SC", "Microsoft YaHei", sans-serif; margin: 24px;}
    h1 { margin-top: 0; }
    .box { border: 1px solid #ddd; padding: 16px; border-radius: 8px; }
    table { width: 100%; border-collapse: collapse; margin-top: 12px; }
    th, td { border-bottom: 1px solid #eee; padding: 8px; text-align: left; }
    small { color: #666; }
  </style>
</head>
<body>
  <h1>文件服务</h1>
  <div class="box">
    {{ url_for(
      <label>选择文件：</label>
      <input type="file" name="file" required />
      <button type="submit">上传</button>
      <small>最大 {{ max_mb }} MB</small>
    </form>
  </div>

  <h2>文件列表</h2>
  <div class="box">
    <table>
      <thead>
        <tr><th>文件名</th><th>大小</th><th>上传时间</th><th>下载</th></tr>
      </thead>
      <tbody>
      {% for f in files %}
        <tr>
          <td>{{ f.name }}</td>
          <td>{{ f.size }}</td>
          <td>{{ f.mtime }}</td>
          <td>{{ url_for(下载</a></td>
        </tr>
      {% endfor %}
      {% if files|length == 0 %}
        <tr><td colspan="4"><em>暂无文件</em></td></tr>
      {% endif %}
      </tbody>
    </table>
  </div>
</body>
</html>
"""

# ===================== 路由 =====================
@app.route("/files")
@requires_auth
def files():
    items = []
    for p in sorted(UPLOAD_DIR.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.is_file():
            st = p.stat()
            items.append({
                "name": p.name,
                "size": human_size(st.st_size),
                "mtime": datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            })
    print(items)
    return render_template_string(PAGE, files=items, max_mb=MAX_UPLOAD_MB)

@app.route("/upload", methods=["POST"])
@requires_auth
def upload():
    if "file" not in request.files:
        abort(400, "缺少文件字段 'file'")
    f = request.files["file"]
    if f.filename == "":
        abort(400, "未选择文件")

    filename = secure_filename(f.filename)
    if not filename:
        abort(400, "文件名非法")

    dest = UPLOAD_DIR / filename
    # 若重名，则在文件名后追加时间戳
    if dest.exists():
        stem = dest.stem
        suffix = dest.suffix
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = UPLOAD_DIR / f"{stem}_{timestamp}{suffix}"

    f.save(dest)

    # 发送通知邮件（异步）
    subject = f"[文件服务] 新文件上传: {dest.name}"
    body = (
        f"文件名: {dest.name}\n"
        f"大小: {human_size(dest.stat().st_size)}\n"
        f"时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"位置: {dest.resolve()}\n"
        f"下载链接（内网/外网按你的暴露方式不同）: /download/{dest.name}\n"
    )
    send_email_async(subject, body, dest)

    return redirect(url_for("files"))

@app.route("/download/<path:filename>")
@requires_auth
def download(filename: str):
    # 仅允许 downloads 目录下的文件
    safe_name = secure_filename(filename)
    target = UPLOAD_DIR / safe_name
    if not target.exists() or not target.is_file():
        abort(404, "文件不存在")
    return send_from_directory(UPLOAD_DIR, safe_name, as_attachment=True)

@app.route("/")
def index():
    # 引导到文件页（登录才可访问）
    return redirect(url_for("files"))


def safe_resolve_in_root(root: Path, rel_path: str) -> Path:
    """
    把相对路径解析到 ROOT_DIR 下，防止目录穿越。
    """
    # 去掉开头的/，保持相对
    rel_path = rel_path.lstrip("/\\")
    target = (root / rel_path).resolve()
    if not str(target).startswith(str(root)):
        abort(403, "越权访问被拒绝")
    return target

# ==== 目录浏览 ====
@app.route("/browse", defaults={"subpath": ""})
@app.route("/browse/<path:subpath>")
@requires_auth
def browse(subpath: str):
    current = safe_resolve_in_root(ROOT_DIR, subpath)
    if not current.exists():
        abort(404, "路径不存在")

    if current.is_file():
        # 如果传来的是文件路径，就直接跳转到预览
        return redirect(url_for("view_file", subpath=subpath))

    # 目录：列出子目录和文件
    entries = []
    try:
        for child in sorted(current.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            # 目录排前，名称字母序
            rel = str(child.relative_to(ROOT_DIR)).replace("\\", "/")
            entries.append({
                "name": child.name,
                "rel": rel,
                "is_dir": child.is_dir(),
                "size": (human_size(child.stat().st_size) if child.is_file() else "-"),
                "mtime": datetime.datetime.fromtimestamp(child.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            })
    except PermissionError:
        abort(403, "无权限访问该目录")

    # 计算上级路径
    parent_rel = ""
    if subpath:
        parent_rel = str(Path(subpath).parent).replace("\\", "/")
        if parent_rel == ".":
            parent_rel = ""

    return render_template_string(BROWSE_PAGE,
                                  root=str(ROOT_DIR),
                                  subpath=subpath,
                                  parent_rel=parent_rel,
                                  entries=entries)

# ==== 文件查看（预览/下载）====
@app.route("/view/<path:subpath>")
@requires_auth
def view_file(subpath: str):
    target = safe_resolve_in_root(ROOT_DIR, subpath)
    if not target.exists() or not target.is_file():
        abort(404, "文件不存在")

    # 尝试识别 MIME
    mime, _ = mimetypes.guess_type(target.name)
    mime = mime or "application/octet-stream"

    # 对常见可预览类型，inline 展示；其余触发下载
    inline_types_prefix = [
        "image/",        # png/jpg/gif/svg/webp…
        "text/",         # txt/csv/log/html/css/js…
        "audio/",        # mp3/ogg/wav…
        "video/",        # mp4/webm…
        "application/pdf",
    ]
    is_inline = mime.startswith(tuple(t for t in ["image/", "text/", "audio/", "video/"])) or mime == "application/pdf"

    try:
        if is_inline:
            # inline 预览
            return send_file(
                target,
                mimetype=mime,
                as_attachment=False,
                download_name=target.name,
                conditional=True  # 支持 Range/缓存
            )
        else:
            # 不可预览 -> 走下载
            return send_file(
                target,
                mimetype=mime,
                as_attachment=True,
                download_name=target.name,
                conditional=True
            )
    except PermissionError:
        abort(403, "无权限读取该文件")

# ===================== 入口 =====================
def main():
    # 用 Waitress 作为生产级 WSGI 服务器
    from waitress import serve
    print(f"Serving on http://{HOST}:{PORT}  (BasicAuth 用户名: {AUTH_USERNAME})")
    serve(app, host=HOST, port=PORT)

if __name__ == "__main__":
    main()
