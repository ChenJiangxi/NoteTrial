"""
NoteTrial Backend - 内容质量评估服务
在生成后评估内容质量，确保输出符合标准
"""
import json
import re
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI

from ..config import get_settings


settings = get_settings()


class ContentQualityAssessor:
    """内容质量评估器"""
    
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.client = AsyncOpenAI(
            api_key=api_key or settings.openai_api_key,
            base_url=base_url or settings.openai_base_url
        )
        self.model = model or settings.default_model
    
    async def assess(
        self,
        title: str,
        body: str,
        topic: str,
        goal: str = "maximize_save"
    ) -> Dict[str, Any]:
        """
        全面评估内容质量
        
        返回：
        {
            "overall_score": 0.85,
            "scores": {
                "ai味检测": 0.72,
                "标题吸引力": 0.88,
                "内容质量": 0.90,
                "合规性": 0.95
            },
            "issues": ["问题1", "问题2"],
            "suggestions": ["建议1", "建议2"],
            "passed": true/false,
            "reasons": ["通过/不通过的理由"]
        }
        """
        
        # 1. AI 味检测
        ai_score = await self._detect_ai_smell(title, body)
        
        # 2. 标题吸引力评估
        title_score = await self._assess_title(title, topic, goal)
        
        # 3. 正文质量评估
        body_score = await self._assess_body(body, topic)
        
        # 4. 合规性检查
        compliance = self._check_compliance(title, body)
        
        # 5. 综合评分
        overall = (
            ai_score * 0.3 +
            title_score * 0.25 +
            body_score * 0.35 +
            compliance["score"] * 0.1
        )
        
        # 6. 生成问题和建议
        issues, suggestions = await self._generate_feedback(
            title, body, topic, ai_score, title_score, body_score, compliance
        )
        
        # 7. 判断是否通过
        passed = (
            ai_score >= 0.6 and
            title_score >= 0.6 and
            body_score >= 0.6 and
            compliance["passed"]
        )
        
        return {
            "overall_score": overall,
            "scores": {
                "ai味检测": ai_score,
                "标题吸引力": title_score,
                "内容质量": body_score,
                "合规性": compliance["score"]
            },
            "issues": issues,
            "suggestions": suggestions,
            "passed": passed,
            "compliance_details": compliance["details"],
            "reasons": self._generate_pass_reasons(passed, ai_score, title_score, body_score, compliance)
        }
    
    async def _detect_ai_smell(self, title: str, body: str) -> float:
        """检测 AI 味"""
        
        ai_indicators = [
            "综上所述", "首先", "其次", "再次", "最后",  # 过于工整
            "具有", "实现", "提供", "确保", "保证",  # 书面化
            "非常", "十分", "相当", "极其",  # 过度修饰
            "可以有效", "能够带来", "有助于",  # AI 常用句式
            "让我们一起", "相信你一定", "相信我",  # 过度推销
            "专业", "高效", "便捷", "智能",  # 营销词汇
        ]
        
        text = title + body
        text_lower = text.lower()
        
        # 计算 AI 词汇出现频率
        ai_count = sum(1 for word in ai_indicators if word.lower() in text_lower)
        
        # 检查结构过于工整
        structure_bonus = 0
        if re.search(r'^[一二三四]、', body) or re.search(r'^首先[，,]', body):
            structure_bonus = 0.1
        
        # 检查是否过于正式
        formality_bonus = 0
        if len(body) > 100:
            sentences = re.split(r'[。！？]', body)
            avg_sentence_len = sum(len(s) for s in sentences) / max(len(sentences), 1)
            if avg_sentence_len > 30:  # 句子太长，AI 味重
                formality_bonus = 0.15
        
        # 计算分数（越低越像真人）
        ai_score = min(1.0, (ai_count * 0.1) + structure_bonus + formality_bonus)
        
        # 返回"像真人"分数（1 - AI味）
        return max(0.0, 1.0 - ai_score)
    
    async def _assess_title(self, title: str, topic: str, goal: str) -> float:
        """评估标题吸引力"""
        score = 0.0
        reasons = []
        
        # 1. 长度检查（8-15字最佳）
        char_count = len(title)
        if 8 <= char_count <= 15:
            score += 0.25
            reasons.append("长度合适")
        elif char_count < 8:
            score += 0.1
            reasons.append("略短")
        elif char_count <= 20:
            score += 0.15
            reasons.append("长度可接受")
        else:
            score += 0.0
            reasons.append("过长")
        
        # 2. 开头词检查（前3字是否吸引人）
        if len(title) >= 3:
            catchy_starts = ["别", "你", "我", "如何", "为什么", "揭秘", "必", "超", "真"]
            if any(title[:3].startswith(word) for word in catchy_starts):
                score += 0.2
                reasons.append("开头吸引人")
            elif title[0].isdigit():
                score += 0.15
                reasons.append("数字开头")
        
        # 3. 情感词检查
        emotional_words = ["绝了", " yyds", "太", "真的", "终于", "哭", "笑"]
        if any(word in title for word in emotional_words):
            score += 0.15
            reasons.append("有情感表达")
        
        # 4. Emoji 检查
        if any(ord(c) > 10000 for c in title):  # 包含 emoji
            score += 0.15
            reasons.append("有emoji")
        
        # 5. 问句检查
        if "？" in title or "?" in title or "吗" in title:
            score += 0.15
            reasons.append("疑问句")
        
        return min(1.0, score)
    
    async def _assess_body(self, body: str, topic: str) -> float:
        """评估正文质量"""
        score = 0.0
        reasons = []
        
        # 1. 长度检查（500-1000字最佳）
        char_count = len(body)
        if 500 <= char_count <= 1000:
            score += 0.25
            reasons.append("长度合适")
        elif 300 <= char_count < 500:
            score += 0.15
            reasons.append("略短")
        elif char_count > 1000:
            score += 0.1
            reasons.append("略长")
        else:
            score += 0.05
            reasons.append("过短")
        
        # 2. 段落检查
        paragraphs = [p for p in body.split('\n\n') if len(p) > 20]
        if 3 <= len(paragraphs) <= 6:
            score += 0.2
            reasons.append("段落清晰")
        elif len(paragraphs) > 0:
            score += 0.1
            reasons.append("有分段")
        
        # 3. 开头检查（前50字是否有 hook）
        first_50 = body[:50]
        hook_indicators = ["我", "姐妹", "真的", "终于", "别再", "为什么", "想问"]
        if any(word in first_50 for word in hook_indicators):
            score += 0.2
            reasons.append("开头有hook")
        elif first_50[0:2] == "关于" or first_50[0:2] == "今天":
            score += 0.1
            reasons.append("开头一般")
        
        # 4. 口语化检查
        casual_words = ["真的", "绝了", "yyds", "姐妹", "太", "爱了", "冲"]
        casual_count = sum(1 for word in casual_words if word in body)
        if casual_count >= 2:
            score += 0.2
            reasons.append("语言口语化")
        elif casual_count >= 1:
            score += 0.1
            reasons.append("略有口语")
        
        # 5. CTA 检查（结尾引导）
        cta_words = ["赞", "收藏", "关注", "评论", "分享", "求"]
        if any(word in body[-100:] for word in cta_words):
            score += 0.15
            reasons.append("有CTA")
        
        return min(1.0, score)
    
    def _check_compliance(self, title: str, body: str) -> Dict[str, Any]:
        """检查合规性"""
        
        # 违禁词列表（部分）
        banned_words = [
            "第一", "顶级", "最好", "绝对", "100%",
            "包治", "根治", "保证治愈", "一天见效",
            "刷单", "刷屏", "虚假"
        ]
        
        text = title + body
        issues = []
        
        for word in banned_words:
            if word in text:
                issues.append(f"可能包含违禁词：{word}")
        
        # 检查联系方式
        phone_pattern = r'1[3-9]\d{9}'
        if re.search(phone_pattern, text):
            issues.append("可能包含手机号")
        
        return {
            "passed": len(issues) == 0,
            "score": 1.0 if len(issues) == 0 else max(0.0, 1.0 - len(issues) * 0.3),
            "details": issues
        }
    
    async def _generate_feedback(
        self,
        title: str,
        body: str,
        topic: str,
        ai_score: float,
        title_score: float,
        body_score: float,
        compliance: Dict
    ) -> Tuple[List[str], List[str]]:
        """生成反馈"""
        
        issues = []
        suggestions = []
        
        if ai_score < 0.6:
            issues.append("AI 味太重")
            suggestions.append("加入更多口语化表达和个人感受")
        
        if title_score < 0.6:
            issues.append("标题吸引力不足")
            suggestions.append("尝试用数字、问句或对比结构")
        
        if body_score < 0.6:
            issues.append("正文质量有待提升")
            suggestions.append("增加开头 hook、优化段落结构")
        
        if not compliance["passed"]:
            issues.append("可能存在合规风险")
            suggestions.append("检查并移除违禁词和联系方式")
        
        if not issues:
            issues.append("内容质量良好")
            suggestions.append("建议保持当前风格")
        
        return issues, suggestions
    
    def _generate_pass_reasons(
        self,
        passed: bool,
        ai_score: float,
        title_score: float,
        body_score: float,
        compliance: Dict
    ) -> List[str]:
        """生成通过/不通过的理由"""
        
        if passed:
            return [
                f"AI 味检测通过（得分: {ai_score:.2f}）",
                f"标题吸引力达标（得分: {title_score:.2f}）",
                f"内容质量达标（得分: {body_score:.2f}）",
                f"合规性检查通过"
            ]
        else:
            reasons = ["未通过质量检查："]
            if ai_score < 0.6:
                reasons.append(f"- AI 味太重（{ai_score:.2f}）")
            if title_score < 0.6:
                reasons.append(f"- 标题吸引力不足（{title_score:.2f}）")
            if body_score < 0.6:
                reasons.append(f"- 正文质量有待提升（{body_score:.2f}）")
            if not compliance["passed"]:
                reasons.append("- 存在合规风险")
            return reasons


# 便捷函数
async def assess_content(
    title: str,
    body: str,
    topic: str,
    goal: str = "maximize_save"
) -> Dict[str, Any]:
    """快速评估内容质量"""
    assessor = ContentQualityAssessor()
    return await assessor.assess(title, body, topic, goal)
