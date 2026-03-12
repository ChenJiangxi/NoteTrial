"""
NoteTrial Backend - 小红书平台校准层
通过 xiaohongshu-mcp 获取平台数据，进行评分校准
"""
import httpx
import json
import os
import re
import tempfile
import uuid
from typing import List, Dict, Any, Optional
from collections import Counter

from ..models import CalibrationData, ContentItem, MCPEvidenceSignal, OptimizationGoal
from ..config import get_settings


settings = get_settings()


class XiaohongshuCalibrator:
    """小红书平台校准器"""
    
    def __init__(self, mcp_url: str = None):
        base_url = mcp_url or settings.xiaohongshu_mcp_url
        self.mcp_url = base_url if base_url.endswith('/mcp') else f"{base_url.rstrip('/')}/mcp"
        self._session_id = None
        # MCP搜索需要父取小红书网页，可能非常慢（需要打开浏览器、加载页面、抓取数据）
        # 设置180秒超时，并单独设置读取超时
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(180.0, read=180.0, connect=30.0)
        )
        self._initialized = False
        self._search_cache = {}  # 简单缓存
    
    async def _request(self, payload: dict) -> dict:
        """发送 MCP 请求"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        
        response = await self._client.post(self.mcp_url, json=payload, headers=headers)
        
        # 保存 session id
        if "mcp-session-id" in response.headers:
            self._session_id = response.headers["mcp-session-id"]
        
        if response.status_code == 200:
            return response.json()
        return {}
    
    async def _init_session(self) -> bool:
        """初始化 MCP 会话"""
        if self._initialized:
            return True
            
        try:
            # 1. Initialize
            result = await self._request({
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "NoteTrial", "version": "1.0.0"}
                }
            })
            
            if not result.get("result"):
                return False
            
            # 2. Send initialized notification
            await self._request({
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            })
            
            self._initialized = True
            return True
        except Exception as e:
            print(f"MCP 初始化失败: {e}")
            return False
    
    async def _call_tool(self, tool_name: str, arguments: dict = None) -> dict:
        """调用 MCP 工具"""
        if not self._initialized:
            if not await self._init_session():
                return {}
        
        try:
            print(f"[MCP] 调用工具: {tool_name}, 参数: {str(arguments)[:200]}...")
            result = await self._request({
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments or {}
                }
            })
            print(f"[MCP] 工具响应: {str(result)[:500]}")
            
            if "error" in result:
                print(f"MCP 工具调用错误: {result['error']}")
                return {}
            
            return result.get("result", {})
        except Exception as e:
            print(f"[MCP] 工具调用异常: {tool_name} - {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    async def check_mcp_status(self) -> bool:
        """检查 MCP 服务是否可用"""
        try:
            if not self._initialized:
                return await self._init_session()
            return True
        except Exception:
            return False
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """列出可用的 MCP 工具"""
        if not self._initialized:
            await self._init_session()
        
        result = await self._request({
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/list",
            "params": {}
        })
        
        return result.get("result", {}).get("tools", [])
    
    async def close(self):
        """关闭连接"""
        await self._client.aclose()
    
    async def search_topic_samples(self, topic: str, limit: int = 50) -> List[Dict[str, Any]]:
        """搜索指定话题的热门内容样本"""
        # 检查缓存（5分钟内的结果）
        import time
        cache_key = f"{topic}:{limit}"
        if cache_key in self._search_cache:
            cached_time, cached_data = self._search_cache[cache_key]
            if time.time() - cached_time < 300:  # 5分钟缓存
                print(f"使用缓存: '{topic}' ({len(cached_data)}条)")
                return cached_data
        
        max_retries = 2
        
        for attempt in range(max_retries):
            try:
                print(f"搜索'{topic}' (尝试 {attempt + 1}/{max_retries})，请稍等...")
                result = await self._call_tool("search_feeds", {"keyword": topic})
                
                if result and "content" in result:
                    content = result.get("content", [])
                    if content and len(content) > 0:
                        text_content = content[0].get("text", "")
                        try:
                            data = json.loads(text_content)
                            # 检查返回的数据结构
                            feeds = []
                            if isinstance(data, dict) and "feeds" in data:
                                feeds = data["feeds"] if isinstance(data["feeds"], list) else []
                            elif isinstance(data, list):
                                feeds = data
                            
                            if feeds:
                                result_feeds = feeds[:limit]
                                # 存入缓存
                                self._search_cache[cache_key] = (time.time(), result_feeds)
                                print(f"搜索'{topic}'成功: 找到 {len(result_feeds)} 条内容")
                                return result_feeds
                        except json.JSONDecodeError as e:
                            print(f"JSON解析失败: {e}")
                print(f"搜索'{topic}'未返回有效数据")
                return []
            except Exception as e:
                error_type = type(e).__name__
                print(f"搜索'{topic}'失败 (尝试 {attempt + 1}): {error_type}")
                if "Timeout" in error_type or "timeout" in str(e).lower():
                    print(f"   → MCP搜索超时，小红书网页加载可能较慢")
                if attempt < max_retries - 1:
                    # 重置会话后重试
                    self._initialized = False
                    self._session_id = None
                    continue
                return []
        return []
    
    async def search_images_for_topic(self, topic: str, limit: int = 5) -> List[str]:
        """搜索话题相关的图片 URL"""
        try:
            samples = await self.search_topic_samples(topic, limit=limit * 3)
            image_urls = []
            
            for sample in samples:
                # 从noteCard.cover中提取图片URL
                note_card = sample.get("noteCard", {})
                cover = note_card.get("cover", {})
                
                if cover:
                    # 优先使用urlDefault，其次urlPre
                    url = cover.get("urlDefault") or cover.get("urlPre") or cover.get("url")
                    if url and url.startswith("http"):
                        image_urls.append(url)
                
                if len(image_urls) >= limit:
                    break
            
            print(f"搜索'{topic}'图片: 找到 {len(image_urls)} 张")
            return image_urls[:limit]
        except Exception as e:
            print(f"搜索图片失败: {e}")
            return []
    
    async def get_calibration_data(self, topic: str) -> CalibrationData:
        """获取话题的校准数据"""
        samples = await self.search_topic_samples(topic)
        
        if not samples:
            return CalibrationData(
                topic=topic,
                avg_title_length=15.0,
                common_opening_patterns=["数字开头", "问题开头", "结果展示"],
                emoji_usage_rate=0.6,
                avg_like_save_ratio=3.0,
                common_tags=[topic],
                sample_count=0
            )
        
        # 分析标题
        titles = [s.get("title", "") for s in samples if s.get("title")]
        avg_title_length = sum(len(t) for t in titles) / len(titles) if titles else 15.0
        
        # 分析开头模式
        opening_patterns = self._analyze_opening_patterns(titles)
        
        # 分析emoji使用
        emoji_count = sum(1 for t in titles if self._contains_emoji(t))
        emoji_usage_rate = emoji_count / len(titles) if titles else 0.5
        
        # 分析标签
        all_tags = []
        for s in samples:
            tags = s.get("tags", [])
            if isinstance(tags, list):
                all_tags.extend(tags)
        common_tags = [tag for tag, _ in Counter(all_tags).most_common(10)]
        
        return CalibrationData(
            topic=topic,
            avg_title_length=avg_title_length,
            common_opening_patterns=opening_patterns,
            emoji_usage_rate=emoji_usage_rate,
            avg_like_save_ratio=3.0,
            common_tags=common_tags or [topic],
            sample_count=len(samples)
        )
    
    def _analyze_opening_patterns(self, titles: List[str]) -> List[str]:
        """分析标题开头模式"""
        patterns = {
            "数字开头": 0, "问题开头": 0, "感叹开头": 0,
            "对比开头": 0, "结果展示": 0, "痛点开头": 0
        }
        
        for title in titles:
            if not title:
                continue
            if re.match(r'^[0-9０-９]', title):
                patterns["数字开头"] += 1
            if title.endswith('?') or title.endswith('？') or '吗' in title[:10]:
                patterns["问题开头"] += 1
            if '!' in title or '！' in title or '绝了' in title or '太' in title[:5]:
                patterns["感叹开头"] += 1
            if 'vs' in title.lower() or '对比' in title or '还是' in title:
                patterns["对比开头"] += 1
            if any(kw in title for kw in ['终于', '成功', '实现', '达到']):
                patterns["结果展示"] += 1
            if any(kw in title for kw in ['别再', '不要', '避坑', '踩雷']):
                patterns["痛点开头"] += 1
        
        sorted_patterns = sorted(patterns.items(), key=lambda x: x[1], reverse=True)
        return [p[0] for p in sorted_patterns if p[1] > 0][:5]
    
    def _contains_emoji(self, text: str) -> bool:
        """检测文本是否包含emoji"""
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF"
            "\U00002702-\U000027B0"
            "]+",
            flags=re.UNICODE
        )
        return bool(emoji_pattern.search(text))
    
    def generate_calibration_hints(self, calibration_data: CalibrationData) -> List[str]:
        """根据校准数据生成提示"""
        hints = []
        
        if calibration_data.avg_title_length < 12:
            hints.append(f"该话题热门内容的标题偏短（平均{calibration_data.avg_title_length:.0f}字），简洁标题更受欢迎")
        elif calibration_data.avg_title_length > 18:
            hints.append(f"该话题热门内容的标题偏长（平均{calibration_data.avg_title_length:.0f}字），详细标题转化更好")
        
        if calibration_data.common_opening_patterns:
            patterns = calibration_data.common_opening_patterns[:3]
            hints.append(f"该话题热门标题常用结构：{', '.join(patterns)}")
        
        if calibration_data.emoji_usage_rate > 0.5:
            hints.append(f"该话题{int(calibration_data.emoji_usage_rate*100)}%的热门内容使用了emoji")
        
        if calibration_data.common_tags:
            hints.append(f"热门标签参考：{', '.join(calibration_data.common_tags[:5])}")
        
        if calibration_data.sample_count > 0:
            hints.append(f"以上分析基于{calibration_data.sample_count}条热门内容样本")
        
        return hints

    def _extract_note_title(self, sample: Dict[str, Any]) -> str:
        note_card = sample.get("noteCard", {}) if isinstance(sample, dict) else {}
        return sample.get("title") or note_card.get("displayTitle") or note_card.get("title") or ""

    def _extract_note_body(self, sample: Dict[str, Any]) -> str:
        note_card = sample.get("noteCard", {}) if isinstance(sample, dict) else {}
        return (
            note_card.get("desc")
            or note_card.get("description")
            or sample.get("desc")
            or sample.get("content")
            or ""
        )

    def _extract_inline_tags(self, text: str) -> List[str]:
        if not text:
            return []

        tags: List[str] = []
        for match in re.findall(r"[#\uFF03]([^\s#\uFF03,，。！？!?:：；;、/]{2,20})", text):
            cleaned = str(match).strip()
            if cleaned:
                tags.append(cleaned)
        return tags

    def _extract_note_tags(self, sample: Dict[str, Any]) -> List[str]:
        tags: List[str] = []
        note_card = sample.get("noteCard", {}) if isinstance(sample, dict) else {}
        for raw in [sample.get("tags"), note_card.get("tagList"), note_card.get("tags")]:
            if not isinstance(raw, list):
                continue
            for item in raw:
                if isinstance(item, str):
                    tags.append(item.strip())
                elif isinstance(item, dict):
                    name = item.get("name") or item.get("tagName") or item.get("text")
                    if name:
                        tags.append(str(name).strip())

        tags.extend(self._extract_inline_tags(self._extract_note_title(sample)))
        tags.extend(self._extract_inline_tags(self._extract_note_body(sample)))

        deduped: List[str] = []
        normalized_seen = set()
        for tag in tags:
            normalized = self._normalize_tag(tag)
            if normalized and normalized not in normalized_seen:
                normalized_seen.add(normalized)
                deduped.append(str(tag).strip())
        return deduped

    def _normalize_tag(self, tag: str) -> str:
        if not tag:
            return ""
        normalized = str(tag).strip().lower()
        normalized = normalized.replace("#", "").replace("?", "")
        normalized = re.sub(r"\s+", "", normalized)
        return normalized

    def _match_tags(self, content_tags: List[str], sample_tags: List[str]) -> List[str]:
        if not content_tags or not sample_tags:
            return []

        normalized_sample_tags = {
            self._normalize_tag(tag): tag for tag in sample_tags if self._normalize_tag(tag)
        }
        matched: List[str] = []
        for raw_tag in content_tags:
            normalized_tag = self._normalize_tag(raw_tag)
            if not normalized_tag:
                continue
            for sample_normalized, sample_raw in normalized_sample_tags.items():
                if (
                    normalized_tag == sample_normalized
                    or normalized_tag in sample_normalized
                    or sample_normalized in normalized_tag
                ):
                    matched.append(sample_raw)
                    break

        deduped: List[str] = []
        for tag in matched:
            if tag not in deduped:
                deduped.append(tag)
        return deduped

    def _match_terms(self, content_terms: List[str], sample_terms: List[str]) -> List[str]:
        if not content_terms or not sample_terms:
            return []

        normalized_sample_terms = {
            self._normalize_tag(term): term for term in sample_terms if self._normalize_tag(term)
        }
        matched: List[str] = []
        for raw_term in content_terms:
            normalized_term = self._normalize_tag(raw_term)
            if not normalized_term:
                continue
            for sample_normalized, sample_raw in normalized_sample_terms.items():
                if (
                    normalized_term == sample_normalized
                    or normalized_term in sample_normalized
                    or sample_normalized in normalized_term
                ):
                    matched.append(sample_raw)
                    break

        deduped: List[str] = []
        for term in matched:
            if term not in deduped:
                deduped.append(term)
        return deduped

    def _extract_keywords(self, text: str) -> List[str]:
        if not text:
            return []

        tokens: List[str] = []
        tokens.extend(self._extract_inline_tags(text))
        for chunk in re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", text.lower()):
            if len(chunk) < 2:
                continue
            if re.fullmatch(r"[a-z0-9]+", chunk):
                tokens.append(chunk)
                continue
            if re.fullmatch(r"[\u4e00-\u9fff]+", chunk):
                if len(chunk) <= 16:
                    tokens.append(chunk)
                else:
                    parts = re.split(r"[\u7684\u4e86\u548c\u4e0e\u53ca\u5c31\u90fd\u53c8\u8fd8\u5f88\u4e5f\u628a\u88ab\u8ba9\u7ed9\u5728\u53bb\u7528\u5c06\u8981\u60f3\u4f1a\u80fd\u5e76\u6216]", chunk)
                    cleaned_parts = [part.strip() for part in parts if 2 <= len(part.strip()) <= 16]
                    if cleaned_parts:
                        tokens.extend(cleaned_parts)
                    else:
                        tokens.append(chunk[:16])
                continue
            tokens.append(chunk)

        deduped: List[str] = []
        for token in tokens:
            token = str(token).strip()
            if len(token) < 2:
                continue
            if token not in deduped:
                deduped.append(token)
        return deduped[:60]

    def _matches_pattern(self, title: str, pattern: str) -> bool:
        if not title or not pattern:
            return False
        if "数字" in pattern:
            return bool(re.match(r"^[0-9一二三四五六七八九十]+", title))
        if "问题" in pattern:
            return "?" in title or "？" in title or "吗" in title[:10]
        if "感叹" in pattern:
            return "!" in title or "！" in title
        if "对比" in pattern:
            return "vs" in title.lower() or "对比" in title or "还是" in title
        if "结果" in pattern:
            return any(word in title for word in ["终于", "成功", "实现", "达到"])
        if "痛点" in pattern:
            return any(word in title for word in ["别再", "不要", "避坑", "踩雷"])
        return False

    def _parse_count(self, value: Any) -> int:
        if isinstance(value, (int, float)):
            return int(value)
        if not isinstance(value, str):
            return 0

        text = value.strip().lower().replace(",", "")
        if not text:
            return 0
        try:
            if "万" in text:
                return int(float(text.replace("万", "")) * 10000)
            if text.endswith("w"):
                return int(float(text[:-1]) * 10000)
            if text.endswith("k"):
                return int(float(text[:-1]) * 1000)
            return int(float(text))
        except Exception:
            return 0

    def _extract_interact_metrics(self, sample: Dict[str, Any]) -> Dict[str, int]:
        note_card = sample.get("noteCard", {}) if isinstance(sample, dict) else {}
        interact = sample.get("interactInfo") or note_card.get("interactInfo") or {}
        likes = self._parse_count(interact.get("likedCount", sample.get("likedCount", 0)))
        collects = self._parse_count(interact.get("collectedCount", sample.get("collectedCount", 0)))
        comments = self._parse_count(interact.get("commentCount", sample.get("commentCount", 0)))
        shares = self._parse_count(
            interact.get("sharedCount", interact.get("shareCount", sample.get("shareCount", sample.get("sharedCount", 0))))
        )
        return {
            "likes": likes,
            "collects": collects,
            "comments": comments,
            "shares": shares,
        }

    def _score_sample_relevance(
        self,
        content: ContentItem,
        content_keywords: set[str],
        sample: Dict[str, Any],
        common_patterns: List[str],
    ) -> tuple[float, Dict[str, Any]]:
        title = self._extract_note_title(sample)
        body = self._extract_note_body(sample)
        tags = self._extract_note_tags(sample)
        sample_keywords = set(self._extract_keywords(" ".join([title, body, " ".join(tags)])))
        keyword_overlap = content_keywords & sample_keywords
        matched_tags = self._match_tags(content.tags or [], tags)
        pattern_match = any(
            self._matches_pattern(content.title, pattern) and self._matches_pattern(title, pattern)
            for pattern in common_patterns[:3]
        )
        practical_match = any(mark in content.body for mark in ["1.", "2.", "3.", "姝ラ", "娓呭崟", "鎬荤粨", "寤鸿"]) and any(
            mark in body for mark in ["1.", "2.", "3.", "姝ラ", "娓呭崟", "鎬荤粨", "寤鸿"]
        )

        score = len(keyword_overlap) * 3.0 + len(matched_tags) * 4.0
        if pattern_match:
            score += 3.0
        if practical_match:
            score += 2.0

        return score, {
            "sample": sample,
            "metrics": self._extract_interact_metrics(sample),
            "keyword_overlap": keyword_overlap,
            "matched_tags": matched_tags,
        }

    def evaluate_content_with_samples(
        self,
        content: ContentItem,
        samples: List[Dict[str, Any]],
        topic: str = "",
        source_keywords: Optional[List[str]] = None,
        goals: Optional[List[OptimizationGoal]] = None,
    ) -> MCPEvidenceSignal:
        """Build an evidence score from MCP samples instead of relying only on LLM judgement."""
        keywords = [kw for kw in (source_keywords or []) if kw]
        goal_values = [goal.value if isinstance(goal, OptimizationGoal) else str(goal) for goal in (goals or [])]
        if not samples:
            return MCPEvidenceSignal(
                score=0.0,
                content_fit_score=0.0,
                engagement_reference_score=0.0,
                goal_alignment_score=0.0,
                sample_count=0,
                reasons=["未拿到可用的小红书样本，当前只保留模型模拟结果。"],
                source_keywords=keywords or ([topic] if topic else []),
            )

        titles = [self._extract_note_title(sample) for sample in samples if self._extract_note_title(sample)]
        avg_title_length = sum(len(title) for title in titles) / len(titles) if titles else 15.0
        common_patterns = self._analyze_opening_patterns(titles) if titles else []
        emoji_usage_rate = (
            sum(1 for title in titles if self._contains_emoji(title)) / len(titles)
            if titles else 0.5
        )
        common_tags = [
            tag for tag, _ in Counter(
                tag
                for sample in samples
                for tag in self._extract_note_tags(sample)
            ).most_common(10)
        ]

        sample_keywords = Counter()
        for sample in samples:
            merged = " ".join(
                [
                    self._extract_note_title(sample),
                    self._extract_note_body(sample),
                    " ".join(self._extract_note_tags(sample)),
                ]
            )
            sample_keywords.update(self._extract_keywords(merged))

        content_keyword_list = self._extract_keywords(" ".join([content.title, content.body, " ".join(content.tags or [])]))
        content_keywords = set(content_keyword_list)
        hot_keywords = [word for word, _ in sample_keywords.most_common(20)]
        provided_keyword_list = self._extract_keywords(" ".join(keywords))
        matched_keywords = self._match_terms(content_keyword_list, hot_keywords + provided_keyword_list)
        matched_tags = self._match_tags(content.tags or [], common_tags)

        scored_samples = [
            self._score_sample_relevance(content, content_keywords, sample, common_patterns)
            for sample in samples
        ]
        scored_samples.sort(key=lambda item: item[0], reverse=True)
        relevant_sample_infos = [info for score, info in scored_samples if score > 0]
        if not relevant_sample_infos:
            fallback_count = min(max(3, len(samples) // 3), len(scored_samples))
            relevant_sample_infos = [info for _, info in scored_samples[:fallback_count]]
        keyword_counter = Counter()
        tag_counter = Counter()
        for info in relevant_sample_infos:
            keyword_counter.update(info.get("keyword_overlap", []))
            tag_counter.update(info.get("matched_tags", []))
        if keyword_counter:
            matched_keywords = [keyword for keyword, _ in keyword_counter.most_common(10)]
        if tag_counter:
            matched_tags = [tag for tag, _ in tag_counter.most_common(10)]
        relevant_metrics = [info["metrics"] for info in relevant_sample_infos]

        title_gap = abs(len(content.title) - avg_title_length)
        title_score = max(0.0, 22.0 - min(title_gap, 22.0))
        pattern_hit = any(self._matches_pattern(content.title, pattern) for pattern in common_patterns[:3])
        pattern_score = 15.0 if pattern_hit else 0.0
        emoji_score = 8.0 if self._contains_emoji(content.title) == (emoji_usage_rate >= 0.45) else 3.0
        tag_score = min(20.0, len(matched_tags) * 7.0)
        keyword_score = min(25.0, len(matched_keywords) * 4.0)
        practical_hit = any(mark in content.body for mark in ["1.", "2.", "3.", "步骤", "清单", "总结", "建议"])
        practical_score = 10.0 if practical_hit else 4.0
        content_fit_score = round(
            min(100.0, title_score + pattern_score + emoji_score + tag_score + keyword_score + practical_score),
            1,
        )

        avg_likes = round(sum(item["likes"] for item in relevant_metrics) / len(relevant_metrics), 1)
        avg_collects = round(sum(item["collects"] for item in relevant_metrics) / len(relevant_metrics), 1)
        avg_comments = round(sum(item["comments"] for item in relevant_metrics) / len(relevant_metrics), 1)
        avg_shares = round(sum(item["shares"] for item in relevant_metrics) / len(relevant_metrics), 1)
        top_sample_metrics = {
            "likes": float(max((item["likes"] for item in relevant_metrics), default=0)),
            "collects": float(max((item["collects"] for item in relevant_metrics), default=0)),
            "comments": float(max((item["comments"] for item in relevant_metrics), default=0)),
            "shares": float(max((item["shares"] for item in relevant_metrics), default=0)),
        }

        high_performance_samples = []
        for info in relevant_sample_infos:
            sample = info["sample"]
            metrics = info["metrics"]
            total = metrics["likes"] + metrics["collects"] * 1.2 + metrics["comments"] * 1.5 + metrics["shares"] * 1.8
            high_performance_samples.append((sample, metrics, total))
        high_performance_samples.sort(key=lambda item: item[2], reverse=True)
        top_samples = high_performance_samples[: max(3, min(8, len(high_performance_samples) // 2 or 1))]

        top_keyword_counter = Counter()
        top_tag_counter = Counter()
        top_pattern_hits = 0
        top_practical_hits = 0
        for sample, _, _ in top_samples:
            merged = " ".join(
                [
                    self._extract_note_title(sample),
                    self._extract_note_body(sample),
                    " ".join(self._extract_note_tags(sample)),
                ]
            )
            top_keyword_counter.update(self._extract_keywords(merged))
            top_tag_counter.update(self._extract_note_tags(sample))
            if any(self._matches_pattern(self._extract_note_title(sample), pattern) for pattern in common_patterns[:3]):
                top_pattern_hits += 1
            if any(mark in self._extract_note_body(sample) for mark in ["1.", "2.", "3.", "步骤", "清单", "总结", "建议"]):
                top_practical_hits += 1

        top_keywords = {word for word, _ in top_keyword_counter.most_common(20)}
        top_tags = {tag for tag, _ in top_tag_counter.most_common(10)}
        high_perf_keyword_hits = len(content_keywords & top_keywords)
        high_perf_tag_hits = len(self._match_tags(content.tags or [], list(top_tags)))
        engagement_reference_score = round(
            min(
                100.0,
                high_perf_keyword_hits * 6.0
                + high_perf_tag_hits * 8.0
                + (12.0 if pattern_hit and top_pattern_hits > 0 else 4.0)
                + (12.0 if practical_hit and top_practical_hits > 0 else 4.0),
            ),
            1,
        )

        goal_alignment_score = 0.0
        if goal_values:
            goal_score_map = {
                "maximize_like": min(35.0, high_perf_keyword_hits * 6.0 + (10.0 if pattern_hit else 0.0)),
                "maximize_save": min(35.0, high_perf_tag_hits * 8.0 + (12.0 if practical_hit else 0.0)),
                "maximize_comment": min(35.0, high_perf_keyword_hits * 4.0 + (12.0 if "?" in content.title or "为什么" in content.title or "你会" in content.title else 0.0)),
                "maximize_share": min(35.0, high_perf_tag_hits * 5.0 + (12.0 if practical_hit or "避坑" in content.title or "清单" in content.title else 0.0)),
            }
            goal_alignment_score = round(
                sum(goal_score_map.get(goal, 0.0) for goal in goal_values) / max(len(goal_values), 1),
                1,
            )

        weighted_total = content_fit_score * 0.45 + engagement_reference_score * 0.30
        weight_sum = 0.75
        if goal_values:
            weighted_total += goal_alignment_score * 0.25
            weight_sum += 0.25
        total_score = round(min(100.0, weighted_total / max(weight_sum, 1e-6)), 1)

        reasons: List[str] = []
        if matched_tags:
            reasons.append("标签表达与热门样本存在重合。")
        if engagement_reference_score >= 70:
            reasons.append("内容特征与高互动样本较接近。")
        elif engagement_reference_score <= 35:
            reasons.append("内容特征与高互动样本仍有明显差距。")
        return MCPEvidenceSignal(
            score=total_score,
            content_fit_score=content_fit_score,
            engagement_reference_score=engagement_reference_score,
            goal_alignment_score=goal_alignment_score,
            sample_count=len(relevant_sample_infos),
            source_sample_count=len(samples),
            matched_keywords=matched_keywords[:10],
            matched_tags=matched_tags[:10],
            avg_likes=avg_likes,
            avg_collects=avg_collects,
            avg_comments=avg_comments,
            avg_shares=avg_shares,
            top_sample_metrics=top_sample_metrics,
            reasons=reasons[:5],
            source_keywords=keywords or ([topic] if topic else []),
        )
    
    async def publish_content(self, content) -> Dict[str, Any]:
        """发布内容到小红书
        
        Args:
            content: ContentItem对象，包含title, body, cover_image, tags等
        
        Returns:
            发布结果字典
        """
        temp_files = []  # 记录临时文件，发布后清理
        
        try:
            # 检查必需的图片参数
            if not content.cover_image:
                return {
                    "success": False,
                    "error": "发布失败：小红书图文内容必须包含至少1张图片"
                }
            
            # 处理图片
            image_path = content.cover_image
            
            # 1. 处理 base64 图片（前端上传的本地文件）
            if image_path.startswith("data:image"):
                print(f"[发布] 检测到base64图片，保存到本地...")
                try:
                    import base64
                    # 解析 data URL: data:image/png;base64,xxxxx
                    header, data = image_path.split(",", 1)
                    # 获取图片格式
                    if "png" in header:
                        ext = ".png"
                    elif "gif" in header:
                        ext = ".gif"
                    elif "webp" in header:
                        ext = ".webp"
                    else:
                        ext = ".jpg"
                    
                    # 解码并保存
                    image_data = base64.b64decode(data)
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                    temp_file.write(image_data)
                    temp_file.close()
                    temp_files.append(temp_file.name)
                    image_path = temp_file.name
                    print(f"[发布] base64图片已保存到: {image_path}")
                except Exception as e:
                    print(f"[发布] base64图片处理失败: {e}")
                    return {
                        "success": False,
                        "error": f"图片处理失败: {str(e)}"
                    }
            
            # 2. 处理 URL 图片（需要下载）
            elif image_path.startswith("http"):
                print(f"[发布] 检测到图片URL，下载到本地: {image_path[:60]}...")
                try:
                    # 下载图片到临时文件
                    async with httpx.AsyncClient(timeout=30.0) as download_client:
                        # 添加Referer头绕过防盗链
                        headers = {
                            "Referer": "https://www.xiaohongshu.com/",
                            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                        }
                        resp = await download_client.get(image_path, headers=headers, follow_redirects=True)
                        if resp.status_code == 200:
                            # 确定文件扩展名
                            content_type = resp.headers.get("content-type", "")
                            if "png" in content_type:
                                ext = ".png"
                            elif "gif" in content_type:
                                ext = ".gif"
                            elif "webp" in content_type:
                                ext = ".webp"
                            else:
                                ext = ".jpg"
                            
                            # 保存到临时文件
                            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                            temp_file.write(resp.content)
                            temp_file.close()
                            temp_files.append(temp_file.name)
                            image_path = temp_file.name
                            print(f"[发布] 图片已下载到: {image_path}")
                        else:
                            print(f"[发布] 图片下载失败: HTTP {resp.status_code}")
                            return {
                                "success": False,
                                "error": f"图片下载失败: HTTP {resp.status_code}"
                            }
                except Exception as e:
                    print(f"[发布] 图片下载异常: {e}")
                    return {
                        "success": False,
                        "error": f"图片下载失败: {str(e)}"
                    }
            
            # 3. 本地文件路径 - 检查文件是否存在
            elif not os.path.exists(image_path):
                return {
                    "success": False,
                    "error": f"图片文件不存在: {image_path}"
                }
            
            # 准备发布参数 - 使用本地图片路径
            publish_args = {
                "title": content.title,
                "content": content.body,
                "images": [image_path],  # 使用本地路径
            }
            
            # 添加标签（可选）
            if content.tags:
                publish_args["tags"] = content.tags
            
            print(f"[发布] 参数: title={content.title}, images={publish_args['images']}, tags={content.tags}")
            
            # 调用MCP发布工具
            result = await self._call_tool("publish_content", publish_args)
            
            print(f"[发布] MCP返回结果: {result}")  # 调试日志
            
            # 解析结果 - 判断是否发布成功
            is_success = False
            text_result = ""
            
            if result and "content" in result:
                content_list = result.get("content", [])
                if content_list and len(content_list) > 0:
                    text_result = content_list[0].get("text", "")
                    print(f"[发布] 解析文本结果: {text_result}")
                    
                    # 判断是否成功（检查关键词）
                    is_success = any(keyword in text_result.lower() for keyword in [
                        "success", "成功", "发布成功", "已发布", "published"
                    ])
            
            # 如果没有content但也没有error，也认为成功
            if not is_success and result and isinstance(result, dict):
                has_error = any(key in str(result).lower() for key in ["error", "错误", "失败", "fail"])
                if not has_error:
                    is_success = True
            
            if not is_success:
                return {
                    "success": False,
                    "error": text_result or "发布失败，未获取到有效响应",
                    "data": result
                }
            
            # 发布成功，尝试通过搜索获取 noteId
            note_id = None
            xsec_token = None
            
            print(f"[发布] 发布成功，等待2秒后搜索获取noteId...")
            import asyncio
            await asyncio.sleep(2)  # 等待小红书索引
            
            # 用标题关键词搜索
            search_keyword = content.title[:8]  # 取前8个字符
            try:
                search_result = await self._call_tool("search_feeds", {"keyword": search_keyword})
                print(f"[发布] 搜索结果: {search_result}")
                
                if search_result and "content" in search_result:
                    search_text = search_result.get("content", [{}])[0].get("text", "")
                    try:
                        search_data = json.loads(search_text) if search_text else {}
                        feeds = search_data.get("feeds", []) if isinstance(search_data, dict) else search_data if isinstance(search_data, list) else []
                        
                        # 找标题匹配的笔记
                        for feed in feeds:
                            note_card = feed.get("noteCard", {})
                            feed_title = note_card.get("displayTitle", "") or note_card.get("title", "")
                            
                            # 检查标题是否匹配（前10个字符）
                            if feed_title and content.title[:10] in feed_title or feed_title[:10] in content.title:
                                note_id = feed.get("id") or note_card.get("noteId")
                                xsec_token = feed.get("xsecToken") or feed.get("xsec_token")
                                print(f"[发布] 找到匹配笔记: noteId={note_id}, xsec_token={xsec_token}")
                                break
                    except json.JSONDecodeError:
                        print(f"[发布] 搜索结果JSON解析失败")
            except Exception as e:
                print(f"[发布] 搜索noteId失败: {e}")
            
            return {
                "success": True,
                "note_id": note_id,
                "xsec_token": xsec_token,
                "message": "发布成功",
                "data": result
            }
            
        except Exception as e:
            print(f"发布失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            # 清理临时文件
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                        print(f"[发布] 已清理临时文件: {temp_file}")
                except Exception as e:
                    print(f"[发布] 清理临时文件失败: {e}")
    
    async def close(self):
        """关闭连接"""
        await self._client.aclose()
