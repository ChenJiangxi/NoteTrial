# NoteTrial 产品改进计划

## 目标：做成一个完整的 C 端/小 B 端产品

## 一、技术架构重构

### 1.1 数据库设计（PostgreSQL）

```sql
-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nickname VARCHAR(100),
    avatar_url TEXT,
    subscription_tier VARCHAR(20) DEFAULT 'free',  -- free/pro/enterprise
    credits INTEGER DEFAULT 100,  -- 免费额度
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 内容表
CREATE TABLE contents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    title VARCHAR(200) NOT NULL,
    body TEXT,
    tags TEXT[],
    status VARCHAR(20) DEFAULT 'draft',  -- draft/published/archived
    topic VARCHAR(200),
    goal VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- A/B 测试表
CREATE TABLE ab_tests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    content_a_id UUID REFERENCES contents(id),
    content_b_id UUID REFERENCES contents(id),
    task_spec JSONB,
    result JSONB,
    status VARCHAR(20) DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT NOW()
);

-- 发布记录表
CREATE TABLE posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    content_id UUID REFERENCES contents(id),
    platform VARCHAR(50),  -- xiaohongshu
    note_id VARCHAR(100),  -- 小红书笔记ID
    stats JSONB,  -- 点赞、收藏、评论数据
    posted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 素材库表
CREATE TABLE materials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    material_type VARCHAR(20),  -- image/text
    content TEXT,
    tags TEXT[],
    source VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 套餐表
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    plan VARCHAR(20),  -- monthly/yearly
    price DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'active',
    starts_at TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 1.2 后端服务架构

```
backend/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py           # 配置管理
│   ├── database.py         # 数据库连接
│   ├── auth.py             # JWT 认证
│   ├── models.py           # SQLAlchemy 模型
│   ├── schemas.py          # Pydantic schemas
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py         # 登录/注册
│   │   ├── users.py        # 用户管理
│   │   ├── contents.py     # 内容CRUD
│   │   ├── ab_tests.py     # A/B 测试
│   │   ├── posts.py       # 发布记录
│   │   ├── analytics.py    # 数据分析
│   │   ├── materials.py    # 素材库
│   │   ├── subscription.py # 订阅管理
│   │   └── mcp.py         # MCP 集成
│   ├── services/
│   │   ├── viral_generator.py    # 爆款生成
│   │   ├── accurate_simulator.py  # 精准测试
│   │   ├── quality_assessor.py    # 质量评估
│   │   ├── mcp_service.py         # MCP 服务
│   │   ├── analytics_engine.py   # 数据分析
│   │   └── scheduler.py          # 定时任务
│   └── workers/
│       ├── __init__.py
│       ├── content_worker.py     # 内容生成队列
│       ├── analytics_worker.py   # 数据统计队列
│       └── scheduler.py          # 定时任务
├── requirements.txt
└── alembic/               # 数据库迁移
```

### 1.3 前端架构

```
frontend/
├── src/
│   ├── components/
│   │   ├── common/        # 通用组件（Button、Input、Modal等）
│   │   ├── layout/       # 布局组件（Header、Sidebar等）
│   │   ├── auth/         # 登录、注册组件
│   │   ├── editor/       # 内容编辑器
│   │   ├── dashboard/    # 数据仪表盘
│   │   ├── analytics/    # 数据分析图表
│   │   └── materials/    # 素材库组件
│   ├── pages/
│   │   ├── Home/         # 首页/Landing
│   │   ├── Auth/         # 登录/注册
│   │   ├── Dashboard/     # 用户仪表盘
│   │   ├── Editor/       # 内容编辑
│   │   ├── ABTest/       # A/B 测试
│   │   ├── Posts/        # 发布历史
│   │   ├── Analytics/     # 数据分析
│   │   ├── Materials/     # 素材库
│   │   ├── Settings/      # 设置
│   │   └── Pricing/      # 定价页面
│   ├── hooks/            # 自定义Hooks
│   ├── services/         # API 服务
│   ├── stores/           # 状态管理
│   ├── utils/           # 工具函数
│   └── types/           # 类型定义
├── package.json
└── tailwind.config.js
```

## 二、核心功能模块

### 2.1 用户系统

- [ ] 邮箱注册/登录
- [ ] 第三方登录（微信/小红书）
- [ ] 密码重置
- [ ] 会员套餐（免费/Pro/Enterprise）
- [ ] 额度管理（免费用户每月100次）

### 2.2 内容生成

- [ ] 对话式内容创作
- [ ] 批量生成（一次10篇）
- [ ] AI 润色/改写
- [ ] 敏感词检测
- [ ] 违禁词检查

### 2.3 A/B 测试

- [ ] 受众模拟测试
- [ ] 多版本对比
- [ ] 统计置信度
- [ ] 历史结果对比

### 2.4 发布追踪

- [ ] 小红书账号绑定
- [ ] 定时发布
- [ ] 效果追踪（点赞/收藏/评论/分享）
- [ ] 趋势图表

### 2.5 数据分析

- [ ] 内容表现仪表盘
- [ ] 爆款内容分析
- [ ] 受众分析
- [ ] 竞品监测

### 2.6 素材库

- [ ] 图片素材管理
- [ ] 文案素材库
- [ ] 标签库
- [ ] 热门话题库

## 三、集成 rednote-mcp

### 3.1 账号管理

```
用户绑定流程：
1. 用户点击"绑定小红书"
2. 后端调用 MCP 获取二维码
3. 用户扫码登录
4. MCP 返回 cookies
5. 后端加密存储用户 cookies
6. 后续操作使用用户账号的 cookies
```

### 3.2 数据同步

```
定时任务（每小时）：
1. 获取用户所有笔记列表
2. 获取每篇笔记的最新互动数据
3. 更新本地数据库
4. 计算趋势变化
5. 触发异常通知（如数据暴跌）
```

### 3.3 MCP 工具封装

```python
class MCPService:
    async def get_user_posts(self, user_id: str) -> List[Post]:
        """获取用户所有帖子"""
        
    async def get_post_stats(self, user_id: str, note_id: str) -> PostStats:
        """获取单篇帖子数据"""
        
    async def publish_content(self, user_id: str, content: ContentItem) -> str:
        """发布内容"""
        
    async def track_history(self, user_id: str) -> List[HistoryRecord]:
        """追踪历史数据变化"""
```

## 四、变现系统

### 4.1 套餐设计

| 功能 | Free | Pro (¥99/月) | Enterprise (¥999/月) |
|------|------|---------------|----------------------|
| A/B 测试/月 | 100次 | 无限 | 无限 |
| 批量生成 | ❌ | 100篇/天 | 无限 |
| 历史追踪 | 7天 | 90天 | 无限 |
| 数据分析 | 基础 | 详细 | 详细 |
| 定时发布 | ❌ | ✅ | ✅ |
| 团队成员 | 1人 | 3人 | 10人 |
| API 接入 | ❌ | ❌ | ✅ |

### 4.2 支付集成

- [ ] Stripe 支付（国际）
- [ ] 支付宝/微信支付（国内）

## 五、前端 UI/UX 设计

### 5.1 页面结构

```
首页 (landing page)
├── Hero 区域 - 产品介绍 + CTA
├── 功能特性 - 三大核心功能
├── 使用流程 - 简单3步
├── 定价展示 - 三个套餐
├── 用户评价 - 社会证明
└── Footer - 链接和版权

用户仪表盘
├── 左侧导航 - 功能菜单
├── 顶部栏 - 用户信息 + 额度显示
├── 数据概览 - 本周数据卡片
├── 近期活动 - 最近操作记录
└── 快捷操作 - 常用功能入口

内容编辑器
├── 左侧 - 对话/任务定义
├── 中间 - A/B 内容编辑
├── 右侧 - 模拟结果
└── 顶部 - 工具栏

数据分析
├── 趋势图表 - 互动数据变化
├── 对比分析 - A/B 测试结果
├── 受众画像 - 粉丝特征
└── 竞品对比 - 与同行对比
```

### 5.2 设计规范

- 配色：主色 #FF2442（小红书红），辅助色 #000000
- 字体：中文思源黑体，英文 Inter
- 圆角：8px-16px
- 阴影：柔和阴影
- 动画：平滑过渡效果

## 六、部署架构

### 6.1 开发环境

```
Docker Compose:
├── backend:3000    # FastAPI
├── frontend:3001   # React
├── postgres:5432   # PostgreSQL
├── redis:6379      # Redis
├── celery-beat:    # 定时任务
└── celery-worker:  # 任务队列
```

### 6.2 生产环境

```
AWS/GCP:
├── Load Balancer
├── Frontend (CloudFront)
├── Backend (ECS/EKS)
├── PostgreSQL (RDS)
├── Redis (ElastiCache)
├── S3 (素材存储)
└── CloudWatch (监控)
```

## 七、开发优先级

### Phase 1: MVP (2周)

- [ ] 用户注册/登录
- [ ] 内容生成（基础版）
- [ ] A/B 测试
- [ ] 简单数据展示
- [ ] 免费额度管理

### Phase 2: 核心功能 (3周)

- [ ] 批量生成
- [ ] MCP 集成发布
- [ ] 历史数据追踪
- [ ] 质量评估
- [ ] Pro 套餐

### Phase 3: 数据分析 (2周)

- [ ] 数据仪表盘
- [ ] 趋势分析
- [ ] 报表导出
- [ ] 竞品分析

### Phase 4: 完善功能 (2周)

- [ ] 定时发布
- [ ] 素材库
- [ ] 团队协作
- [ ] API 接入

## 八、技术选型

| 分类 | 选择 | 理由 |
|------|------|------|
| 后端 | FastAPI + Python | 开发效率高、AI 生态好 |
| 前端 | React + TypeScript | 生态成熟、类型安全 |
| UI 组件 | Shadcn UI | 现代化、定制性强 |
| 数据库 | PostgreSQL | 稳定、功能强 |
| ORM | SQLAlchemy | 灵活、功能全 |
| 任务队列 | Celery | 成熟稳定 |
| 缓存 | Redis | 速度快 |
| 部署 | Docker + K8s | 可扩展 |
| 支付 | Stripe/Alipay | 行业标准 |

## 九、预计工作量

| 阶段 | 功能 | 工作量 |
|------|------|--------|
| Phase 1 | MVP | 2 人周 |
| Phase 2 | 核心功能 | 3 人周 |
| Phase 3 | 数据分析 | 2 人周 |
| Phase 4 | 完善功能 | 2 人周 |
| **总计** | | **9 人周** |

## 十、下一步行动

1. ✅ 本文档确认
2. 创建数据库迁移脚本
3. 实现用户认证系统
4. 重构后端架构
5. 重新设计前端
6. 集成 MCP
7. 测试和部署
