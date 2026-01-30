#!/bin/bash

# NoteTrial 启动脚本

echo "🚀 启动 NoteTrial..."

# 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python3，请先安装"
    exit 1
fi

# 检查 Node.js 环境
if ! command -v node &> /dev/null; then
    echo "❌ 未找到 Node.js，请先安装"
    exit 1
fi

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 创建 .env 文件（如果不存在）
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  已创建 .env 文件，请编辑填入你的 OpenAI API Key"
    echo "   位置: $SCRIPT_DIR/.env"
fi

# 安装后端依赖
echo "📦 安装后端依赖..."
cd backend
python3 -m venv venv 2>/dev/null || true
source venv/bin/activate
pip install -r requirements.txt -q

# 安装前端依赖
echo "📦 安装前端依赖..."
cd ../frontend
npm install --silent

# 启动后端服务（后台运行）
echo "🔧 启动后端服务..."
cd ../backend
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "   后端 PID: $BACKEND_PID"

# 等待后端启动
sleep 3

# 启动前端服务
echo "🎨 启动前端服务..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!
echo "   前端 PID: $FRONTEND_PID"

# 等待前端启动
sleep 3

echo ""
echo "✅ NoteTrial 启动成功！"
echo ""
echo "📍 访问地址:"
echo "   前端: http://localhost:3000"
echo "   后端: http://localhost:8000"
echo "   API 文档: http://localhost:8000/docs"
echo ""
echo "💡 提示:"
echo "   1. 确保已配置 .env 文件中的 OPENAI_API_KEY"
echo "   2. 如需小红书数据校准，请先启动 xiaohongshu-mcp 服务"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 捕获退出信号
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM

# 等待子进程
wait
