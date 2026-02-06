"""
NoteTrial Backend - 受众模拟引擎
基于 viral-predictor 的思路，实现针对小红书的受众模拟
"""
import asyncio
import json
from typing import List, Dict, Any, Tuple
from openai import AsyncOpenAI
import numpy as np
from scipy import stats
from statsmodels.stats.proportion import proportions_ztest

from ..models import (
    TaskSpec, ContentItem, PersonaSimulationResult,
    EngagementScore, StatisticalConfidence, CrowdTestResult, OptimizationGoal,
    MultiCrowdTestResult, VersionScore
)
from ..config import get_settings


settings = get_settings()


class AudienceSimulator:
    """受众模拟器 - 核心引擎"""
    
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.client = AsyncOpenAI(
            api_key=api_key or settings.openai_api_key,
            base_url=base_url or settings.openai_base_url
        )
        self.model = model or settings.default_model
    
    def _generate_personas(
        self,
        task_spec: TaskSpec,
        count: int = 5,
        audience_tags: List[str] = None
    ) -> List[Dict[str, str]]:
        """根据任务规格生成多样化的用户画像"""
        if audience_tags:
            personas = []
            for i, tag in enumerate(audience_tags, 1):
                personas.append({
                    "id": f"tag{i}",
                    "type": tag,
                    "desc": f"{tag}相关人群的反馈视角"
                })
            return personas[:count]

        base_personas = [
            {"id": "p1", "type": "核心用户", "desc": f"对{task_spec.topic or task_spec.audience}有明确需求，愿意深读"},
            {"id": "p2", "type": "泛兴趣用户", "desc": f"对{task_spec.topic or '该话题'}有一般兴趣，互动意愿中等"},
            {"id": "p3", "type": "实用派", "desc": "重视可执行和性价比，倾向收藏干货、清单和避坑信息"},
            {"id": "p4", "type": "互动派", "desc": "表达意愿较强，愿意评论、提问和交流"},
            {"id": "p5", "type": "传播派", "desc": "遇到有价值或有话题内容时，愿意转发分享"},
        ]
        return base_personas[:count]
    
    def _build_simulation_prompt(
        self, 
        persona: Dict[str, str], 
        content: ContentItem, 
        task_spec: TaskSpec,
        calibration_hints: List[str] = None
    ) -> str:
        """构建单个用户模拟的提示词"""
        
        calibration_context = ""
        if calibration_hints:
            calibration_context = f"""
【小红书平台特征参考】
{chr(10).join(f'- {hint}' for hint in calibration_hints)}
"""
        
        prompt = f"""你正在模拟一个小红书用户浏览首页的场景。

【你的用户画像】
类型：{persona['type']}
特征：{persona['desc']}

【你看到的笔记内容】
标题：{content.title}
正文：{content.body}
标签：{', '.join(content.tags) if content.tags else '无'}
{calibration_context}
【任务】
作为这个用户画像，决定你对这篇笔记的互动行为。

请输出JSON格式的决策：
{{
    "like": true/false,      // 是否点赞（觉得内容有价值/有共鸣）
    "save": true/false,      // 是否收藏（内容实用/想之后再看）
    "comment": true/false,   // 是否评论（想发表看法/提问）
    "share": true/false,     // 是否分享（想推荐给朋友）
    "reasoning": "简短说明你的决策理由（1-2句话）"
}}

注意：
1. 基于用户画像的真实行为模式做决策
2. 大多数用户对大多数内容不会有太多互动，请保持真实
3. 收藏行为在小红书上相对常见（如果内容实用）
4. 评论和分享的门槛较高
"""
        return prompt
    
    async def _simulate_single_user(
        self,
        persona: Dict[str, str],
        content: ContentItem,
        task_spec: TaskSpec,
        calibration_hints: List[str] = None
    ) -> PersonaSimulationResult:
        """模拟单个用户对内容的反应"""
        prompt = self._build_simulation_prompt(persona, content, task_spec, calibration_hints)
        
        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.8  # 增加随机性以模拟不同用户
            )
            result = json.loads(completion.choices[0].message.content)
            
            return PersonaSimulationResult(
                persona_id=persona['id'],
                persona_description=f"{persona['type']}: {persona['desc']}",
                version_preference="",  # 单独模拟时不设置
                like=result.get("like", False),
                save=result.get("save", False),
                comment=result.get("comment", False),
                share=result.get("share", False),
                reasoning=result.get("reasoning", "")
            )
        except Exception as e:
            # 出错时返回默认结果
            return PersonaSimulationResult(
                persona_id=persona['id'],
                persona_description=f"{persona['type']}: {persona['desc']}",
                version_preference="",
                like=False,
                save=False,
                comment=False,
                share=False,
                reasoning=f"模拟出错: {str(e)}"
            )
    
    async def simulate_ab_test(
        self,
        task_spec: TaskSpec,
        content_a: ContentItem,
        content_b: ContentItem,
        max_users: int = 20,
        audience_tags: List[str] = None,
        calibration_hints: List[str] = None,
        on_progress: callable = None
    ) -> CrowdTestResult:
        """
        执行 A/B 测试模拟
        
        Args:
            task_spec: 任务规格
            content_a: 版本A内容
            content_b: 版本B内容
            max_users: 模拟用户数量
            calibration_hints: 平台校准提示
            on_progress: 进度回调函数
        """
        tag_list = [t.strip() for t in (audience_tags or []) if t and t.strip()]
        if tag_list:
            personas = self._generate_personas(task_spec, len(tag_list), tag_list)
            runs_per_persona = 3
        else:
            personas = self._generate_personas(task_spec, min(max_users, 5))
            runs_per_persona = max(1, max_users // len(personas))

        all_results_a: List[PersonaSimulationResult] = []
        all_results_b: List[PersonaSimulationResult] = []
        
        # 批量并行模拟
        batch_size = settings.batch_size
        total_runs = len(personas) * runs_per_persona
        completed = 0
        
        for persona in personas:
            for run in range(runs_per_persona):
                # 并行模拟A和B
                result_a, result_b = await asyncio.gather(
                    self._simulate_single_user(persona, content_a, task_spec, calibration_hints),
                    self._simulate_single_user(persona, content_b, task_spec, calibration_hints)
                )
                all_results_a.append(result_a)
                all_results_b.append(result_b)
                
                completed += 1
                if on_progress:
                    await on_progress(completed, total_runs)
        
        # 计算分数
        score_a = self._calculate_score(all_results_a)
        score_b = self._calculate_score(all_results_b)
        
        # 计算统计置信度
        total_users = len(all_results_a)
        like_conf = self._calc_confidence(total_users, score_a.like_count, score_b.like_count)
        save_conf = self._calc_confidence(total_users, score_a.save_count, score_b.save_count)
        comment_conf = self._calc_confidence(total_users, score_a.comment_count, score_b.comment_count)
        share_conf = self._calc_confidence(total_users, score_a.share_count, score_b.share_count)
        overall_conf = self._calc_confidence(total_users, score_a.total, score_b.total)
        
        # 生成诊断和建议
        diagnosis = await self._generate_diagnosis(task_spec, content_a, content_b, score_a, score_b, all_results_a, all_results_b)
        suggestions = await self._generate_suggestions(task_spec, content_a, content_b, score_a, score_b, calibration_hints)
        
        # 合并persona结果
        combined_results = []
        for ra, rb in zip(all_results_a, all_results_b):
            ra.version_preference = "A" if (ra.like + ra.save + ra.comment + ra.share) >= (rb.like + rb.save + rb.comment + rb.share) else "B"
            combined_results.append(ra)
        
        return CrowdTestResult(
            version_a_score=score_a,
            version_b_score=score_b,
            like_confidence=like_conf,
            save_confidence=save_conf,
            comment_confidence=comment_conf,
            share_confidence=share_conf,
            overall_confidence=overall_conf,
            diagnosis=diagnosis,
            suggestions=suggestions,
            persona_results=combined_results
        )

    async def simulate_multi_test(
        self,
        task_spec: TaskSpec,
        versions: List[Tuple[str, ContentItem]],
        max_users: int = 20,
        audience_tags: List[str] = None,
        calibration_hints: List[str] = None,
        on_progress: callable = None
    ) -> MultiCrowdTestResult:
        """Multi-version simulation for direct comparison."""
        if not versions or len(versions) < 2:
            return MultiCrowdTestResult(
                version_scores=[],
                like_confidence=StatisticalConfidence(winner="-", confidence=0.0),
                save_confidence=StatisticalConfidence(winner="-", confidence=0.0),
                comment_confidence=StatisticalConfidence(winner="-", confidence=0.0),
                share_confidence=StatisticalConfidence(winner="-", confidence=0.0),
                overall_confidence=StatisticalConfidence(winner="-", confidence=0.0),
                diagnosis=[],
                suggestions=[],
                persona_results=[],
            )

        tag_list = [t.strip() for t in (audience_tags or []) if t and t.strip()]
        if tag_list:
            personas = self._generate_personas(task_spec, len(tag_list), tag_list)
            runs_per_persona = 3
        else:
            personas = self._generate_personas(task_spec, min(max_users, 5))
            runs_per_persona = max(1, max_users // len(personas))

        version_map = {label: content for label, content in versions}
        version_labels = [label for label, _ in versions]
        results_by_label: Dict[str, List[PersonaSimulationResult]] = {label: [] for label in version_labels}
        combined_results: List[PersonaSimulationResult] = []

        total_runs = len(personas) * runs_per_persona
        completed = 0

        for persona in personas:
            for _ in range(runs_per_persona):
                results = await asyncio.gather(
                    *[
                        self._simulate_single_user(persona, version_map[label], task_spec, calibration_hints)
                        for label in version_labels
                    ]
                )
                for label, result in zip(version_labels, results):
                    results_by_label[label].append(result)

                best_index = max(
                    range(len(results)),
                    key=lambda i: (results[i].like + results[i].save + results[i].comment + results[i].share)
                )
                best_label = version_labels[best_index]
                best_result = results[best_index]
                best_result.version_preference = best_label
                combined_results.append(best_result)

                completed += 1
                if on_progress:
                    await on_progress(completed, total_runs)

        version_scores = [
            VersionScore(label=label, score=self._calculate_score(results_by_label[label]))
            for label in version_labels
        ]
        version_scores_sorted = sorted(version_scores, key=lambda v: v.score.total, reverse=True)

        users = len(next(iter(results_by_label.values()))) if results_by_label else 0
        like_conf = self._calc_multi_confidence(users, {v.label: v.score.like_count for v in version_scores})
        save_conf = self._calc_multi_confidence(users, {v.label: v.score.save_count for v in version_scores})
        comment_conf = self._calc_multi_confidence(users, {v.label: v.score.comment_count for v in version_scores})
        share_conf = self._calc_multi_confidence(users, {v.label: v.score.share_count for v in version_scores})
        overall_conf = self._calc_multi_confidence(users, {v.label: v.score.total for v in version_scores})

        diagnosis: List[str] = []
        suggestions: List[str] = []
        if len(version_scores_sorted) >= 2:
            top = version_scores_sorted[0]
            second = version_scores_sorted[1]
            top_content = version_map[top.label]
            second_content = version_map[second.label]
            diagnosis = await self._generate_diagnosis(
                task_spec,
                top_content,
                second_content,
                top.score,
                second.score,
                results_by_label[top.label],
                results_by_label[second.label],
            )
            suggestions = await self._generate_suggestions(
                task_spec,
                top_content,
                second_content,
                top.score,
                second.score,
                calibration_hints,
            )

        return MultiCrowdTestResult(
            version_scores=version_scores_sorted,
            like_confidence=like_conf,
            save_confidence=save_conf,
            comment_confidence=comment_conf,
            share_confidence=share_conf,
            overall_confidence=overall_conf,
            diagnosis=diagnosis,
            suggestions=suggestions,
            persona_results=combined_results,
        )
    
    def _calculate_score(self, results: List[PersonaSimulationResult]) -> EngagementScore:
        """计算互动分数"""
        like_count = sum(1 for r in results if r.like)
        save_count = sum(1 for r in results if r.save)
        comment_count = sum(1 for r in results if r.comment)
        share_count = sum(1 for r in results if r.share)
        
        return EngagementScore(
            like_count=like_count,
            save_count=save_count,
            comment_count=comment_count,
            share_count=share_count,
            total=like_count + save_count + comment_count + share_count
        )
    
    def _calc_confidence(self, users: int, vote_a: int, vote_b: int) -> StatisticalConfidence:
        """计算统计置信度 (基于 viral-predictor 的逻辑)"""
        if vote_a == 0 and vote_b == 0:
            return StatisticalConfidence(winner="-", confidence=0.0)
        
        # 平票时不偏向任一版本
        if vote_a == vote_b:
            return StatisticalConfidence(winner="-", confidence=50.0)
        
        if vote_a == 0:
            return StatisticalConfidence(winner="B", confidence=100.0)
        if vote_b == 0:
            return StatisticalConfidence(winner="A", confidence=100.0)
        
        try:
            if vote_a >= vote_b:
                z_stat, p_value = proportions_ztest(
                    count=[vote_a, vote_b],
                    nobs=[users, users],
                    alternative='larger'
                )
                confidence = (1 - p_value) * 100
                return StatisticalConfidence(
                    winner="A",
                    confidence=confidence if not np.isnan(confidence) else 50.0
                )
            else:
                z_stat, p_value = proportions_ztest(
                    count=[vote_b, vote_a],
                    nobs=[users, users],
                    alternative='larger'
                )
                confidence = (1 - p_value) * 100
                return StatisticalConfidence(
                    winner="B",
                    confidence=confidence if not np.isnan(confidence) else 50.0
                )
        except Exception:
            total_votes = vote_a + vote_b
            if vote_a > vote_b:
                return StatisticalConfidence(winner="A", confidence=(vote_a / total_votes) * 100)
            else:
                return StatisticalConfidence(winner="B", confidence=(vote_b / total_votes) * 100)
    
    def _calc_multi_confidence(self, users: int, counts: Dict[str, int]) -> StatisticalConfidence:
        """Compute confidence for multi-version by comparing top-2."""
        if not counts:
            return StatisticalConfidence(winner="-", confidence=0.0)

        sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        top_label, top_count = sorted_items[0]
        if len(sorted_items) == 1:
            return StatisticalConfidence(winner=top_label, confidence=100.0)

        second_label, second_count = sorted_items[1]
        if top_count == second_count:
            return StatisticalConfidence(winner="-", confidence=50.0)

        base = self._calc_confidence(users, top_count, second_count)
        winner = top_label if base.winner == "A" else second_label
        return StatisticalConfidence(winner=winner, confidence=base.confidence)

    async def _generate_diagnosis(
        self,
        task_spec: TaskSpec,
        content_a: ContentItem,
        content_b: ContentItem,
        score_a: EngagementScore,
        score_b: EngagementScore,
        results_a: List[PersonaSimulationResult],
        results_b: List[PersonaSimulationResult]
    ) -> List[str]:
        """生成诊断解释"""
        winner = "A" if score_a.total > score_b.total else "B"
        winner_content = content_a if winner == "A" else content_b
        loser_content = content_b if winner == "A" else content_a
        winner_score = score_a if winner == "A" else score_b
        loser_score = score_b if winner == "A" else score_a
        
        # 收集用户反馈理由
        winner_results = results_a if winner == "A" else results_b
        positive_reasons = [r.reasoning for r in winner_results if r.save or r.like][:3]
        
        # 处理多目标
        goals_str = ', '.join([g.value for g in task_spec.goals]) if task_spec.goals else 'maximize_save'
        
        prompt = f"""分析以下小红书A/B测试结果，生成3-5条诊断解释。

【任务目标】
受众：{task_spec.audience}
优化目标：{goals_str}

【胜出版本{winner}】
标题：{winner_content.title}
正文前100字：{winner_content.body[:100]}...
分数：点赞{winner_score.like_count} 收藏{winner_score.save_count} 评论{winner_score.comment_count}

【落后版本】
标题：{loser_content.title}
正文前100字：{loser_content.body[:100]}...
分数：点赞{loser_score.like_count} 收藏{loser_score.save_count} 评论{loser_score.comment_count}

【用户反馈摘要】
{chr(10).join(f'- {r}' for r in positive_reasons)}

请输出JSON格式：
{{
    "diagnosis": [
        "诊断1：...",
        "诊断2：...",
        "诊断3：..."
    ]
}}

要求：
1. 解释为什么版本{winner}更受欢迎
2. 具体指出内容层面的差异
3. 与小红书平台特性结合
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
    
    async def _generate_suggestions(
        self,
        task_spec: TaskSpec,
        content_a: ContentItem,
        content_b: ContentItem,
        score_a: EngagementScore,
        score_b: EngagementScore,
        calibration_hints: List[str] = None
    ) -> List[str]:
        """生成改写建议"""
        loser = "A" if score_a.total < score_b.total else "B"
        loser_content = content_a if loser == "A" else content_b
        
        calibration_context = ""
        if calibration_hints:
            calibration_context = f"""
【小红书平台校准提示】
{chr(10).join(f'- {hint}' for hint in calibration_hints)}
"""
        
        # 处理多目标
        goals_str = ', '.join([g.value for g in task_spec.goals]) if task_spec.goals else 'maximize_save'
        
        prompt = f"""为以下小红书内容提供具体的改写建议。

【内容】
标题：{loser_content.title}
正文：{loser_content.body}

【目标受众】{task_spec.audience}
【优化目标】{goals_str}
{calibration_context}
请输出JSON格式：
{{
    "title_suggestions": ["标题候选1", "标题候选2", "标题候选3"],
    "hook_suggestions": ["开头hook建议1", "开头hook建议2"],
    "structure_suggestions": ["结构建议1", "结构建议2"]
}}

要求：
1. 标题不超过20字
2. 开头要有明确的hook
3. 建议要具体可执行
"""
        
        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            result = json.loads(completion.choices[0].message.content)
            
            suggestions = []
            if result.get("title_suggestions"):
                suggestions.append(f"📝 标题建议：{' | '.join(result['title_suggestions'])}")
            if result.get("hook_suggestions"):
                suggestions.append(f"🎣 开头Hook：{' | '.join(result['hook_suggestions'])}")
            if result.get("structure_suggestions"):
                for s in result['structure_suggestions']:
                    suggestions.append(f"📋 {s}")
            
            return suggestions
        except Exception as e:
            return [f"建议生成出错: {str(e)}"]
