"""
NoteTrial Backend - 学习引擎
根据发布效果反馈优化生成策略
"""
import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class ContentFeatures:
    """内容特征"""
    title_length: int
    title_has_emoji: bool
    title_has_numbers: bool
    title_pattern: str  # 如 "疑问句", "感叹句", "清单式"
    body_length: int
    body_paragraph_count: int
    body_emoji_count: int
    tag_count: int
    tags: List[str]
    topic: str


@dataclass
class PerformanceRecord:
    """效果记录"""
    content_id: str
    features: ContentFeatures
    stats: Dict[str, int]  # likes, collects, comments, views
    performance_score: float
    created_at: str
    

class LearningEngine:
    """
    学习引擎：根据历史发布效果学习最佳内容策略
    
    核心思路：
    1. 记录每篇发布内容的特征
    2. 获取效果数据后计算 performance_score
    3. 分析高分内容的共同特征
    4. 生成优化后的 prompt 指导
    """
    
    def __init__(self, storage_path: str = "data/learning_data.json"):
        self.storage_path = storage_path
        self.records: List[PerformanceRecord] = []
        self.good_patterns: Dict[str, Any] = {}
        self.bad_patterns: Dict[str, Any] = {}
        self._load_data()
    
    def _load_data(self):
        """从文件加载历史数据"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.records = [
                        PerformanceRecord(
                            content_id=r['content_id'],
                            features=ContentFeatures(**r['features']),
                            stats=r['stats'],
                            performance_score=r['performance_score'],
                            created_at=r['created_at']
                        )
                        for r in data.get('records', [])
                    ]
                    self.good_patterns = data.get('good_patterns', {})
                    self.bad_patterns = data.get('bad_patterns', {})
            except Exception as e:
                print(f"[LearningEngine] 加载数据失败: {e}")
    
    def _save_data(self):
        """保存数据到文件"""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        try:
            data = {
                'records': [
                    {
                        'content_id': r.content_id,
                        'features': asdict(r.features),
                        'stats': r.stats,
                        'performance_score': r.performance_score,
                        'created_at': r.created_at
                    }
                    for r in self.records
                ],
                'good_patterns': self.good_patterns,
                'bad_patterns': self.bad_patterns
            }
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[LearningEngine] 保存数据失败: {e}")
    
    def extract_features(self, title: str, body: str, tags: List[str], topic: str) -> ContentFeatures:
        """从内容中提取特征"""
        import re
        
        # 标题特征
        title_length = len(title)
        title_has_emoji = bool(re.search(r'[\U0001F300-\U0001F9FF]', title))
        title_has_numbers = bool(re.search(r'\d+', title))
        
        # 判断标题模式
        if '?' in title or '？' in title or '吗' in title or '呢' in title:
            title_pattern = "疑问句"
        elif '!' in title or '！' in title or '绝了' in title or '太' in title:
            title_pattern = "感叹句"
        elif re.search(r'\d+[个件款条家]', title):
            title_pattern = "清单式"
        elif '如何' in title or '怎么' in title or '攻略' in title:
            title_pattern = "教程式"
        else:
            title_pattern = "陈述句"
        
        # 正文特征
        body_length = len(body)
        body_paragraph_count = len([p for p in body.split('\n') if p.strip()])
        body_emoji_count = len(re.findall(r'[\U0001F300-\U0001F9FF]', body))
        
        return ContentFeatures(
            title_length=title_length,
            title_has_emoji=title_has_emoji,
            title_has_numbers=title_has_numbers,
            title_pattern=title_pattern,
            body_length=body_length,
            body_paragraph_count=body_paragraph_count,
            body_emoji_count=body_emoji_count,
            tag_count=len(tags),
            tags=tags,
            topic=topic
        )
    
    def calculate_performance_score(
        self, 
        stats: Dict[str, int],
        goals: List[str] = None
    ) -> float:
        """
        计算内容表现分数
        
        根据优化目标加权计算：
        - maximize_save: 收藏权重最高
        - maximize_like: 点赞权重最高
        - maximize_comment: 评论权重最高
        """
        likes = stats.get('likes', 0)
        collects = stats.get('collects', 0)
        comments = stats.get('comments', 0)
        views = max(stats.get('views', 1), 1)
        
        # 计算互动率
        like_rate = likes / views
        collect_rate = collects / views
        comment_rate = comments / views
        
        # 默认权重
        weights = {'like': 0.3, 'collect': 0.5, 'comment': 0.2}
        
        # 根据目标调整权重
        if goals:
            if 'maximize_save' in goals:
                weights = {'like': 0.2, 'collect': 0.6, 'comment': 0.2}
            elif 'maximize_like' in goals:
                weights = {'like': 0.6, 'collect': 0.2, 'comment': 0.2}
            elif 'maximize_comment' in goals:
                weights = {'like': 0.2, 'collect': 0.2, 'comment': 0.6}
        
        # 综合得分 (归一化到0-100)
        score = (
            like_rate * weights['like'] * 1000 +
            collect_rate * weights['collect'] * 2000 +
            comment_rate * weights['comment'] * 3000
        )
        
        return min(score, 100)
    
    def record_content(
        self,
        content_id: str,
        title: str,
        body: str,
        tags: List[str],
        topic: str
    ) -> ContentFeatures:
        """记录新发布的内容"""
        features = self.extract_features(title, body, tags, topic)
        
        record = PerformanceRecord(
            content_id=content_id,
            features=features,
            stats={'likes': 0, 'collects': 0, 'comments': 0, 'views': 0},
            performance_score=0.0,
            created_at=datetime.now().isoformat()
        )
        
        self.records.append(record)
        self._save_data()
        
        return features
    
    def update_performance(
        self,
        content_id: str,
        stats: Dict[str, int],
        goals: List[str] = None
    ):
        """更新内容的效果数据"""
        for record in self.records:
            if record.content_id == content_id:
                record.stats = stats
                record.performance_score = self.calculate_performance_score(stats, goals)
                break
        
        self._analyze_patterns()
        self._save_data()
    
    def _analyze_patterns(self):
        """分析高分和低分内容的模式"""
        if len(self.records) < 3:
            return
        
        # 按分数排序
        sorted_records = sorted(
            [r for r in self.records if r.performance_score > 0],
            key=lambda x: x.performance_score,
            reverse=True
        )
        
        if len(sorted_records) < 2:
            return
        
        # 取前 30% 为好内容，后 30% 为差内容
        n = len(sorted_records)
        good_records = sorted_records[:max(1, n // 3)]
        bad_records = sorted_records[-max(1, n // 3):]
        
        # 分析好内容的模式
        self.good_patterns = {
            'avg_title_length': sum(r.features.title_length for r in good_records) / len(good_records),
            'title_emoji_rate': sum(1 for r in good_records if r.features.title_has_emoji) / len(good_records),
            'title_number_rate': sum(1 for r in good_records if r.features.title_has_numbers) / len(good_records),
            'common_title_patterns': self._get_common_patterns([r.features.title_pattern for r in good_records]),
            'avg_body_length': sum(r.features.body_length for r in good_records) / len(good_records),
            'avg_paragraph_count': sum(r.features.body_paragraph_count for r in good_records) / len(good_records),
            'avg_emoji_count': sum(r.features.body_emoji_count for r in good_records) / len(good_records),
            'avg_tag_count': sum(r.features.tag_count for r in good_records) / len(good_records),
            'common_tags': self._get_common_tags(good_records),
        }
        
        # 分析差内容的模式
        self.bad_patterns = {
            'avg_title_length': sum(r.features.title_length for r in bad_records) / len(bad_records),
            'common_title_patterns': self._get_common_patterns([r.features.title_pattern for r in bad_records]),
            'avg_body_length': sum(r.features.body_length for r in bad_records) / len(bad_records),
        }
    
    def _get_common_patterns(self, patterns: List[str]) -> List[str]:
        """获取最常见的模式"""
        from collections import Counter
        counter = Counter(patterns)
        return [p for p, _ in counter.most_common(3)]
    
    def _get_common_tags(self, records: List[PerformanceRecord]) -> List[str]:
        """获取最常用的标签"""
        from collections import Counter
        all_tags = []
        for r in records:
            all_tags.extend(r.features.tags)
        counter = Counter(all_tags)
        return [t for t, _ in counter.most_common(10)]
    
    def get_optimization_hints(self) -> Dict[str, Any]:
        """获取优化建议，用于指导内容生成"""
        if not self.good_patterns:
            return {}
        
        hints = {
            'title_suggestions': [],
            'body_suggestions': [],
            'tag_suggestions': [],
            'avoid_patterns': [],
        }
        
        # 标题建议
        if self.good_patterns.get('title_emoji_rate', 0) > 0.5:
            hints['title_suggestions'].append("标题中使用 emoji 效果更好")
        
        if self.good_patterns.get('title_number_rate', 0) > 0.5:
            hints['title_suggestions'].append("标题中包含数字效果更好")
        
        common_patterns = self.good_patterns.get('common_title_patterns', [])
        if common_patterns:
            hints['title_suggestions'].append(f"推荐标题模式: {', '.join(common_patterns)}")
        
        avg_title_len = self.good_patterns.get('avg_title_length', 15)
        hints['title_suggestions'].append(f"推荐标题长度: {int(avg_title_len)} 字左右")
        
        # 正文建议
        avg_body_len = self.good_patterns.get('avg_body_length', 300)
        hints['body_suggestions'].append(f"推荐正文长度: {int(avg_body_len)} 字左右")
        
        avg_para = self.good_patterns.get('avg_paragraph_count', 5)
        hints['body_suggestions'].append(f"推荐分 {int(avg_para)} 个段落")
        
        avg_emoji = self.good_patterns.get('avg_emoji_count', 5)
        hints['body_suggestions'].append(f"推荐使用 {int(avg_emoji)} 个 emoji")
        
        # 标签建议
        common_tags = self.good_patterns.get('common_tags', [])
        if common_tags:
            hints['tag_suggestions'] = common_tags[:5]
        
        # 避免的模式
        bad_patterns = self.bad_patterns.get('common_title_patterns', [])
        if bad_patterns:
            hints['avoid_patterns'].append(f"避免使用: {', '.join(bad_patterns)} 类型的标题")
        
        return hints
    
    def build_optimized_prompt(self, base_prompt: str) -> str:
        """在基础 prompt 上添加学习到的优化建议"""
        hints = self.get_optimization_hints()
        
        if not hints:
            return base_prompt
        
        optimization_section = "\n\n## 基于历史效果的优化建议（重要！）\n"
        
        if hints.get('title_suggestions'):
            optimization_section += "\n### 标题优化\n"
            for s in hints['title_suggestions']:
                optimization_section += f"- {s}\n"
        
        if hints.get('body_suggestions'):
            optimization_section += "\n### 正文优化\n"
            for s in hints['body_suggestions']:
                optimization_section += f"- {s}\n"
        
        if hints.get('tag_suggestions'):
            optimization_section += f"\n### 推荐标签\n优先使用这些高效果标签: {', '.join(hints['tag_suggestions'])}\n"
        
        if hints.get('avoid_patterns'):
            optimization_section += "\n### 避免的模式\n"
            for s in hints['avoid_patterns']:
                optimization_section += f"- {s}\n"
        
        return base_prompt + optimization_section
    
    def get_stats_summary(self) -> Dict[str, Any]:
        """获取学习统计摘要"""
        total = len(self.records)
        scored = len([r for r in self.records if r.performance_score > 0])
        
        if scored == 0:
            return {
                'total_records': total,
                'scored_records': 0,
                'avg_score': 0,
                'best_score': 0,
                'has_learned': False
            }
        
        scores = [r.performance_score for r in self.records if r.performance_score > 0]
        
        return {
            'total_records': total,
            'scored_records': scored,
            'avg_score': sum(scores) / len(scores),
            'best_score': max(scores),
            'has_learned': bool(self.good_patterns),
            'good_patterns': self.good_patterns,
        }
