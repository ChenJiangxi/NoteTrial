# NoteTrial 产品改进计划 v2.0

## 核心目标

**内容质量才是核心竞争力**

---

## 一、内容生成优化

### 1.1 文字生成（优先级 P0）

#### 爆款 Prompt 库
```python
# prompts/viral_prompts.py
PROMPT_TEMPLATES = {
    "title": {
        "数字结果型": """你是小红书爆款标题专家。
任务：为「{topic}」写一个{goal}的标题。
要求：
- 8-15字
- 数字+结果开头
- 口语化
- 开头前3字决定点击
输出 JSON: {{"title": "...", "style": "数字结果型"}}""",
        
        "对比型": """...""",
        "问句型": """...""",
        "揭秘型": """...""",
        "痛点型": """...""",
    },
    
    "body": {
        "干货教程型": """你是小红书干货博主。
任务：写一篇{topic}的教程类笔记。
结构：
1. 开头 Hook（50字以内）
2. 背景/问题（100字）
3. 核心干货（500字，分3-4点）
4. 总结+CTA（50字）
要求：
- 口语化
- 适当 emoji
- 短句为主
- 像真人分享""",
        
        "经验分享型": """...""",
        "好物推荐型": """...""",
        "避坑攻略型": """...""",
    }
}
```

#### 多模型投票生成
```python
class MultiModelVoter:
    """多模型投票选择最佳生成结果"""
    
    MODELS = ["gpt-4o", "claude-3-opus", "gemini-pro"]
    
    async def generate_and_vote(
        self,
        prompt: str,
        voting_models: List[str] = None
    ) -> GeneratedContent:
        # 并行调用多个模型
        results = await asyncio.gather(*[
            self.call_model(model, prompt)
            for model in voting_models or self.MODELS
        ])
        
        # 投票选择最佳结果
        winner = self.vote(results)
        
        # 返回获胜者 + 投票详情
        return winner, {"results": results, "votes": vote_counts}
```

#### AI 检测规避
```python
class AIHumanizer:
    """AI 内容人性化处理"""
    
    async def humanize(self, content: str) -> str:
        # 1. 随机插入口语化表达
        content = self.add_casual_expressions(content)
        
        # 2. 调整句子长度分布
        content = self.adjust_sentence_lengths(content)
        
        # 3. 添加个人化表达
        content = self.add_personal_expressions(content)
        
        # 4. 随机大小写变化
        content = self.add_case_variations(content)
        
        # 5. 添加轻微"不完美"
        content = self.add_imperfections(content)
        
        return content
    
    async def check_ai_score(self, content: str) -> float:
        """检测 AI 味分数（越低越像真人）"""
        # 调用 AI 检测 API 或本地模型
```

### 1.2 图片生成（优先级 P1）

#### 封面图生成
```python
class CoverGenerator:
    """小红书封面图生成器"""
    
    STYLES = [
        "真实照片风",
        "插画风",
        "漫画风",
        "极简风",
        "撞色风",
    ]
    
    async def generate_cover(
        self,
        title: str,
        topic: str,
        style: str = "真实照片风"
    ) -> str:
        # 1. 提取关键词
        keywords = self.extract_keywords(title, topic)
        
        # 2. 生成 prompt
        prompt = self.build_image_prompt(keywords, style)
        
        # 3. 调用图片生成 API
        image_url = await self.call_image_api(prompt)
        
        # 4. 添加标题水印
        final_url = await self.add_watermark(image_url, title)
        
        return final_url
```

#### 配图建议
```python
class ImageAdvisor:
    """配图建议引擎"""
    
    async def suggest_images(
        self,
        content: str,
        topic: str
    ) -> List[ImageSuggestion]:
        """根据内容推荐配图"""
        # 1. 分析内容结构
        sections = self.segment_content(content)
        
        # 2. 为每个段落推荐配图
        suggestions = []
        for section in sections:
            suggestion = await self.get_image_for_section(
                section, topic
            )
            suggestions.append(suggestion)
        
        return suggestions
```

### 1.3 真实数据校准（优先级 P0）

```python
class RealDataCalibrator:
    """真实数据校准器"""
    
    async def calibrate_prompt(
        self,
        topic: str,
        goal: str
    ) -> dict:
        # 1. MCP 获取该话题真实爆款
        viral_posts = await self.mcp.search_topic_samples(
            topic, limit=50
        )
        
        # 2. 分析成功模式
        patterns = self.analyze_patterns(viral_posts)
        
        # 3. 生成校准提示
        calibration = {
            "title_patterns": patterns["title_patterns"],
            "opening_patterns": patterns["opening_patterns"],
            "emoji_style": patterns["emoji_style"],
            "length_preference": patterns["avg_length"],
            "success_factors": patterns["success_factors"],
        }
        
        return calibration
    
    def build_calibrated_prompt(
        self,
        base_prompt: str,
        calibration: dict
    ) -> str:
        """将校准数据注入到 prompt 中"""
        # ...
```

---

## 二、人机交互优化

### 2.1 对话式编辑器

```
┌─────────────────────────────────────────────────┐
│  对话区域                                        │
│  ───────────────────────────────────────────── │
│  用户：我想写一篇防晒霜推荐                       │
│                                                 │
│  AI：请问你的目标受众是谁？                      │
│                                                 │
│  用户：学生党，预算有限                          │
│                                                 │
│  AI：好的，想侧重哪些方面？                     │
│    ○ 性价比      ○ 成分安全    ○ 使用感受     │
│                                                 │
│  用户：性价比 + 成分安全                         │
│                                                 │
│  AI：✅ 已了解，开始生成...                      │
└─────────────────────────────────────────────────┘
```

### 2.2 多轮迭代

```python
class ConversationEditor:
    """对话式内容编辑器"""
    
    async def chat_generate(
        self,
        conversation: List[Message]
    ) -> ContentIteration:
        """对话生成，返回可编辑的内容"""
        # 1. 分析对话提取关键信息
        context = self.extract_context(conversation)
        
        # 2. 生成初稿
        draft = await self.generate_draft(context)
        
        # 3. 用户反馈迭代
        iteration = await self.iterate(
            draft, 
            user_feedback=conversation[-1].content
        )
        
        return iteration
    
    async def suggest_improvements(
        self,
        content: Content
    ) -> List[ImprovementSuggestion]:
        """基于 AI 分析给出改进建议"""
```

---

## 三、自动模式

### 3.1 定时发布

```python
class SchedulerService:
    """定时发布服务"""
    
    async def schedule_post(
        self,
        content_id: str,
        publish_at: datetime,
        platforms: List[str]
    ) -> ScheduledPost:
        """安排定时发布"""
        # 1. 验证时间（1小时 - 14天范围）
        # 2. 创建 Celery 定时任务
        task = celery_app.add_job(
            "tasks.publish_content",
            trigger="date",
            run_at=publish_at,
            args=[content_id, platforms]
        )
        
        # 3. 发送确认通知
        await self.notify_user(content_id, publish_at)
        
        return ScheduledPost(
            content_id=content_id,
            scheduled_at=publish_at,
            task_id=task.id,
            status="scheduled"
        )
```

### 3.2 数据分析仪表盘

```
┌────────────────────────────────────────────────────────────┐
│  数据概览                                 2024年1月     │
├────────────────────────────────────────────────────────────┤
│                                                            │
│   📊 互动趋势              📈  TOP 5 笔记              │
│   ┌────────────────┐       ┌────────────────────────┐    │
│   │   📈📈📈📈📈  │       │ 1. 防晒霜推荐      2.3k  │    │
│   │   📈📈📈📈📈  │       │ 2. 程序员副业       1.8k  │    │
│   │   📈📈📈📈📈  │       │ 3. AI 工具推荐      1.5k  │    │
│   │   周一  周二  ...│       │ 4. 效率提升         1.2k  │    │
│   └────────────────┘       │ 5. 职场感悟          980   │    │
│                            └────────────────────────┘    │
│                                                            │
│   📈 关键指标                             📊  转化漏斗     │
│   ┌────────────────────┐              ┌───────────────┐ │
│   │  总发布    45 篇   │              │ 曝光 → 点击   │ │
│   │  总互动   12.5k   │              │  100% → 35%  │ │
│   │  互动率    5.2%    │              │ 点击 → 收藏   │ │
│   │  爆款率    8.5%   │              │  35% → 12%   │ │
│   └────────────────────┘              └───────────────┘ │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 3.3 多项目管理

```python
# Models
class Project(Base):
    """项目"""
    id = Column(UUID, primary_key=True)
    name = Column(String(100))
    description = Column(Text)
    owner_id = Column(UUID, ForeignKey("users.id"))
    
    contents = relationship("Content", back_populates="project")
    members = relationship("ProjectMember", back_populates="project")

class ProjectMember(Base):
    """项目成员"""
    id = Column(UUID, primary_key=True)
    project_id = Column(UUID, ForeignKey("projects.id"))
    user_id = Column(UUID, ForeignKey("users.id"))
    role = Column(String(20))  # owner/editor/viewer
```

---

## 四、UI 设计规范

### 4.1 设计系统

```css
/* 设计令牌 */
:root {
  /* 颜色 */
  --color-primary: #FF2442;
  --color-primary-light: #FF4D6A;
  --color-primary-dark: #CC1D36;
  
  --color-success: #10B981;
  --color-warning: #F59E0B;
  --color-error: #EF4444;
  
  /* 字体 */
  --font-sans: 'Inter', 'Noto Sans SC', sans-serif;
  
  /* 圆角 */
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  
  /* 阴影 */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-md: 0 4px 6px rgba(0,0,0,0.07);
  --shadow-lg: 0 10px 15px rgba(0,0,0,0.1);
}
```

### 4.2 组件库

| 组件 | 用法 |
|------|------|
| `Button` | 主要操作按钮 |
| `Input` | 文本输入 |
| `Select` | 下拉选择 |
| `Card` | 内容卡片 |
| `Modal` | 弹窗 |
| `Table` | 数据表格 |
| `Chart` | 图表 |
| `Avatar` | 用户头像 |
| `Badge` | 状态标签 |
| `Empty` | 空状态 |

### 4.3 页面结构

```
Page Layout
├── Header
│   ├── Logo
│   ├── Navigation
│   └── User Menu
├── Sidebar (Collapsible)
│   ├── Dashboard
│   ├── Projects
│   │   └── Project List
│   ├── Contents
│   │   ├── All
│   │   ├── Drafts
│   │   └── Published
│   ├── Analytics
│   ├── Settings
│   └── Team
└── Main Content
    └── Page Specific Content
```

---

## 五、开发任务清单

### Phase 1: 内容生成优化（P0）

- [ ] 重构 `viral_generator.py`
- [ ] 实现多模型投票生成
- [ ] 实现 AI 人性化处理
- [ ] 实现真实数据校准
- [ ] 重构 `image_generator.py`
- [ ] 实现封面图生成
- [ ] 实现配图建议

### Phase 2: 人机交互优化（P0）

- [ ] 设计对话式编辑器 UI
- [ ] 实现多轮迭代功能
- [ ] 添加智能建议系统
- [ ] 实现实时预览

### Phase 3: 自动模式（P1）

- [ ] 实现定时发布任务
- [ ] 实现 Celery 调度
- [ ] 实现数据分析仪表盘
- [ ] 实现多项目管理

### Phase 4: UI 优化（P2）

- [ ] 统一设计系统
- [ ] 优化页面布局
- [ ] 添加动画效果
- [ ] 响应式适配

### Phase 5: 测试与提交（P0）

- [ ] 编译检查所有代码
- [ ] 运行测试
- [ ] 提交到 openclaw 分支
- [ ] 创建 PR

---

## 六、文件结构

```
backend/
├── app/
│   ├── prompts/           # Prompt 库
│   │   ├── viral_prompts.py
│   │   └── image_prompts.py
│   ├── services/
│   │   ├── viral_generator.py    # 重构
│   │   ├── image_generator.py    # 重构
│   │   ├── multi_model_voter.py # 新增
│   │   ├── ai_humanizer.py      # 新增
│   │   ├── real_calibrator.py   # 新增
│   │   ├── scheduler.py         # 新增
│   │   └── analytics_engine.py  # 新增
│   ├── api/
│   │   ├── contents.py         # 重构
│   │   ├── projects.py          # 新增
│   │   └── analytics.py        # 重构
│   └── models/
│       ├── project.py          # 新增
│       └── scheduled_post.py    # 新增

frontend/
├── src/
│   ├── components/
│   │   ├── ui/              # 基础组件
│   │   ├── editor/          # 编辑器组件
│   │   └── analytics/        # 图表组件
│   ├── pages/
│   │   ├── Editor.tsx       # 重构
│   │   ├── Projects.tsx      # 新增
│   │   └── Analytics.tsx     # 重构
│   └── hooks/
│       └── useEditor.ts      # 新增

tests/
├── test_generation.py
├── test_humanizer.py
└── test_scheduler.py
```
