"""
NoteTrial Backend - 内容生成服务
处理对话、任务解析、内容生成等功能
"""
import json
from typing import Optional, List, Tuple
from openai import AsyncOpenAI

from ..models import (
    TaskSpec, ContentItem, ChatMessage, ChatResponse,
    Platform, OptimizationGoal
)
from ..config import get_settings


settings = get_settings()


class ContentGenerator:
    """内容生成器"""
    
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.client = AsyncOpenAI(
            api_key=api_key or settings.openai_api_key,
            base_url=base_url or settings.openai_base_url
        )
        self.model = model or settings.default_model
    
    async def parse_task_from_chat(
        self, 
        messages: List[ChatMessage],
        current_content: Optional[ContentItem] = None
    ) -> Tuple[str, Optional[TaskSpec], Optional[ContentItem]]:
        """
        从对话中解析任务规格
        
        返回：(回复消息, 解析出的TaskSpec, 生成的内容)
        """
        # 构建对话历史
        chat_history = "\n".join([
            f"{'用户' if m.role == 'user' else '助手'}: {m.content}"
            for m in messages
        ])
        
        content_context = ""
        if current_content:
            content_context = f"""
【当前编辑的内容】
标题：{current_content.title}
正文：{current_content.body[:200]}...
标签：{', '.join(current_content.tags) if current_content.tags else '无'}
"""
        
        system_prompt = f"""你是NoteTrial的AI助手，帮助用户创建小红书内容并进行A/B测试。

你的任务：
1. 理解用户想要创作的内容类型和目标
2. 提取关键信息：选题、目标受众、优化目标
3. 帮助用户完善内容创意

【重要】关于上传的文档：
- 如果用户上传了文档（消息中会有 [上传文件: xxx] 标记），你必须仔细阅读文档内容
- 生成内容时，要充分参考文档中的产品信息、特点、卖点等
- 把文档中的关键信息融入到标题和正文中
- 不要忽略用户上传的任何资料

当你收集到足够信息后，输出结构化的任务规格。
{content_context}
请用JSON格式回复：
{{
    "message": "给用户的回复消息",
    "task_spec_ready": true/false,  // 是否已收集到足够信息
    "task_spec": {{  // 仅当task_spec_ready为true时
        "platform": "xiaohongshu",
        "goals": ["maximize_save", "maximize_like"],  // 可以有1个或多个目标: maximize_save, maximize_like, maximize_comment, maximize_share
        "audience": "目标受众描述",
        "tone_constraints": ["语气约束1", "语气约束2"],
        "topic": "选题/话题"
    }},
    "generated_content": {{  // 如果用户要求生成内容
        "title": "标题（严格≤20字，数清楚再输出）",
        "body": "正文（严格≤1000字）",
        "tags": ["标签1", "标签2"]
    }}
}}

【绝对不可违反的规则】：
1. 标题严格限制在20字以内（含标点和emoji，超过必须删减）
2. 正文严格限制在1000字以内
3. goals字段是数组，可以有多个目标。可选值：maximize_save（收藏）、maximize_like（点赞）、maximize_comment（评论）、maximize_share（分享）
4. 如果用户没有明确说优化目标，默认为["maximize_save"]（收藏率）
5. 保持对话自然，不要一次问太多问题

回复格式要求（非常重要）：
1. message字段中的文字必须使用纯文本，禁止使用任何markdown格式（如**加粗**、*斜体*、# 标题等）
2. message中不要出现内部技术术语如"maximize_save"、"maximize_like"等，用中文表达，如"提高收藏率"、"增加点赞数"
3. 回复语气要友好自然，像朋友一样交流
"""
        
        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"对话历史：\n{chat_history}\n\n请分析并回复。"}
                ],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(completion.choices[0].message.content)
            
            message = result.get("message", "")
            task_spec = None
            generated_content = None
            
            if result.get("task_spec_ready") and result.get("task_spec"):
                ts = result["task_spec"]
                
                # 处理goals字段，支持多个目标
                valid_goals = ["maximize_save", "maximize_like", "maximize_comment", "maximize_share"]
                goals_raw = ts.get("goals") or ts.get("goal", ["maximize_save"])
                
                # 如果是字符串，转为列表
                if isinstance(goals_raw, str):
                    # 处理斜杠分隔的情况
                    if "/" in goals_raw:
                        goals_raw = [g.strip() for g in goals_raw.split("/")]
                    else:
                        goals_raw = [goals_raw]
                
                # 过滤有效目标
                goals_list = [g for g in goals_raw if g in valid_goals]
                if not goals_list:
                    goals_list = ["maximize_save"]  # 默认值
                
                task_spec = TaskSpec(
                    platform=Platform(ts.get("platform", "xiaohongshu")),
                    goals=[OptimizationGoal(g) for g in goals_list],
                    audience=ts.get("audience", ""),
                    tone_constraints=ts.get("tone_constraints", []),
                    topic=ts.get("topic", "")
                )
            
            if result.get("generated_content"):
                gc = result["generated_content"]
                generated_content = ContentItem(
                    title=gc.get("title", "")[:20],  # 确保不超过20字
                    body=gc.get("body", "")[:1000],  # 确保不超过1000字
                    tags=gc.get("tags", [])
                )
            
            return message, task_spec, generated_content
            
        except Exception as e:
            return f"抱歉，处理出错了：{str(e)}", None, None
    
    async def generate_variant(
        self,
        task_spec: TaskSpec,
        base_content: ContentItem,
        variant_type: str = "alternative",
        reference_samples: List[dict] = None
    ) -> ContentItem:
        """
        基于现有内容生成变体版本
        
        variant_type:
        - alternative: 完全不同的角度
        - hook: 不同的开头hook
        - actionable: 更偏"可抄作业"的版本
        
        reference_samples: 从MCP搜索获取的高赞内容样本，用于模仿降低AI味
        """
        # 处理多目标
        goals_str = ', '.join([g.value for g in task_spec.goals]) if task_spec.goals else 'maximize_save'
        
        # 构建参考内容部分
        reference_section = ""
        if reference_samples and len(reference_samples) > 0:
            reference_section = "\n【高赞爆款参考】\n以下是小红书上该话题的真实高赞内容，请学习它们的写作风格、表达方式和内容结构：\n\n"
            for i, sample in enumerate(reference_samples[:5], 1):
                title = sample.get("title", "") or sample.get("noteCard", {}).get("displayTitle", "")
                # 获取互动数据
                note_card = sample.get("noteCard", {}) or sample.get("note_card", {})
                interact_info = note_card.get("interactInfo", {})
                liked_count = interact_info.get("likedCount", "")
                
                if title:
                    reference_section += f"参考{i}：{title}"
                    if liked_count:
                        reference_section += f" (点赞: {liked_count})"
                    reference_section += "\n"
            
            reference_section += """
【重要】请深度模仿以上高赞内容的特点：
1. 学习它们的标题结构和吸引力技巧
2. 模仿它们的口语化表达，避免书面语
3. 参考它们的内容排版和节奏感
4. 使用类似的emoji和符号风格
5. 保持真实、接地气的语气，降低AI味
"""
        
        prompt = f"""你是小红书资深创作者，擅长写出高赞爆款内容。

【原始内容（Version A）】
标题：{base_content.title}
正文：{base_content.body}
标签：{', '.join(base_content.tags) if base_content.tags else '无'}

【目标受众】{task_spec.audience}
【优化目标】{goals_str}
【语气要求】{', '.join(task_spec.tone_constraints) if task_spec.tone_constraints else '无特殊要求'}
{reference_section}
【你的任务】
基于原始内容的核心信息，重新创作一篇更有爆款潜力的Version B：
- 用更吸引人的方式表达同样的内容
- 语言要口语化、真实、有温度
- 像真人博主在分享，而不是AI在输出
- 可以加入适当的emoji增加亲和力

请输出JSON格式：
{{
    "title": "新标题（严格≤20字，含标点emoji）",
    "body": "新正文（≤1000字，口语化、有节奏感）",
    "tags": ["标签1", "标签2", "标签3"]
}}

【绝对不可违反的规则】：
1. 标题严格≤20字（含标点、emoji、空格，多了就删）
2. 正文严格≤1000字
3. 内容要像真人写的，避免AI味
"""
        
        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(completion.choices[0].message.content)
            
            return ContentItem(
                title=result.get("title", base_content.title)[:20],
                body=result.get("body", base_content.body)[:1000],
                tags=result.get("tags", base_content.tags)
            )
            
        except Exception as e:
            # 出错时返回原内容的简单变体
            return ContentItem(
                title=f"【版本B】{base_content.title}"[:20],
                body=base_content.body,
                tags=base_content.tags
            )
    
    async def improve_content(
        self,
        content: ContentItem,
        suggestions: List[str],
        task_spec: Optional[TaskSpec] = None
    ) -> ContentItem:
        """根据建议改进内容"""
        
        task_context = ""
        if task_spec:
            goals_str = ', '.join([g.value for g in task_spec.goals]) if task_spec.goals else 'maximize_save'
            task_context = f"""
【目标受众】{task_spec.audience}
【优化目标】{goals_str}
"""
        
        prompt = f"""你是小红书内容优化专家。

【原始内容】
标题：{content.title}
正文：{content.body}
标签：{', '.join(content.tags) if content.tags else '无'}
{task_context}
【改进建议】
{chr(10).join(f'- {s}' for s in suggestions)}

请根据以上建议优化内容，输出JSON格式：
{{
    "title": "优化后的标题（不超过20字）",
    "body": "优化后的正文（不超过1000字）",
    "tags": ["标签1", "标签2", "标签3"]
}}
"""
        
        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(completion.choices[0].message.content)
            
            return ContentItem(
                title=result.get("title", content.title)[:20],
                body=result.get("body", content.body)[:1000],
                tags=result.get("tags", content.tags)
            )
            
        except Exception as e:
            return content

    async def generate_authentic_content(
        self,
        task_spec: TaskSpec,
        reference_samples: List[dict] = None,
        calibration_data = None,
        extra_hints: List[str] = None
    ) -> ContentItem:
        """
        生成真实风格的小红书内容（低AI味）
        
        通过学习真实爆款内容的风格来生成
        
        Args:
            task_spec: 任务规格
            reference_samples: 参考样本
            calibration_data: 校准数据
            extra_hints: 额外的优化提示（来自学习引擎、多样性控制器等）
        """
        # 构建参考内容样本
        reference_text = ""
        if reference_samples:
            samples = []
            for i, sample in enumerate(reference_samples[:8], 1):
                note_card = sample.get("noteCard", {})
                title = note_card.get("displayTitle", sample.get("title", ""))
                desc = note_card.get("desc", sample.get("desc", ""))
                interact = note_card.get("interactInfo", {})
                likes = interact.get("likedCount", "0")
                collects = interact.get("collectedCount", "0")
                
                if title:
                    samples.append(f"""
【样本{i}】点赞:{likes} 收藏:{collects}
标题：{title}
内容：{desc[:200] if desc else '(无)'}
""")
            reference_text = "\n".join(samples)
        
        # 构建校准提示
        calibration_text = ""
        if calibration_data:
            calibration_text = f"""
【该话题的成功规律】
- 标题平均长度：{calibration_data.avg_title_length:.0f}字
- 常用开头模式：{', '.join(calibration_data.common_opening_patterns[:3])}
- Emoji使用率：{int(calibration_data.emoji_usage_rate * 100)}%
- 热门标签：{', '.join(calibration_data.common_tags[:5])}
"""
        
        # P0: 构建额外优化提示
        extra_hints_text = ""
        if extra_hints:
            valid_hints = [h for h in extra_hints if h and h.strip()]
            if valid_hints:
                extra_hints_text = "\n【优化建议（来自学习系统）】\n" + "\n".join(valid_hints)
        
        goals_str = ', '.join([
            {'maximize_save': '高收藏', 'maximize_like': '高点赞', 
             'maximize_comment': '高评论', 'maximize_share': '高分享'}
             .get(g.value, g.value) for g in task_spec.goals
        ])
        
        prompt = f"""你是小红书爆款内容创作专家。现在需要创作一篇关于「{task_spec.topic}」的笔记。

【创作要求】
- 目标受众：{task_spec.audience}
- 优化目标：{goals_str}
- 语气约束：{', '.join(task_spec.tone_constraints) if task_spec.tone_constraints else '真实、不营销'}

{calibration_text}
{extra_hints_text}

【真实爆款参考】（学习这些内容的风格和表达方式，不要抄袭）
{reference_text if reference_text else '暂无参考样本，请按照小红书真实用户的风格创作'}

【重要创作原则】
1. 模仿真实用户的口吻，像朋友分享一样写作
2. 使用小红书特有的表达（如：绝绝子、yyds、姐妹们、真的会谢）
3. 适当使用emoji，但不要过度
4. 标题要有吸引力，可用数字、问句、感叹句
5. 内容要有干货，让人想收藏
6. 不要有明显的AI痕迹，不要太书面化

【绝对不可违反的硬性规则】
⚠️ 标题严格限制≤20字（含所有标点、emoji、空格，必须数清楚！）
⚠️ 正文严格限制≤1000字

请用JSON格式输出：
{{
    "title": "吸引人的标题（严格≤20字，数清楚再输出）",
    "body": "正文内容（分段有结构，≤1000字）",
    "tags": ["相关标签1", "相关标签2", "相关标签3"]
}}
"""
        
        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(completion.choices[0].message.content)
            
            return ContentItem(
                title=result.get("title", f"{task_spec.topic}分享")[:20],
                body=result.get("body", "")[:1000],
                tags=result.get("tags", [task_spec.topic])
            )
            
        except Exception as e:
            print(f"生成内容失败: {e}")
            return ContentItem(
                title=f"{task_spec.topic}｜真实分享"[:20],
                body=f"关于{task_spec.topic}，我想和大家分享一下我的经验...",
                tags=[task_spec.topic]
            )
