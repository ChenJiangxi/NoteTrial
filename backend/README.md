# NoteTrial Backend

## 环境变量

```bash
# 复制示例文件
cp .env.example .env

# 编辑 .env 填入以下配置：
```

## 环境变量说明

```env
# 数据库
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/notetrial

# JWT 密钥（生成一个随机字符串）
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# OpenAI / OpenRouter
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://openrouter.ai/api/v1
DEFAULT_MODEL=gpt-4o

# MCP 服务
MCP_URL=http://localhost:18060/mcp
MCP_API_KEY=

# Redis (Celery Broker)
REDIS_URL=redis://localhost:6379/0

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000", "http://localhost:3001"]
```

## 开发

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 运行
python -m uvicorn app.main:app --reload --port 8000
```

## Docker

```bash
docker compose up -d
```
