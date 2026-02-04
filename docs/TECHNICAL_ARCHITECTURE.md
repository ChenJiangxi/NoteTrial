# NoteTrial 技术架构与数据流程

## 一、产品概述

**NoteTrial** 是一个小红书内容 A/B 测试工具，帮助创作者在发布前预测内容效果，生成更容易火的笔记。

## 二、用户使用流程与技术对应

### 流程阶段 1：用户认证与数据导入

```
用户操作          →  前端                →  后端              →  数据库
────────────────────────────────────────────────────────────────────────────
1. 注册/登录      →  LoginPage          →  POST /auth/login  →  users 表
                   →  保存 JWT Token                         →  auth_tokens 表

2. 导入历史发帖    →  HistoryLearning    →  MCP 获取笔记列表   →  learning_data 表
                   →  分析写作风格       →  POST /learning    →  user_profiles 表
```

**数据流**：
```
小红书网页
    ↓ (browser MCP)
获取笔记列表 (note_id, title, likes, saves, comments)
    ↓
POST /history/import/xhs
    ↓
解析 → 存储到 learning_data
    ↓
AI 分析 → 更新 user_profiles (writing_tone, favorite_tags, avg_title_length)
```

---

### 流程阶段 2：设定创作目标

```
用户操作          →  前端                →  后端              →  数据库
────────────────────────────────────────────────────────────────────────────
1. 输入话题       →  ChatPanel          →  POST /chat        →  sessions 表
                   →  或 AutoModePage

2. 选择优化目标    →  下拉选择           →  存入 task_spec    →  task_specs 表
   - 最大化点赞
   - 最大化收藏
   - 最大化评论
   - 最大化分享

3. 输入目标受众    →  文本输入           →  存入 task_spec    →  task_specs 表
   - "年轻女生"
   - "职场白领"
   - "母婴用户"
```

**TaskSpec 数据结构**：
```typescript
{
  platform: 'xiaohongshu',
  goals: ['maximize_like', 'maximize_save'],
  audience: '18-25岁女性',
  tone_constraints: ['轻松', '真实'],
  topic: '防晒霜推荐',
  test_type: 'crowd_simulation'
}
```

---

### 流程阶段 3：AI 内容生成

```
用户操作          →  前端                →  后端              →  数据库
────────────────────────────────────────────────────────────────────────────
1. 点击生成       →  generateComplete() →  POST /contents/   →  contents 表
                   →  AutoModePage         generate          →  content_variants 表

2. AI 多模型投票   →  等待结果           →  MultiModelVoter   →  (不存储)
                   →  显示生成结果         调用 GPT-4o
                                        →  调用 Claude
                                        →  调用 Gemini
                                        →  投票选择最佳

3. 人性化处理      →  显示评分           →  AIHumanizer       →  (不存储)
                   →  可选择是否应用        检测 AI 痕迹
                                        →  重写更像真人
                                        →  输出 humanness_score
```

**生成流程图**：
```
POST /contents/generate
    ↓
┌─────────────────────────────────────────────────────────────┐
│  1. 获取用户偏好 (user_profiles)                             │
│  2. 获取相关素材 (materials/relevant?topic=xxx)             │
│  3. 构建 Prompt:                                             │
│     - 基础 Prompt 模板                                       │
│     - + 用户风格 (writing_tone, emoji_density)              │
│     - + 相关素材 (images, texts)                            │
│     - + 优化目标 (goals)                                    │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  4. 多模型投票 (3个模型各自生成)                              │
│     GPT-4o → 生成标题1 / 正文1                               │
│     Claude → 生成标题2 / 正文2                               │
│     Gemini → 生成标题3 / 正文3                               │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  5. 投票选择 (每个模型评价其他两个的结果)                      │
│     最高分版本 → 作为最终输出                                │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  6. 人性化处理                                               │
│     - 检测 AI 特征词                                         │
│     - 重写使其更自然                                         │
│     - 输出 humanness_score (0-100)                          │
└─────────────────────────────────────────────────────────────┘
    ↓
返回: { title, body, tags, cover_image?, humanness_score }
```

---

### 流程阶段 4：A/B 测试

```
用户操作          →  前端                →  后端              →  数据库
────────────────────────────────────────────────────────────────────────────
1. 创建 A/B 测试   →  CrowdTestPanel    →  POST /ab-tests   →  ab_tests 表
                   →  输入 A/B 内容       →  存入 test_spec   →  test_results 表

2. 模拟人群测试    →  显示进度           →  PersonaSimulator →  (不存储)
                   →  显示 A/B 对比        调用多个 Persona
                                        →   (学生/白领/宝妈等)
                                        →   收集反馈
                                        →   计算胜出率

3. 查看结果       →  显示胜出版本       →  返回测试结果      →  test_results 表
                   →  选择发布版本       →  记录用户选择      →  contents.published_version
```

**A/B 测试流程**：
```
POST /ab-tests/{id}/run
    ↓
┌─────────────────────────────────────────────────────────────┐
│  Persona 模拟 (10-50 个虚拟用户)                             │
│  每个 Persona 有:                                            │
│  - persona_id: "student_18_25_female"                       │
│  - interests: ["美妆", "护肤"]                               │
│  - personality: ["跟风", "理性"]                             │
│  - platform_habit: "晚8点刷小红书"                           │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  每个 Persona 对 A 和 B 评分:                                │
│  - like: boolean                                            │
│  - save: boolean                                            │
│  - comment: boolean                                         │
│  - share: boolean                                           │
│  - reasoning: "为什么喜欢/不喜欢"                             │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  统计结果:                                                   │
│  - version_a_score: { likes: 8, saves: 5, ... }             │
│  - version_b_score: { likes: 6, saves: 3, ... }             │
│  - like_confidence: { winner: "A", confidence: 0.87 }       │
│  - diagnosis: ["A 的标题更有吸引力"]                          │
│  - suggestions: ["建议使用 A 版本发布"]                       │
└─────────────────────────────────────────────────────────────┘
```

---

### 流程阶段 5：素材库自动使用

```
用户操作          →  前端                →  后端              →  数据库
────────────────────────────────────────────────────────────────────────────
1. 上传素材       →  MaterialLibrary    →  POST /materials/  →  material_images 表
                   →  图片/文案素材        images             →  material_texts 表

2. 生成时使用素材  →  AutoModePage       →  POST /contents/   →  (不存储)
                   →  use_materials: true  generate-with-   →  相关素材自动
                                        →  materials         →  融入生成内容
                                        →  GET /materials/   →  materials/relevant
                                        →  ?topic=xxx
```

**素材库使用流程**：
```
POST /contents/generate-with-materials
{
  "topic": "防晒霜推荐",
  "use_materials": true,
  "max_images": 5,
  "max_texts": 10
}
    ↓
┌─────────────────────────────────────────────────────────────┐
│  1. 查询相关素材                                              │
│     GET /materials/relevant?topic=防晒霜&max_images=5       │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  2. 素材格式化为 Prompt 片段                                  │
│     Images:                                                 │
│     - ![防晒霜1](url1)                                       │
│     - ![防晒霜2](url2)                                       │
│                                                             │
│     Texts:                                                  │
│     - 已有文案: "SPF50+ 持久防晒..."                         │
│     - 标签: #防晒 #护肤 #夏天                                │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  3. 融入 Prompt                                              │
│     "根据以下素材生成小红书内容:                              │
│      素材图片: [url1, url2, ...]                             │
│      已有文案: [text1, text2, ...]                           │
│      标签: #防晒 #护肤 #夏天                                 │
│                                                             │
│      要求: 开头 Hook、干货内容、CTA 引导"                     │
└─────────────────────────────────────────────────────────────┘
    ↓
生成内容 (已融入素材)
```

---

### 流程阶段 6：定时发布

```
用户操作          →  前端                →  后端              →  数据库
────────────────────────────────────────────────────────────────────────────
1. 设置定时发布   →  AutoModePage       →  POST /scheduler   →  scheduler_tasks 表
                   →  选择时间/频率       →  添加任务

2. 定时任务执行    →  (后台)            →  APScheduler       →  (不存储)
                   →  通知用户            →  时间到达时触发
                                        →  调用小红书 MCP
                                        →  发布内容

3. 发送通知       →  显示通知           →  发送通知          →  notifications 表
```

**定时发布流程**：
```
SchedulerService (APScheduler)
    ↓
cronjob: 每天 20:00 执行
    ↓
┌─────────────────────────────────────────────────────────────┐
│  检查待发布任务                                               │
│  SELECT * FROM scheduler_tasks                              │
│  WHERE status = 'pending'                                   │
│    AND scheduled_at <= NOW()                                │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  遍历任务:                                                    │
│  1. 获取 content                                             │
│  2. 调用小红书 MCP 发布                                       │
│  3. 记录 post_id                                             │
│  4. 启动数据追踪 (monitor_task)                              │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  发送通知:                                                   │
│  - 成功: "笔记已发布"                                        │
│  - 失败: "发布失败，请重试"                                  │
└─────────────────────────────────────────────────────────────┘
```

---

### 流程阶段 7：数据追踪与闭环学习

```
用户操作          →  前端                →  后端              →  数据库
────────────────────────────────────────────────────────────────────────────
1. 发布后追踪     →  Dashboard          →  GET /posts/      →  posts 表
                   →  显示数据             {id}/refresh      →  post_metrics 表

2. 定时获取数据    →  (后台)            →  MonitorService   →  (不存储)
                   →  更新图表              → 小红书 MCP
                                        →  get_note_stats
                                        →  记录 likes/saves/

                                        comments/shares
                                        →  更新 posts 表

3. 数据校准 AI    →  Analytics          →  POST /calibrate  →  calibration 表
                   →  查看预测准确率       →  对比预测 vs 真实
                                        →  调整 Persona 权重
                                        →  更新 Prompt 模板
```

**数据追踪流程**：
```
MonitorService (每 6 小时执行)
    ↓
┌─────────────────────────────────────────────────────────────┐
│  1. 获取待监控的 post_ids                                    │
│     SELECT id FROM posts                                    │
│     WHERE status = 'published'                              │
│       AND last_checked < 6_hours_ago                        │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  2. 调用小红书 MCP 获取真实数据                               │
│     xiaohongshu.get_note_stats(note_id)                     │
│     返回: { likes, saves, comments, shares }                │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  3. 存储真实数据                                             │
│     UPDATE posts                                            │
│     SET metrics = { likes: 523, saves: 89, ... }            │
│     WHERE id = 'xxx'                                        │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  4. 对比预测 vs 真实                                         │
│     SELECT predicted_score, metrics FROM posts              │
│     WHERE id = 'xxx'                                        │
│                                                             │
│     计算准确率:                                              │
│     accuracy = 1 - |predicted - actual| / max_value         │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│  5. 校准 Persona 权重                                        │
│     - 如果 "学生" Persona 预测偏高                            │
│     - 降低该 Persona 的权重                                   │
│     - 更新 calibration 表                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、数据库 Schema

### 核心表

```sql
-- 用户表
users (
  id: UUID PRIMARY KEY,
  email: VARCHAR(255) UNIQUE,
  password_hash: VARCHAR(255),
  created_at: TIMESTAMP,
  updated_at: TIMESTAMP
)

-- 内容表 (生成的 A/B 版本)
contents (
  id: UUID PRIMARY KEY,
  user_id: UUID REFERENCES users(id),
  title: VARCHAR(200),
  body: TEXT,
  cover_image: VARCHAR(500),
  tags: JSONB,
  task_spec: JSONB,
  predicted_score: FLOAT,
  humanness_score: FLOAT,
  status: 'draft' | 'published',
  published_version: 'A' | 'B',
  created_at: TIMESTAMP
)

-- 发布记录表 (小红书实际发布)
posts (
  id: UUID PRIMARY KEY,
  content_id: UUID REFERENCES contents(id),
  user_id: UUID REFERENCES users(id),
  note_id: VARCHAR(100),      -- 小红书笔记 ID
  xsec_token: VARCHAR(200),
  scheduled_at: TIMESTAMP,
  published_at: TIMESTAMP,
  metrics: JSONB,             -- { likes, saves, comments, shares }
  last_checked: TIMESTAMP,
  status: 'scheduled' | 'published' | 'failed'
)

-- 素材库 - 图片
material_images (
  id: UUID PRIMARY KEY,
  user_id: UUID REFERENCES users(id),
  url: VARCHAR(500),
  path: VARCHAR(500),
  filename: VARCHAR(200),
  tags: JSONB,
  description: TEXT,
  source: VARCHAR(50),
  created_at: TIMESTAMP
)

-- 素材库 - 文案
material_texts (
  id: UUID PRIMARY KEY,
  user_id: UUID REFERENCES users(id),
  content: TEXT,
  text_type: VARCHAR(50),     -- 'copy', 'title', 'tag', 'hook'
  tags: JSONB,
  description: TEXT,
  performance: JSONB,         -- 历史表现数据
  created_at: TIMESTAMP
)

-- 学习数据 (历史发帖分析)
learning_data (
  id: UUID PRIMARY KEY,
  user_id: UUID REFERENCES users(id),
  note_id: VARCHAR(100),
  title: VARCHAR(200),
  body: TEXT,
  metrics: JSONB,
  imported_at: TIMESTAMP
)

-- 用户画像 (AI 分析结果)
user_profiles (
  id: UUID PRIMARY KEY,
  user_id: UUID REFERENCES users(id),
  writing_tone: VARCHAR(50),      -- 'casual', 'cute', 'professional'
  paragraph_style: VARCHAR(50),   -- 'short', 'medium', 'long'
  emoji_density: VARCHAR(50),     -- 'low', 'medium', 'high'
  avg_title_length: INT,
  avg_body_length: INT,
  favorite_tags: JSONB,
  content_preferences: JSONB,
  last_updated: TIMESTAMP
)

-- A/B 测试表
ab_tests (
  id: UUID PRIMARY KEY,
  user_id: UUID REFERENCES users(id),
  content_a_id: UUID REFERENCES contents(id),
  content_b_id: UUID REFERENCES contents(id),
  task_spec: JSONB,
  status: 'pending' | 'running' | 'completed',
  created_at: TIMESTAMP
)

-- A/B 测试结果
test_results (
  id: UUID PRIMARY KEY,
  test_id: UUID REFERENCES ab_tests(id),
  version_a_score: JSONB,
  version_b_score: JSONB,
  persona_results: JSONB,
  winner: 'A' | 'B' | 'tie',
  confidence: FLOAT,
  diagnosis: JSONB,
  suggestions: JSONB
)

-- 定时任务表
scheduler_tasks (
  id: UUID PRIMARY KEY,
  user_id: UUID REFERENCES users(id),
  content_id: UUID REFERENCES contents(id),
  scheduled_at: TIMESTAMP,
  interval_hours: INT,       -- 0 表示单次
  status: 'pending' | 'running' | 'completed' | 'failed',
  last_run: TIMESTAMP,
  created_at: TIMESTAMP
)

-- 校准数据 (预测准确率追踪)
calibration (
  id: UUID PRIMARY KEY,
  user_id: UUID REFERENCES users(id),
  content_id: UUID REFERENCES contents(id),
  predicted_score: FLOAT,
  actual_score: FLOAT,
  accuracy: FLOAT,
  calibrated_at: TIMESTAMP
)
```

---

## 四、外部服务集成

### 小红书 MCP (xiaohongshu-mcp)

```
┌─────────────────────────────────────────────────────────────┐
│                    xiaohongshu MCP                           │
├─────────────────────────────────────────────────────────────┤
│  功能:                                                       │
│  - login() → QRCode + Token                                 │
│  - check_login_status() → logged_in                         │
│  - get_note_stats(note_id) → { likes, saves, ... }          │
│  - publish_note(title, body, images) → note_id              │
│  - search_notes(keyword) → [{ note_id, title, ... }]        │
│  - get_user_notes(user_id) → [{ note_id, title, ... }]      │
│  - get_hot_feeds(limit) → [{ note_id, title, ... }]         │
├─────────────────────────────────────────────────────────────┤
│  依赖:                                                       │
│  - 小红书 cookies (从浏览器获取)                              │
│  - _acw_tc (Anti-Crawler Token)                             │
└─────────────────────────────────────────────────────────────┘
```

### AI 模型

```
┌─────────────────────────────────────────────────────────────┐
│                    AI 模型配置                               │
├─────────────────────────────────────────────────────────────┤
│  GPT-4o (OpenAI)                                            │
│  - 用途: 内容生成、标题优化                                   │
│  - Prompt: viral_generator.py 中的模板                       │
├─────────────────────────────────────────────────────────────┤
│  Claude (Anthropic)                                         │
│  - 用途: 内容生成、风格转换                                   │
│  - Prompt: 与 GPT-4o 相同模板                                │
├─────────────────────────────────────────────────────────────┤
│  Gemini (Google)                                            │
│  - 用途: 内容生成、热点分析                                   │
│  - Prompt: 与 GPT-4o 相同模板                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 五、API 端点完整列表

### 认证模块 (/api/v1/auth)

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | /auth/register | 用户注册 |
| POST | /auth/login | 用户登录 |
| POST | /auth/logout | 退出登录 |
| GET | /auth/me | 获取当前用户 |
| GET | /auth/qrcode | 获取登录二维码 |
| GET | /auth/login-status | 检查登录状态 |

### 内容模块 (/api/v1/contents)

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | /contents | 列表内容 |
| POST | /contents | 创建内容 |
| GET | /contents/{id} | 获取内容 |
| PATCH | /contents/{id} | 更新内容 |
| DELETE | /contents/{id} | 删除内容 |
| POST | /contents/generate | 生成内容 |
| POST | /contents/generate-with-materials | 用素材生成 |
| POST | /contents/auto-generate | 自动生成多版本 |
| POST | /contents/publish | 发布到小红书 |
| POST | /contents/{id}/variants | 生成变体 |
| GET | /contents/relevant-materials/{topic} | 获取相关素材 |

### A/B 测试模块 (/api/v1/ab-tests)

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | /ab-tests | 列表测试 |
| POST | /ab-tests | 创建测试 |
| GET | /ab-tests/{id} | 获取测试 |
| POST | /ab-tests/{id}/run | 运行测试 |
| DELETE | /ab-tests/{id} | 删除测试 |

### 素材库模块 (/api/v1/materials)

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | /materials/images | 列表图片 |
| POST | /materials/images | 上传图片 |
| DELETE | /materials/images/{id} | 删除图片 |
| GET | /materials/texts | 列表文案 |
| POST | /materials/texts | 添加文案 |
| DELETE | /materials/texts/{id} | 删除文案 |
| GET | /materials/stats | 统计 |
| GET | /materials/relevant | 获取相关素材 |

### 数据分析模块 (/api/v1/analytics)

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | /analytics/summary | 概览数据 |
| GET | /analytics/trends | 趋势数据 |
| GET | /analytics/top-posts | 热门帖子 |

### 学习模块 (/api/v1/learning)

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | /learning/stats | 学习统计 |
| GET | /learning/style-prompt | 风格 Prompt |
| POST | /learning/update-style | 更新风格 |

### 历史记录模块 (/api/v1/history)

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | /history/stats | 历史统计 |
| GET | /history/posts | 历史帖子 |
| POST | /history/analyze | 分析内容 |
| POST | /history/import/xhs | 从小红书导入 |

### 定时任务模块 (/api/v1/scheduler)

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | /scheduler/tasks | 列表任务 |
| POST | /scheduler/tasks | 创建任务 |
| DELETE | /scheduler/tasks/{id} | 删除任务 |

### 监控模块 (/api/v1/monitor)

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | /monitor/tasks | 创建监控 |
| GET | /monitor/tasks | 列表监控 |
| DELETE | /monitor/tasks/{id} | 删除监控 |

---

## 六、性能与扩展

### 当前性能指标

| 操作 | 响应时间 | 并发限制 |
|------|---------|---------|
| 内容生成 | 5-15s | 3/用户 |
| A/B 测试 | 10-30s | 1/用户 |
| 数据同步 | 1-3s | 5/用户 |
| 素材查询 | <1s | 无限制 |

### 扩展方案

1. **水平扩展**: 后端服务可部署多个实例
2. **缓存层**: Redis 缓存热门话题、用户画像
3. **队列**: Celery 处理长时间任务 (A/B 测试、数据同步)
4. **CDN**: 素材图片使用 CDN 加速
