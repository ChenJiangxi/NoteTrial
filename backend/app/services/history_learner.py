"""
历史发帖学习服务 - History Learning Service
分析用户历史发帖，学习写作风格和偏好，生成更贴合用户的内容
"""
import os
import json
import re
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
from collections import Counter


class HistoryLearner:
    """历史发帖学习器"""
    
    def __init__(self, storage_path: str = "data/history"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.history_file = self.storage_path / "user_history.json"
        self.profile_file = self.storage_path / "user_profile.json"
        
        self.history = self._load_history()
        self.profile = self._load_profile()
    
    def _load_history(self) -> List[Dict[str, Any]]:
        """加载历史发帖"""
        if self.history_file.exists():
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
    
    def _save_history(self):
        """保存历史发帖"""
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)
    
    def _load_profile(self) -> Dict[str, Any]:
        """加载用户画像"""
        if self.profile_file.exists():
            with open(self.profile_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return self._default_profile()
    
    def _save_profile(self):
        """保存用户画像"""
        with open(self.profile_file, "w", encoding="utf-8") as f:
            json.dump(self.profile, f, ensure_ascii=False, indent=2)
    
    def _default_profile(self) -> Dict[str, Any]:
        """默认用户画像"""
        return {
            "writing_style": {
                "tone": "neutral",  # casual, professional, cute, neutral
                "emoji_density": 0.0,
                "avg_title_length": 0,
                "avg_body_length": 0,
                "paragraph_style": "mixed",  # short, medium, long, mixed
                "punctuation_style": "normal"  # normal, expressive, minimal
            },
            "content_preferences": {
                "favorite_topics": [],
                "favorite_tags": [],
                "common_hooks": [],  # 常用开头句式
                "common_endings": []  # 常用结尾句式
            },
            "performance_insights": {
                "best_performing_topics": [],
                "best_performing_tags": [],
                "optimal_title_length": 0,
                "optimal_body_length": 0,
                "best_posting_time": None
            },
            "last_updated": None
        }
    
    # ==================== 历史记录管理 ====================
    
    def add_post(
        self,
        note_id: str,
        title: str,
        body: str,
        tags: List[str],
        cover_image: Optional[str] = None,
        posted_at: Optional[str] = None,
        performance: Optional[Dict[str, int]] = None
    ) -> Dict[str, Any]:
        """
        添加历史发帖记录
        
        Args:
            note_id: 笔记ID
            title: 标题
            body: 正文
            tags: 标签
            cover_image: 封面图
            posted_at: 发布时间
            performance: 效果数据 {likes, collects, comments, views}
        
        Returns:
            添加的记录
        """
        record = {
            "note_id": note_id,
            "title": title,
            "body": body,
            "tags": tags,
            "cover_image": cover_image,
            "posted_at": posted_at or datetime.now().isoformat(),
            "performance": performance or {},
            "analyzed": False
        }
        
        # 检查是否已存在
        for i, h in enumerate(self.history):
            if h.get("note_id") == note_id:
                self.history[i] = record
                self._save_history()
                return record
        
        self.history.append(record)
        self._save_history()
        
        # 触发增量学习
        self._incremental_learn(record)
        
        return record
    
    def update_performance(
        self,
        note_id: str,
        performance: Dict[str, int]
    ) -> bool:
        """更新笔记效果数据"""
        for post in self.history:
            if post.get("note_id") == note_id:
                post["performance"] = performance
                post["performance_updated_at"] = datetime.now().isoformat()
                self._save_history()
                
                # 重新分析
                self._analyze_performance()
                return True
        return False
    
    def get_history(
        self,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "posted_at"  # posted_at, likes, collects
    ) -> List[Dict[str, Any]]:
        """获取历史发帖列表"""
        posts = self.history.copy()
        
        if sort_by == "posted_at":
            posts.sort(key=lambda x: x.get("posted_at", ""), reverse=True)
        elif sort_by == "likes":
            posts.sort(key=lambda x: x.get("performance", {}).get("likes", 0), reverse=True)
        elif sort_by == "collects":
            posts.sort(key=lambda x: x.get("performance", {}).get("collects", 0), reverse=True)
        
        return posts[offset:offset + limit]
    
    def import_from_xhs(self, posts: List[Dict[str, Any]]) -> int:
        """
        从小红书导入历史发帖
        
        Args:
            posts: MCP返回的笔记列表
        
        Returns:
            导入数量
        """
        imported = 0
        for post in posts:
            note_id = post.get("noteId") or post.get("note_id") or post.get("id")
            if not note_id:
                continue
            
            self.add_post(
                note_id=note_id,
                title=post.get("title", ""),
                body=post.get("desc", "") or post.get("content", ""),
                tags=post.get("tagList", []) or post.get("tags", []),
                cover_image=post.get("cover", {}).get("url") if isinstance(post.get("cover"), dict) else post.get("cover"),
                posted_at=post.get("time") or post.get("created_at"),
                performance={
                    "likes": int(post.get("likedCount", 0) or post.get("interactInfo", {}).get("likedCount", 0)),
                    "collects": int(post.get("collectedCount", 0) or post.get("interactInfo", {}).get("collectedCount", 0)),
                    "comments": int(post.get("commentCount", 0) or post.get("interactInfo", {}).get("commentCount", 0)),
                    "views": int(post.get("viewCount", 0))
                }
            )
            imported += 1
        
        # 完整分析
        if imported > 0:
            self.analyze_all()
        
        return imported
    
    # ==================== 风格分析 ====================
    
    def _incremental_learn(self, post: Dict[str, Any]):
        """增量学习单篇内容"""
        title = post.get("title", "")
        body = post.get("body", "")
        tags = post.get("tags", [])
        
        # 更新偏好标签
        for tag in tags:
            if tag not in self.profile["content_preferences"]["favorite_tags"]:
                self.profile["content_preferences"]["favorite_tags"].append(tag)
        
        # 保持标签数量限制
        self.profile["content_preferences"]["favorite_tags"] = \
            self.profile["content_preferences"]["favorite_tags"][-50:]
        
        self._save_profile()
    
    def analyze_all(self):
        """完整分析所有历史发帖，更新用户画像"""
        if len(self.history) < 3:
            return  # 数据太少，不分析
        
        titles = [p.get("title", "") for p in self.history if p.get("title")]
        bodies = [p.get("body", "") for p in self.history if p.get("body")]
        all_tags = []
        for p in self.history:
            all_tags.extend(p.get("tags", []))
        
        # 1. 分析写作风格
        self._analyze_writing_style(titles, bodies)
        
        # 2. 分析内容偏好
        self._analyze_content_preferences(titles, bodies, all_tags)
        
        # 3. 分析效果数据
        self._analyze_performance()
        
        self.profile["last_updated"] = datetime.now().isoformat()
        self._save_profile()
    
    def _analyze_writing_style(self, titles: List[str], bodies: List[str]):
        """分析写作风格"""
        if not titles or not bodies:
            return
        
        # 标题长度
        avg_title_len = sum(len(t) for t in titles) / len(titles)
        self.profile["writing_style"]["avg_title_length"] = round(avg_title_len, 1)
        
        # 正文长度
        avg_body_len = sum(len(b) for b in bodies) / len(bodies)
        self.profile["writing_style"]["avg_body_length"] = round(avg_body_len, 1)
        
        # emoji 密度
        all_text = " ".join(titles + bodies)
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"
            "\U0001f926-\U0001f937"
            "\U00010000-\U0010ffff"
            "]+",
            flags=re.UNICODE
        )
        emoji_count = len(emoji_pattern.findall(all_text))
        char_count = len(all_text)
        emoji_density = emoji_count / char_count * 100 if char_count > 0 else 0
        self.profile["writing_style"]["emoji_density"] = round(emoji_density, 2)
        
        # 语气分析
        tone = self._detect_tone(all_text)
        self.profile["writing_style"]["tone"] = tone
        
        # 段落风格
        paragraph_lens = []
        for body in bodies:
            paragraphs = [p.strip() for p in body.split("\n") if p.strip()]
            paragraph_lens.extend([len(p) for p in paragraphs])
        
        if paragraph_lens:
            avg_para_len = sum(paragraph_lens) / len(paragraph_lens)
            if avg_para_len < 30:
                self.profile["writing_style"]["paragraph_style"] = "short"
            elif avg_para_len < 80:
                self.profile["writing_style"]["paragraph_style"] = "medium"
            else:
                self.profile["writing_style"]["paragraph_style"] = "long"
        
        # 标点风格
        exclamation_count = all_text.count("！") + all_text.count("!")
        question_count = all_text.count("？") + all_text.count("?")
        if (exclamation_count + question_count) / len(all_text) * 100 > 2:
            self.profile["writing_style"]["punctuation_style"] = "expressive"
        elif (exclamation_count + question_count) / len(all_text) * 100 < 0.5:
            self.profile["writing_style"]["punctuation_style"] = "minimal"
        else:
            self.profile["writing_style"]["punctuation_style"] = "normal"
    
    def _detect_tone(self, text: str) -> str:
        """检测语气风格"""
        casual_markers = ["哈哈", "嘿嘿", "嘻嘻", "啦", "呀", "吧", "呢", "哇", "耶"]
        cute_markers = ["宝", "姐妹", "集美", "yyds", "绝绝子", "太可了", "爱了", "冲鸭"]
        professional_markers = ["首先", "其次", "总结", "建议", "推荐", "分析", "评测"]
        
        casual_count = sum(text.count(m) for m in casual_markers)
        cute_count = sum(text.count(m) for m in cute_markers)
        professional_count = sum(text.count(m) for m in professional_markers)
        
        max_count = max(casual_count, cute_count, professional_count)
        if max_count == 0:
            return "neutral"
        elif max_count == cute_count:
            return "cute"
        elif max_count == casual_count:
            return "casual"
        elif max_count == professional_count:
            return "professional"
        return "neutral"
    
    def _analyze_content_preferences(
        self,
        titles: List[str],
        bodies: List[str],
        all_tags: List[str]
    ):
        """分析内容偏好"""
        # 最常用标签
        tag_counter = Counter(all_tags)
        self.profile["content_preferences"]["favorite_tags"] = [
            tag for tag, _ in tag_counter.most_common(20)
        ]
        
        # 常用开头句式（hook）
        hooks = []
        for body in bodies:
            first_line = body.split("\n")[0].strip() if body else ""
            if first_line and len(first_line) < 50:
                hooks.append(first_line)
        
        self.profile["content_preferences"]["common_hooks"] = hooks[:10]
        
        # 常用结尾句式
        endings = []
        for body in bodies:
            lines = [l.strip() for l in body.split("\n") if l.strip()]
            if lines:
                endings.append(lines[-1])
        
        self.profile["content_preferences"]["common_endings"] = endings[:10]
        
        # 话题词提取（简单实现）
        topic_words = []
        for title in titles:
            # 提取标题中的关键词
            words = re.findall(r"[\u4e00-\u9fa5]{2,4}", title)
            topic_words.extend(words)
        
        word_counter = Counter(topic_words)
        self.profile["content_preferences"]["favorite_topics"] = [
            word for word, count in word_counter.most_common(15) if count >= 2
        ]
    
    def _analyze_performance(self):
        """分析效果数据，找出最佳模式"""
        posts_with_perf = [
            p for p in self.history 
            if p.get("performance") and p["performance"].get("likes", 0) > 0
        ]
        
        if len(posts_with_perf) < 3:
            return
        
        # 按收藏排序，找出 top 表现
        sorted_by_collects = sorted(
            posts_with_perf,
            key=lambda x: x.get("performance", {}).get("collects", 0),
            reverse=True
        )
        
        top_posts = sorted_by_collects[:max(3, len(sorted_by_collects) // 3)]
        
        # 分析 top 表现的共同特征
        top_tags = []
        top_title_lens = []
        top_body_lens = []
        
        for post in top_posts:
            top_tags.extend(post.get("tags", []))
            top_title_lens.append(len(post.get("title", "")))
            top_body_lens.append(len(post.get("body", "")))
        
        tag_counter = Counter(top_tags)
        self.profile["performance_insights"]["best_performing_tags"] = [
            tag for tag, _ in tag_counter.most_common(10)
        ]
        
        if top_title_lens:
            self.profile["performance_insights"]["optimal_title_length"] = \
                round(sum(top_title_lens) / len(top_title_lens))
        
        if top_body_lens:
            self.profile["performance_insights"]["optimal_body_length"] = \
                round(sum(top_body_lens) / len(top_body_lens))
    
    # ==================== 生成辅助 ====================
    
    def get_style_prompt(self) -> str:
        """
        获取基于用户风格的生成提示词
        
        Returns:
            风格提示词
        """
        style = self.profile["writing_style"]
        prefs = self.profile["content_preferences"]
        perf = self.profile["performance_insights"]
        
        prompts = []
        
        # 语气风格
        tone_map = {
            "casual": "轻松随意、口语化",
            "cute": "可爱俏皮、使用网络流行语",
            "professional": "专业严谨、有条理",
            "neutral": "自然平实"
        }
        prompts.append(f"语气风格：{tone_map.get(style['tone'], '自然')}")
        
        # emoji 使用
        if style["emoji_density"] > 3:
            prompts.append("大量使用emoji表情")
        elif style["emoji_density"] > 1:
            prompts.append("适当使用emoji表情")
        else:
            prompts.append("少量或不使用emoji")
        
        # 标题长度
        if style["avg_title_length"] > 0:
            prompts.append(f"标题长度约 {int(style['avg_title_length'])} 字")
        
        # 正文长度
        if style["avg_body_length"] > 0:
            prompts.append(f"正文长度约 {int(style['avg_body_length'])} 字")
        
        # 段落风格
        para_map = {
            "short": "短段落，每段1-2句",
            "medium": "中等段落",
            "long": "长段落，信息密集"
        }
        prompts.append(f"段落风格：{para_map.get(style['paragraph_style'], '混合')}")
        
        # 常用标签
        if prefs["favorite_tags"]:
            prompts.append(f"倾向使用的标签：{', '.join(prefs['favorite_tags'][:5])}")
        
        # 效果优化建议
        if perf["optimal_title_length"] > 0:
            prompts.append(f"【高效果】标题 {perf['optimal_title_length']} 字左右效果最好")
        
        if perf["best_performing_tags"]:
            prompts.append(f"【高效果】这些标签效果好：{', '.join(perf['best_performing_tags'][:5])}")
        
        return "\n".join(prompts)
    
    def get_reference_content(self, topic: str, max_count: int = 3) -> List[Dict[str, Any]]:
        """
        获取相关的历史发帖作为参考
        
        Args:
            topic: 当前话题
            max_count: 最大返回数量
        
        Returns:
            相关历史发帖列表
        """
        topic_keywords = topic.lower().split()
        
        scored_posts = []
        for post in self.history:
            title = post.get("title", "").lower()
            body = post.get("body", "").lower()
            tags = [t.lower() for t in post.get("tags", [])]
            
            score = 0
            for kw in topic_keywords:
                if kw in title:
                    score += 3
                if kw in body:
                    score += 1
                if any(kw in t for t in tags):
                    score += 2
            
            # 效果加成
            perf = post.get("performance", {})
            collects = perf.get("collects", 0)
            if collects > 100:
                score += 5
            elif collects > 50:
                score += 3
            elif collects > 20:
                score += 1
            
            if score > 0:
                scored_posts.append((score, post))
        
        scored_posts.sort(key=lambda x: x[0], reverse=True)
        
        return [p[1] for p in scored_posts[:max_count]]
    
    def get_profile(self) -> Dict[str, Any]:
        """获取用户画像"""
        return self.profile
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计数据"""
        total_posts = len(self.history)
        posts_with_perf = [
            p for p in self.history 
            if p.get("performance") and p["performance"].get("likes", 0) > 0
        ]
        
        total_likes = sum(p.get("performance", {}).get("likes", 0) for p in self.history)
        total_collects = sum(p.get("performance", {}).get("collects", 0) for p in self.history)
        total_comments = sum(p.get("performance", {}).get("comments", 0) for p in self.history)
        
        return {
            "total_posts": total_posts,
            "analyzed_posts": len(posts_with_perf),
            "total_engagement": {
                "likes": total_likes,
                "collects": total_collects,
                "comments": total_comments
            },
            "avg_engagement": {
                "likes": round(total_likes / total_posts, 1) if total_posts > 0 else 0,
                "collects": round(total_collects / total_posts, 1) if total_posts > 0 else 0,
                "comments": round(total_comments / total_posts, 1) if total_posts > 0 else 0
            },
            "profile_updated": self.profile.get("last_updated"),
            "writing_tone": self.profile["writing_style"]["tone"],
            "top_tags": self.profile["content_preferences"]["favorite_tags"][:10]
        }


# 全局实例
_history_learner: Optional[HistoryLearner] = None

def get_history_learner() -> HistoryLearner:
    """获取历史学习器单例"""
    global _history_learner
    if _history_learner is None:
        _history_learner = HistoryLearner()
    return _history_learner
