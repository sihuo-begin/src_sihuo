
# -*- coding: utf-8 -*-
import os
import csv
import mimetypes
from pathlib import Path
from datetime import datetime
from urllib.parse import quote, unquote

from flask import Flask, request, send_from_directory, abort, render_template_string
from numpy.random import random_integers

# === 基本配置 ===
BASE_DIR = Path(__file__).parent.resolve()
# BASE_DIR = "C:\Pthon_Dir\PMI_Test_Tranining"
print(BASE_DIR, type(BASE_DIR))
# C:\Production_Related\B15\src_sihuo\code_backup\Internal_network_share\docs
DOCS_DIR = BASE_DIR / "docs"
METADATA_CSV = DOCS_DIR / "metadata.csv"

app = Flask(__name__)
# 简单页面模板（内嵌，避免额外文件）
PAGE_TEMPLATE = r"""
<!doctype html>
<html lang="zh">
<head>
  <meta charset="utf-8">
  <title>培训文档内网</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    :root { color-scheme: light dark; }
    body { font-family: -apple-system, Segoe UI, Roboto, "Noto Sans", Arial, "PingFang SC", "Microsoft YaHei", sans-serif; margin: 20px; }
    h1 { margin: 0 0 12px 0; font-size: 20px; }
    .toolbar { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:12px; }
    .toolbar input, .toolbar select, .toolbar button { padding:8px; font-size: 14px; }
    table { width:100%; border-collapse: collapse; }
    th, td { border-bottom: 1px solid #ccc; padding: 10px; text-align: left; }
    th { background: #f6f6f6; position: sticky; top: 0; }
    a { color: #0b5fff; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .muted { color: #777; }
    .badge { display:inline-block; padding: 2px 8px; border-radius: 12px; background: #eee; font-size: 12px; }
    .nowrap { white-space: nowrap; }
    .footer { margin-top: 14px; font-size: 12px; color:#666; }
  </style>
</head>
<body>
  <h1>培训文档内网</h1>
  <form classt type="text" name="q" placeholder="按文件名关键词搜索…" value="{{ q|e }}">
    <select name="station">
      <option value="">全部工站</option>
      {% for st in stations %}
        <option value="{{ st|e }}" {% if st == station %}selected{% endif %}>{{ st }}</option>
      {% endfor %}
    </select>
    <select name="sort">
      <option value="date_desc" {% if sort=='date_desc' %}selected{% endif %}>按更新日期 ⬇︎</option>
      <option value="date_asc"  {% if sort=='date_asc'  %}selected{% endif %}>按更新日期 ⬆︎</option>
      <option value="name_asc"  {% if sort=='name_asc'  %}selected{% endif %}>按文件名 ⬇︎</option>
      <option value="name_desc" {% if sort=='name_desc' %}selected{% endif %}>按文件名 ⬆︎</option>
    </select>
    <button type="submit">筛选</button
    <a href="/" style="align-self:centeread>
      <tr>
        <th>文件名</th>
        <th>测试工站名</th>
        <th class="nowrap">更新日期</th>
        <th class="nowrap"><span class="muted">位置</span></th>
      </tr>
    </thead>
    <tbody>
      {% for f in files %}
      <tr>
        <td>
          <a href="/files/{{ f.url_path }}" target="_blank" title="点击在新窗口       <td>
          {% if f.station %}<span class="badge">{{ f.station }}</span>{% else %}<span class="muted">未标注</span>{% endif %}
        </td>
        <td class="nowrap">{{ f.updated_date }}</td>
        <td class="muted">{{ f.rel_dir or '.' }}</td>
      </tr>
      {% endfor %}
      {% if files|length == 0 %}
      <tr><td colspan="4" class="muted">没有匹配的文档。</td></tr>
      {% endif %}
    </tbody>
  </table>

  <div class="footer">
    提示：将文档放到 <code>{{ docs_dir }}</code>（或其子目录）后，刷新本页面即可看到最新列表。<br>
    工站/日期可通过 <code>metadata.csv</code> 定义，或采用文件名规则 <code>文件名__工站名__YYYY-MM-DD.扩展名</code>。
  </div>
</body>
</html>
"""

def load_metadata():
    """
    读取 docs/metadata.csv，返回 dict:
    {
      "相对路径/文件名.ext": {"station": "...", "updated_date": "YYYY-MM-DD"},
      ...
    }
    """
    meta = {}
    if METADATA_CSV.exists():
        # 兼容 UTF-8 和 GBK
        for enc in ("utf-8-sig", "gbk"):
            try:
                with open(METADATA_CSV, "r", encoding=enc, newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        filename = (row.get("filename") or "").strip()
                        if not filename:
                            continue
                        key = filename.replace("\\", "/")  # 统一分隔符
                        meta[key] = {
                            "station": (row.get("station") or "").strip(),
                            "updated_date": (row.get("updated_date") or "").strip(),
                        }
                break
            except UnicodeDecodeError:
                continue
    return meta

def try_parse_from_filename(path: Path):
    """
    支持：文件名__工站名__YYYY-MM-DD.ext
    返回 (name_no_ext, station, date_str or None)
    """
    name_no_ext = path.stem
    station, date_str = None, None
    # 只在存在两个或以上 "__" 时尝试
    if "__" in name_no_ext:
        parts = name_no_ext.split("__")
        if len(parts) >= 3:
            # 末两段尝试 station 和 date
            maybe_station = parts[-2].strip()
            maybe_date = parts[-1].strip()
            # 简单校验日期格式
            try:
                datetime.strptime(maybe_date, "%Y-%m-%d")
                station = maybe_station
                date_str = maybe_date
                # 真正的“文件名”部分为前面的拼接
                name_no_ext = "__".join(parts[:-2]).strip() or name_no_ext
            except ValueError:
                pass
    return name_no_ext, station, date_str

def scan_docs(q: str = "", station_filter: str = ""):
    """
    扫描 DOCS_DIR 下所有文件（递归），返回用于渲染的文件列表。
    """
    meta = load_metadata()
    items = []
    print(DOCS_DIR)
    for path in DOCS_DIR.rglob("*"):
        if path.is_dir():
            continue
        # 忽略 metadata.csv 自身
        if path.name.lower() == "metadata.csv":
            continue

        rel_path = path.relative_to(DOCS_DIR).as_posix()  # 相对路径，用于查表
        display_name = path.name  # 默认展示名：文件名（含扩展）

        # 1) metadata.csv 优先
        station = None
        updated_date = None
        if rel_path in meta:
            station = meta[rel_path].get("station") or None
            updated_date = meta[rel_path].get("updated_date") or None

        # 2) 文件名规则解析
        if not station or not updated_date:
            parsed_name, parsed_station, parsed_date = try_parse_from_filename(path)
            if not station and parsed_station:
                station = parsed_station
            if not updated_date and parsed_date:
                updated_date = parsed_date
            # 若按规则解析成功，显示名改为解析出的“纯文件名 + 扩展名”
            if parsed_name != path.stem:
                display_name = f"{parsed_name}{path.suffix}"

        # 3) 日期兜底：用文件修改时间
        if not updated_date:
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            updated_date = mtime.strftime("%Y-%m-%d")

        # 过滤：关键词 / 工站
        if q and q.strip() and (q.strip().lower() not in display_name.lower()):
            continue
        if station_filter and station_filter.strip() and (station or "") != station_filter.strip():
            continue

        rel_dir = path.parent.relative_to(DOCS_DIR).as_posix() if path.parent != DOCS_DIR else ""

        items.append({
            "display_name": display_name,
            "station": station,
            "updated_date": updated_date,
            "url_path": quote(rel_path),   # URL 安全
            "rel_dir": rel_dir,
            "sort_key": {
                "date": updated_date,
                "name": display_name.lower(),
            }
        })

    return items

@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    station = request.args.get("station", "").strip()
    sort = request.args.get("sort", "date_desc")

    files = scan_docs(q=q, station_filter=station)

    # 收集工站列表（去重、排序）
    stations = sorted({f["station"] for f in files if f["station"]})

    # 排序
    if sort == "date_asc":
        files.sort(key=lambda x: x["sort_key"]["date"])
    elif sort == "name_asc":
        files.sort(key=lambda x: x["sort_key"]["name"])
    elif sort == "name_desc":
        files.sort(key=lambda x: x["sort_key"]["name"], reverse=True)
    else:
        # 默认：日期倒序
        files.sort(key=lambda x: x["sort_key"]["date"], reverse=True)

    return render_template_string(PAGE_TEMPLATE,
                                  files=files,
                                  q=q,
                                  station=station,
                                  stations=stations,
                                  sort=sort,
                                  docs_dir=str(DOCS_DIR))

@app.route("/files/<path:relpath>")
def serve_file(relpath):
    # 安全防护：不允许跳出 DOCS_DIR
    safe_rel = Path(unquote(relpath)).as_posix()
    target = (DOCS_DIR / safe_rel).resolve()
    if DOCS_DIR not in target.parents and target != DOCS_DIR:
        abort(403)

    if not target.exists() or not target.is_file():
        abort(404)

    # 让浏览器尽量内联预览（PDF/图片/文本等）
    mime, _ = mimetypes.guess_type(target.name)
    return send_from_directory(
        DOCS_DIR,
        safe_rel,
        mimetype=mime or "application/octet-stream",
        as_attachment=False
    )

if __name__ == "__main__":
    # 确保 docs 目录存在
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    # 监听 0.0.0.0 允许局域网访问；如仅本机可访问，可改为 host="127.0.0.1"
    app.run(host="10.200.147.157", port=8000, debug=False)

