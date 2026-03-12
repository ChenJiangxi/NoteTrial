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
    MultiCrowdTestResult, VersionScore, MCPEvidenceSignal
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
    

    def _build_evidence_context(self, external_evidence: Dict[str, Any] = None) -> str:
        """Turn MCP evidence into platform background for persona decisions."""
        if not external_evidence:
            return ""

        evidence_reasons = external_evidence.get("reasons", [])[:3]
        evidence_keywords = external_evidence.get("matched_keywords", [])[:5]
        evidence_tags = external_evidence.get("matched_tags", [])[:5]
        sample_count = int(external_evidence.get("sample_count", 0) or 0)
        avg_likes = round(float(external_evidence.get("avg_likes", 0.0) or 0.0))
        avg_collects = round(float(external_evidence.get("avg_collects", 0.0) or 0.0))
        avg_comments = round(float(external_evidence.get("avg_comments", 0.0) or 0.0))
        avg_shares = round(float(external_evidence.get("avg_shares", 0.0) or 0.0))
        fit_score = float(external_evidence.get("content_fit_score", 0.0) or 0.0)
        engagement_score = float(external_evidence.get("engagement_reference_score", 0.0) or 0.0)
        goal_score = float(external_evidence.get("goal_alignment_score", 0.0) or 0.0)

        lines = [
            "【来自小红书 MCP 的外部参考资料】",
            f"- 已对比 {sample_count} 条真实小红书样本",
            f"- 样本平均互动：赞 {avg_likes} / 藏 {avg_collects} / 评 {avg_comments} / 转 {avg_shares}",
            f"- 内容贴合度参考：{fit_score:.1f}/100",
            f"- 高互动表现参考：{engagement_score:.1f}/100",
            f"- 当前目标对齐度：{goal_score:.1f}/100",
            f"- 命中的关键词：{', '.join(evidence_keywords) if evidence_keywords else '无明显命中'}",
            f"- 命中的标签：{', '.join(evidence_tags) if evidence_tags else '无明显命中'}",
        ]
        lines.extend(f"- {item}" for item in evidence_reasons)
        lines.append("- 请把这些信息当作你浏览内容时额外知道的平台背景资料，再决定是否互动。")
        return "\n".join(lines)

    def _build_simulation_prompt(
        self, 
        persona: Dict[str, str], 
        content: ContentItem, 
        task_spec: TaskSpec,
        calibration_hints: List[str] = None,
        external_evidence: Dict[str, Any] = None,
    ) -> str:
        """构建单个用户模拟的提示词"""
        
        calibration_context = ""
        if calibration_hints:
            calibration_context = f"""
【小红书平台特征参考】
{chr(10).join(f'- {hint}' for hint in calibration_hints)}
"""

        evidence_context = ""
        if external_evidence:
            evidence_context = f"""
{self._build_evidence_context(external_evidence)}
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
{evidence_context}
【任务】
作为这个用户画像，决定你对这篇笔记的互动行为。

请输出 JSON 格式的决策：
{{
    "like": true/false,
    "save": true/false,
    "comment": true/false,
    "share": true/false,
    "reasoning": "简短说明你的决策理由（1-2句话）"
}}

注意：
1. 基于用户画像的真实行为模式做决策
2. 大多数用户对大多数内容不会有太多互动，请保持真实
3. 收藏行为在小红书上相对常见（如果内容实用）
4. 评论和分享的门槛较高
5. 上面的 MCP 资料来自真实平台样本，请先参考这些外部资料，再按用户画像做判断
6. 不要把 MCP 当成额外打分器，而是把它理解成你在做决策时知道的平台背景信息
"""
        return prompt

    async def _simulate_single_user(
        self,
        persona: Dict[str, str],
        content: ContentItem,
        task_spec: TaskSpec,
        calibration_hints: List[str] = None,
        external_evidence: Dict[str, Any] = None
    ) -> PersonaSimulationResult:
        """模拟单个用户对内容的反应"""
        prompt = self._build_simulation_prompt(
            persona, content, task_spec, calibration_hints, external_evidence
        )
        
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
        version_evidence: Dict[str, Dict[str, Any]] = None,
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
                    self._simulate_single_user(
                        persona, content_a, task_spec, calibration_hints, (version_evidence or {}).get("A")
                    ),
                    self._simulate_single_user(
                        persona, content_b, task_spec, calibration_hints, (version_evidence or {}).get("B")
                    )
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
        overall_conf = self._calc_multi_confidence(
            total_users,
            {
                "A": float(score_a.total),
                "B": float(score_b.total),
            },
        )
        
        # 生成诊断和建议
        diagnosis = await self._generate_diagnosis(
            task_spec,
            content_a,
            content_b,
            score_a,
            score_b,
            all_results_a,
            all_results_b,
            (version_evidence or {}).get("A"),
            (version_evidence or {}).get("B"),
            "A",
            "B",
        )
        loser_label = "A" if score_a.total < score_b.total else "B"
        suggestions = await self._generate_suggestions(
            task_spec,
            content_a,
            content_b,
            score_a,
            score_b,
            calibration_hints,
            (version_evidence or {}).get(loser_label),
            "A",
            "B",
        )
        
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
            persona_results=combined_results,
            version_evidence=version_evidence or {},
        )

    async def simulate_multi_test(
        self,
        task_spec: TaskSpec,
        versions: List[Tuple[str, ContentItem]],
        max_users: int = 20,
        audience_tags: List[str] = None,
        calibration_hints: List[str] = None,
        version_evidence: Dict[str, Dict[str, Any]] = None,
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
                        self._simulate_single_user(
                            persona,
                            version_map[label],
                            task_spec,
                            calibration_hints,
                            (version_evidence or {}).get(label),
                        )
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

        version_scores = []
        for label in version_labels:
            raw_score = self._calculate_score(results_by_label[label])
            evidence = (version_evidence or {}).get(label)
            version_scores.append(
                VersionScore(
                    label=label,
                    score=raw_score,
                    evidence_score=float((evidence or {}).get("score", 0.0)),
                    composite_score=float(raw_score.total),
                    mcp_evidence=evidence,
                )
            )
        version_scores_sorted = sorted(
            version_scores,
            key=lambda v: self._version_sort_key(v, task_spec.goals),
            reverse=True,
        )

        users = len(next(iter(results_by_label.values()))) if results_by_label else 0
        like_conf = self._calc_multi_confidence(users, {v.label: v.score.like_count for v in version_scores})
        save_conf = self._calc_multi_confidence(users, {v.label: v.score.save_count for v in version_scores})
        comment_conf = self._calc_multi_confidence(users, {v.label: v.score.comment_count for v in version_scores})
        share_conf = self._calc_multi_confidence(users, {v.label: v.score.share_count for v in version_scores})
        overall_conf = self._calc_multi_confidence(users, {v.label: float(v.score.total) for v in version_scores})

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
                (version_evidence or {}).get(top.label),
                (version_evidence or {}).get(second.label),
                top.label,
                second.label,
            )
            suggestions = await self._generate_suggestions(
                task_spec,
                top_content,
                second_content,
                top.score,
                second.score,
                calibration_hints,
                (version_evidence or {}).get(second.label),
                top.label,
                second.label,
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
            version_evidence=version_evidence or {},
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

    def _version_sort_key(self, version: VersionScore, goals: List[OptimizationGoal] = None) -> tuple:
        primary_goal = goals[0] if goals else OptimizationGoal.maximize_save
        primary_goal_value = primary_goal.value if isinstance(primary_goal, OptimizationGoal) else str(primary_goal)
        goal_metric = {
            "maximize_like": version.score.like_count,
            "maximize_save": version.score.save_count,
            "maximize_comment": version.score.comment_count,
            "maximize_share": version.score.share_count,
        }.get(primary_goal_value, version.score.save_count)

        return (
            float(version.composite_score or 0.0),
            float(goal_metric),
            float(version.evidence_score or 0.0),
            float(version.score.save_count),
            float(version.score.like_count),
            float(version.score.comment_count),
            float(version.score.share_count),
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
    
    def _calc_multi_confidence(self, users: int, counts: Dict[str, float]) -> StatisticalConfidence:
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

        if all(float(value).is_integer() for value in counts.values()):
            base = self._calc_confidence(users, int(top_count), int(second_count))
            winner = top_label if base.winner == "A" else second_label
            return StatisticalConfidence(winner=winner, confidence=base.confidence)

        gap = max(float(top_count) - float(second_count), 0.0)
        denom = max(float(top_count), 1.0)
        confidence = min(99.0, 50.0 + (gap / denom) * 50.0)
        return StatisticalConfidence(winner=top_label, confidence=confidence)

    async def _generate_diagnosis(
        self,
        task_spec: TaskSpec,
        content_a: ContentItem,
        content_b: ContentItem,
        score_a: EngagementScore,
        score_b: EngagementScore,
        results_a: List[PersonaSimulationResult],
        results_b: List[PersonaSimulationResult],
        evidence_a: Dict[str, Any] = None,
        evidence_b: Dict[str, Any] = None,
        label_a: str = "A",
        label_b: str = "B"
    ) -> List[str]:
        """生成诊断解释"""
        first_label = label_a or "A"
        second_label = label_b or "B"
        first_beats_second = score_a.total >= score_b.total
        winner_label = first_label if first_beats_second else second_label
        loser_label = second_label if first_beats_second else first_label
        winner_content = content_a if first_beats_second else content_b
        loser_content = content_b if first_beats_second else content_a
        winner_score = score_a if first_beats_second else score_b
        loser_score = score_b if first_beats_second else score_a
        
        # 收集用户反馈理由
        winner_results = results_a if first_beats_second else results_b
        positive_reasons = [r.reasoning for r in winner_results if r.save or r.like][:3]
        winner_evidence = evidence_a if first_beats_second else evidence_b
        loser_evidence_data = evidence_b if first_beats_second else evidence_a
        
        # 处理多目标
        goals_str = ', '.join([g.value for g in task_spec.goals]) if task_spec.goals else 'maximize_save'
        
        prompt = f"""分析以下小红书A/B测试结果，生成3-5条诊断解释。

【任务目标】
受众：{task_spec.audience}
优化目标：{goals_str}

【胜出版本（{winner_label}）】
标题：{winner_content.title}
正文前100字：{winner_content.body[:100]}...
分数：点赞{winner_score.like_count} 收藏{winner_score.save_count} 评论{winner_score.comment_count}

【落后版本（{loser_label}）】
标题：{loser_content.title}
正文前100字：{loser_content.body[:100]}...
分数：点赞{loser_score.like_count} 收藏{loser_score.save_count} 评论{loser_score.comment_count}

【用户反馈摘要】
{chr(10).join(f'- {r}' for r in positive_reasons)}

【MCP 外部证据】
- 胜出版本证据分: {(winner_evidence or {}).get('score', 0)}
- 落后版本证据分: {(loser_evidence_data or {}).get('score', 0)}
{chr(10).join(f"- {item}" for item in (winner_evidence or {}).get('reasons', [])[:3])}

请输出JSON格式：
{{
    "diagnosis": [
        "诊断1：...",
        "诊断2：...",
        "诊断3：..."
    ]
}}

要求：
1. 解释为什么版本{winner_label}更受欢迎
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
        calibration_hints: List[str] = None,
        loser_evidence: Dict[str, Any] = None,
        label_a: str = "A",
        label_b: str = "B"
    ) -> List[str]:
        """生成改写建议"""
        first_label = label_a or "A"
        second_label = label_b or "B"
        loser_is_first = score_a.total < score_b.total
        loser_label = first_label if loser_is_first else second_label
        loser_content = content_a if loser_is_first else content_b
        
        calibration_context = ""
        if calibration_hints:
            calibration_context = f"""
【小红书平台校准提示】
{chr(10).join(f'- {hint}' for hint in calibration_hints)}
"""
        if loser_evidence:
            calibration_context += f"""
【MCP 外部证据】
- 当前版本证据分: {loser_evidence.get('score', 0)}
{chr(10).join(f"- {item}" for item in loser_evidence.get('reasons', [])[:3])}
"""
        
        # 处理多目标
        goals_str = ', '.join([g.value for g in task_spec.goals]) if task_spec.goals else 'maximize_save'
        
        prompt = f"""为以下小红书内容提供具体的改写建议。

【待优化的版本（{loser_label}）】
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
                suggestions.append(f"标题建议：{' | '.join(result['title_suggestions'])}")
            if result.get("hook_suggestions"):
                suggestions.append(f"开头 Hook 建议：{' | '.join(result['hook_suggestions'])}")
            if result.get("structure_suggestions"):
                for s in result['structure_suggestions']:
                    suggestions.append(f"结构优化：{s}")
            
            return suggestions
        except Exception as e:
            return [f"建议生成出错: {str(e)}"]
