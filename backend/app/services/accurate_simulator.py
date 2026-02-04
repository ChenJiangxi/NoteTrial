"""
NoteTrial Backend - 增强版受众模拟器
提升测试准确性，支持真实数据校准
"""
import asyncio
import json
from typing import List, Dict, Any, Optional, Tuple
from openai import AsyncOpenAI
import numpy as np
from scipy import stats
from statsmodels.stats.proportion import proportions_ztest

from ..models import (
    TaskSpec, ContentItem, PersonaSimulationResult,
    EngagementScore, StatisticalConfidence, CrowdTestResult, OptimizationGoal
)
from ..config import get_settings


settings = get_settings()


# ============ 细分 Persona 库 ============

DETAILED_PERSONAS = {
    # 价格敏感型
    "price_sensitive": {
        "name": "价格敏感型",
        "desc": "关注性价比、促销信息、穷鬼攻略",
        "behaviors": [
            "关注价格、优惠、折扣",
            "喜欢'均价XX'、'平替'类内容",
            "收藏清单、攻略类内容",
            "购买前会做功课"
        ],
        "trigger_words": ["便宜", "平价", "省钱", "性价比", "均价", "穷鬼"],
        "interaction_pattern": "save_first"
    },
    
    # 品质追求型
    "quality_seeker": {
        "name": "品质追求型",
        "desc": "关注成分、功效、口碑、测评",
        "behaviors": [
            "研究成分、配方、功效",
            "关注博主专业度",
            "信任真实测评和对比",
            "愿意为品质付溢价"
        ],
        "trigger_words": ["成分", "功效", "测评", "对比", "真实", "推荐"],
        "interaction_pattern": "like_save"
    },
    
    # 跟风型
    "trendy": {
        "name": "跟风型",
        "desc": "关注热门、趋势、博主推荐",
        "behaviors": [
            "跟随热门话题和趋势",
            "信任喜欢的博主",
            "容易被种草",
            "看到别人有自己也想要"
        ],
        "trigger_words": ["热门", "爆款", "跟风", "火", "都在用"],
        "interaction_pattern": "quick_engage"
    },
    
    # 研究型
    "researcher": {
        "name": "研究型",
        "desc": "关注详细测评、数据、对比",
        "behaviors": [
            "看详细的测评和对比",
            "关注数据、图表、实验",
            "会翻评论区看反馈",
            "做功课直到搞清楚"
        ],
        "trigger_words": ["测评", "数据", "对比", "实验", "真实反馈"],
        "interaction_pattern": "comment_heavy"
    },
    
    # 冲动型
    "impulsive": {
        "name": "冲动型",
        "desc": "被视觉效果、限时吸引",
        "behaviors": [
            "被好看的图片/视频吸引",
            "容易被限时、限量打动",
            "看到就想买",
            "决策快，但容易后悔"
        ],
        "trigger_words": ["绝美", "太好看了", "限时", "限量", "衝"],
        "interaction_pattern": "immediate_action"
    },
    
    # 社交分享型
    "social_sharer": {
        "name": "社交分享型",
        "desc": "关注有趣、有话题、可分享的内容",
        "behaviors": [
            "喜欢有趣、有梗的内容",
            "想分享给朋友或朋友圈",
            "关注话题性和讨论度",
            "乐于在评论区互动"
        ],
        "trigger_words": ["笑死", "绝了", "朋友圈", "分享", "话题"],
        "interaction_pattern": "share_comment"
    },
    
    # 实用主义型
    "pragmatic": {
        "name": "实用主义型",
        "desc": "关注干货、教程、避坑",
        "behaviors": [
            "收藏干货、教程、攻略",
            "关注可操作性",
            "喜欢清单、步骤类内容",
            "会收藏之后再看"
        ],
        "trigger_words": ["教程", "步骤", "干货", "避坑", "攻略"],
        "interaction_pattern": "save_focused"
    },
    
    # 情感共鸣型
    "emotional": {
        "name": "情感共鸣型",
        "desc": "被故事、经历、情感打动",
        "behaviors": [
            "被真实故事打动",
            "有共鸣时会点赞",
            "会在评论区分享自己经历",
            "关注博主这个人"
        ],
        "trigger_words": ["真实", "经历", "故事", "感受", "共鸣"],
        "interaction_pattern": "like_comment"
    }
}


class EnhancedAudienceSimulator:
    """增强版受众模拟器"""
    
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.client = AsyncOpenAI(
            api_key=api_key or settings.openai_api_key,
            base_url=base_url or settings.openai_base_url
        )
        self.model = model or settings.default_model
    
    def select_relevant_personas(
        self,
        task_spec: TaskSpec,
        max_personas: int = 6
    ) -> List[Dict[str, Any]]:
        """根据任务规格选择最相关的 Persona"""
        
        topic = (task_spec.topic or "").lower()
        audience = (task_spec.audience or "").lower()
        goals = [g.value for g in task_spec.goals]
        
        # 计算每个 Persona 的相关性分数
        persona_scores = []
        
        for pid, persona in DETAILED_PERSONAS.items():
            score = 0
            
            # 匹配关键词
            all_keywords = (
                persona["desc"] + " " + 
                " ".join(persona["trigger_words"])
            ).lower()
            
            if any(kw in topic or kw in audience for kw in persona["trigger_words"]):
                score += 3
            
            # 根据目标调整权重
            if "save" in goals and persona["interaction_pattern"] in ["save_first", "save_focused"]:
                score += 1
            if "like" in goals and persona["interaction_pattern"] in ["like_save", "like_comment"]:
                score += 1
            if "comment" in goals and persona["interaction_pattern"] in ["comment_heavy", "like_comment"]:
                score += 1
            if "share" in goals and persona["interaction_pattern"] in ["share_comment"]:
                score += 1
            
            persona_scores.append((pid, score, persona))
        
        # 按分数排序，选择最高的
        persona_scores.sort(key=lambda x: x[1], reverse=True)
        selected = []
        
        for pid, score, persona in persona_scores[:max_personas]:
            selected.append({
                "id": pid,
                **persona,
                "relevance_score": score
            })
        
        return selected
    
    def _build_simulation_prompt(
        self,
        persona: Dict[str, Any],
        content: ContentItem,
        task_spec: TaskSpec,
        calibration_data: Dict[str, Any] = None
    ) -> str:
        """构建模拟 Prompt"""
        
        # 构建校准上下文
        calibration_context = ""
        if calibration_data:
            avg_engagement = calibration_data.get("avg_engagement_rate", 0.05)
            calibration_context = f"""
【小红书平台背景】
- 该话题平均互动率约 {avg_engagement:.1%}
- 用户对该类型内容的平均反应比较{calibration_data.get("user_mood", "中立")}
- 热门内容通常具备：{calibration_data.get("success_factors", [])[:3]}
"""
        
        prompt = f"""你正在以小红书用户的身份浏览首页。

【你的用户画像】
类型：{persona['name']}
特征：{persona['desc']}
典型行为：{'；'.join(persona['behaviors'][:2])}

【你看到的笔记】
标题：{content.title}
正文：{content.body[:300]}...
标签：{', '.join(content.tags) if content.tags else '无'}
{calibration_context}

【模拟任务】
作为这个类型的用户，决定你的互动行为。

规则：
- 你的行为要符合这个用户画像的典型特征
- 大多数用户对大多数内容不会互动（符合真实情况）
- 收藏是相对常见的行为（如果内容有用）
- 评论和分享门槛较高

请用JSON输出你的决策：
{{
    "will_view": true/false,  // 是否会点进来看详情
    "will_like": true/false,  // 是否会点赞
    "will_save": true/false,  // 是否会收藏
    "will_comment": true/false,  // 是否会评论
    "will_share": true/false,  // 是否会分享
    "confidence": 0.0-1.0,  // 你做出这个决策的把握程度
    "reasoning": "1-2句话说明理由"
}}

【互动概率基准】
- 点击率约 10-30%（取决于标题吸引力）
- 点赞率约 1-5%（取决于内容质量）
- 收藏率约 0.5-3%（取决于实用性）
- 评论率约 0.1-1%（需要特别吸引）
- 分享率约 0.05-0.5%（需要有话题性）
"""
        return prompt
    
    async def _simulate_user(
        self,
        persona: Dict[str, Any],
        content: ContentItem,
        task_spec: TaskSpec,
        calibration_data: Dict[str, Any] = None
    ) -> PersonaSimulationResult:
        """模拟单个用户"""
        prompt = self._build_simulation_prompt(persona, content, task_spec, calibration_data)
        
        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            result = json.loads(completion.choices[0].message.content)
            
            return PersonaSimulationResult(
                persona_id=persona['id'],
                persona_description=f"{persona['name']}: {persona['desc']}",
                version_preference="",
                like=result.get("will_like", False),
                save=result.get("will_save", False),
                comment=result.get("will_comment", False),
                share=result.get("will_share", False),
                reasoning=result.get("reasoning", "")
            )
        except Exception as e:
            return PersonaSimulationResult(
                persona_id=persona['id'],
                persona_description=f"{persona['name']}: {persona['desc']}",
                version_preference="",
                like=False,
                save=False,
                comment=False,
                share=False,
                reasoning=f"模拟出错: {str(e)}"
            )
    
    async def run_enhanced_test(
        self,
        task_spec: TaskSpec,
        content_a: ContentItem,
        content_b: ContentItem,
        max_users: int = 20,
        calibration_data: Dict[str, Any] = None,
        on_progress: callable = None
    ) -> CrowdTestResult:
        """运行增强版 A/B 测试"""
        
        # 1. 选择相关 Persona
        personas = self.select_relevant_personas(task_spec, max_personas=min(max_users, 6))
        
        # 2. 为每个 Persona 运行多次模拟
        runs_per_persona = max(1, max_users // len(personas))
        
        all_results_a = []
        all_results_b = []
        
        completed = 0
        total_runs = len(personas) * runs_per_persona
        
        for persona in personas:
            for _ in range(runs_per_persona):
                # 并行模拟 A 和 B
                result_a, result_b = await asyncio.gather(
                    self._simulate_user(persona, content_a, task_spec, calibration_data),
                    self._simulate_user(persona, content_b, task_spec, calibration_data)
                )
                
                all_results_a.append(result_a)
                all_results_b.append(result_b)
                
                completed += 1
                if on_progress:
                    await on_progress(completed, total_runs)
        
        # 3. 计算分数
        score_a = self._calculate_engagement_score(all_results_a)
        score_b = self._calculate_engagement_score(all_results_b)
        
        # 4. 计算置信度
        total_users = len(all_results_a)
        confidence = self._calculate_confidence(
            total_users,
            score_a.like_count, score_b.like_count,
            score_a.save_count, score_b.save_count
        )
        
        # 5. 生成诊断和建议
        diagnosis = await self._generate_enhanced_diagnosis(
            task_spec, content_a, content_b, score_a, score_b, 
            all_results_a, all_results_b, personas
        )
        suggestions = await self._generate_enhanced_suggestions(
            task_spec, content_a, content_b, score_a, score_b, calibration_data
        )
        
        # 6. 合并结果
        combined_results = []
        for ra, rb in zip(all_results_a, all_results_b):
            score_a_total = ra.like + ra.save + ra.comment + ra.share
            score_b_total = rb.like + rb.save + rb.comment + rb.share
            ra.version_preference = "A" if score_a_total >= score_b_total else "B"
            combined_results.append(ra)
        
        return CrowdTestResult(
            version_a_score=score_a,
            version_b_score=score_b,
            like_confidence=confidence["like"],
            save_confidence=confidence["save"],
            comment_confidence=confidence["comment"],
            share_confidence=confidence["share"],
            overall_confidence=confidence["overall"],
            diagnosis=diagnosis,
            suggestions=suggestions,
            persona_results=combined_results
        )
    
    def _calculate_engagement_score(self, results: List[PersonaSimulationResult]) -> EngagementScore:
        """计算互动分数"""
        return EngagementScore(
            like_count=sum(1 for r in results if r.like),
            save_count=sum(1 for r in results if r.save),
            comment_count=sum(1 for r in results if r.comment),
            share_count=sum(1 for r in results if r.share),
            total=sum(1 for r in results if r.like or r.save or r.comment or r.share)
        )
    
    def _calculate_confidence(
        self,
        users: int,
        like_a: int, like_b: int,
        save_a: int, save_b: int
    ) -> Dict[str, StatisticalConfidence]:
        """计算各维度的统计置信度"""
        
        def calc(winner: str, count_a: int, count_b: int) -> StatisticalConfidence:
            if count_a == count_b:
                return StatisticalConfidence(winner="-", confidence=50.0)
            if count_a == 0:
                return StatisticalConfidence(winner="B", confidence=100.0 if count_b > 0 else 50.0)
            if count_b == 0:
                return StatisticalConfidence(winner="A", confidence=100.0 if count_a > 0 else 50.0)
            
            total = count_a + count_b
            try:
                if count_a >= count_b:
                    z_stat, p_value = proportions_ztest(
                        count=[count_a, count_b],
                        nobs=[users, users],
                        alternative='larger'
                    )
                    conf = (1 - p_value) * 100
                else:
                    z_stat, p_value = proportions_ztest(
                        count=[count_b, count_a],
                        nobs=[users, users],
                        alternative='larger'
                    )
                    conf = (1 - p_value) * 100
                winner = "A" if count_a >= count_b else "B"
                return StatisticalConfidence(
                    winner=winner,
                    confidence=conf if not np.isnan(conf) else 50.0
                )
            except Exception:
                winner = "A" if count_a >= count_b else "B"
                conf = max(count_a, count_b) / total * 100
                return StatisticalConfidence(winner=winner, confidence=conf)
        
        like_conf = calc("A", like_a, like_b)
        save_conf = calc("A", save_a, save_b)
        comment_conf = calc("A", sum(r.comment for r in []), sum(r.comment for r in []))
        share_conf = calc("A", sum(r.share for r in []), sum(r.share for r in []))
        overall_conf = StatisticalConfidence(
            winner=like_conf.winner if like_conf.confidence > 50 else save_conf.winner,
            confidence=(like_conf.confidence + save_conf.confidence) / 2
        )
        
        return {
            "like": like_conf,
            "save": save_conf,
            "comment": comment_conf,
            "share": share_conf,
            "overall": overall_conf
        }
    
    async def _generate_enhanced_diagnosis(
        self,
        task_spec: TaskSpec,
        content_a: ContentItem,
        content_b: ContentItem,
        score_a: EngagementScore,
        score_b: EngagementScore,
        results_a: List[PersonaSimulationResult],
        results_b: List[PersonaSimulationResult],
        personas: List[Dict]
    ) -> List[str]:
        """生成增强版诊断"""
        winner = "A" if score_a.total >= score_b.total else "B"
        winner_content = content_a if winner == "A" else content_b
        loser_content = content_b if winner == "A" else content_a
        
        # 分析不同 Persona 的偏好
        persona_prefs = {}
        for i, (ra, rb) in enumerate(zip(results_a, results_b)):
            pid = ra.persona_id
            pref = "A" if (ra.like + ra.save) >= (rb.like + rb.save) else "B"
            if pid not in persona_prefs:
                persona_prefs[pid] = {"A": 0, "B": 0}
            persona_prefs[pid][pref] += 1
        
        # 找出哪个 Persona 更喜欢胜出版本
        winning_personas = []
        for pid, prefs in persona_prefs.items():
            if prefs[winner] > prefs["A" if winner == "B" else "B"]:
                p = next((p for p in personas if p["id"] == pid), None)
                if p:
                    winning_personas.append(p["name"])
        
        goals = [g.value for g in task_spec.goals] if task_spec.goals else ["save"]
        primary_goal = goals[0] if goals else "save"
        
        prompt = f"""分析以下小红书A/B测试结果，生成诊断。

【测试目标】
- 受众：{task_spec.audience}
- 优化目标：{primary_goal}

【胜出版本 {winner}】
标题：{winner_content.title}
正文：{winner_content.body[:200]}...
得分：点赞{score_a.like_count if winner=='A' else score_b.like_count} 收藏{score_a.save_count if winner=='A' else score_b.save_count}

【胜出的用户群体】
{', '.join(winning_personas) if winning_personas else '各类型用户'}

请用JSON输出3条诊断：
{{
    "diagnosis": [
        "诊断1：...",
        "诊断2：...", 
        "诊断3：..."
    ]
}}
"""
        
        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            result = json.loads(completion.choices[0].message.content)
            return result.get("diagnosis", [])
        except Exception as e:
            return [f"诊断生成出错: {str(e)}"]
    
    async def _generate_enhanced_suggestions(
        self,
        task_spec: TaskSpec,
        content_a: ContentItem,
        content_b: ContentItem,
        score_a: EngagementScore,
        score_b: EngagementScore,
        calibration_data: Dict[str, Any] = None
    ) -> List[str]:
        """生成增强版建议"""
        loser = "A" if score_a.total < score_b.total else "B"
        loser_content = content_a if loser == "A" else content_b
        
        calibration_context = ""
        if calibration_data:
            calibration_context = f"""
平台特征参考：
- 平均互动率：{calibration_data.get('avg_engagement_rate', '5%')}
- 热门内容特点：{', '.join(calibration_data.get('success_factors', [])[:3])}
"""
        
        goals = [g.value for g in task_spec.goals] if task_spec.goals else ["save"]
        primary_goal = goals[0] if goals else "save"
        
        prompt = f"""为以下小红书内容提供改写建议。

【当前内容】
标题：{loser_content.title}
正文：{loser_content.body[:300]}...

【优化目标】
- 目标：{primary_goal}
- 受众：{task_spec.audience}
{calibration_context}

请用JSON输出具体建议：
{{
    "title_options": ["候选标题1", "候选标题2", "候选标题3"],
    "hook_options": ["开头建议1", "开头建议2"],
    "structure_tips": ["结构建议1", "结构建议2"]
}}
"""
        
        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            result = json.loads(completion.choices[0].message.content)
            
            suggestions = []
            if result.get("title_options"):
                suggestions.append(f"📝 标题候选：{' | '.join(result['title_options'][:3])}")
            if result.get("hook_options"):
                suggestions.append(f"🎣 开头Hook：{' | '.join(result['hook_options'][:2])}")
            if result.get("structure_tips"):
                for tip in result['structure_tips'][:2]:
                    suggestions.append(f"📋 {tip}")
            
            return suggestions if suggestions else ["内容质量良好，保持当前版本"]
        except Exception as e:
            return [f"建议生成出错: {str(e)}"]


# 便捷函数
async def run_accurate_ab_test(
    task_spec: TaskSpec,
    content_a: ContentItem,
    content_b: ContentItem,
    max_users: int = 20,
    topic: str = None
) -> CrowdTestResult:
    """运行准确的 A/B 测试"""
    simulator = EnhancedAudienceSimulator()
    
    # 获取校准数据（如果有 MCP）
    calibration_data = None
    # 这里可以接入 MCP 获取真实数据
    
    return await simulator.run_enhanced_test(
        task_spec=task_spec,
        content_a=content_a,
        content_b=content_b,
        max_users=max_users,
        calibration_data=calibration_data
    )
