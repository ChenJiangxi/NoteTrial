"""
NoteTrial Backend - 增强版内容生成服务
专注于生成高质量、低 AI 味、能成为爆款的内容
"""
import json
import re
from typing import Optional, List, Dict, Any, Tuple
from openai import AsyncOpenAI
import asyncio

from ..models import (
    TaskSpec, ContentItem, ChatMessage, ChatResponse,
    Platform, OptimizationGoal
)
from ..config import get_settings


settings = get_settings()


# ============ 高质量 Prompt 模板库 ============

VIRAL_TITLE_PROMPT = """
你是小红书爆款标题专家，精通创造高点击率标题。

【任务】
为以下内容创作一个高点击率的{goal}标题。

【内容信息】
- 话题：{topic}
- 受众：{audience}
- 核心卖点：{key_points}

【爆款标题公式】
1. **数字+结果型**："3天瘦5斤"、"坚持28天..."
2. **对比型**："平替vs大牌"、"之前vs现在..."
3. **问句型**："还在用...?..."、"为什么...?"
4. **揭秘型** "内部员工说..."、"很少人知道..."
5. **痛点型**："别再...了！"、"...的救星！"

【小红书标题特征】
- 8-15字最佳
- 前3字最重要（决定是否继续看）
- 适当使用 emoji 增加亲和力
- 口语化，像朋友推荐

【输出要求】
输出JSON格式：
{{
    "title": "你的标题（严格≤20字，必须数清楚）",
    "style": "数字型/对比型/问句型/揭秘型/痛点型",
    "hook_type": "结果先行/提问/对比/痛点/揭秘",
    "emoji_used": "是否使用了emoji (yes/no)",
    "why_work": "这个标题为什么能火（1句话）"
}}

【绝对规则】
⚠️ 标题严格≤20字！数清楚再输出！
"""

VIRAL_BODY_PROMPT = """
你是小红书爆款内容创antian，精通创造高互动内容。

【任务】
围绕「{topic}」创作一篇能提高{goal}的小红书笔记。

【基本信息】
- 受众：{audience}
- 语气：{tone}
- 目标：{goal}

【开头 Hook（决定用户是否继续看）】
从以下选择最合适的开头：
1. **结果先行**：直接给结论/效果
2. **痛点共鸣**：描述共同困境
3. **提问互动**：引发思考
4. **揭秘吸引**：抛出悬念
5. **身份认同**：用身份标签锁定人群

【正文结构模板】
```
开头 Hook（50字以内）
  ↓
背景/问题（100字）
  ↓
核心内容（500-600字）
  ├─ 干货1 + 细节
  ├─ 干货2 + 细节
  └─ 干货3 + 细节
  ↓
结尾引导（50-100字）
  ├─ 总结价值
  └─ CTA（求赞/求收藏/引导评论）
```

【语言风格要求】
✅ 使用口语化表达（绝绝子、yyds、真的...、姐妹们...）
✅ 适当 emoji（✨💄⚠️📌）
✅ 短句为主，段落分明（2-3句一段）
❌ 避免：长篇大论、书面化表达、AI味词汇

【小红书高互动内容特征】
- 收藏率高：清单、教程、避坑、对比
- 点赞率高：共鸣、认同、惊叹、共情
- 评论率高：提问、投票、争议、求助

【输出要求】
输出JSON格式：
{{
    "hook_type": "选择的开头类型",
    "hook": "开头文案（≤50字，必须口语化）",
    "body": "正文内容（≤1000字，分段清晰）",
    "cta": "结尾引导语",
    "structure": "使用的结构类型",
    "emoji_count": "emoji数量",
    "readability": "可读性评分 1-10"
}}

【绝对规则】
⚠️ 正文严格≤1000字！
⚠️ 开头必须有明确 Hook！
⚠️ 语言必须口语化！
"""

HUMANIZE_PROMPT = """
你是资深小红书用户，精通把AI味内容改写成真人风格。

【原文】
标题：{title}
正文：{body}

【问题诊断】
{issues}

【真人写作特征】
1. **口语化**：用"真的"、"绝了"、"姐妹们"等
2. **情绪化**：有感叹、有态度、有喜好
3. **细节感**：有具体数字、具体场景、具体感受
4. **不完美**：偶尔有口语错误、语气词
5. **个人化**：有"我觉得"、"我的感受是"

【AI味常见特征】
- 过于工整的结构
- 缺乏具体细节
- 缺少情感波动
- 过于客观中立
- 用词过于正式

【改写要求】
1. 保持核心信息不变
2. 把书面语改口语化
3. 加入真实情感和态度
4. 添加合适的 emoji
5. 让内容像真人发的

【输出】
输出JSON：
{{
    "humanized_title": "改写后的标题",
    "humanized_body": "改写后的正文",
    "changes": ["改动点1", "改动点2"],
    "ai_removed": "移除了哪些AI味表达"
}}
"""


class EnhancedContentGenerator:
    """增强版内容生成器"""
    
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.client = AsyncOpenAI(
            api_key=api_key or settings.openai_api_key,
            base_url=base_url or settings.openai_base_url
        )
        self.model = model or settings.default_model
    
    async def generate_viral_title(
        self,
        topic: str,
        audience: str,
        key_points: str,
        goal: str = "maximize_save"
    ) -> Dict[str, Any]:
        """生成爆款标题"""
        goal_map = {
            "maximize_save": "收藏率",
            "maximize_like": "点赞率",
            "maximize_comment": "评论率",
            "maximize_share": "分享率"
        }
        goal_text = goal_map.get(goal, "互动率")
        
        prompt = VIRAL_TITLE_PROMPT.format(
            topic=topic,
            audience=audience,
            key_points=key_points,
            goal=goal_text
        )
        
        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.9
            )
            result = json.loads(completion.choices[0].message.content)
            
            # 确保标题不超长
            result["title"] = self._truncate_to_limit(result.get("title", ""), 20)
            
            return result
        except Exception as e:
            return {"error": str(e)}
    
    async def generate_viral_body(
        self,
        topic: str,
        audience: str,
        goal: str = "maximize_save",
        tone: str = "真实、不营销",
        reference_samples: List[dict] = None
    ) -> Dict[str, Any]:
        """生成爆款正文"""
        goal_map = {
            "maximize_save": "收藏率",
            "maximize_like": "点赞率",
            "maximize_comment": "评论率",
            "maximize_share": "分享率"
        }
        goal_text = goal_map.get(goal, "互动率")
        
        # 添加参考样本
        ref_section = ""
        if reference_samples:
            ref_section = "\n【真实爆款参考】\n"
            for i, sample in enumerate(reference_samples[:3], 1):
                title = sample.get("title", "") or sample.get("displayTitle", "")
                if title:
                    ref_section += f"参考{i}：{title}\n"
        
        prompt = VIRAL_BODY_PROMPT.format(
            topic=topic,
            audience=audience,
            goal=goal_text,
            tone=tone
        ) + ref_section
        
        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.9
            )
            result = json.loads(completion.choices[0].message.content)
            
            # 确保不超长
            result["body"] = self._truncate_to_limit(result.get("body", ""), 1000)
            result["hook"] = self._truncate_to_limit(result.get("hook", ""), 50)
            
            return result
        except Exception as e:
            return {"error": str(e)}
    
    async def humanize_content(
        self,
        title: str,
        body: str,
        issues: List[str] = None
    ) -> Dict[str, Any]:
        """AI 味去除"""
        if issues is None:
            issues = ["语言过于正式", "缺乏情感", "结构过于工整"]
        
        prompt = HUMANIZE_PROMPT.format(
            title=title,
            body=body,
            issues="\n".join(f"- {i}" for i in issues)
        )
        
        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.95
            )
            result = json.loads(completion.choices[0].message.content)
            
            result["humanized_title"] = self._truncate_to_limit(
                result.get("humanized_title", title), 20
            )
            result["humanized_body"] = self._truncate_to_limit(
                result.get("humanized_body", body), 1000
            )
            
            return result
        except Exception as e:
            return {"error": str(e)}
    
    async def generate_complete_content(
        self,
        task_spec: TaskSpec,
        reference_samples: List[dict] = None,
        do_humanize: bool = True
    ) -> ContentItem:
        """生成完整内容（标题+正文+标签）"""
        
        # 1. 生成标题
        key_points = task_spec.topic or "相关内容"
        title_result = await self.generate_viral_title(
            topic=task_spec.topic,
            audience=task_spec.audience,
            key_points=key_points,
            goal=task_spec.goals[0].value if task_spec.goals else "maximize_save"
        )
        
        # 2. 生成正文
        goal_value = task_spec.goals[0].value if task_spec.goals else "maximize_save"
        tone = ", ".join(task_spec.tone_constraints) if task_spec.tone_constraints else "真实、不营销"
        
        body_result = await self.generate_viral_body(
            topic=task_spec.topic,
            audience=task_spec.audience,
            goal=goal_value,
            tone=tone,
            reference_samples=reference_samples
        )
        
        # 3. 生成标签
        tags = await self._generate_tags(task_spec.topic)
        
        # 4. AI 味去除
        if do_humanize and not title_result.get("error"):
            humanized = await self.humanize_content(
                title=title_result.get("title", ""),
                body=body_result.get("body", "")
            )
            if not humanized.get("error"):
                title = humanized.get("humanized_title", title_result.get("title", ""))
                body = humanized.get("humanized_body", body_result.get("body", ""))
            else:
                title = title_result.get("title", "")
                body = body_result.get("body", "")
        else:
            title = title_result.get("title", "")
            body = body_result.get("body", "")
        
        return ContentItem(
            title=title[:20],
            body=body[:1000],
            tags=tags
        )
    
    async def _generate_tags(self, topic: str) -> List[str]:
        """生成相关标签"""
        prompt = f"""为「{topic}」生成5个小红书标签。

要求：
1. 热门且相关
2. 不要太泛泛
3. 符合小红书风格

输出JSON：{{"tags": ["标签1", "标签2", "标签3", "标签4", "标签5"]}}"""
        
        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            result = json.loads(completion.choices[0].message.content)
            return result.get("tags", [topic])
        except Exception:
            return [topic]
    
    def _truncate_to_limit(self, text: str, limit: int) -> str:
        """确保文本不超过字数限制"""
        if len(text) <= limit:
            return text
        
        # 如果超长，截取到 limit-3 并添加 "..."
        return text[:limit-3] + "..."
    
    def _count_chinese_chars(self, text: str) -> int:
        """计算中文字符数（包含中文标点）"""
        return sum(1 for c in text if '\u4e00' <= c <= '\u9fa5' or c in '，。！？：；""''【】《》')


# 便捷函数
async def generate_viral_content(
    topic: str,
    audience: str,
    goal: str = "maximize_save",
    reference_samples: List[dict] = None
) -> ContentItem:
    """快速生成爆款内容"""
    generator = EnhancedContentGenerator()
    
    task_spec = TaskSpec(
        platform=Platform.XIAOHONGSHU,
        goals=[OptimizationGoal(goal)],
        audience=audience,
        topic=topic,
        tone_constraints=["真实", "口语化"]
    )
    
    return await generator.generate_complete_content(
        task_spec=task_spec,
        reference_samples=reference_samples,
        do_humanize=True
    )
