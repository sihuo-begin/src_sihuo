#!/bin/bash
# FCST Waterfall Tool 一键启动脚本
# 用法: ./start.sh
# 访问: http://localhost:8765
set -e
cd "$(dirname "$0")"

echo "🚀 启动 FCST Waterfall 比对工具..."
echo "📂 工作目录: $(pwd)"

# 检查依赖
python3 -c "import fastapi, uvicorn, multipart" 2>/dev/null || {
  echo "❌ 缺少依赖, 正在安装..."
  pip install fastapi uvicorn python-multipart openpyxl --quiet
}

# 创建目录
mkdir -p uploads outputs

# 启动
PORT=${10.200.147.103:-8765}
echo "🌐 访问地址: http://localhost:10.200.147.103"
echo "⏹️  停止服务: Ctrl+C"
echo ""
python3 app.py
