# NoteTrial 🧪

> 发小红书之前，用 AI 模拟真实用户，提前做一次 A/B Crowd Test

![NoteTrial](https://img.shields.io/badge/version-0.1.0--MVP-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## 🎯 产品功能

通过**平台校准后的受众模拟**，帮助用户在"发帖前"判断：哪一版内容更可能在小红书获得更高互动（点赞 / 收藏 / 评论）。

**目标用户：** 小红书个人创作者 / 小团队 / 中小商家 / 独立开发者

## ✨ 核心特性

- 🤖 **AI 对话定义任务** - 自然语言描述你的内容创意
- ✍️ **A/B 内容编辑** - 对比两个版本的内容
- 👥 **多 Persona 受众模拟** - 模拟真实用户的互动行为
- 📊 **统计置信度分析** - 科学评估哪个版本更优
- 🔧 **平台校准层** - 结合小红书平台特性优化评分
- 💡 **诊断与建议** - 告诉你为什么 B 比 A 更好

## 🏗️ 系统架构

```
┌───────────────┬─────────────────────┬──────────────────┐
│ 左栏：对话     │ 中栏：内容编辑区     │ 右栏：CrowdTest   │
│ Chat / Task   │ Content A / B        │ Audience Sim     │
└───────────────┴─────────────────────┴──────────────────┘
```

### 技术栈

- **后端**: Python + FastAPI
- **前端**: React + TypeScript + Tailwind CSS
- **AI**: OpenAI GPT-4o (通过 OpenRouter)
- **平台集成**: xiaohongshu-mcp

## 🚀 快速开始

### 1. 环境要求

- Python 3.10+
- Node.js 18+
- OpenAI API Key（或 OpenRouter API Key）

### 2. 克隆项目

```bash
git clone https://github.com/yourusername/notetrial.git
cd notetrial
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key
```

```env
# .env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1

# 如果使用 OpenRouter
# OPENAI_BASE_URL=https://openrouter.ai/api/v1
```

### 4. 启动服务

**方式一：一键启动**

```bash
chmod +x start.sh
./start.sh
```

**方式二：分别启动**

```bash
# 终端 1 - 启动后端
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000

# 终端 2 - 启动前端
cd frontend
npm install
npm run dev
```

### 5. 访问应用

- 前端: http://localhost:3000
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

## 📖 使用指南

### Step 1: 定义任务

在左侧对话栏描述你的内容创意：

```
我想写一篇程序员副业的内容，
主要想提高收藏率，
内容不要太像广告。
```

AI 会帮你结构化为测试任务。

### Step 2: 编辑内容

- 在中栏填写 **版本 A** 的标题、正文、标签
- 点击 **AI 生成 B 版本** 自动创建对照版本
- 或手动编辑 **版本 B**

### Step 3: 运行测试

- 在右栏设置模拟用户数量（5-100）
- 点击 **开始测试**
- 查看各维度的对比结果和置信度

### Step 4: 优化内容

根据诊断分析和改写建议，优化你的内容。

## 🔧 小红书 MCP 集成（可选）

如果你想获得更精准的平台校准，可以集成 [xiaohongshu-mcp](https://github.com/xpzouying/xiaohongshu-mcp)：

```bash
# 1. 下载并启动 xiaohongshu-mcp
./xiaohongshu-login-darwin-arm64  # 先登录
./xiaohongshu-mcp-darwin-arm64    # 启动服务

# 2. 确认 MCP 服务运行在 http://localhost:18060/mcp
```

NoteTrial 会自动检测 MCP 服务状态，并使用平台数据进行校准。

## 📁 项目结构

```
notetrial/
├── backend/                 # 后端服务
│   ├── app/
│   │   ├── main.py         # FastAPI 入口
│   │   ├── config.py       # 配置管理
│   │   ├── models.py       # 数据模型
│   │   └── services/       # 核心服务
│   │       ├── audience_simulator.py  # 受众模拟引擎
│   │       ├── xhs_calibrator.py      # 小红书校准层
│   │       └── content_generator.py   # 内容生成
│   └── requirements.txt
├── frontend/               # 前端应用
│   ├── src/
│   │   ├── components/     # React 组件
│   │   ├── services/       # API 服务
│   │   ├── types/          # TypeScript 类型
│   │   └── App.tsx         # 主应用
│   └── package.json
├── .env.example            # 环境变量示例
├── start.sh                # 启动脚本
└── README.md
```

## 🔮 技术原理

### CrowdTest 核心逻辑

```
用户输入 Task Spec
        ↓
Audience Simulation (LLM 多 Persona 模拟)
        ↓
XHS Calibration Layer (使用 MCP + 样本统计校准)
        ↓
Statistical Confidence (统计置信度计算)
        ↓
Final A/B Score + 诊断 + 建议
```

### 受众模拟

基于 [viral-predictor](https://github.com/Azure-Vision/viral-predictor) 的思路：

1. 构造 10 种用户画像（核心受众、边缘受众、专业人士、新手小白等）
2. 让 LLM 扮演每个画像，对内容做出互动决策
3. 统计各版本的点赞/收藏/评论/分享数
4. 使用 Z-test 计算统计置信度

### 平台校准

MCP 数据**不是用来预测具体点赞数**，而是：

- 分析热门内容的标题结构分布
- 提取平台语言风格特征
- 调整受众模拟的打分权重

## 🤝 参考项目

- [xiaohongshu-mcp](https://github.com/xpzouying/xiaohongshu-mcp) - 小红书 MCP 服务
- [viral-predictor](https://github.com/Azure-Vision/viral-predictor) - 内容病毒性预测

## 📄 License

MIT License

---

**NoteTrial** - 让每一次发帖都更有把握 ✨
