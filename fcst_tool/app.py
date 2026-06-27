"""
FCST Waterfall Web Tool - FastAPI 后端
========================================
- POST /api/generate: 接收 3 份 xlsx 上传, 生成比对报表
- GET /api/download/{task_id}: 下载已生成的报表
- GET /: 前端页面

所有文件仅在本地处理,不上传云端,适合企业敏感数据。
"""
import os
import sys
import uuid
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# 加载引擎
sys.path.insert(0, str(Path(__file__).parent))
from fcst_engine import parse_fcst_xlsx, build_report

BASE = Path(__file__).parent
UPLOAD_DIR = BASE / 'uploads'
OUTPUT_DIR = BASE / 'outputs'
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

app = FastAPI(title='FCST Waterfall Tool')

# CORS (本地开发)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

# 静态资源
app.mount('/static', StaticFiles(directory=str(BASE / 'static')), name='static')

# 任务状态(task_id -> {status, progress, messages, output, error})
TASKS = {}

# ============== 页面 ==============
@app.get('/', response_class=HTMLResponse)
async def index():
    html_path = BASE / 'static' / 'index.html'
    if not html_path.exists():
        return HTMLResponse('<h1>前端页面未找到</h1>', status_code=500)
    return HTMLResponse(html_path.read_text(encoding='utf-8'))


# ============== API ==============
@app.post('/api/generate')
async def generate_report(
    background_tasks: BackgroundTasks,
    wk21: UploadFile = File(..., description='Snapshot 1: 较早的 FCST (例如 WK21 SF04)'),
    wk22: UploadFile = File(..., description='Snapshot 2: 中间 FCST (例如 WK22 SF05)'),
    wk23: UploadFile = File(..., description='Snapshot 3: 最新 FCST (例如 WK23 SF05)'),
    output_name: str = Form('FCST_Waterfall_比对'),
):
    # 1. 校验文件
    for f in (wk21, wk22, wk23):
        if not f.filename or not f.filename.lower().endswith('.xlsx'):
            raise HTTPException(400, f'文件 {f.filename} 不是 .xlsx 格式')

    # 2. 创建 task
    task_id = str(uuid.uuid4())[:8]
    safe_name = ''.join(c for c in output_name if c.isalnum() or c in '._-') or 'FCST_Waterfall'
    output_path = OUTPUT_DIR / f'{safe_name}_{task_id}.xlsx'

    # 3. 保存上传
    p21 = UPLOAD_DIR / f'{task_id}_WK21.xlsx'
    p22 = UPLOAD_DIR / f'{task_id}_WK22.xlsx'
    p23 = UPLOAD_DIR / f'{task_id}_WK23.xlsx'
    for fobj, p in [(wk21, p21), (wk22, p22), (wk23, p23)]:
        with open(p, 'wb') as f:
            content = await fobj.read()
            f.write(content)

    TASKS[task_id] = {
        'status': 'processing',
        'progress': 0,
        'messages': [f'[启动] 任务 {task_id}'],
        'output': None,
        'error': None,
        'created': datetime.now().isoformat(timespec='seconds'),
    }

    # 4. 异步处理
    background_tasks.add_task(_process, task_id, p21, p22, p23, output_path)

    return JSONResponse({'task_id': task_id, 'status': 'processing'})


def _process(task_id, p21, p22, p23, output_path):
    """后台处理: 解析 + 生成报表"""
    msgs = TASKS[task_id]['messages']

    def log(msg):
        msgs.append(f'[{datetime.now().strftime("%H:%M:%S")}] {msg}')
        TASKS[task_id]['progress'] = min(99, TASKS[task_id]['progress'] + 5)

    try:
        TASKS[task_id]['progress'] = 5
        log('开始解析 3 份 xlsx 报表...')
        all_data, weeks = parse_fcst_xlsx(str(p21), str(p22), str(p23), log)

        TASKS[task_id]['progress'] = 40
        log(f'数据解析完成, 共 {sum(len(v) for v in all_data.values())} 行')
        log('开始生成比对 Excel 报表...')

        build_report(all_data, weeks, str(output_path), log)

        TASKS[task_id]['status'] = 'done'
        TASKS[task_id]['progress'] = 100
        TASKS[task_id]['output'] = str(output_path)
        TASKS[task_id]['output_name'] = output_path.name
        log(f'✅ 完成! 报表: {output_path.name}')

    except Exception as e:
        TASKS[task_id]['status'] = 'error'
        TASKS[task_id]['error'] = str(e)
        log(f'❌ 错误: {e}')
        import traceback
        msgs.append(traceback.format_exc())

    finally:
        # 清理上传文件
        for p in (p21, p22, p23):
            try:
                p.unlink()
            except Exception:
                pass


@app.get('/api/status/{task_id}')
async def get_status(task_id: str):
    if task_id not in TASKS:
        raise HTTPException(404, '任务不存在')
    return TASKS[task_id]


@app.get('/api/download/{task_id}')
async def download(task_id: str):
    if task_id not in TASKS:
        raise HTTPException(404, '任务不存在')
    t = TASKS[task_id]
    if t['status'] != 'done':
        raise HTTPException(400, f"任务状态: {t['status']}")
    return FileResponse(
        t['output'],
        filename=t['output_name'],
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


@app.get('/api/health')
async def health():
    return {'status': 'ok', 'time': datetime.now().isoformat(timespec='seconds')}


if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get('PORT', 8765))
    print(f'🚀 启动 FCST Waterfall Tool: http://localhost:{port}')
    uvicorn.run(app, host='10.200.147.103', port=port, log_level='info')
