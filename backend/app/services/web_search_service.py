"""
NoteTrial Backend - 网页搜索服务
支持搜索互联网内容（知乎、微信公众号、百度等）作为内容创作参考
"""
import httpx
import json
import re
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

from ..config import get_settings

settings = get_settings()


@dataclass
class SearchResult:
    """搜索结果"""
    title: str
    content: str  # 摘要或正文
    url: str
    source: str  # 来源平台
    author: Optional[str] = None
    publish_time: Optional[str] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    

class BaseSearchProvider(ABC):
    """搜索提供者基类"""
    
    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        pass


class SerpAPIProvider(BaseSearchProvider):
    """
    通过 SerpAPI 搜索 Google/Bing 结果
    需要配置 SERP_API_KEY
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or getattr(settings, 'serp_api_key', '')
        self.base_url = "https://serpapi.com/search"
    
    async def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        if not self.api_key:
            return []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(self.base_url, params={
                    "q": query,
                    "api_key": self.api_key,
                    "engine": "google",
                    "num": limit,
                    "hl": "zh-CN",
                    "gl": "cn"
                })
                
                if response.status_code != 200:
                    return []
                
                data = response.json()
                results = []
                
                for item in data.get("organic_results", [])[:limit]:
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        content=item.get("snippet", ""),
                        url=item.get("link", ""),
                        source="google"
                    ))
                
                return results
            except Exception as e:
                print(f"SerpAPI 搜索失败: {e}")
                return []


class DuckDuckGoProvider(BaseSearchProvider):
    """
    DuckDuckGo 搜索（免费，无需API Key）
    注意：可能会被限速
    """
    
    async def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        # 使用 DuckDuckGo 的即时答案 API（有限制）
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    "https://api.duckduckgo.com/",
                    params={
                        "q": query,
                        "format": "json",
                        "no_html": 1,
                        "skip_disambig": 1
                    }
                )
                
                if response.status_code != 200:
                    return []
                
                data = response.json()
                results = []
                
                # 主题结果
                for topic in data.get("RelatedTopics", [])[:limit]:
                    if "Text" in topic and "FirstURL" in topic:
                        results.append(SearchResult(
                            title=topic.get("Text", "")[:50],
                            content=topic.get("Text", ""),
                            url=topic.get("FirstURL", ""),
                            source="duckduckgo"
                        ))
                
                return results
            except Exception as e:
                print(f"DuckDuckGo 搜索失败: {e}")
                return []


class AIWebSearchProvider(BaseSearchProvider):
    """
    使用 AI（如 Perplexity API 或 OpenAI Web Browse）进行智能搜索
    返回经过 AI 整理的搜索结果
    """
    
    def __init__(self):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url
        )
        self.model = settings.default_model
    
    async def search(self, query: str, limit: int = 5) -> List[SearchResult]:
        """
        让 AI 模拟搜索并返回结构化结果
        注意：这不是真实的网页抓取，而是基于 AI 知识库的回答
        适合获取通用知识和写作参考
        """
        prompt = f"""你是一个内容研究助手。用户想要创作关于「{query}」的小红书笔记。

请提供 {limit} 条高质量的参考资料，每条包含：
1. 标题（吸引人的角度）
2. 核心内容要点（100-200字）
3. 写作角度建议

以 JSON 格式返回：
{{
    "results": [
        {{
            "title": "标题",
            "content": "核心内容要点",
            "angle": "写作角度建议",
            "source": "知识来源（如：护肤常识、用户经验、专业知识）"
        }}
    ]
}}

要求：
- 内容要有干货，不要空泛
- 角度要多样化，有不同的切入点
- 适合小红书风格，贴近用户
"""
        
        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            data = json.loads(completion.choices[0].message.content)
            results = []
            
            for item in data.get("results", [])[:limit]:
                results.append(SearchResult(
                    title=item.get("title", ""),
                    content=item.get("content", "") + "\n\n💡 " + item.get("angle", ""),
                    url="",
                    source=item.get("source", "AI知识库"),
                    author="AI研究助手"
                ))
            
            return results
        except Exception as e:
            print(f"AI 搜索失败: {e}")
            return []


class WebSearchService:
    """
    网页搜索服务 - 聚合多个搜索源
    
    支持的搜索源：
    1. AI 智能搜索（默认，基于 LLM 知识库）
    2. SerpAPI（需要配置 API Key）
    3. DuckDuckGo（免费但有限制）
    """
    
    def __init__(self):
        self.providers: Dict[str, BaseSearchProvider] = {
            "ai": AIWebSearchProvider(),
            "duckduckgo": DuckDuckGoProvider(),
        }
        
        # 如果配置了 SerpAPI Key，添加 SerpAPI
        if getattr(settings, 'serp_api_key', ''):
            self.providers["google"] = SerpAPIProvider()
    
    async def search(
        self,
        query: str,
        sources: List[str] = None,
        limit: int = 10
    ) -> List[SearchResult]:
        """
        搜索互联网内容
        
        Args:
            query: 搜索关键词
            sources: 使用的搜索源，默认 ["ai"]
            limit: 返回结果数量
        
        Returns:
            搜索结果列表
        """
        sources = sources or ["ai"]
        all_results: List[SearchResult] = []
        
        for source in sources:
            if source in self.providers:
                try:
                    results = await self.providers[source].search(query, limit)
                    all_results.extend(results)
                except Exception as e:
                    print(f"搜索源 {source} 失败: {e}")
        
        return all_results[:limit]
    
    async def search_for_content_creation(
        self,
        topic: str,
        content_type: str = "分享",
        target_audience: str = "小红书用户"
    ) -> Dict[str, Any]:
        """
        为内容创作搜索参考资料
        
        Returns:
            {
                "knowledge_points": [...],  # 知识要点
                "writing_angles": [...],    # 写作角度
                "key_tips": [...],          # 关键提示
                "raw_results": [...]        # 原始搜索结果
            }
        """
        # 构建搜索 prompt
        search_prompt = f"{topic} {content_type} 攻略 经验 技巧"
        
        # 使用 AI 搜索获取结构化结果
        results = await self.search(search_prompt, sources=["ai"], limit=5)
        
        # 提取知识点
        knowledge_points = []
        writing_angles = []
        
        for r in results:
            if r.content:
                # 简单提取
                knowledge_points.append({
                    "title": r.title,
                    "content": r.content[:300]
                })
                
                # 从 💡 后面提取写作角度
                if "💡" in r.content:
                    angle = r.content.split("💡")[-1].strip()
                    writing_angles.append(angle)
        
        return {
            "knowledge_points": knowledge_points,
            "writing_angles": writing_angles,
            "key_tips": [kp["title"] for kp in knowledge_points],
            "raw_results": [
                {
                    "title": r.title,
                    "content": r.content,
                    "source": r.source
                }
                for r in results
            ]
        }
    
    async def enrich_topic(self, topic: str) -> Dict[str, Any]:
        """
        丰富话题信息 - 获取相关知识、常见问题、热门角度
        
        用于内容生成前的预处理，让 AI 有更多素材参考
        """
        prompt = f"""分析话题「{topic}」，提供创作小红书笔记所需的背景信息。

请返回 JSON 格式：
{{
    "topic_summary": "话题简介（50字内）",
    "key_knowledge": ["关键知识点1", "关键知识点2", "关键知识点3"],
    "common_questions": ["用户常问问题1", "用户常问问题2"],
    "hot_angles": ["热门切入角度1", "热门切入角度2", "热门切入角度3"],
    "related_topics": ["相关话题1", "相关话题2"],
    "target_users": ["目标用户群体1", "目标用户群体2"],
    "content_tips": ["创作建议1", "创作建议2"]
}}

要求实用、具体，贴近小红书用户需求。
"""
        
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url
            )
            
            completion = await client.chat.completions.create(
                model=settings.default_model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            return json.loads(completion.choices[0].message.content)
        except Exception as e:
            print(f"丰富话题失败: {e}")
            return {
                "topic_summary": topic,
                "key_knowledge": [],
                "common_questions": [],
                "hot_angles": [],
                "related_topics": [],
                "target_users": ["小红书用户"],
                "content_tips": []
            }


# 全局实例
_web_search_service: Optional[WebSearchService] = None

def get_web_search_service() -> WebSearchService:
    """获取网页搜索服务单例"""
    global _web_search_service
    if _web_search_service is None:
        _web_search_service = WebSearchService()
    return _web_search_service
