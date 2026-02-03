"""
NoteTrial Backend - 去重与多样性控制
避免生成重复或相似内容
"""
import re
import json
import os
from typing import List, Tuple, Optional
from datetime import datetime
from difflib import SequenceMatcher


class DiversityController:
    """
    内容多样性控制器
    
    核心功能：
    1. 标题去重：检测与历史标题的相似度
    2. 关键词轮换：避免反复使用相同关键词
    3. 风格变化：建议不同的写作风格
    """
    
    def __init__(self, storage_path: str = "data/diversity_data.json"):
        self.storage_path = storage_path
        self.recent_titles: List[str] = []
        self.recent_keywords: List[str] = []
        self.used_patterns: List[str] = []
        self.title_history: List[dict] = []  # 保存更多历史信息
        self._load_data()
    
    def _load_data(self):
        """加载历史数据"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.recent_titles = data.get('recent_titles', [])
                    self.recent_keywords = data.get('recent_keywords', [])
                    self.used_patterns = data.get('used_patterns', [])
                    self.title_history = data.get('title_history', [])
            except Exception as e:
                print(f"[DiversityController] 加载数据失败: {e}")
    
    def _save_data(self):
        """保存数据"""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        try:
            data = {
                'recent_titles': self.recent_titles[-50:],  # 保留最近50条
                'recent_keywords': self.recent_keywords[-100:],
                'used_patterns': self.used_patterns[-20:],
                'title_history': self.title_history[-100:],
            }
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[DiversityController] 保存数据失败: {e}")
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """计算两个文本的相似度 (0-1)"""
        return SequenceMatcher(None, text1, text2).ratio()
    
    def check_title_duplicate(self, title: str, threshold: float = 0.6) -> Tuple[bool, Optional[str]]:
        """
        检查标题是否与历史重复
        
        Returns:
            (is_duplicate, similar_title): 是否重复，以及相似的历史标题
        """
        for old_title in self.recent_titles:
            similarity = self.calculate_similarity(title, old_title)
            if similarity > threshold:
                return True, old_title
        return False, None
    
    def check_keywords_overuse(self, tags: List[str], max_repeat: int = 3) -> List[str]:
        """
        检查哪些关键词被过度使用
        
        Returns:
            过度使用的关键词列表
        """
        from collections import Counter
        recent_count = Counter(self.recent_keywords[-30:])  # 最近30个关键词
        
        overused = []
        for tag in tags:
            if recent_count.get(tag, 0) >= max_repeat:
                overused.append(tag)
        
        return overused
    
    def suggest_style_variation(self) -> str:
        """
        建议一种不同的写作风格
        
        根据最近使用的风格，推荐一个不同的
        """
        all_styles = [
            "实用攻略型",
            "情感共鸣型", 
            "清单盘点型",
            "故事叙述型",
            "问答互动型",
            "对比测评型",
            "经验分享型",
            "干货教程型",
        ]
        
        # 找出最近没用过的风格
        recent_patterns = set(self.used_patterns[-5:])
        available_styles = [s for s in all_styles if s not in recent_patterns]
        
        if not available_styles:
            available_styles = all_styles
        
        # 返回第一个可用的
        return available_styles[0]
    
    def record_content(self, title: str, tags: List[str], style: str = ""):
        """记录新发布的内容"""
        self.recent_titles.append(title)
        self.recent_keywords.extend(tags)
        if style:
            self.used_patterns.append(style)
        
        self.title_history.append({
            'title': title,
            'tags': tags,
            'style': style,
            'created_at': datetime.now().isoformat()
        })
        
        self._save_data()
    
    def get_diversity_prompt(self) -> str:
        """获取多样性提示，用于指导内容生成"""
        prompts = []
        
        # 1. 避免的标题关键词
        if self.recent_titles:
            recent_5 = self.recent_titles[-5:]
            prompts.append(f"避免与以下标题相似: {', '.join(recent_5)}")
        
        # 2. 建议的风格
        suggested_style = self.suggest_style_variation()
        prompts.append(f"本次建议使用「{suggested_style}」风格")
        
        # 3. 避免的标签
        if self.recent_keywords:
            from collections import Counter
            counter = Counter(self.recent_keywords[-20:])
            overused = [k for k, v in counter.most_common(5) if v >= 2]
            if overused:
                prompts.append(f"避免过度使用这些标签: {', '.join(overused)}")
        
        return "\n".join(prompts)
    
    def validate_content(self, title: str, body: str, tags: List[str]) -> dict:
        """
        验证内容的多样性
        
        Returns:
            {
                'is_valid': bool,
                'issues': List[str],
                'suggestions': List[str]
            }
        """
        issues = []
        suggestions = []
        
        # 检查标题重复
        is_dup, similar = self.check_title_duplicate(title)
        if is_dup:
            issues.append(f"标题与历史内容相似: 「{similar}」")
            suggestions.append("建议更换标题角度或用词")
        
        # 检查关键词过度使用
        overused = self.check_keywords_overuse(tags)
        if overused:
            issues.append(f"标签过度使用: {', '.join(overused)}")
            suggestions.append("建议替换部分标签，增加新鲜感")
        
        # 检查正文长度
        if len(body) < 100:
            issues.append("正文过短")
            suggestions.append("建议丰富内容，至少200字")
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'suggestions': suggestions
        }
    
    def get_stats(self) -> dict:
        """获取多样性统计"""
        from collections import Counter
        
        tag_counter = Counter(self.recent_keywords)
        
        return {
            'total_titles': len(self.title_history),
            'recent_titles_count': len(self.recent_titles),
            'unique_tags': len(set(self.recent_keywords)),
            'top_tags': tag_counter.most_common(10),
            'recent_styles': self.used_patterns[-5:],
        }
