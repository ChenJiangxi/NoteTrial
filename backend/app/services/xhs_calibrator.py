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

from ..models import CalibrationData, ContentItem, MCPEvidenceSignal
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
        return [tag for tag in tags if tag]

    def _extract_keywords(self, text: str) -> List[str]:
        if not text:
            return []

        tokens: List[str] = []
        for chunk in re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", text.lower()):
            if len(chunk) < 2:
                continue
            if re.fullmatch(r"[a-z0-9]+", chunk):
                tokens.append(chunk)
                continue
            if re.fullmatch(r"[\u4e00-\u9fff]+", chunk):
                if len(chunk) <= 4:
                    tokens.append(chunk)
                else:
                    for width in (2, 3, 4):
                        for i in range(0, len(chunk) - width + 1):
                            tokens.append(chunk[i:i + width])
                continue
            tokens.append(chunk)

        deduped: List[str] = []
        for token in tokens:
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

    def evaluate_content_with_samples(
        self,
        content: ContentItem,
        samples: List[Dict[str, Any]],
        topic: str = "",
        source_keywords: Optional[List[str]] = None,
    ) -> MCPEvidenceSignal:
        """Build an evidence score from MCP samples instead of relying only on LLM judgement."""
        keywords = [kw for kw in (source_keywords or []) if kw]
        if not samples:
            return MCPEvidenceSignal(
                score=0.0,
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

        content_keywords = set(
            self._extract_keywords(" ".join([content.title, content.body, " ".join(content.tags or [])]))
        )
        hot_keywords = [word for word, _ in sample_keywords.most_common(20)]
        hot_keyword_set = set(hot_keywords)
        provided_keyword_set = set(self._extract_keywords(" ".join(keywords)))
        matched_keywords = sorted((content_keywords & hot_keyword_set) | (content_keywords & provided_keyword_set))
        matched_tags = sorted(set(content.tags or []) & set(common_tags))

        title_gap = abs(len(content.title) - avg_title_length)
        title_score = max(0.0, 22.0 - min(title_gap, 22.0))
        pattern_score = 15.0 if any(self._matches_pattern(content.title, pattern) for pattern in common_patterns[:3]) else 0.0
        emoji_score = 8.0 if self._contains_emoji(content.title) == (emoji_usage_rate >= 0.45) else 3.0
        tag_score = min(20.0, len(matched_tags) * 7.0)
        keyword_score = min(25.0, len(matched_keywords) * 4.0)
        practical_score = 10.0 if any(mark in content.body for mark in ["1.", "2.", "3.", "步骤", "清单", "总结", "建议"]) else 4.0

        reasons: List[str] = [f"MCP 对比了 {len(samples)} 条小红书样本。"]
        if matched_keywords:
            reasons.append(f"命中热门关键词：{', '.join(matched_keywords[:5])}")
        if matched_tags:
            reasons.append(f"命中热门标签：{', '.join(matched_tags[:5])}")
        if any(self._matches_pattern(content.title, pattern) for pattern in common_patterns[:3]):
            reasons.append("标题结构贴近热门样本常见开头。")
        else:
            reasons.append("标题结构与热门样本仍有差距。")
        if title_gap <= 3:
            reasons.append("标题长度接近热门样本均值。")

        total_score = round(
            min(100.0, title_score + pattern_score + emoji_score + tag_score + keyword_score + practical_score),
            1,
        )

        return MCPEvidenceSignal(
            score=total_score,
            sample_count=len(samples),
            matched_keywords=matched_keywords[:10],
            matched_tags=matched_tags[:10],
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
