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



CARDS_PAGE = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <title>工位文件卡片</title>
  <style>
    :root { --primary:#0366d6; --bg:#f7f7f7; }
    body {
      font-family: -apple-system, Segoe UI, Roboto, "Helvetica Neue",
      Arial, "Noto Sans", "PingFang SC", "Microsoft YaHei", sans-serif;
      margin: 24px;
      background: var(--bg);
    }
    h1 { margin-top: 0; }

    .box {
      background:#fff;
      border:1px solid #e5e5e5;
      padding:16px;
      border-radius:10px;
      margin-bottom:14px;
    }

    .toolbar {
      display:flex;
      gap:12px;
      align-items:center;
      flex-wrap:wrap;
    }

    input[type="text"] {
      padding:8px 10px;
      width:260px;
    }
    button {
      padding:8px 14px;
      cursor:pointer;
    }

    .grid {
      display:grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap:14px;
    }

    .card {
      background:#fff;
      border:1px solid #e8e8e8;
      border-radius:12px;
      padding:14px;
      cursor:pointer;
      transition: box-shadow .15s ease, transform .06s ease;
    }
    .card:hover {
      box-shadow: 0 6px 18px rgba(0,0,0,.08);
      transform: translateY(-2px);
    }

    .badge {
      display:inline-block;
      background:#eef4ff;
      color:#1f57c3;
      padding:2px 8px;
      border-radius:999px;
      font-size:12px;
      border:1px solid #d9e6ff;
    }
    .name {
      margin:8px 0 6px 0;
      font-weight:600;
      word-break:break-all;
    }
    .meta {
      color:#777;
      font-size:12px;
    }
    .empty {
      color:#888;
      font-style:italic;
    }
    a.link {
      color: var(--primary);
      text-decoration:none;
    }
  </style>
</head>

<body>
  <h1>Volcano Tester Cookbook</h1>

  <!-- 搜索 -->
  <div class="box">
    <form class="toolbar" method="get" action="q"
             placeholder="搜索（文件名或工位）"
             value="{{ q|default('') }}">
      <button type="submit">搜索</button>
      {% if q %}
        <a class="link"a>
      {% endif %}
      <span style="color:#999;">共 {{ total }} 条</span>
    </form>
  </div>

  <!-- 上传 -->
  <div class="box">
    <form class="toolbar"
          method="post"
          action="{{ url_for('upload') }}"
          required>
      <input type="file" name="file" required>
      <button type="submit">上传</button>
      <span style="color:#999;">最大 {{ max_mb }} MB</span>
    </form>
  </div>

  <!-- 文件卡片 -->
  <div class="grid">
    {% for f in files %}
      <divrl_for(
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


