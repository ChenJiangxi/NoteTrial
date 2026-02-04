"""
真实数据校准器 - RealDataCalibrator

功能：
1. 获取真实爆款数据：调用 MCP 获取小红书热门笔记
2. 分析成功模式：标题模式、开头模式、Emoji风格、长度偏好、标签
3. 生成校准提示：返回 JSON 格式的校准结果
4. 构建校准 Prompt：将校准数据注入到生成 prompt 中

集成 MCP 服务，使用 async 异步
"""

import re
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional
from collections import Counter
from dataclasses import dataclass, field

from .mcp_service import MCPService, MCPClient
from .xhs_calibrator import XiaohongshuCalibrator

logger = logging.getLogger(__name__)


@dataclass
class CalibrationResult:
    """
    校准结果数据类
    
    Attributes:
        title_patterns: 标题模式列表（数字型、对比型、问句型等）
        opening_patterns: 开头模式列表（痛点共鸣、结果先行、揭秘吸引等）
        emoji_style: Emoji使用风格列表
        avg_title_length: 平均标题长度
        success_factors: 成功因素列表（口语化、短句、干货多等）
        sample_count: 样本数量
        topic: 分析的话题
    """
    title_patterns: List[str] = field(default_factory=list)
    opening_patterns: List[str] = field(default_factory=list)
    emoji_style: List[str] = field(default_factory=list)
    avg_title_length: float = 0.0
    success_factors: List[str] = field(default_factory=list)
    sample_count: int = 0
    topic: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "title_patterns": self.title_patterns,
            "opening_patterns": self.opening_patterns,
            "emoji_style": self.emoji_style,
            "avg_title_length": self.avg_title_length,
            "success_factors": self.success_factors,
            "sample_count": self.sample_count,
            "topic": self.topic
        }
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class RealDataCalibrator:
    """
    真实数据校准器
    
    通过 MCP 获取小红书热门笔记数据，分析成功模式，
    生成可注入到 prompt 的校准信息，帮助生成更符合平台规律的内容。
    
    Usage:
        calibrator = RealDataCalibrator()
        result = await calibrator.calibrate("护肤")
        prompt = calibrator.build_calibrated_prompt(result, base_prompt)
    """
    
    # 标题模式正则匹配规则
    TITLE_PATTERNS = {
        "数字型": r"^[0-9０-９一二三四五六七八九十百千万]+[\s\·\-\：\:\.]",
        "对比型": r"(vs|VS|对比|还是|和|与|相比| versus)",
        "问句型": r"[？?]|吗\??$|怎么|如何|为什么",
        "感叹型": r"[！!]|绝了|太|真的|太绝了",
        "揭秘型": r"(揭秘|揭秘|真相|内幕|背后的|终于)",
        "干货型": r"(教程|攻略|指南|方法|技巧|步骤)",
        "清单型": r"(清单|列表|合集|大全|Top|NO\.|排名)",
        "痛点型": r"(别再|不要|避坑|踩雷|后悔|毁脸|烂脸)"
    }
    
    # 开头模式关键词
    OPENING_PATTERNS = {
        "痛点共鸣": ["别再", "不要再", "你是不是", "你是不是也", "很多人", "是不是"],
        "结果先行": ["终于", "成功", "实现了", "达到了", "真的", "太绝了"],
        "揭秘吸引": ["揭秘", "真相", "内幕", "背后的", "竟然", "原来"],
        "数字冲击": ["1", "2", "3", "100", "1000", "99"],
        "问句引导": ["你知道吗", "有没有", "想不想", "要不要"],
        "场景代入": ["每次", "今天", "周末", "逛街", "在家"]
    }
    
    # 常见成功因素关键词
    SUCCESS_FACTOR_KEYWORDS = {
        "口语化": ["我", "真的", "太", "绝了", "姐妹", "姐妹们", "姐妹们", "我先", "我来说"],
        "短句": lambda text: len(text) < 30,
        "干货多": ["干货", "教程", "步骤", "方法", "技巧", "攻略", "指南"],
        "实用性强": ["收藏", "保存", "用到", "跟着", "学会"],
        "情感共鸣": ["真的", "太难了", "崩溃", "哭了", "爱了"],
        "视觉冲击": ["图", "图片", "前后", "对比图", "效果图"]
    }
    
    # 常见 Emoji
    COMMON_EMOJIS = [
        "✨", "💄", "⚠️", "🔥", "💢", "✅", "❌", 
        "👉", "👈", "👍", "👎", "❤️", "💔", 
        "💡", "📌", "📍", "💯", "💪", "🙌",
        "😭", "😍", "🤔", "🙈", "🙉", "🙊",
        "💃", "🕺", "👀", "🤷", "🤦", "🤷‍♀️"
    ]
    
    def __init__(self, db_session=None, mcp_url: str = None):
        """
        初始化校准器
        
        Args:
            db_session: 数据库会话（可选，用于 MCPService）
            mcp_url: MCP 服务 URL（可选，用于 XiaohongshuCalibrator）
        """
        self.db_session = db_session
        self.mcp_url = mcp_url
        
        # 优先使用 XiaohongshuCalibrator（功能更完整）
        self._calibrator = XiaohongshuCalibrator(mcp_url)
        self._mcp_client: Optional[MCPClient] = None
        
        if db_session:
            self._mcp_service = MCPService(db_session)
        else:
            self._mcp_service = None
    
    async def initialize(self) -> bool:
        """初始化 MCP 连接"""
        return await self._calibrator.check_mcp_status()
    
    async def close(self):
        """关闭连接"""
        if self._calibrator:
            await self._calibrator.close()
        if self._mcp_service:
            await self._mcp_service.close()
    
    # ==================== 获取真实数据 ====================
    
    async def fetch_trending_notes(
        self, 
        topic: str, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取小红书热门笔记数据
        
        通过 MCP 搜索指定话题的热门内容，返回笔记列表。
        
        Args:
            topic: 搜索话题关键词
            limit: 获取数量限制（默认50条）
            
        Returns:
            笔记数据列表，每条包含标题、正文、互动数据等
            
        Example:
            >>> notes = await calibrator.fetch_trending_notes("护肤", limit=30)
            >>> print(f"获取到 {len(notes)} 条热门笔记")
        """
        try:
            # 使用 XiaohongshuCalibrator 的搜索功能
            notes = await self._calibrator.search_topic_samples(topic, limit=limit)
            
            # 解析笔记数据
            parsed_notes = []
            for note in notes:
                parsed_note = self._parse_note_data(note)
                if parsed_note:
                    parsed_notes.append(parsed_note)
            
            logger.info(f"成功解析 {len(parsed_notes)} 条笔记数据")
            return parsed_notes
            
        except Exception as e:
            logger.error(f"获取热门笔记失败: {e}")
            return []
    
    def _parse_note_data(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        解析原始笔记数据
        
        从 MCP 返回的原始数据中提取关键字段。
        
        Args:
            raw_data: MCP 返回的原始数据
            
        Returns:
            解析后的笔记数据，解析失败返回 None
        """
        try:
            # 尝试多种数据结构
            note_card = raw_data.get("noteCard", raw_data)
            
            # 提取标题
            title = (
                note_card.get("displayTitle") or 
                note_card.get("title") or 
                raw_data.get("title") or
                ""
            )
            
            # 提取正文（如果有）
            desc = (
                note_card.get("desc") or
                raw_data.get("desc") or
                raw_data.get("content") or
                ""
            )
            
            # 提取互动数据
            interact_info = note_card.get("interactInfo", {}) or raw_data.get("interactInfo", {})
            
            return {
                "title": title,
                "content": desc,
                "likes": interact_info.get("likedCount", 0) or raw_data.get("like_count", 0),
                "collects": interact_info.get("collectCount", 0) or raw_data.get("collect_count", 0),
                "comments": interact_info.get("commentCount", 0) or raw_data.get("comment_count", 0),
                "tags": note_card.get("tags", []) or raw_data.get("tags", []),
                "cover": note_card.get("cover", {}),
                "time": raw_data.get("time", "")
            }
            
        except Exception as e:
            logger.warning(f"解析笔记数据失败: {e}")
            return None
    
    # ==================== 分析成功模式 ====================
    
    def analyze_title_patterns(self, titles: List[str]) -> List[str]:
        """
        分析标题模式
        
        识别标题中的常见模式类型，返回按出现频率排序的模式列表。
        
        Args:
            titles: 标题列表
            
        Returns:
            模式类型排序）
            
       列表（按频率 Example:
            >>> patterns = analyzer.analyze_title_patterns([
            ...     "3步学会护肤",
            ...     "大牌vs平价"
            ... ])
            >>> print(patterns)  # ['数字型', '对比型']
        """
        if not titles:
            return []
        
        pattern_counts = Counter()
        
        for title in titles:
            if not title:
                continue
            
            # 检查每种模式
            for pattern_name, pattern_regex in self.TITLE_PATTERNS.items():
                if re.search(pattern_regex, title):
                    pattern_counts[pattern_name] += 1
        
        # 按频率排序，返回前5个
        sorted_patterns = [
            pattern for pattern, count 
            in pattern_counts.most_common(5)
        ]
        
        return sorted_patterns
    
    def analyze_opening_patterns(self, titles: List[str]) -> List[str]:
        """
        分析开头模式
        
        识别标题开头的吸引模式类型。
        
        Args:
            titles: 标题列表
            
        Returns:
            开头模式列表
        """
        if not titles:
            return []
        
        opening_counts = Counter()
        
        for title in titles:
            if not title:
                continue
            
            # 检查每种开头模式
            for pattern_name, keywords in self.OPENING_PATTERNS.items():
                for keyword in keywords:
                    if title.startswith(keyword) or keyword in title[:15]:
                        opening_counts[pattern_name] += 1
                        break
        
        # 按频率排序，返回前5个
        sorted_patterns = [
            pattern for pattern, count 
            in opening_counts.most_common(5)
        ]
        
        return sorted_patterns
    
    def analyze_emoji_style(self, texts: List[str]) -> List[str]:
        """
        分析 Emoji 使用风格
        
        识别文本中常用的 Emoji，返回按频率排序的列表。
        
        Args:
            texts: 文本列表（标题或正文）
            
        Returns:
            常用 Emoji 列表
            
        Example:
            >>> emojis = analyzer.analyze_emoji_style([
            ...     "✨护肤干货✨",
            ...     "💄新手必看💄"
            ... ])
            >>> print(emojis)  # ['✨', '💄']
        """
        if not texts:
            return []
        
        # 检测文本中的所有 Emoji
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # 笑脸
            "\U0001F300-\U0001F5FF"  # 符号和图案
            "\U0001F680-\U0001F6FF"  # 交通和地图
            "\U0001F1E0-\U0001F1FF"  # 国旗
            "\U00002702-\U000027B0"  # 符号
            "\U000024C2-\U0001F251"  # 圆形符号
            "\U0001F900-\U0001F9FF"  # 补充符号
            "\U0001FA00-\U0001FA6F"  # 国际象棋符号
            "\U00002600-\U000026FF"  # 杂项符号
            "]+",
            flags=re.UNICODE
        )
        
        all_emojis = []
        for text in texts:
            found_emojis = emoji_pattern.findall(text)
            all_emojis.extend(found_emojis)
        
        # 统计频率，返回前10个
        emoji_counts = Counter(all_emojis)
        top_emojis = [emoji for emoji, count in emoji_counts.most_common(10)]
        
        # 如果没有检测到 Emoji，返回常见美妆/生活方式类 Emoji
        if not top_emojis:
            return self.COMMON_EMOJIS[:5]
        
        return top_emojis
    
    def analyze_length_preference(self, titles: List[str]) -> float:
        """
        分析长度偏好
        
        计算标题的平均长度。
        
        Args:
            titles: 标题列表
            
        Returns:
            平均标题长度（字符数）
        """
        if not titles:
            return 0.0
        
        total_length = sum(len(title) for title in titles)
        return total_length / len(titles)
    
    def analyze_success_factors(self, notes: List[Dict[str, Any]]) -> List[str]:
        """
        分析成功因素
        
        根据笔记的互动数据（点赞、收藏、评论）分析成功因素。
        
        Args:
            notes: 笔记列表
            
        Returns:
            成功因素列表
        """
        if not notes:
            return []
        
        # 计算互动指标
        total_likes = sum(note.get("likes", 0) for note in notes)
        total_collects = sum(note.get("collects", 0) for note in notes)
        total_comments = sum(note.get("comments", 0) for note in notes)
        
        # 计算收藏率（收藏/点赞）和互动率
        avg_collect_rate = total_collects / total_likes if total_likes > 0 else 0
        
        factors = []
        
        # 分析互动特征
        if avg_collect_rate > 0.5:
            factors.append("收藏价值高")
        if total_comments > 0:
            factors.append("互动性强")
        
        # 分析内容特征
        titles_text = " ".join(note.get("title", "") for note in notes)
        
        for factor, keywords in self.SUCCESS_FACTOR_KEYWORDS.items():
            if factor == "短句":
                # 短句通过平均长度判断
                avg_len = self.analyze_length_preference(
                    [note.get("title", "") for note in notes]
                )
                if avg_len < 25:
                    factors.append(factor)
            elif callable(keywords):
                if keywords(titles_text):
                    factors.append(factor)
            else:
                if any(kw in titles_text for kw in keywords):
                    factors.append(factor)
        
        # 常见成功因素
        if len(factors) < 3:
            factors.extend(["口语化", "实用性强", "视觉吸引"])
        
        return list(set(factors))[:8]
    
    def analyze_tags(self, notes: List[Dict[str, Any]]) -> List[str]:
        """
        分析标签使用
        
        统计笔记中最常用的标签。
        
        Args:
            notes: 笔记列表
            
        Returns:
            常用标签列表
        """
        if not notes:
            return []
        
        all_tags = []
        for note in notes:
            tags = note.get("tags", [])
            if isinstance(tags, list):
                all_tags.extend(tags)
        
        # 按频率排序，返回前10个
        tag_counts = Counter(all_tags)
        top_tags = [tag for tag, count in tag_counts.most_common(10)]
        
        return top_tags
    
    # ==================== 校准主流程 ====================
    
    async def calibrate(
        self, 
        topic: str, 
        sample_size: int = 50
    ) -> CalibrationResult:
        """
        执行校准分析
        
        获取热门笔记数据，分析成功模式，生成校准结果。
        
        Args:
            topic: 话题关键词
            sample_size: 样本数量
            
        Returns:
            CalibrationResult 校准结果对象
            
        Example:
            >>> result = await calibrator.calibrate("护肤", sample_size=30)
            >>> print(result.to_json())
        """
        logger.info(f"开始校准分析: topic={topic}, sample_size={sample_size}")
        
        # 1. 获取真实爆款数据
        notes = await self.fetch_trending_notes(topic, limit=sample_size)
        
        if not notes:
            logger.warning(f"未获取到 {topic} 的热门数据，使用空数据")
            return CalibrationResult(
                topic=topic,
                sample_count=0,
                title_patterns=["数字型", "干货型"],
                opening_patterns=["痛点共鸣", "结果先行"],
                emoji_style=["✨", "💄", "🔥"],
                avg_title_length=15.0,
                success_factors=["口语化", "实用性强", "干货多"]
            )
        
        logger.info(f"获取到 {len(notes)} 条笔记数据")
        
        # 2. 提取标题列表
        titles = [note.get("title", "") for note in notes if note.get("title")]
        
        # 3. 分析各维度
        title_patterns = self.analyze_title_patterns(titles)
        opening_patterns = self.analyze_opening_patterns(titles)
        emoji_style = self.analyze_emoji_style(titles)
        avg_title_length = self.analyze_length_preference(titles)
        success_factors = self.analyze_success_factors(notes)
        tags = self.analyze_tags(notes)
        
        # 4. 构建校准结果
        result = CalibrationResult(
            topic=topic,
            sample_count=len(notes),
            title_patterns=title_patterns,
            opening_patterns=opening_patterns,
            emoji_style=emoji_style,
            avg_title_length=round(avg_title_length, 1),
            success_factors=success_factors
        )
        
        logger.info(f"校准完成: {result.sample_count} 条样本, {len(title_patterns)} 种标题模式")
        
        return result
    
    # ==================== 构建校准 Prompt ====================
    
    def build_calibrated_prompt(
        self, 
        calibration: CalibrationResult, 
        base_prompt: str,
        include_examples: bool = True
    ) -> str:
        """
        构建校准后的 Prompt
        
        将校准数据注入到生成 prompt 中，生成符合平台规律的内容。
        
        Args:
            calibration: 校准结果
            base_prompt: 基础 prompt 模板
            include_examples: 是否包含示例
            
        Returns:
            校准后的完整 prompt
            
        Example:
            >>> result = await calibrator.calibrate("护肤")
            >>> prompt = calibrator.build_calibrated_prompt(
            ...     result,
            ...     "请帮我写一篇小红书笔记"
            ... )
        """
        # 构建校准提示
        calibration_hint = self._generate_calibration_hint(calibration)
        
        # 注入到基础 prompt
        calibrated_prompt = f"""【小红书内容校准】

{base_prompt}

{calibration_hint}

【写作要求】
1. 标题控制在 {int(calibration.avg_title_length)} 字左右
2. 开头使用痛点共鸣或结果先行的吸引模式
3. 标题使用 {"、".join(calibration.title_patterns[:3])} 等模式
4. 适当使用 Emoji 增强视觉效果
5. 保持口语化、干货多的风格
6. 内容实用性强，便于收藏
"""
        
        return calibrated_prompt
    
    def _generate_calibration_hint(self, calibration: CalibrationResult) -> str:
        """
        生成校准提示文本
        
        将校准结果转换为可读性高的提示文本。
        """
        lines = ["【平台规律分析】", ""]
        
        # 标题模式
        if calibration.title_patterns:
            lines.append(f"📝 热门标题模式: {', '.join(calibration.title_patterns[:3])}")
        
        # 开头模式
        if calibration.opening_patterns:
            lines.append(f"🎣 吸引开头方式: {', '.join(calibration.opening_patterns[:3])}")
        
        # Emoji 风格
        if calibration.emoji_style:
            lines.append(f"😊 常用 Emoji: {''.join(calibration.emoji_style[:5])}")
        
        # 长度
        if calibration.avg_title_length > 0:
            lines.append(f"📏 平均标题长度: {calibration.avg_title_length:.1f} 字")
        
        # 成功因素
        if calibration.success_factors:
            lines.append(f"✨ 成功关键因素: {', '.join(calibration.success_factors[:4])}")
        
        # 样本数
        lines.append(f"📊 分析样本数: {calibration.sample_count} 条")
        
        return "\n".join(lines)
    
    # ==================== 工具方法 ====================
    
    def generate_calibration_json(self, calibration: CalibrationResult) -> str:
        """
        生成校准 JSON 字符串
        
        返回符合输出示例格式的 JSON。
        
        Returns:
            JSON 字符串
            
        Example Output:
            {
                "title_patterns": ["数字+结果", "对比", "问句"],
                "opening_patterns": ["痛点共鸣", "结果先行", "揭秘吸引"],
                "emoji_style": ["✨", "💄", "⚠️"],
                "avg_title_length": 14,
                "success_factors": ["口语化", "短句", "干货多"]
            }
        """
        output = {
            "title_patterns": calibration.title_patterns,
            "opening_patterns": calibration.opening_patterns,
            "emoji_style": calibration.emoji_style[:5] if calibration.emoji_style else [],
            "avg_title_length": int(calibration.avg_title_length),
            "success_factors": calibration.success_factors[:5] if calibration.success_factors else []
        }
        
        return json.dumps(output, ensure_ascii=False, indent=2)
    
    async def batch_calibrate(
        self, 
        topics: List[str], 
        sample_size: int = 30
    ) -> Dict[str, CalibrationResult]:
        """
        批量校准多个话题
        
        并发处理多个话题的校准分析。
        
        Args:
            topics: 话题列表
            sample_size: 每个话题的样本数量
            
        Returns:
            话题到校准结果的映射字典
            
        Example:
            >>> results = await calibrator.batch_calibrate(
            ...     ["护肤", "穿搭", "美食"],
            ...     sample_size=20
            ... )
            >>> for topic, result in results.items():
            ...     print(f"{topic}: {result.sample_count} samples")
        """
        tasks = [
            self.calibrate(topic, sample_size)
            for topic in topics
        ]
        
        results = await asyncio.gather(*tasks)
        
        return dict(zip(topics, results))


# ==================== 便捷函数 ====================

async def quick_calibrate(
    topic: str, 
    sample_size: int = 50
) -> CalibrationResult:
    """
    快速校准（便捷函数）
    
    无需初始化，直接创建校准器并执行校准。
    
    Args:
        topic: 话题关键词
        sample_size: 样本数量
        
    Returns:
        校准结果
        
    Example:
        >>> result = await quick_calibrate("护肤")
        >>> print(result.to_json())
    """
    calibrator = RealDataCalibrator()
    
    try:
        await calibrator.initialize()
        return await calibrator.calibrate(topic, sample_size)
    finally:
        await calibrator.close()


if __name__ == "__main__":
    # 测试代码
    async def test():
        print("=" * 50)
        print("RealDataCalibrator 测试")
        print("=" * 50)
        
        # 初始化
        calibrator = RealDataCalibrator()
        initialized = await calibrator.initialize()
        print(f"MCP 初始化: {'成功' if initialized else '失败'}")
        
        if not initialized:
            print("MCP 服务不可用，跳过测试")
            return
        
        # 执行校准
        print("\n正在获取热门笔记数据...")
        result = await calibrator.calibrate("护肤", sample_size=20)
        
        # 输出结果
        print("\n" + "=" * 50)
        print("校准结果:")
        print("=" * 50)
        print(f"话题: {result.topic}")
        print(f"样本数: {result.sample_count}")
        print(f"标题模式: {result.title_patterns}")
        print(f"开头模式: {result.opening_patterns}")
        print(f"Emoji风格: {result.emoji_style}")
        print(f"平均标题长度: {result.avg_title_length}")
        print(f"成功因素: {result.success_factors}")
        
        print("\n" + "=" * 50)
        print("JSON 输出:")
        print("=" * 50)
        print(calibrator.generate_calibration_json(result))
        
        print("\n" + "=" * 50)
        print("校准 Prompt 示例:")
        print("=" * 50)
        prompt = calibrator.build_calibrated_prompt(
            result,
            "请帮我写一篇关于护肤的小红书笔记，介绍新手入门方法"
        )
        print(prompt)
        
        await calibrator.close()
        print("\n测试完成")
    
    # 运行测试
    asyncio.run(test())
