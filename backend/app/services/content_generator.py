"""
NoteTrial Backend - 内容生成服务
处理对话、任务解析、内容生成等功能

支持多源参考：
1. 小红书爆款样本（从 MCP 获取）
2. 互联网知识搜索（AI 知识库）
3. 用户素材库（图片、文案）
"""
import json
from typing import Optional, List, Tuple, Dict, Any
from openai import AsyncOpenAI

from ..models import (
    TaskSpec, ContentItem, ChatMessage, ChatResponse,
    Platform, OptimizationGoal
)
from ..config import get_settings


settings = get_settings()


class ContentGenerator:
    """内容生成器 - 支持多源参考的智能内容创作"""
    
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
    ) -> Tuple[str, Optional[TaskSpec], Optional[ContentItem], str]:
        """
        从对话中解析任务规格
        
        返回：(回复消息, 解析出的TaskSpec, 生成的内容)
        """
        import re
        
        # 判断模型是否支持视觉（Vision API 多模态格式）
        vision_models = ['gpt-4o', 'gpt-4-vision', 'gpt-4-turbo', 'gpt-4.1', 'gpt-4.5', 'claude', 'gemini']
        supports_vision = any(vm in self.model.lower() for vm in vision_models)
        
        # 处理消息，将图片提取为合适的格式
        openai_messages = []
        chat_history_text = []  # 用于文本摘要的对话历史（不含图片base64）
        
        for m in messages:
            content = m.content
            
            if m.role == 'user' and '[图片文件:' in content:
                # 提取图片 base64 数据和用户文字
                match = re.match(
                    r'\[图片文件: (.+?)\]\n(data:image/[^;]+;base64,[^\n]+)\n\n(.*)$',
                    content, re.DOTALL
                )
                if match:
                    filename = match.group(1)
                    image_data_url = match.group(2)
                    user_text = match.group(3).strip()
                    
                    if supports_vision:
                        # 支持视觉的模型：使用多模态消息格式
                        multimodal_parts = []
                        multimodal_parts.append({
                            "type": "image_url",
                            "image_url": {
                                "url": image_data_url,
                                "detail": "low"
                            }
                        })
                        text_part = f"[用户上传了图片: {filename}] 请仔细观察这张图片的内容。"
                        if user_text:
                            text_part += f"\n\n{user_text}"
                        multimodal_parts.append({"type": "text", "text": text_part})
                        openai_messages.append({"role": "user", "content": multimodal_parts})
                    else:
                        # 不支持视觉的模型：只发送文本描述
                        text_content = f"[用户上传了图片: {filename}]（当前模型无法直接查看图片，请根据用户描述和上下文来理解图片内容）"
                        if user_text:
                            text_content += f"\n\n{user_text}"
                        openai_messages.append({"role": "user", "content": text_content})
                    
                    # 文本摘要中记录（不含 base64）
                    summary = f"用户: [上传了图片: {filename}]"
                    if user_text:
                        summary += f" {user_text}"
                    chat_history_text.append(summary)
                    continue
            
            # 普通文本消息
            openai_messages.append({"role": m.role, "content": content})
            role_label = '用户' if m.role == 'user' else '助手'
            chat_history_text.append(f"{role_label}: {content}")
        
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

【重要】关于上传的文档和图片：
- 如果用户上传了文档（消息中会有 [上传文件: xxx] 标记），你必须仔细阅读文档内容
- 如果用户上传了图片，你可以直接看到图片内容！请仔细观察图片中的所有细节（文字、产品、场景、颜色等）
- 生成内容时，要充分参考文档中的产品信息、特点、卖点等
- 对于图片，必须基于你看到的图片内容来创作，不要忽视图片信息
- 把文档和图片中的关键信息融入到标题和正文中
- 不要忽略用户上传的任何资料

当你收集到足够信息后，输出结构化的任务规格。
{content_context}
请用JSON格式回复：
{{
    "message": "给用户的回复消息",
    "task_spec_ready": true/false,  // 是否已收集到足够信息
    "action": "all",  // 用户意图：all=全部重新生成, text_only=只改文案/标题, image_only=只换图片, none=仅对话不生成
    "task_spec": {{  // 仅当task_spec_ready为true时
        "platform": "xiaohongshu",
        "goals": ["maximize_save", "maximize_like"],  // 可以有1个或多个目标: maximize_save, maximize_like, maximize_comment, maximize_share
        "audience": "目标受众描述",
        "tone_constraints": ["语气约束1", "语气约束2"],
        "topic": "选题/话题"
    }},
    "generated_content": {{  // 仅当action为all或text_only时需要
        "title": "标题（严格≤20字，数清楚再输出）",
        "body": "正文（严格≤200字，像发朋友圈一样随意）",
        "tags": ["标签1", "标签2"]
    }}
}}

【action字段判断规则】
- 用户首次创建内容、或说"重新生成"、"换一个" → action="all"
- 用户说"改下标题"、"正文换个说法"、"文案不够好" → action="text_only"
- 用户说"换张图"、"换个封面"、"图片不合适" → action="image_only"
- 用户只是聊天、问问题、没有生成需求 → action="none"

【核心：去AI味、写出真人感】
你生成的正文必须像一个真实的小红书用户随手写的，不是AI写的文章。

绝对禁止的AI味写法（出现任何一条就是失败）：
❌ "嘿！有没有想过..." "来看看..." "让我们一起..."  ← 假热情开头
❌ "趣味连连" "奇妙碰撞" "擦出火花" ← 陈词滥调
❌ "人称行走的宝藏" "贤者风范" ← 过度修饰
❌ **加粗** *斜体* 任何markdown格式 ← 正文里绝对不能有
❌ "快来看看" "快找找" "你是否中招" ← 万能结尾
❌ 排比句、对仗句 ← AI最爱用的作文手法
❌ 每段都差不多长 ← 太整齐就是AI
❌ "总结" "综上" "因此" ← 论文腔

正确的真人写法：
✅ 开头直接说事，不要寒暄："INTJ配正官 我觉得绝了"
✅ 想到啥写啥，可以跳跃："突然发现这个 哈哈哈哈哈"
✅ 句子长短不一，有的就一个词："绝。"
✅ 用emoji代替描述：🤯 > "令人震惊"
✅ 口语碎片："就很离谱" "懂的都懂" "不是 这也太准了"
✅ 可以有语气词和语气重复："啊啊啊啊" "救命"
✅ 段落有长有短，别排版太整齐

【其他硬性规则】：
1. 标题严格≤20字（含标点emoji）
2. 正文严格≤200字 —— 越短越好，100字以内最佳
3. 正文禁止任何markdown格式（**加粗**、*斜体*、- 列表等全部禁止）
4. 正文用纯文本 + emoji，换行用\\n
5. 事实准确性 - 最高优先级：
   - 绝对不能编造虚假信息
   - 不同体系（如MBTI和五行）不能强行混搭乱编
   - 不确定的知识宁可不写
6. goals字段是数组，可选值：maximize_save、maximize_like、maximize_comment、maximize_share
7. 如果用户没说优化目标，默认["maximize_save"]
8. 保持对话自然，不要一次问太多

回复格式要求（非常重要）：
1. message字段中的文字必须使用纯文本，禁止使用任何markdown格式（如**加粗**、*斜体*、# 标题等）
2. generated_content.body 也必须是纯文本，绝对不能有markdown！不能有**、*、-、#等符号
3. message中不要出现内部技术术语如"maximize_save"、"maximize_like"等，用中文表达
4. 回复语气要友好自然，像朋友一样交流
"""
        
        try:
            # 构建发送给 LLM 的消息列表
            # 使用多模态消息格式：包含图片的消息会以 Vision API 格式传递
            llm_messages = [{"role": "system", "content": system_prompt}]
            
            # 添加实际对话历史（含图片的多模态消息）
            for msg in openai_messages:
                llm_messages.append(msg)
            
            # 添加最终指令
            llm_messages.append({
                "role": "user", 
                "content": "请根据以上对话历史分析并回复。如果用户上传了图片，请仔细描述你看到的图片内容，并基于图片内容来创作。"
            })
            
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=llm_messages,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(completion.choices[0].message.content)
            
            message = result.get("message", "")
            task_spec = None
            generated_content = None
            action = result.get("action", "all")  # 提取用户意图
            
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
                    body=gc.get("body", "")[:200],  # 限制200字，话少、梗多
                    tags=gc.get("tags", [])
                )
            
            return message, task_spec, generated_content, action
            
        except Exception as e:
            return f"抱歉，处理出错了：{str(e)}", None, None, "none"
    
    async def generate_variant(
        self,
        task_spec: TaskSpec,
        base_content: ContentItem,
        variant_type: str = "alternative",
        reference_samples: List[dict] = None,
        prompt_keywords: List[str] = None,
        force_regenerate: bool = False,
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
        
        keywords_section = ""
        if prompt_keywords:
            clean_keywords = [kw.strip() for kw in prompt_keywords if kw and kw.strip()]
            if clean_keywords:
                keywords_section = (
                    "\n【关键词要求】\n"
                    f"{' / '.join(clean_keywords[:6])}\n"
                    "你必须基于这些新关键词对文案进行改写，而不是仅做微调。\n"
                    "重点修改正文内容，围绕关键词重组正文结构与信息表达。\n"
                    "至少自然融入 2 个关键词，避免堆砌。\n"
                )

        regenerate_section = ""
        if force_regenerate:
            regenerate_section = (
                "\n【重生成约束】\n"
                "这是一次基于新关键词的重生成，必须与基准版本有明显差异。\n"
                "至少改动标题表达方式，并重写正文开头和结构。\n"
            )

        prompt = f"""你是小红书资深创作者，擅长写出高赞爆款内容。

【原始内容（Version A）】
标题：{base_content.title}
正文：{base_content.body}
标签：{', '.join(base_content.tags) if base_content.tags else '无'}

【目标受众】{task_spec.audience}
【优化目标】{goals_str}
【语气要求】{', '.join(task_spec.tone_constraints) if task_spec.tone_constraints else '无特殊要求'}
{reference_section}
{keywords_section}
{regenerate_section}
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
                tags=self._dedupe_tags(result.get("tags", base_content.tags))
            )
            
        except Exception as e:
            # 出错时返回原内容的简单变体
            return ContentItem(
                title=f"【版本B】{base_content.title}"[:20],
                body=base_content.body,
                tags=self._dedupe_tags(base_content.tags)
            )

    def _dedupe_tags(self, tags: Optional[List[str]]) -> List[str]:
        if not tags:
            return []
        seen = set()
        deduped: List[str] = []
        for tag in tags:
            clean = (tag or "").strip()
            if not clean or clean in seen:
                continue
            seen.add(clean)
            deduped.append(clean)
        return deduped
    
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

    async def generate_with_multi_source(
        self,
        task_spec: TaskSpec,
        xhs_samples: List[dict] = None,
        web_knowledge: Dict[str, Any] = None,
        material_texts: List[dict] = None,
        user_materials: str = None,
        calibration_data = None,
        extra_hints: List[str] = None
    ) -> ContentItem:
        """
        多源参考内容生成 - 整合多种信息源创作高质量内容
        
        Args:
            task_spec: 任务规格
            xhs_samples: 小红书爆款样本（从 MCP 搜索获取）
            web_knowledge: 互联网知识搜索结果
            material_texts: 素材库中的文案素材
            user_materials: 用户输入的素材文本
            calibration_data: 平台校准数据
            extra_hints: 额外优化提示
        
        Returns:
            生成的内容
        """
        # 1. 构建小红书爆款参考部分
        xhs_reference = ""
        if xhs_samples:
            xhs_reference = "\n【小红书爆款参考】（学习风格和表达，不要抄袭）\n"
            for i, sample in enumerate(xhs_samples[:5], 1):
                note_card = sample.get("noteCard", {})
                title = note_card.get("displayTitle", sample.get("title", ""))
                desc = note_card.get("desc", sample.get("desc", ""))
                interact = note_card.get("interactInfo", {})
                likes = interact.get("likedCount", "")
                
                if title:
                    xhs_reference += f"\n样本{i}（👍{likes}）：{title}\n"
                    if desc:
                        xhs_reference += f"   内容：{desc[:150]}...\n"
        
        # 2. 构建互联网知识参考部分
        web_reference = ""
        if web_knowledge:
            knowledge_points = web_knowledge.get("knowledge_points", [])
            writing_angles = web_knowledge.get("writing_angles", [])
            
            if knowledge_points:
                web_reference = "\n【互联网知识参考】\n"
                for kp in knowledge_points[:3]:
                    web_reference += f"• {kp.get('title', '')}: {kp.get('content', '')[:200]}\n"
            
            if writing_angles:
                web_reference += "\n【推荐写作角度】\n"
                for angle in writing_angles[:3]:
                    web_reference += f"• {angle}\n"
        
        # 3. 构建素材库参考部分
        material_reference = ""
        if material_texts:
            material_reference = "\n【素材库文案参考】\n"
            for m in material_texts[:5]:
                text_type = m.get("text_type", "copy")
                content = m.get("content", "")[:200]
                type_label = {"copy": "正文", "title": "标题", "hook": "金句", "tag": "标签"}.get(text_type, "")
                material_reference += f"• [{type_label}] {content}\n"
        
        # 4. 构建用户素材部分
        user_material_section = ""
        if user_materials:
            user_material_section = f"\n【用户提供的素材】（必须融入以下信息）\n{user_materials}\n"
        
        # 5. 构建校准提示
        calibration_text = ""
        if calibration_data:
            calibration_text = f"""
【该话题的成功规律】
- 标题平均长度：{calibration_data.avg_title_length:.0f}字
- 常用开头模式：{', '.join(calibration_data.common_opening_patterns[:3])}
- Emoji使用率：{int(calibration_data.emoji_usage_rate * 100)}%
- 热门标签：{', '.join(calibration_data.common_tags[:5])}
"""
        
        # 6. 构建额外优化提示
        extra_hints_text = ""
        if extra_hints:
            valid_hints = [h for h in extra_hints if h and h.strip()]
            if valid_hints:
                extra_hints_text = "\n【优化建议】\n" + "\n".join(f"• {h}" for h in valid_hints)
        
        # 7. 构建目标描述
        goals_str = ', '.join([
            {'maximize_save': '高收藏', 'maximize_like': '高点赞', 
             'maximize_comment': '高评论', 'maximize_share': '高分享'}
             .get(g.value, g.value) for g in task_spec.goals
        ])
        
        # 8. 组装完整 prompt
        prompt = f"""你是小红书爆款内容创作专家。现在需要创作一篇关于「{task_spec.topic}」的笔记。

【创作要求】
- 目标受众：{task_spec.audience}
- 优化目标：{goals_str}
- 语气约束：{', '.join(task_spec.tone_constraints) if task_spec.tone_constraints else '真实、不营销'}
{calibration_text}
{xhs_reference}
{web_reference}
{material_reference}
{user_material_section}
{extra_hints_text}

【重要创作原则】
1. 融合多源信息：结合小红书爆款的表达风格 + 互联网知识的专业内容 + 用户素材的独特信息
2. 模仿真实用户的口吻，像朋友分享一样写作
3. 使用小红书特有的表达（如：绝绝子、yyds、姐妹们、真的会谢）
4. 如果用户提供了素材，必须将其核心信息融入内容中
5. 标题要有吸引力，可用数字、问句、感叹句
6. 内容要有干货，让人想收藏

【绝对不可违反的硬性规则】
⚠️ 标题严格限制≤20字（含所有标点、emoji、空格，必须数清楚！）
⚠️ 正文严格限制≤1000字

请用JSON格式输出：
{{
    "title": "吸引人的标题（严格≤20字）",
    "body": "正文内容（分段有结构，≤1000字）",
    "tags": ["相关标签1", "相关标签2", "相关标签3"],
    "sources_used": ["使用了哪些参考源"]
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
            print(f"多源生成内容失败: {e}")
            # 降级到普通生成
            return await self.generate_authentic_content(
                task_spec=task_spec,
                reference_samples=xhs_samples,
                calibration_data=calibration_data,
                extra_hints=extra_hints
            )
