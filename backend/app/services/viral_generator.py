"""
NoteTrial Backend - 增强版爆款内容生成服务
专注于生成高质量、低 AI 味、能成为爆款的内容

功能特性：
1. 多模型投票生成（MultiModelVoter）
2. 爆款 Prompt 库（PROMPT_TEMPLATES）
3. AI 检测规避（AIHumanizer）
4. 增强生成质量与评估

Author: NoteTrial Team
Date: 2024
"""
import json
import re
import random
import asyncio
from typing import Optional, List, Dict, Any, Tuple, Callable
from enum import Enum
from dataclasses import dataclass

# 假设的模型客户端（实际使用时替换为真实实现）
# from openai import AsyncOpenAI
# from anthropic import AsyncAnthropic
# from google.generativeai import AsyncGenerativeModel


class TitleStyle(Enum):
    """
    标题风格枚举
    
    定义了小红书爆款标题的几种主要风格类型，
    每种风格都有其独特的心理触发机制和适用场景。
    """
    NUMERIC_RESULT = "数字结果型"  # "3天瘦5斤"、"7天学会..." 强调可量化的效果
    COMPARISON = "对比型"          # "平替vs大牌"、"之前vs现在..." 突出差异和变化
    QUESTION = "问句型"            # "还在用...?..."、"为什么...?" 引发思考和共鸣
    REVEAL = "揭秘型"              # "内部员工说..."、"很少人知道..." 满足求知欲
    PAIN_POINT = "痛点型"          # "别再...了！"、"...的救星！" 直击用户痛点


class BodyType(Enum):
    """
    正文类型枚举
    
    定义了小红书笔记的几种主要正文类型，
    每种类型对应不同的内容策略和用户需求。
    """
    TUTORIAL = "干货教程型"        # 教程、指南、步骤 满足学习需求
    EXPERIENCE = "经验分享型"      # 个人经历、心得、感受 建立信任和共鸣
    RECOMMENDATION = "好物推荐型"   # 产品推荐、种草 满足购物决策需求
    WARNING = "避坑攻略型"         # 避坑、踩雷、攻略 帮助用户避免损失


class ContentGoal(Enum):
    """
    内容目标枚举
    
    定义了小红书内容的不同优化目标，
    每种目标对应不同的内容策略和互动引导方式。
    """
    SAVE_RATE = "收藏率"           # 清单、教程、避坑内容高收藏
    LIKE_RATE = "点赞率"           # 共鸣、惊叹、共情内容高点赞
    COMMENT_RATE = "评论率"        # 提问、投票、争议内容高评论
    SHARE_RATE = "分享率"          # 有用、有趣、可分享内容高转发


# ============================================================================
# 第一部分：爆款 Prompt 模板库
# ============================================================================

PROMPT_TEMPLATES = {
    # ===================== 标题模板 =====================
    "title": {
        "system_prompt": """你是小红书爆款标题专家，精通创造高点击率标题。

你的专长：
1. 精准把握用户心理和注意力规律
2. 创造有强烈点击欲望的标题
3. 平衡吸引力与真实性，避免标题党

请严格遵循以下规则：
- 标题长度严格控制在 8-15 字最佳（小红书最佳标题长度）
- 前3字至关重要，决定用户是否继续浏览（黄金前3字原则）
- 使用数字和具体结果增加可信度和记忆点
- 适当使用 emoji 增加亲和力但不过度（1-2个为宜）
- 口语化表达，像朋友真诚推荐，避免官方腔调
- 避免过度夸张和虚假承诺，保持真实可信""",

        TitleStyle.NUMERIC_RESULT: """【数字结果型标题生成要求】

核心特点：
- 使用具体数字（3、7、21、28天等时间类；5斤、10cm等变化类）
- 强调可量化的结果和变化
- 突出快速/高效/显著的特点
- 数字放在开头或关键位置增强视觉冲击

字数要求：严格控制在 10-15 字

写作技巧：
1. 数字+时间+结果 = 高点击公式
2. 使用"|"分隔主题和补充说明
3. 可以加入"亲测"、"实测"等增强可信度

示例：
- "3天瘦5斤｜亲测有效的减脂攻略"
- "坚持21天｜皮肤嫩到发光"
- "7天学会｜零基础也能上手"

输出 JSON 格式：{"title": "...", "style": "数字结果型", "why_work": "..."}""",

        TitleStyle.COMPARISON: """【对比型标题生成要求】

核心特点：
- 使用对比结构（之前vs现在、平替vs大牌）
- 突出差异、变化、反差
- 引发好奇心和讨论欲望
- 满足用户的比较决策需求

字数要求：严格控制在 10-15 字

写作技巧：
1. 使用"vs"或"对比"结构
2. 强调前后差异或产品差异
3. 可以加入主观评价增强吸引力

示例：
- "平替vs大牌｜90%人看不出区别"
- "化妆前后｜判若两人"
- "大学vs社会｜真实变化太大"

输出 JSON 格式：{"title": "...", "style": "对比型", "why_work": "..."}""",

        TitleStyle.QUESTION: """【问句型标题生成要求】

核心特点：
- 提问引发思考或共鸣
- 痛点问题或知识疑问
- 引发用户想要找到答案的欲望
- 激发"我也想知道"的冲动

字数要求：严格控制在 10-15 字

写作技巧：
1. 使用"还在..."、"为什么..."、"是不是..."句式
2. 直击目标用户的痛点或困惑
3. 可以暗示答案在正文中

示例：
- "还在用错方法护肤？"
- "为什么你的妆容总是显老？"
- "毛孔粗大怎么办？"

输出 JSON 格式：{"title": "...", "style": "问句型", "why_work": "..."}""",

        TitleStyle.REVEAL: """【揭秘型标题生成要求】

核心特点：
- 抛出悬念或内部信息
- 使用"很少人知道"、"内部员工说"等
- 满足用户的求知欲和优越感
- 制造"我知道你不知道"的吸引力

字数要求：严格控制在 10-15 字

写作技巧：
1. 使用揭秘、爆料、内部等关键词
2. 强调稀有性和独家性
3. 暗示看完能获得别人不知道的信息

示例：
- "很少人知道的护肤真相"
- "内部员工透露的省钱攻略"
- "业内人士爆料｜真相惊人"

输出 JSON 格式：{"title": "...", "style": "揭秘型", "why_work": "..."}""",

        TitleStyle.PAIN_POINT: """【痛点型标题生成要求】

核心特点：
- 直击用户痛点和困扰
- 提供解决方案暗示
- 使用"别再"、"救星"、"终于"等强烈词汇
- 激发用户共鸣和解决欲望

字数要求：严格控制在 10-15 字

写作技巧：
1. 使用否定句式（别再...了）
2. 使用强烈形容词（救星、终于、绝了）
3. 明确目标人群和痛点

示例：
- "别再无效护肤了！"
- "毛孔粗大的救星找到了"
- "黄皮逆袭｜终于白了"

输出 JSON 格式：{"title": "...", "style": "痛点型", "why_work": "..."}"""
    },

    # ===================== 正文模板 =====================
    "body": {
        "system_prompt": """你是小红书爆款内容创作者，精通创造高互动内容。

你的专长：
1. 用精彩的开头抓住用户注意力（Hook）
2. 结构清晰、逻辑流畅的正文
3. 真实自然的口语化表达
4. 有效的结尾引导（CTA）

请严格遵循以下规则：
- 开头 Hook 必须在 50 字以内抓住用户（黄金3秒原则）
- 正文分段清晰，每段 2-4 行（移动端阅读友好）
- 使用口语化表达（真的、绝了、姐妹们等真人用语）
- 适当使用 emoji 增加亲和力（3-10个为宜）
- 干货内容要有具体细节和可操作性
- 结尾必须有明确的 CTA 引导互动""",

        BodyType.TUTORIAL: """【干货教程型正文结构模板】

1. 开场 Hook（30-50字）：
   - 直接告诉用户学完能获得什么具体成果
   - 用数字+结果增强吸引力
   - 例："学会这3招，7天就能见效！"

2. 背景铺垫（50-80字）：
   - 为什么这个话题重要/常见问题
   - 引发目标用户共鸣
   - 过渡到核心内容

3. 核心步骤（400-500字）：
   - 3-5个清晰步骤，每个步骤包含：
     * 具体操作方法（新手也能做）
     * 注意事项和常见错误
     * 时间、数量、频率等具体数字
     * 个人小tips增强真实感
   - 步骤之间有自然过渡

4. 常见误区（100-150字）：
   - 新手最容易犯的错误
   - 为什么这些是误区
   - 正确做法是什么

5. 总结+CTA（30-50字）：
   - 强调核心价值
   - 引导收藏、点赞、评论

要求：
- 步骤清晰，可操作性强
- 有具体细节和数字支撑
- 语言轻松自然，像在和朋友聊天
- 避免过于专业晦涩的术语""",

        BodyType.EXPERIENCE: """【经验分享型正文结构模板】

1. 开场 Hook（30-50字）：
   - 用真实经历开场
   - 设置悬念或反转
   - 引发读者继续阅读的欲望
   - 例："曾经我也觉得不可能，直到..."

2. 背景经历（80-100字）：
   - 当时的状况和想法
   - 面临的困难和挑战
   - 心理活动和感受

3. 过程分享（300-400字）：
   - 关键转折点和决定性时刻
   - 具体细节和心理活动
   - 加入不完美的真实经历（更有说服力）
   - 使用口语化表达和感叹词
   - 起承转合，有故事感

4. 最终结果（80-100字）：
   - 客观描述最终结果
   - 主观感受和评价
   - 数据支撑（如果有）

5. 感悟+CTA（30-50字）：
   - 总结核心收获和感悟
   - 引导互动（评论你的经历）

要求：
- 真实感强，有起承转合
- 情感充沛，引起共鸣
- 细节丰富，像在讲故事
- 适当暴露不完美增加可信度""",

        BodyType.RECOMMENDATION: """【好物推荐型正文结构模板】

1. 开场 Hook（30-50字）：
   - 场景化痛点引入
   - 引发目标用户共鸣
   - 例："毛孔大到能养鱼？"

2. 购买背景（50-80字）：
   - 为什么想买/为什么选这款
   - 购买决策过程
   - 真实的使用需求

3. 核心亮点（300-400字）：
   - 3-4个推荐理由，每个包含：
     * 具体使用场景和效果
     * 对比其他产品的优势
     * 真实使用感受和细节
     * 优缺点客观评价（更真实）
   - 配合图片描述增强说服力

4. 适用人群（80-100字）：
   - 什么样的人适合这款
   - 什么样的人不适合
   - 使用建议和注意事项

5. 总结+CTA（30-50字）：
   - 强调核心价值
   - 引导购买/收藏

要求：
- 真实使用感受，不是广告软文
- 优缺点都要说，更真实可信
- 给出具体使用场景和数据支撑
- 像朋友推荐而不是卖家广告""",

        BodyType.WARNING: """【避坑攻略型正文结构模板】

1. 开场 Hook（30-50字）：
   - 用踩坑经历开场
   - 引发"我也踩过"的共鸣
   - 例："花了3000块买来的教训..."

2. 问题背景（50-80字）：
   - 为什么这个坑很常见
   - 多少人踩过这个坑
   - 造成什么后果

3. 避坑指南（400-500字）：
   - 3-5个避坑要点，每个包含：
     * 坑在哪里、为什么是坑
     * 真实案例或数据
     * 正确做法和替代方案
     * 避免再次踩坑的建议
   - 要点清晰，有理有据

4. 补救措施（80-100字）：
   - 如果已经踩坑怎么办
   - 如何最大程度减少损失
   - 经验教训总结

5. 总结+CTA（30-50字）：
   - 提醒收藏，避免踩坑
   - 引导评论区分享经历

要求：
- 坑点具体，不是泛泛而谈
- 有正确做法，不只是批评
- 像过来人真诚提醒
- 数据和案例支撑可信度"""
    },

    # ===================== Humanizer 模板 =====================
    "humanizer": {
        "system_prompt": """你是资深小红书用户，精通把AI味内容改写成真人风格。

你的任务：
1. 识别并去除 AI 味表达
2. 添加真人写作的自然感
3. 保持核心信息不变
4. 增强内容的真实感和亲和力

AI 味的常见特征：
- 过于工整的排比句式（首先、其次、再次、最后）
- 缺乏具体细节和数字
- 缺少情感波动和态度
- 用词过于正式和官方（综上所述、不言而喻）
- 句子结构过于完美
- 缺少口语化和感叹词

真人写作的特征：
- 口语化表达（真的、绝了、姐妹们...）
- 有态度和情感（喜欢/不喜欢、推荐/不推荐）
- 有具体数字和细节
- 偶尔有不完美的表达
- 有个人主观感受（我觉得...）
- 使用 emoji 增加表达力""",

        "check_template": """【AI 检测评分】
分析以下内容的 AI 味程度：

标题：{title}
正文：{body}

请从以下维度评分（1-10分，越高越像AI）：
1. 语言正式程度（1=口语化，10=非常正式）
2. 情感表达强度（1=冷淡，10=情感充沛）
3. 细节丰富度（1=笼统，10=具体详细）
4. 句子完美度（1=有瑕疵，10=过于工整）
5. 结构规整度（1=随意，10=非常工整）

输出 JSON 格式，包含：
- ai_score: 综合 AI 味评分（1-10，越高越像AI）
- is_human_like: 是否像真人写的（boolean）
- issues: AI 味问题列表
- suggestions: 改进建议""",

        "humanize_template": """【真人化改写】
将以下 AI 味内容改写成真人风格：

原文标题：{title}
原文正文：{body}

诊断出的问题：
{issues}

要求：
1. 保持核心信息不变
2. 把书面语改口语化（如"总的来说"替代"综上所述"）
3. 加入真实情感和态度（"真的绝了"、"推荐给大家"）
4. 添加合适的 emoji（3-10个为宜）
5. 让内容像真人发的朋友圈
6. 可以适当加入小瑕疵增加真实感

输出 JSON 格式，包含：
- humanized_title: 改写后的标题
- humanized_body: 改写后的正文
- changes: 改动点列表
- ai_removed: 移除的 AI 味表达"""
    },

    # ===================== 质量评估模板 =====================
    "quality_check": {
        "title_template": """【标题质量评估】
标题：{title}
目标：{goal}

评估维度（1-10分）：
1. 吸引力：能否引起点击欲望
2. 相关性：与目标受众的关联度
3. 真实性：是否过度夸张
4. 记忆点：是否有独特记忆点
5. 平台适配：小红书风格契合度

输出 JSON 格式，包含：
- scores: 各维度分数
- total_score: 综合分数
- strengths: 优点
- weaknesses: 缺点
- suggestions: 改进建议""",

        "body_template": """【正文质量评估】
正文：{body}
目标：{goal}

评估维度（1-10分）：
1. 开头吸引力：Hook 是否抓人
2. 内容价值：是否有干货
3. 可操作性：能否实际应用
4. 情感共鸣：能否引发共鸣
5. 阅读体验：是否流畅易读
6. CTA 效果：结尾引导是否有效

输出 JSON 格式，包含：
- scores: 各维度分数
- total_score: 综合分数
- strengths: 优点
- weaknesses: 缺点
- suggestions: 改进建议"""
    }
}


# ============================================================================
# 第二部分：AI 检测规避工具类
# ============================================================================

class AIHumanizer:
    """
    AI 内容人性化处理工具

    功能：
    1. humanize() - 将 AI 生成内容改写成真人风格
    2. check_ai_score() - 检测内容的 AI 味程度

    特点：
    - 支持规则检测（无须调用 AI）
    - 支持 AI 深度检测（需要 AI 客户端）
    - 返回详细的改进建议
    """

    def __init__(self, client=None, model: str = "gpt-4o"):
        """
        初始化 AIHumanizer

        Args:
            client: AI 模型客户端（可选，用于深度检测）
            model: 使用的模型名称（默认 gpt-4o）
        """
        self.client = client
        self.model = model

        # 真人化表达词库
        self.human_words = {
            "口语词": ["真的", "绝了", "姐妹们", "兄弟们", "说实话", "讲真", "其实", "不过", "但是"],
            "感叹词": ["太绝了", "太强了", "太好了", "爱了", "哭了", "惊艳", "吹爆", "推荐", "避雷"],
            "模糊词": ["大概", "差不多", "感觉", "好像", "应该是", "据说"],
            "不完美词": ["有点", "稍微", "可能", "我一开始", "后来发现"],
            "个人态度": ["我觉得", "我的感受", "个人建议", "仅供参考"],
        }

        # 需要替换的 AI 味表达映射
        self.ai_phrases = {
            "首先、其次、再次、最后": "然后",
            "综上所述": "总的来说",
            "总而言之": "总的来说",
            "不言而喻": "不用说",
            "众所周知": "都知道",
            "值得注意的是": "要说的是",
            "从某种意义上说": "说实话",
            "客观来说": "我觉得",
            "不得不承认": "说实话",
        }

    async def check_ai_score(self, title: str, body: str) -> Dict[str, Any]:
        """
        检测内容的 AI 味程度

        Args:
            title: 标题文本
            body: 正文文本

        Returns:
            Dict 包含：
            - ai_score: AI 味评分（1-10，越高越像AI）
            - is_human_like: 是否像真人写的
            - issues: AI 味问题列表
            - suggestions: 改进建议
            - method: 检测方法（rule-based/hybrid）
        """
        # 规则匹配检测（快速、无须 API 调用）
        rule_based_score = self._rule_based_ai_check(title, body)

        # 如果有客户端，使用 AI 进行深度检测
        if self.client:
            return await self._ai_based_check(title, body, rule_based_score)

        return rule_based_score

    def _rule_based_ai_check(self, title: str, body: str) -> Dict[str, Any]:
        """
        基于规则检测 AI 味（快速检测，无需 API 调用）

        检测维度：
        1. 标题模式检测
        2. 正文结构检测
        3. 句子完美度检测
        4. 情感表达检测

        Args:
            title: 标题
            body: 正文

        Returns:
            AI 味检测结果
        """
        issues = []
        score = 0  # 0 表示更像真人，10 表示更像 AI

        # ========== 检测标题 AI 味 ==========
        title_ai_patterns = [
            (r"^[0-9]+[、]", "标题数字开头可能是AI套路"),
            (r"[\|｜]", "使用分隔符可能是AI格式"),
            (r"^[是否有没有]+", "疑问式标题可能是AI生成"),
        ]

        for pattern, issue in title_ai_patterns:
            if re.search(pattern, title):
                issues.append(f"标题: {issue}")
                score += 0.5

        # ========== 检测正文 AI 味 ==========
        body_ai_patterns = [
            (r"首先、其次、再次、最后", "使用了AI常见的排比结构"),
            (r"综上所述|总而言之", "使用了AI常见的总结词"),
            (r"值得注意的是|不言而喻", "使用了AI常见的高端词"),
            (r"^[\s　]+", "段落缩进可能是AI格式"),
            (r"[。]{3,}", "过多句号可能是AI节奏"),
        ]

        for pattern, issue in body_ai_patterns:
            if re.search(pattern, body):
                issues.append(f"正文: {issue}")
                score += 1

        # ========== 检测句子完美度 ==========
        # AI 生成的句子长度通常较为均匀
        sentences = re.split(r"[。！？]", body)
        if sentences:
            para_lengths = [len(s) for s in sentences if s.strip()]
            if para_lengths:
                avg_length = sum(para_lengths) / len(para_lengths)
                variance = sum((l - avg_length) ** 2 for l in para_lengths) / len(para_lengths)
                # 方差小说明句子长度过于均匀，可能是 AI
                if variance < 50:
                    issues.append("句子长度过于均匀，可能是AI生成")
                    score += 1

        # ========== 检测段落结构 ==========
        paragraphs = [p.strip() for p in body.split("\n") if p.strip()]
        if len(paragraphs) > 3:
            para_lengths = [len(p) for p in paragraphs]
            if max(para_lengths) - min(para_lengths) < 50:
                issues.append("段落长度过于均匀，可能是AI生成")
                score += 1

        # ========== 检测情感表达 ==========
        emotional_words = ["真的", "绝了", "爱了", "太", "超级", "强烈推荐", "吹爆"]
        emotional_count = sum(1 for word in emotional_words if word in body)
        if emotional_count < 2:
            issues.append("情感表达不足，像AI一样冷淡")
            score += 1.5

        # ========== 检测口语化程度 ==========
        if "我觉得" not in body and "个人感觉" not in body and len(body) > 200:
            issues.append("缺少个人主观表达，不像真人写的")
            score += 1

        # ========== 限制分数范围 ==========
        score = min(10, max(0, round(score, 1)))

        return {
            "ai_score": score,
            "is_human_like": score < 5,
            "issues": issues,
            "suggestions": self._get_suggestions(issues) if issues else [],
            "method": "rule-based"
        }

    async def _ai_based_check(
        self,
        title: str,
        body: str,
        rule_result: Dict
    ) -> Dict[str, Any]:
        """
        使用 AI 进行深度检测（需要 AI 客户端）

        当规则检测不够准确时，使用 AI 模型进行更精准的判断

        Args:
            title: 标题
            body: 正文
            rule_result: 规则检测结果

        Returns:
            综合检测结果
        """
        prompt = PROMPT_TEMPLATES["humanizer"]["check_template"].format(
            title=title,
            body=body
        )

        try:
            # 注意：这里需要根据实际客户端实现
            # 以下是 OpenAI API 的调用示例：
            # completion = await self.client.chat.completions.create(
            #     model=self.model,
            #     messages=[{"role": "user", "content": prompt}],
            #     response_format={"type": "json_object"}
            # )
            # ai_result = json.loads(completion.choices[0].message.content)

            # 模拟 AI 检测结果（实际使用时替换为真实 API 调用）
            ai_result = {
                "ai_score": 4.5,
                "is_human_like": True,
                "issues": ["语言较为正式", "缺少感叹词"],
                "suggestions": ["增加口语化表达", "加入感叹词"]
            }

            # 混合两种检测结果
            return {
                **rule_result,
                "ai_score": (rule_result["ai_score"] + ai_result["ai_score"]) / 2,
                "is_human_like": ai_result["is_human_like"],
                "issues": list(set(rule_result["issues"] + ai_result["issues"])),
                "suggestions": ai_result.get("suggestions", rule_result["suggestions"]),
                "method": "hybrid"
            }
        except Exception as e:
            # 如果 AI 检测失败，返回规则检测结果
            return {
                **rule_result,
                "method": "rule-based (AI failed)"
            }

    def _get_suggestions(self, issues: List[str]) -> List[str]:
        """
        根据问题生成改进建议

        Args:
            issues: 问题列表

        Returns:
            改进建议列表
        """
        suggestions = []

        if any("排比" in issue or "结构" in issue for issue in issues):
            suggestions.append("使用更自然的段落过渡，避免'首先、其次、再次'等机械结构")
        if any("情感" in issue for issue in issues):
            suggestions.append("增加个人情感表达，如'真的绝了'、'推荐给大家'等")
        if any("总结词" in issue or "高端词" in issue for issue in issues):
            suggestions.append("用口语化词汇替换官方表达，如'总的来说'替代'综上所述'")
        if any("数字" in issue or "套路" in issue for issue in issues):
            suggestions.append("数字使用更随意自然，避免开头就用数字套路")

        if not suggestions:
            suggestions.append("内容已经很自然，保持即可")

        return suggestions

    def humanize(self, title: str, body: str) -> Dict[str, Any]:
        """
        将 AI 内容改写成真人风格（基于规则，无须调用 AI）

        核心功能：
        1. 替换 AI 味表达为口语化表达
        2. 添加情感词和感叹词
        3. 插入个人态度表达
        4. 添加合适的 emoji

        Args:
            title: 原始标题
            body: 原始正文

        Returns:
            Dict 包含：
            - humanized_title: 改写后的标题
            - humanized_body: 改写后的正文
            - changes: 改动点列表
            - ai_removed: 移除的 AI 味表达
            - ai_score_reduced: 改写后的 AI 味评分
            - improvement: 是否有改善
        """
        changes = []

        # 1. 改写标题
        humanized_title = self._humanize_title(title)
        if humanized_title != title:
            changes.append(f"标题口语化：'{title}' -> '{humanized_title}'")

        # 2. 改写正文
        humanized_body = self._humanize_body(body)
        if humanized_body != body:
            changes.append("正文进行了口语化改写")

        # 3. 添加 emoji
        humanized_body = self._add_emojis(humanized_body)

        # 4. 检测 AI 味是否降低
        new_check = self._rule_based_ai_check(humanized_title, humanized_body)
        old_check = self._rule_based_ai_check(title, body)
        ai_reduced = new_check["ai_score"] < old_check["ai_score"]

        return {
            "humanized_title": humanized_title,
            "humanized_body": humanized_body,
            "changes": changes,
            "ai_removed": "基于规则的真人化处理（替换AI味表达、添加口语化词、插入emoji）",
            "ai_score_reduced": round(old_check["ai_score"] - new_check["ai_score"], 1),
            "improvement": ai_reduced,
            "old_ai_score": old_check["ai_score"],
            "new_ai_score": new_check["ai_score"]
        }

    def _humanize_title(self, title: str) -> str:
        """
        改写标题使其更口语化

        处理逻辑：
        1. 去除过于正式的前缀
        2. 替换正式表达为口语
        3. 去除多余格式符号

        Args:
            title: 原始标题

        Returns:
            改写后的标题
        """
        result = title.strip()

        # 去除过于正式的前缀
        prefixes_to_remove = ["关于", "论", "浅谈", "分析", "探讨"]
        for prefix in prefixes_to_remove:
            if result.startswith(prefix):
                result = result[len(prefix):]
                break

        # 替换过于正式的表达
        formal_phrases = {
            "是否": "",
            "有没有": "",
            "如何": "怎么",
            "为什么": "为啥",
        }
        for formal, informal in formal_phrases.items():
            result = result.replace(formal, informal)

        # 去除多余的符号
        result = result.replace("｜", "|").strip("| ").strip()

        return result

    def _humanize_body(self, body: str) -> str:
        """
        改写正文使其更口语化

        处理逻辑：
        1. 替换 AI 味表达
        2. 随机添加口语词
        3. 插入个人态度表达
        4. 添加感叹词增强情感

        Args:
            body: 原始正文

        Returns:
            改写后的正文
        """
        result = body

        # 1. 替换 AI 味表达为口语化表达
        for ai_phrase, human_phrase in self.ai_phrases.items():
            if ai_phrase in result:
                result = result.replace(ai_phrase, human_phrase)

        # 2. 随机添加口语词（30%概率）
        if random.random() < 0.3 and len(result) > 100:
            colloquial_word = random.choice(self.human_words["口语词"])
            sentences = re.split(r"([。！？])", result)
            if len(sentences) > 4:
                insert_pos = random.randint(2, len(sentences) // 2)
                sentences.insert(insert_pos, f"{colloquial_word}，")
                result = "".join(sentences)

        # 3. 添加个人态度表达（如果没有）
        if "我觉得" not in result and "个人感觉" not in result:
            sentences = re.split(r"([。！？])", result)
            if len(sentences) > 6:
                insert_pos = random.randint(2, len(sentences) - 3)
                attitude = random.choice(self.human_words["个人态度"])
                sentences.insert(insert_pos, f"{attitude}，")
                result = "".join(sentences)

        # 4. 添加感叹词增强情感（如果情感不足）
        if "！" not in result and len(result) > 200:
            sentences = result.split("。")
            for i, sentence in enumerate(sentences):
                if len(sentence) > 20 and random.random() > 0.7:
                    exclamation = random.choice(self.human_words["感叹词"])
                    sentences[i] = sentence + f"，{感叹词}！"
                    break
            result = "。".join(sentences)

        return result

    def _add_emojis(self, body: str) -> str:
        """
        为正文添加合适的 emoji

        Args:
            body: 正文

        Returns:
            添加 emoji 后的正文
        """
        # 根据内容类型选择合适的 emoji
        emoji_map = {
            "tips": ["💡", "✨", "📌", "⚠️"],
            "good": ["👍", "❤️", "🔥", "💯"],
            "warning": ["⚠️", "🚫", "💣"],
            "time": ["⏰", "🕐", "📅"],
            "money": ["💰", "💸", "💳"],
        }

        result = body

        # 为干货内容添加 tips emoji（40%概率）
        if any(kw in body for kw in ["步骤", "方法", "技巧", "建议"]):
            if random.random() < 0.4:
                result = re.sub(
                    r"(步骤|方法|技巧|建议)[：:]",
                    random.choice(emoji_map["tips"]) + r"\1：",
                    result,
                    count=1
                )

        # 为推荐内容添加情感 emoji（如果提到推荐）
        if any(kw in body for kw in ["推荐", "喜欢", "爱了"]):
            result = result.replace(
                random.choice(["推荐", "喜欢"]),
                random.choice(emoji_map["good"]) + random.choice(["推荐", "喜欢"])
            )

        return result


# ============================================================================
# 第三部分：多模型投票生成器
# ============================================================================

class MaterialService:
    """
    素材库服务

    功能：
    1. 从素材库获取相关素材
    2. 将素材融入生成内容
    3. 格式化素材数据

    特点：
    - 支持图片和文案素材
    - 根据话题智能匹配
    - 返回格式化后的素材信息
    """

    def __init__(self, materials_api_url: str = None):
        """
        初始化素材服务

        Args:
            materials_api_url: 素材库 API 地址（可选，用于 HTTP 调用）
        """
        self.materials_api_url = materials_api_url

    async def get_relevant_materials(
        self,
        topic: str,
        max_images: int = 5,
        max_texts: int = 10
    ) -> Dict[str, Any]:
        """
        获取与话题相关的素材

        Args:
            topic: 话题关键词
            max_images: 最大图片数量
            max_texts: 最大文案数量

        Returns:
            相关素材字典
        """
        # 注意：实际实现时，这里可以通过 HTTP 调用素材库 API
        # 或者通过依赖注入获取素材库服务实例
        #
        # 示例返回格式：
        # {
        #     "images": [
        #         {"id": "xxx", "image_data": "base64...", "tags": ["防晒", "夏天"]}
        #     ],
        #     "texts": [
        #         {"id": "xxx", "content": "文案内容", "text_type": "hook"}
        #     ]
        # }

        return {"images": [], "texts": []}

    def format_materials_for_prompt(
        self,
        materials: Dict[str, Any],
        include_images: bool = True
    ) -> str:
        """
        将素材格式化为 prompt 的一部分

        Args:
            materials: 素材字典
            include_images: 是否包含图片信息

        Returns:
            格式化的素材描述
        """
        formatted_parts = []

        # 格式化文案素材
        texts = materials.get("texts", [])
        if texts:
            formatted_parts.append("【相关文案素材】")
            for i, text in enumerate(texts, 1):
                content = text.get("content", "")
                text_type = text.get("text_type", "copy")
                formatted_parts.append(f"{i}. [{text_type}] {content}")

        # 格式化图片素材
        if include_images:
            images = materials.get("images", [])
            if images:
                formatted_parts.append("【相关图片素材】")
                for i, img in enumerate(images, 1):
                    tags = img.get("tags", [])
                    desc = img.get("description", "")
                    formatted_parts.append(
                        f"{i}. 图片标签: {', '.join(tags)} - 描述: {desc}"
                    )

        return "\n".join(formatted_parts) if formatted_parts else ""


class MultiModelVoter:
    """
    多模型投票生成器

    功能：
    1. 并行调用多个 AI 模型（gpt-4o、claude-3-opus、gemini-pro）
    2. 根据评分标准投票选择最佳结果
    3. 返回生成结果和详细的投票详情

    特点：
    - 异步并行调用，提高效率
    - 多种投票策略（分数加权、多数投票）
    - 支持单模型备用方案
    """

    def __init__(
        self,
        openai_client=None,
        anthropic_client=None,
        google_client=None,
        default_model: str = "gpt-4o",
        material_service: MaterialService = None
    ):
        """
        初始化 MultiModelVoter

        Args:
            openai_client: OpenAI 客户端（用于 gpt-4o）
            anthropic_client: Anthropic 客户端（用于 claude-3-opus）
            google_client: Google 客户端（用于 gemini-pro）
            default_model: 默认使用的模型
        """
        self.clients = {
            "gpt-4o": openai_client,
            "claude-3-opus": anthropic_client,
            "gemini-pro": google_client,
        }
        self.default_model = default_model
        self.material_service = material_service or MaterialService()

    async def generate_with_voting(
        self,
        prompt: str,
        voting_type: str = "title",
        temperature: float = 0.9
    ) -> Dict[str, Any]:
        """
        使用多模型投票生成内容

        Args:
            prompt: 提示词
            voting_type: 投票类型（title/body）
            temperature: 温度参数（0.1-1.0）

        Returns:
            Dict 包含：
            - best_result: 投票选出的最佳结果
            - voting_details: 投票详情
            - all_results: 所有模型的生成结果
            - models_used: 使用的模型列表
        """
        # 筛选可用的模型
        model_names = ["gpt-4o", "claude-3-opus", "gemini-pro"]
        available_models = [
            name for name in model_names
            if self.clients.get(name) is not None
        ]

        if not available_models:
            # 如果没有可用客户端，使用默认模型
            return await self._single_model_generate(
                self.clients.get(self.default_model),
                self.default_model,
                prompt,
                temperature
            )

        # 并行调用所有可用的模型
        tasks = []
        for model_name in available_models:
            task = self._call_model(
                self.clients[model_name],
                model_name,
                prompt,
                temperature
            )
            tasks.append(task)

        # 等待所有模型返回结果
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        generation_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                generation_results.append({
                    "model": available_models[i],
                    "success": False,
                    "error": str(result)
                })
            else:
                generation_results.append({
                    "model": available_models[i],
                    "success": True,
                    "content": result
                })

        # 投票选择最佳结果
        best_result, voting_details = self._vote(
            generation_results,
            voting_type
        )

        return {
            "best_result": best_result,
            "voting_details": voting_details,
            "all_results": generation_results,
            "models_used": available_models
        }

    async def _call_model(
        self,
        client,
        model_name: str,
        prompt: str,
        temperature: float
    ) -> Dict[str, Any]:
        """
        调用单个模型生成内容

        Args:
            client: 模型客户端
            model_name: 模型名称
            prompt: 提示词
            temperature: 温度参数

        Returns:
            生成的内容（字典格式）
        """
        try:
            # 根据不同模型实现不同的调用方式
            if model_name.startswith("gpt"):
                # OpenAI GPT-4 API 调用示例
                # completion = await client.chat.completions.create(
                #     model="gpt-4o",
                #     messages=[{"role": "user", "content": prompt}],
                #     response_format={"type": "json_object"},
                #     temperature=temperature
                # )
                # return json.loads(completion.choices[0].message.content)
                pass

            elif model_name.startswith("claude"):
                # Anthropic Claude API 调用示例
                # response = await client.messages.create(
                #     model="claude-3-opus-20240229",
                #     max_tokens=4096,
                #     messages=[{"role": "user", "content": prompt}]
                # )
                # return json.loads(response.content[0].text)
                pass

            elif model_name.startswith("gemini"):
                # Google Gemini API 调用示例
                # response = await client.generate_content(prompt)
                # return json.loads(response.text)
                pass

            # 模拟返回（实际使用时替换为真实 API 调用）
            # 这里返回占位符，实际使用时需要根据真实 API 实现
            return {
                "title": f"[{model_name}] 生成的标题",
                "body": f"[{model_name}] 生成的内容正文...",
                "model": model_name
            }

        except Exception as e:
            # 重新抛出异常，让上层处理
            raise Exception(f"模型 {model_name} 调用失败: {str(e)}")

    async def _single_model_generate(
        self,
        client,
        model_name: str,
        prompt: str,
        temperature: float
    ) -> Dict[str, Any]:
        """
        单模型生成（备用方案）

        当没有足够的模型可用时，使用单个模型生成内容

        Args:
            client: 模型客户端
            model_name: 模型名称
            prompt: 提示词
            temperature: 温度参数

        Returns:
            生成的结果
        """
        result = await self._call_model(client, model_name, prompt, temperature)

        return {
            "best_result": result,
            "voting_details": {
                "method": "single_model",
                "model_used": model_name,
                "reason": "没有足够的模型可用，使用单模型生成"
            },
            "all_results": [{"model": model_name, "success": True, "content": result}],
            "models_used": [model_name]
        }

    def _vote(
        self,
        results: List[Dict],
        voting_type: str
    ) -> Tuple[Dict, Dict]:
        """
        对多个模型的结果进行投票

        投票策略：
        1. 筛选成功的模型结果
        2. 根据投票类型选择评分标准
        3. 选择得分最高的结果

        Args:
            results: 各模型的生成结果列表
            voting_type: 投票类型（title/body）

        Returns:
            Tuple[最佳结果, 投票详情]
        """
        # 筛选成功的模型结果
        successful_results = [
            r for r in results
            if r.get("success") and r.get("content")
        ]

        if not successful_results:
            return (
                {"error": "所有模型生成失败"},
                {"error": "投票无法进行"}
            )

        # 如果只有一个成功结果，直接返回
        if len(successful_results) == 1:
            return (
                successful_results[0]["content"],
                {
                    "method": "single_winner",
                    "selected_model": successful_results[0]["model"],
                    "reason": "只有单个模型成功"
                }
            )

        # 根据投票类型选择评分标准
        if voting_type == "title":
            scores = self._score_titles(successful_results)
        else:
            scores = self._score_bodies(successful_results)

        # 选择得分最高的结果
        best_index = max(range(len(scores)), key=lambda i: scores[i])
        best_result = successful_results[best_index]["content"]

        voting_details = {
            "method": "voting",
            "criteria": voting_type,
            "scores": [
                {"model": r["model"], "score": round(s, 2)}
                for r, s in zip(successful_results, scores)
            ],
            "selected_model": successful_results[best_index]["model"],
            "vote_count": len(successful_results),
            "winning_score": round(scores[best_index], 2)
        }

        return best_result, voting_details

    async def get_materials_for_topic(
        self,
        topic: str,
        max_images: int = 5,
        max_texts: int = 10
    ) -> Dict[str, Any]:
        """
        获取话题相关的素材

        Args:
            topic: 话题关键词
            max_images: 最大图片数量
            max_texts: 最大文案数量

        Returns:
            相关素材
        """
        if self.material_service:
            return await self.material_service.get_relevant_materials(
                topic=topic,
                max_images=max_images,
                max_texts=max_texts
            )
        return {"images": [], "texts": []}

    def enhance_prompt_with_materials(
        self,
        topic: str,
        base_prompt: str,
        materials: Dict[str, Any]
    ) -> str:
        """
        将素材融入到 prompt 中

        Args:
            topic: 话题
            base_prompt: 基础 prompt
            materials: 素材字典

        Returns:
            增强后的 prompt
        """
        if not materials or (
            not materials.get("images") and not materials.get("texts")
        ):
            return base_prompt

        # 获取格式化的素材描述
        materials_section = self.material_service.format_materials_for_prompt(
            materials,
            include_images=True
        )

        if not materials_section:
            return base_prompt

        # 构建增强后的 prompt
        enhanced_prompt = f"""{base_prompt}

以下是与话题「{topic}」相关的素材库素材，请在生成内容时参考这些素材，融入相关内容：

{materials_section}

要求：
- 参考素材的风格和表达方式
- 如有图片素材，提及相关视觉元素
- 保持素材中的核心信息准确
"""

        return enhanced_prompt

    def _score_titles(self, results: List[Dict]) -> List[float]:
        """
        对标题结果进行评分

        评分维度：
        1. 长度评分（8-15字最佳）
        2. 数字开头加分
        3. emoji 加分
        4. 口语化加分
        5. 风格标签存在加分

        Args:
            results: 标题结果列表

        Returns:
            分数列表
        """
        scores = []

        for result in results:
            content = result.get("content", {})
            title = content.get("title", "")

            score = 0

            # 1. 长度评分（8-15字最佳）
            title_len = len(title)
            if 8 <= title_len <= 15:
                score += 3
            elif 6 <= title_len <= 20:
                score += 2
            else:
                score += 0.5

            # 2. 数字开头加分
            if re.match(r"^[0-9]", title):
                score += 1.5

            # 3. emoji 加分
            if re.search(r"[\U0001F300-\U0001F9FF]", title):
                score += 1

            # 4. 口语化加分
            colloquial_words = ["真的", "绝了", "姐妹们", "兄弟们", "别再", "终于", "救星"]
            if any(word in title for word in colloquial_words):
                score += 1.5

            # 5. 分隔符使用（"|"用于分隔主题和补充）
            if "|" in title:
                score += 0.5

            # 6. 风格标签存在
            if content.get("style"):
                score += 0.5

            # 7. why_work 存在且合理
            if content.get("why_work") and len(content.get("why_work", "")) > 5:
                score += 0.5

            scores.append(score)

        return scores

    def _score_bodies(self, results: List[Dict]) -> List[float]:
        """
        对正文结果进行评分

        评分维度：
        1. Hook 存在且短（50字以内）
        2. CTA 存在
        3. 正文长度（300-800字最佳）
        4. 分段清晰（3-8段最佳）
        5. emoji 数量适中（3-10个）
        6. 口语化表达（至少2处）

        Args:
            results: 正文结果列表

        Returns:
            分数列表
        """
        scores = []

        for result in results:
            content = result.get("content", {})
            body = content.get("body", "")
            hook = content.get("hook", "")
            cta = content.get("cta", "")

            score = 0

            # 1. Hook 存在且短（50字以内）
            if hook and len(hook) <= 50:
                score += 3
            elif hook:
                score += 1

            # 2. CTA 存在
            if cta:
                score += 2

            # 3. 正文长度（300-800字最佳）
            body_len = len(body)
            if 300 <= body_len <= 800:
                score += 3
            elif 200 <= body_len <= 1000:
                score += 2
            else:
                score += 1

            # 4. 分段清晰
            paragraphs = [p.strip() for p in body.split("\n") if p.strip()]
            if 3 <= len(paragraphs) <= 8:
                score += 2
            elif 2 <= len(paragraphs) <= 10:
                score += 1

            # 5. emoji 数量适中（3-10个）
            emoji_count = len(re.findall(r"[\U0001F300-\U0001F9FF]", body))
            if 3 <= emoji_count <= 10:
                score += 2
            elif emoji_count > 0:
                score += 1

            # 6. 口语化表达
            colloquial_patterns = [
                r"真的", r"绝了", r"姐妹们", r"兄弟们",
                r"我觉得", r"推荐", r"太[棒好绝了]"
            ]
            colloquial_count = sum(
                1 for pattern in colloquial_patterns
                if re.search(pattern, body)
            )
            if colloquial_count >= 3:
                score += 2
            elif colloquial_count >= 1:
                score += 1

            # 7. 结构类型存在
            if content.get("structure"):
                score += 0.5

            scores.append(score)

        return scores


# ============================================================================
# 第四部分：质量评估工具
# ============================================================================

class QualityAssessor:
    """
    内容质量评估工具

    功能：
    1. 评估标题质量
    2. 评估正文质量
    3. 提供改进建议

    特点：
    - 多维度评分
    - 详细的优缺点分析
    - 可执行的改进建议
    """

    def __init__(self, client=None, model: str = "gpt-4o"):
        """
        初始化 QualityAssessor

        Args:
            client: AI 模型客户端（可选）
            model: 使用的模型名称
        """
        self.client = client
        self.model = model

    async def assess_title(
        self,
        title: str,
        goal: str = "收藏率"
    ) -> Dict[str, Any]:
        """
        评估标题质量

        Args:
            title: 标题文本
            goal: 目标（收藏率/点赞率/评论率/分享率）

        Returns:
            质量评估结果
        """
        # 规则基础评估
        rule_assessment = self._rule_based_title_assessment(title)

        # 如果有客户端，使用 AI 进行深度评估
        if self.client:
            return await self._ai_based_assessment(
                title, goal, rule_assessment, "title"
            )

        return rule_assessment

    async def assess_body(
        self,
        body: str,
        goal: str = "收藏率"
    ) -> Dict[str, Any]:
        """
        评估正文质量

        Args:
            body: 正文文本
            goal: 目标（收藏率/点赞率/评论率/分享率）

        Returns:
            质量评估结果
        """
        # 规则基础评估
        rule_assessment = self._rule_based_body_assessment(body)

        # 如果有客户端，使用 AI 进行深度评估
        if self.client:
            return await self._ai_based_assessment(
                body, goal, rule_assessment, "body"
            )

        return rule_assessment

    def _rule_based_title_assessment(self, title: str) -> Dict[str, Any]:
        """
        基于规则评估标题质量

        Args:
            title: 标题

        Returns:
            评估结果
        """
        scores = {}
        strengths = []
        weaknesses = []
        suggestions = []

        # 1. 长度评估
        title_len = len(title)
        if 8 <= title_len <= 15:
            scores["长度"] = 9
            strengths.append("标题长度在最佳范围内（8-15字）")
        elif 6 <= title_len <= 20:
            scores["长度"] = 7
            suggestions.append("标题可以再精简一点，控制在8-15字最佳")
        else:
            scores["长度"] = 4
            weaknesses.append("标题过长或过短")
            suggestions.append("控制在8-15字最佳")

        # 2. 数字检测
        if re.search(r"[0-9]+", title):
            scores["数字使用"] = 8
            strengths.append("使用数字增加可信度和记忆点")
        else:
            scores["数字使用"] = 5
            suggestions.append("可以加入具体数字增强吸引力（如3天、7天）")

        # 3. Emoji 检测
        if re.search(r"[\U0001F300-\U0001F9FF]", title):
            scores["emoji使用"] = 8
            strengths.append("使用emoji增加亲和力")
        else:
            scores["emoji使用"] = 6
            suggestions.append("可以适当添加1-2个emoji")

        # 4. 口语化检测
        colloquial_words = ["真的", "绝了", "姐妹们", "兄弟们", "别再", "终于", "救星"]
        if any(word in title for word in colloquial_words):
            scores["口语化"] = 8
            strengths.append("使用口语化表达，亲和力强")
        else:
            scores["口语化"] = 5
            suggestions.append("可以加入口语化表达（真的、绝了等）")

        # 5. 情感检测
        emotional_words = ["!", "！", "?", "？"]
        if any(word in title for word in emotional_words):
            scores["情感表达"] = 8
            strengths.append("使用感叹或疑问增加情感表达")
        else:
            scores["情感表达"] = 6
            suggestions.append("可以加入感叹词增强情感")

        # 计算综合分数
        total_score = sum(scores.values()) / len(scores) if scores else 0

        return {
            "scores": scores,
            "total_score": round(total_score, 1),
            "strengths": strengths,
            "weaknesses": weaknesses,
            "suggestions": suggestions,
            "method": "rule-based"
        }

    def _rule_based_body_assessment(self, body: str) -> Dict[str, Any]:
        """
        基于规则评估正文质量

        Args:
            body: 正文

        Returns:
            评估结果
        """
        scores = {}
        strengths = []
        weaknesses = []
        suggestions = []

        # 1. 开头 Hook 检测
        paragraphs = [p.strip() for p in body.split("\n") if p.strip()]
        first_para = paragraphs[0] if paragraphs else ""
        if first_para and len(first_para) <= 50:
            scores["开头Hook"] = 9
            strengths.append("开头简洁有力，Hook 效果好的开头")
        elif first_para:
            scores["开头Hook"] = 6
            suggestions.append("开头可以再精简，控制在50字以内")
        else:
            scores["开头Hook"] = 3
            weaknesses.append("缺少有效的开头Hook")

        # 2. 分段评估
        para_count = len(paragraphs)
        if 3 <= para_count <= 8:
            scores["分段结构"] = 8
            strengths.append("段落数量适中，阅读体验好")
        elif 2 <= para_count <= 10:
            scores["分段结构"] = 6
            suggestions.append("可以适当调整段落数量（3-8段最佳）")
        else:
            scores["分段结构"] = 4
            weaknesses.append("段落过多或过少")
            suggestions.append("控制在3-8段，阅读体验最佳")

        # 3. 长度评估
        body_len = len(body)
        if 300 <= body_len <= 800:
            scores["内容长度"] = 9
            strengths.append("长度适中，干货充足")
        elif 200 <= body_len <= 1000:
            scores["内容长度"] = 7
            suggestions.append("长度可以再优化（300-800字最佳）")
        else:
            scores["内容长度"] = 4
            weaknesses.append("内容过短或过长")
            suggestions.append("控制在300-800字最佳")

        # 4. CTA 检测
        cta_patterns = ["收藏", "点赞", "评论", "关注", "分享", "赞", "求"]
        if any(pattern in body for pattern in cta_patterns):
            scores["CTA引导"] = 8
            strengths.append("有明确的互动引导（CTA）")
        else:
            scores["CTA引导"] = 4
            weaknesses.append("缺少明确的CTA引导")
            suggestions.append("添加收藏、点赞等互动引导")

        # 5. Emoji 检测
        emoji_count = len(re.findall(r"[\U0001F300-\U0001F9FF]", body))
        if 3 <= emoji_count <= 10:
            scores["emoji使用"] = 8
            strengths.append("emoji使用数量适中")
        elif emoji_count > 0:
            scores["emoji使用"] = 6
            suggestions.append("emoji数量可以调整（3-10个为宜）")
        else:
            scores["emoji使用"] = 4
            weaknesses.append("缺少emoji")
            suggestions.append("添加适量emoji增加亲和力")

        # 6. 口语化检测
        colloquial_patterns = [
            r"真的", r"绝了", r"姐妹们", r"兄弟们",
            r"我觉得", r"太[棒好绝了]", r"推荐"
        ]
        colloquial_count = sum(
            1 for pattern in colloquial_patterns
            if re.search(pattern, body)
        )
        if colloquial_count >= 3:
            scores["口语化"] = 8
            strengths.append("口语化表达丰富，真实感强")
        elif colloquial_count >= 1:
            scores["口语化"] = 6
            suggestions.append("可以增加口语化表达")
        else:
            scores["口语化"] = 4
            weaknesses.append("口语化不足，像AI写的")
            suggestions.append("加入口语化表达（真的、绝了、我觉得等）")

        # 计算综合分数
        total_score = sum(scores.values()) / len(scores) if scores else 0

        return {
            "scores": scores,
            "total_score": round(total_score, 1),
            "strengths": strengths,
            "weaknesses": weaknesses,
            "suggestions": suggestions,
            "method": "rule-based"
        }

    async def _ai_based_assessment(
        self,
        content: str,
        goal: str,
        rule_result: Dict,
        content_type: str
    ) -> Dict[str, Any]:
        """
        使用 AI 进行深度评估

        Args:
            content: 内容文本
            goal: 目标
            rule_result: 规则评估结果
            content_type: 内容类型（title/body）

        Returns:
            综合评估结果
        """
        template = PROMPT_TEMPLATES["quality_check"]["title_template"] if content_type == "title" else PROMPT_TEMPLATES["quality_check"]["body_template"]
        prompt = template.format(title=content, body=content, goal=goal)

        try:
            # AI 评估（实际使用时需要根据真实 API 实现）
            # completion = await self.client.chat.completions.create(
            #     model=self.model,
            #     messages=[{"role": "user", "content": prompt}],
            #     response_format={"type": "json_object"}
            # )
            # ai_result = json.loads(completion.choices[0].message.content)

            # 使用规则结果作为主要结果
            return {
                **rule_result,
                "method": "hybrid"
            }
        except Exception:
            return {
                **rule_result,
                "method": "rule-based (AI failed)"
            }


# ============================================================================
# 第五部分：增强版内容生成器
# ============================================================================

class ViralGenerator:
    """
    增强版爆款内容生成器

    整合了：
    1. 多模型投票生成（MultiModelVoter）
    2. 爆款 Prompt 模板库（PROMPT_TEMPLATES）
    3. AI 检测规避（AIHumanizer）
    4. 质量评估（QualityAssessor）

    特点：
    - 使用 async 异步调用
    - 返回生成结果 + 投票详情
    - 添加详细注释
    - 支持完整的生成流程
    """

    def __init__(
        self,
        openai_client=None,
        anthropic_client=None,
        google_client=None,
        model: str = "gpt-4o"
    ):
        """
        初始化 ViralGenerator

        Args:
            openai_client: OpenAI 客户端
            anthropic_client: Anthropic 客户端
            google_client: Google 客户端
            model: 默认使用的模型
        """
        # 初始化多模型投票器
        self.voter = MultiModelVoter(
            openai_client=openai_client,
            anthropic_client=anthropic_client,
            google_client=google_client,
            default_model=model
        )

        # 初始化 AI 人性化工具
        self.humanizer = AIHumanizer(client=openai_client, model=model)

        # 初始化素材服务
        self.material_service = MaterialService()

        # 初始化质量评估工具
        self.assessor = QualityAssessor(client=openai_client, model=model)

        self.default_model = model

    async def generate_title(
        self,
        topic: str,
        audience: str,
        key_points: str,
        goal: str = "收藏率",
        style: TitleStyle = None,
        temperature: float = 0.9
    ) -> Dict[str, Any]:
        """
        生成爆款标题

        Args:
            topic: 话题主题
            audience: 目标受众
            key_points: 核心卖点
            goal: 目标（收藏率/点赞率/评论率/分享率）
            style: 标题风格（可选，不指定则随机选择）
            temperature: 温度参数

        Returns:
            生成结果和投票详情
        """
        # 如果没有指定风格，随机选择一个
        if style is None:
            style = random.choice(list(TitleStyle))

        # 构建提示词
        goal_map = {
            "收藏率": "收藏率（清单、教程、避坑内容）",
            "点赞率": "点赞率（共鸣、惊叹、共情内容）",
            "评论率": "评论率（提问、投票、争议内容）",
            "分享率": "分享率（有用、有趣、可分享内容）"
        }
        goal_text = goal_map.get(goal, "收藏率")

        # 组合完整提示词
        style_prompt = PROMPT_TEMPLATES["title"].get(style, PROMPT_TEMPLATES["title"][TitleStyle.NUMERIC_RESULT])
        full_prompt = f"{PROMPT_TEMPLATES['title']['system_prompt']}\n\n{style_prompt}\n\n【任务信息】\n- 话题：{topic}\n- 受众：{audience}\n- 核心卖点：{key_points}\n- 目标：{goal_text}"

        # 使用多模型投票生成
        result = await self.voter.generate_with_voting(
            prompt=full_prompt,
            voting_type="title",
            temperature=temperature
        )

        # 如果生成成功，进行人性化处理
        if "error" not in result.get("best_result", {}):
            title = result["best_result"].get("title", "")
            if title:
                humanized = self.humanizer.humanize(title, "")
                result["best_result"]["humanized_title"] = humanized["humanized_title"]
                result["humanizer_result"] = humanized

        return result

    async def generate_body(
        self,
        topic: str,
        audience: str,
        goal: str = "收藏率",
        body_type: BodyType = None,
        tone: str = "真实、不营销",
        temperature: float = 0.9,
        materials: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        生成爆款正文

        Args:
            topic: 话题主题
            audience: 目标受众
            goal: 目标（收藏率/点赞率/评论率/分享率）
            body_type: 正文类型（可选，不指定则随机选择）
            tone: 语气风格
            temperature: 温度参数
            materials: 素材库素材（可选，用于融入内容）

        Returns:
            生成结果和投票详情
        """
        # 如果没有指定类型，随机选择一个
        if body_type is None:
            body_type = random.choice(list(BodyType))

        # 构建提示词
        goal_map = {
            "收藏率": "收藏率（清单、教程、避坑内容）",
            "点赞率": "点赞率（共鸣、惊叹、共情内容）",
            "评论率": "评论率（提问、投票、争议内容）",
            "分享率": "分享率（有用、有趣、可分享内容）"
        }
        goal_text = goal_map.get(goal, "收藏率")

        # 组合完整提示词
        type_prompt = PROMPT_TEMPLATES["body"].get(body_type, PROMPT_TEMPLATES["body"][BodyType.TUTORIAL])
        full_prompt = f"{PROMPT_TEMPLATES['body']['system_prompt']}\n\n{type_prompt}\n\n【任务信息】\n- 话题：{topic}\n- 受众：{audience}\n- 目标：{goal_text}\n- 语气：{tone}"

        # 如果提供了素材，融入到 prompt 中
        if materials and self.voter.material_service:
            full_prompt = self.voter.enhance_prompt_with_materials(
                topic=topic,
                base_prompt=full_prompt,
                materials=materials
            )

        # 使用多模型投票生成
        result = await self.voter.generate_with_voting(
            prompt=full_prompt,
            voting_type="body",
            temperature=temperature
        )

        # 如果生成成功，进行人性化处理
        if "error" not in result.get("best_result", {}):
            body = result["best_result"].get("body", "")
            title = result["best_result"].get("title", "")
            if body:
                humanized = self.humanizer.humanize(title, body)
                result["best_result"]["humanized_body"] = humanized["humanized_body"]
                result["humanizer_result"] = humanized

        return result

    async def generate_complete(
        self,
        topic: str,
        audience: str,
        key_points: str = None,
        goal: str = "收藏率",
        body_type: BodyType = None,
        temperature: float = 0.9,
        do_humanize: bool = True,
        do_assess: bool = True,
        auto_use_materials: bool = False
    ) -> Dict[str, Any]:
        """
        生成完整内容（标题 + 正文）

        Args:
            topic: 话题主题
            audience: 目标受众
            key_points: 核心卖点（用于标题生成）
            goal: 目标（收藏率/点赞率/评论率/分享率）
            body_type: 正文类型
            temperature: 温度参数
            do_humanize: 是否进行人性化处理
            do_assess: 是否进行质量评估
            auto_use_materials: 是否自动使用素材库素材

        Returns:
            完整生成结果
        """
        materials = {}
        enhanced_prompt_body = None

        # 如果启用自动使用素材，从素材库获取相关素材
        if auto_use_materials and self.voter.material_service:
            materials = await self.voter.material_service.get_relevant_materials(
                topic=topic,
                max_images=5,
                max_texts=10
            )

        # 生成标题
        title_result = await self.generate_title(
            topic=topic,
            audience=audience,
            key_points=key_points or topic,
            goal=goal,
            temperature=temperature
        )

        # 生成正文（可选择融入素材）
        body_result = await self.generate_body(
            topic=topic,
            audience=audience,
            goal=goal,
            body_type=body_type,
            temperature=temperature,
            materials=materials if auto_use_materials else None
        )

        # 组合结果
        final_title = title_result.get("best_result", {}).get(
            "humanized_title",
            title_result.get("best_result", {}).get("title", "")
        )
        final_body = body_result.get("best_result", {}).get(
            "humanized_body",
            body_result.get("best_result", {}).get("body", "")
        )

        result = {
            "title": final_title,
            "body": final_body,
            "title_result": title_result,
            "body_result": body_result,
        }

        # 如果使用了素材，添加到结果中
        if materials:
            result["used_materials"] = {
                "images_count": len(materials.get("images", [])),
                "texts_count": len(materials.get("texts", [])),
                "materials": materials
            }

        # 质量评估
        if do_assess and final_title and final_body:
            title_assessment = await self.assessor.assess_title(final_title, goal)
            body_assessment = await self.assessor.assess_body(final_body, goal)

            result["quality_assessment"] = {
                "title": title_assessment,
                "body": body_assessment,
                "overall_score": round(
                    (title_assessment["total_score"] + body_assessment["total_score"]) / 2, 1
                )
            }

        return result

    def generate_tags(self, topic: str, count: int = 5) -> List[str]:
        """
        生成相关标签

        Args:
            topic: 话题主题
            count: 生成标签数量

        Returns:
            标签列表
        """
        # 基于关键词生成标签
        keywords = topic.split(",")[0].split("、")[0].split()
        tags = []

        for keyword in keywords[:3]:
            tags.append(f"#{keyword}")
            # 添加常见后缀
            if len(keyword) >= 2:
                tags.append(f"#{keyword}教程")
                tags.append(f"#{keyword}分享")

        # 添加通用标签
        general_tags = ["#干货分享", "#种草清单", "#避坑指南"]
        tags.extend(general_tags[:count - len(tags) + 1])

        return tags[:count]


# ============================================================================
# 第六部分：便捷函数
# ============================================================================

async def generate_viral_title(
    topic: str,
    audience: str,
    key_points: str,
    goal: str = "收藏率",
    style: TitleStyle = None
) -> Dict[str, Any]:
    """
    便捷函数：生成爆款标题

    Args:
        topic: 话题主题
        audience: 目标受众
        key_points: 核心卖点
        goal: 目标
        style: 标题风格

    Returns:
        生成结果
    """
    generator = ViralGenerator()
    return await generator.generate_title(
        topic=topic,
        audience=audience,
        key_points=key_points,
        goal=goal,
        style=style
    )


async def generate_viral_body(
    topic: str,
    audience: str,
    goal: str = "收藏率",
    body_type: BodyType = None
) -> Dict[str, Any]:
    """
    便捷函数：生成爆款正文

    Args:
        topic: 话题主题
        audience: 目标受众
        goal: 目标
        body_type: 正文类型

    Returns:
        生成结果
    """
    generator = ViralGenerator()
    return await generator.generate_body(
        topic=topic,
        audience=audience,
        goal=goal,
        body_type=body_type
    )


async def generate_viral_content(
    topic: str,
    audience: str,
    key_points: str = None,
    goal: str = "收藏率"
) -> Dict[str, Any]:
    """
    便捷函数：生成完整爆款内容

    Args:
        topic: 话题主题
        audience: 目标受众
        key_points: 核心卖点
        goal: 目标

    Returns:
        完整生成结果
    """
    generator = ViralGenerator()
    return await generator.generate_complete(
        topic=topic,
        audience=audience,
        key_points=key_points,
        goal=goal
    )


def humanize_content(title: str, body: str) -> Dict[str, Any]:
    """
    便捷函数：人性化处理内容

    Args:
        title: 标题
        body: 正文

    Returns:
        人性化处理结果
    """
    humanizer = AIHumanizer()
    return humanizer.humanize(title, body)


def check_ai_score(title: str, body: str) -> Dict[str, Any]:
    """
    便捷函数：检测 AI 味评分

    Args:
        title: 标题
        body: 正文

    Returns:
        AI 味检测结果
    """
    humanizer = AIHumanizer()
    return asyncio.run(humanizer.check_ai_score(title, body))
