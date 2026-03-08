# NoteTrial 分支对比：openclaw vs main

本文档总结 `openclaw` 分支相对于 `main` 分支的所有改动。

> **统计概览**：64 个文件变更，+20,721 行，-2,208 行

---

## 一、架构变更

### 1.1 前端架构重构

| 方面 | main 分支 | openclaw 分支 |
|------|-----------|---------------|
| **应用结构** | 单页应用 (SPA)，所有功能在 `App.tsx` 中（~1040 行） | 路由驱动的多页面应用 |
| **路由系统** | 无 | React Router DOM |
| **状态管理** | React Context | Zustand 状态管理 |
| **数据请求** | 内联 fetch 调用 | TanStack Query + 结构化 API 层 |
| **类型系统** | 内联类型定义 | 独立 `types/index.ts` |

### 1.2 后端架构重构

| 方面 | main 分支 | openclaw 分支 |
|------|-----------|---------------|
| **API 结构** | 单文件路由 | 模块化 API 目录 (`app/api/`) |
| **认证系统** | 无 | JWT 认证 + 刷新令牌 |
| **数据库** | SQLite 简单模型 | SQLAlchemy ORM + 完整关系模型 |
| **服务层** | 基础服务 | 丰富的业务服务层 |

---

## 二、新增前端模块

### 2.1 页面组件 (`frontend/src/pages/`)

| 文件 | 功能描述 | 行数 |
|------|----------|------|
| `Login.tsx` | 用户登录/注册页面 | 156 |
| `Dashboard.tsx` | 工作台首页，显示统计和快捷入口 | 456 |
| `Editor.tsx` | 对话创作模式，三栏布局（AI助手｜内容工坊｜模拟测试） | 876 |
| `History.tsx` | 历史记录查看和管理 | 270 |
| `Projects.tsx` | 多项目管理页面 | 586 |
| `Analytics.tsx` | 数据分析看板 | 483 |
| `Scheduler.tsx` | 定时发布调度器 | 581 |

### 2.2 布局组件

| 文件 | 功能描述 |
|------|----------|
| `Layout.tsx` | 应用布局框架，包含侧边栏导航、移动端响应式菜单 |

### 2.3 状态管理 (`frontend/src/stores/`)

| 文件 | Store 名称 | 功能 |
|------|------------|------|
| `auth.ts` | `useAuthStore` | 用户认证状态、JWT 令牌管理 |
| `ui.ts` | `useUIStore` | 侧边栏状态、主题切换 |
| `ui.ts` | `useRecentItemsStore` | 最近访问的内容和测试 |
| `ui.ts` | `useEditorStore` | 编辑器当前状态 |

### 2.4 API 服务层 (`frontend/src/services/`)

```
api.ts          - 重构的 API 调用层
endpoints.ts    - API 端点常量定义
```

**新增 API 功能**：
- 用户认证 (登录、注册、刷新令牌)
- 项目 CRUD
- 内容管理
- A/B 测试
- 定时发布
- 数据分析

### 2.5 类型定义 (`frontend/src/types/index.ts`)

新增完整的 TypeScript 类型：
- `User` - 用户模型
- `Project` - 项目模型
- `Content` - 内容模型
- `ABTest` - A/B 测试模型
- `Post` - 发布记录模型
- `ScheduledPost` - 定时发布模型
- `Material` - 素材模型
- API 响应类型

---

## 三、新增后端模块

### 3.1 API 路由 (`backend/app/api/`)

| 文件 | 路由前缀 | 功能 | 行数 |
|------|----------|------|------|
| `auth.py` | `/auth` | 用户认证、JWT 管理、密码重置 | 199 |
| `projects.py` | `/projects` | 项目 CRUD、项目成员管理 | 497 |
| `contents.py` | `/contents` | 内容生成、变体管理、人性化处理 | 350 |
| `ab_tests.py` | `/ab-tests` | A/B 测试创建、运行、结果分析 | 286 |
| `posts.py` | `/posts` | 发布记录管理 | 276 |
| `materials.py` | `/materials` | 素材库管理（图片、文本） | 316 |
| `analytics.py` | `/analytics` | 数据分析、报表生成 | 348 |
| `schemas.py` | - | API 请求/响应模型 | 231 |

### 3.2 业务服务 (`backend/app/services/`)

| 文件 | 功能描述 | 行数 |
|------|----------|------|
| `scheduler.py` | 定时任务基础调度器 | 556 |
| `scheduler_service.py` | 定时发布业务逻辑 | 921 |
| `viral_generator.py` | 爆款内容生成算法 | 2,240 |
| `analytics_engine.py` | 数据分析引擎 | 878 |
| `accurate_simulator.py` | 精准人群模拟器 | 610 |
| `quality_assessor.py` | 内容质量评估 | 346 |
| `real_calibrator.py` | 真实数据校准 | 770 |
| `mcp_service.py` | MCP 协议服务 | 626 |
| `image_generator.py` | 图片生成服务 (大幅增强) | +785 |

### 3.3 数据模型

**新增模型 (`backend/app/models.py`)**：
- `User` - 用户模型（含认证信息）
- `Project` - 项目模型
- `Content` - 内容模型
- `ContentVariant` - 内容变体
- `ABTest` - A/B 测试
- `TestResult` - 测试结果
- `ScheduledPost` - 定时发布
- `Material` - 素材
- `LearningData` - 学习数据

**MCP 模型 (`backend/app/models/mcp_models.py`)**：
- MCP 协议相关数据模型

### 3.4 认证系统 (`backend/app/auth.py`)

完整的 JWT 认证实现：
- 密码哈希 (bcrypt)
- JWT 令牌生成/验证
- 刷新令牌机制
- 权限装饰器

---

## 四、前端依赖变更

### 新增依赖

```json
{
  "react-router-dom": "^7.1.1",      // 路由
  "@tanstack/react-query": "^5.x",   // 数据请求
  "zustand": "^5.0.3",               // 状态管理
  "recharts": "^2.x",                // 图表
  "lucide-react": "^0.x",            // 图标
  "axios": "^1.x"                    // HTTP 客户端
}
```

---

## 五、配置文件变更

| 文件 | 变更内容 |
|------|----------|
| `docker-compose.yml` | 新增完整的 Docker 部署配置 |
| `frontend/vite.config.ts` | 添加路径别名配置 |
| `frontend/tsconfig.json` | 添加路径映射 (`@/`) |
| `frontend/tailwind.config.js` | 扩展主题配置 |

---

## 六、文档新增

| 文件 | 内容 |
|------|------|
| `PRODUCT_PLAN.md` | 产品规划文档 v1 |
| `PRODUCT_PLAN_v2.md` | 产品规划文档 v2 |
| `TECHNICAL_ARCHITECTURE.md` | 技术架构详细说明 |
| `DEVELOPMENT.md` | 开发指南 |
| `backend/README.md` | 后端说明文档 |
| `backend/app/api/README.md` | API 接口文档 |

---

## 七、功能对比

### main 分支功能
- ✅ 基础对话创作
- ✅ 人群模拟测试
- ✅ 素材库（基础）

### openclaw 分支新增功能
- ✅ **用户认证系统** - 登录、注册、JWT 认证
- ✅ **多项目管理** - 创建和切换不同项目
- ✅ **工作台仪表盘** - 数据概览、快捷入口
- ✅ **路由系统** - 多页面导航
- ✅ **对话创作模式** - 重构的三栏布局
- ✅ **自动学习模式** - 独立页面
- ✅ **历史记录** - 完整的历史管理
- ✅ **数据分析** - 分析看板页面
- ✅ **定时发布** - 调度器功能
- ✅ **爆款生成器** - viral_generator 服务
- ✅ **MCP 协议支持** - 小红书数据对接

---

## 八、模块架构图

```
NoteTrial 模块架构 (补充建议)
┌─────────────────────────────────────────────────────────────────┐
│                         前端 (React)                            │
├───────────────┬───────────────┬─────────────────────────────────┤
│   认证模块    │   路由层      │        状态管理 (Zustand)        │
│   Login.tsx   │  React Router │  auth.ts | ui.ts                │
├───────────────┴───────────────┴─────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐│
│  │  Dashboard  │  │   Editor    │  │  AutoMode   │  │Analytics││
│  │   工作台    │  │  对话创作   │  │  自动学习   │  │ 数据分析││
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘│
│                          │                │                     │
│  ┌─────────────┐  ┌──────┴──────┐  ┌──────┴──────┐  ┌─────────┐│
│  │  Projects   │  │ ChatPanel   │  │HistoryLearn│  │Scheduler││
│  │  项目管理   │  │ CrowdTest   │  │ AutoMonitor │  │定时发布 ││
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                         API 调用层
                              │
┌─────────────────────────────────────────────────────────────────┐
│                       后端 (FastAPI)                            │
├─────────────────────────────────────────────────────────────────┤
│  API 路由层                                                     │
│  /auth │ /projects │ /contents │ /ab-tests │ /analytics │ ...  │
├─────────────────────────────────────────────────────────────────┤
│  业务服务层                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │viral_generator│ │scheduler_svc │  │analytics_eng │          │
│  │   爆款生成   │  │  定时发布    │  │  数据分析    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │audience_sim  │  │ mcp_service  │  │quality_assess│          │
│  │   人群模拟   │  │  MCP 协议    │  │  质量评估    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
├─────────────────────────────────────────────────────────────────┤
│  数据层：SQLAlchemy ORM + SQLite/PostgreSQL                     │
└─────────────────────────────────────────────────────────────────┘
```



```
NoteTrial (openclaw 分支)
├── 前端 (React + TypeScript)
│   ├── 路由层 (React Router)
│   │   ├── / (WelcomePage)
│   │   ├── /login (Login)
│   │   ├── /dashboard (Dashboard)
│   │   ├── /editor (Editor - 对话创作)
│   │   ├── /auto-mode (AutoMode - 自动学习)
│   │   ├── /history (History)
│   │   ├── /projects (Projects)
│   │   ├── /analytics (Analytics)
│   │   └── /scheduler (Scheduler)
│   │
│   ├── 状态管理 (Zustand)
│   │   ├── auth.ts (认证状态)
│   │   └── ui.ts (UI 状态)
│   │
│   └── 服务层
│       ├── api.ts (API 调用)
│       └── endpoints.ts (端点定义)
│
└── 后端 (FastAPI + Python)
    ├── API 路由
    │   ├── /auth (认证)
    │   ├── /projects (项目)
    │   ├── /contents (内容)
    │   ├── /ab-tests (A/B 测试)
    │   ├── /posts (发布)
    │   ├── /materials (素材)
    │   └── /analytics (分析)
    │
    ├── 业务服务
    │   ├── viral_generator (爆款生成)
    │   ├── scheduler_service (定时发布)
    │   ├── analytics_engine (数据分析)
    │   ├── accurate_simulator (人群模拟)
    │   ├── mcp_service (MCP 协议)
    │   └── ...
    │
    └── 数据层
        ├── models.py (ORM 模型)
        ├── database.py (数据库连接)
        └── schemas.py (Pydantic 模型)
```

---

## 九、迁移注意事项

从 main 分支迁移到 openclaw 分支需要注意：

1. **数据库迁移** - 需要运行数据库迁移脚本
2. **环境变量** - 需要配置 JWT 密钥等新增环境变量
3. **依赖安装** - 前端需要安装新的 npm 依赖
4. **API 调用** - 前端 API 调用方式已重构

---

*生成时间：2024年*
