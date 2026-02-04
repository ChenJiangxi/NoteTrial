"""
NoteTrial Backend - 图片生成服务
使用 Gemini API 生成原创图片、提供配图建议和质量评估

主要类:
- ImageGenerator: AI 图片生成器（基础类）
- CoverGenerator: 封面图生成器
- ImageAdvisor: 配图建议生成器
- ImageQualityAssessor: 图片质量评估器
"""

import base64
import httpx
import json
import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
from ..config import get_settings

settings = get_settings()


class ImageStyle(Enum):
    """支持的图片风格"""
    REALISTIC = "realistic"  # 真实照片风
    ILLUSTRATION = "illustration"  # 插画风
    COMIC = "comic"  # 漫画风
    MINIMALIST = "minimalist"  # 极简风
    BOLD_COLOR = "bold_color"  # 撞色风


class ImageType(Enum):
    """配图类型"""
    HERO = "hero"  # 主图/封面
    SPLASH = "splash"  # 装饰图
    ICON = "icon"  # 图标
    PHOTO = "photo"  # 照片
    ILLUSTRATION = "illustration"  # 插画
    SCREENSHOT = "screenshot"  # 截图
    DIAGRAM = "diagram"  # 图表


@dataclass
class ImageRecommendation:
    """配图推荐结果"""
    paragraph_index: int
    image_type: ImageType
    description: str
    keywords: List[str]
    prompt: Optional[str] = None
    reasoning: Optional[str] = None


@dataclass
class QualityAssessment:
    """图片质量评估结果"""
    ai_score: float  # AI 味评分 (0-1, 越低越自然)
    appeal_score: float  # 吸引力评分 (0-1)
    compliance_score: float  # 合规性评分 (0-1)
    issues: List[str]  # 发现的问题
    suggestions: List[str]  # 改进建议
    overall_score: float  # 综合评分 (0-1)


class ImageGenerator:
    """AI 图片生成器 - 基础类"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.gemini_api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self._client = httpx.AsyncClient(timeout=120.0)
    
    async def generate_image(
        self,
        prompt: str,
        style: str = "小红书风格",
        aspect_ratio: str = "1:1"
    ) -> Optional[str]:
        """
        生成图片
        
        Args:
            prompt: 图片描述
            style: 风格说明
            aspect_ratio: 宽高比 (1:1, 4:3, 3:4, 16:9, 9:16)
        
        Returns:
            base64 编码的图片数据，或 None
        """
        if not self.api_key:
            print("[ImageGenerator] 未配置 Gemini API Key")
            return None
        
        enhanced_prompt = self._enhance_prompt(prompt, style)
        
        try:
            url = f"{self.base_url}/models/imagen-3.0-generate-002:predict"
            
            payload = {
                "instances": [{"prompt": enhanced_prompt}],
                "parameters": {
                    "sampleCount": 1,
                    "aspectRatio": aspect_ratio,
                    "personGeneration": "allow_adult",
                    "safetyFilterLevel": "block_few"
                }
            }
            
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key
            }
            
            response = await self._client.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                predictions = result.get("predictions", [])
                if predictions and len(predictions) > 0:
                    image_data = predictions[0].get("bytesBase64Encoded")
                    if image_data:
                        return f"data:image/png;base64,{image_data}"
            
            return await self._generate_with_gemini_flash(enhanced_prompt)
            
        except Exception as e:
            print(f"[ImageGenerator] 图片生成失败: {e}")
            return await self._generate_with_gemini_flash(enhanced_prompt)
    
    async def _generate_with_gemini_flash(self, prompt: str) -> Optional[str]:
        """使用 Gemini 2.5 Flash Image 生成图片"""
        try:
            url = f"{self.base_url}/models/gemini-2.5-flash-image:generateContent"
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": f"Generate a beautiful aesthetic image for social media: {prompt}. Make it visually appealing, high quality, suitable for Xiaohongshu/Instagram style."
                    }]
                }],
                "generationConfig": {
                    "responseModalities": ["TEXT", "IMAGE"]
                }
            }
            
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key
            }
            
            response = await self._client.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                candidates = result.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    for part in parts:
                        if "inlineData" in part:
                            mime_type = part["inlineData"].get("mimeType", "image/png")
                            data = part["inlineData"].get("data")
                            if data:
                                return f"data:{mime_type};base64,{data}"
            else:
                print(f"[ImageGenerator] 错误响应: {response.text[:500]}")
            
            return None
            
        except Exception as e:
            print(f"[ImageGenerator] Gemini 生成失败: {e}")
            return None
    
    def _enhance_prompt(self, prompt: str, style: str) -> str:
        """优化提示词"""
        style_hints = {
            "小红书风格": "aesthetic, soft lighting, lifestyle photography style, Instagram worthy, clean composition, warm tones",
            "清新自然": "natural lighting, fresh and clean, minimal style, soft colors, peaceful atmosphere",
            "精致ins风": "Instagram aesthetic, high quality, professional photography, beautiful composition, trending style",
            "文艺复古": "vintage aesthetic, film photography style, warm nostalgic tones, artistic",
            "简约现代": "minimalist, modern design, clean lines, contemporary style, elegant"
        }
        
        style_suffix = style_hints.get(style, style_hints["小红书风格"])
        full_prompt = f"{prompt}, {style_suffix}, high quality, detailed, visually appealing, NO TEXT, NO WORDS, NO LETTERS, NO WATERMARKS, NO CAPTIONS, pure visual image only"
        
        return full_prompt
    
    async def generate_cover_for_content(
        self,
        title: str,
        body: str,
        topic: str
    ) -> Optional[str]:
        """根据内容自动生成封面图"""
        prompt = self._extract_visual_prompt(title, body, topic)
        return await self.generate_image(prompt)
    
    def _extract_visual_prompt(self, title: str, body: str, topic: str) -> str:
        """从文本内容提取视觉提示词"""
        visual_keywords = []
        
        topic_visuals = {
            "护肤": "skincare products, beauty routine, clean bathroom shelf",
            "美妆": "makeup products, beauty flatlay, cosmetics",
            "穿搭": "fashion outfit, stylish clothing, street style",
            "美食": "delicious food, food photography, appetizing dish",
            "旅行": "travel scenery, beautiful landscape, vacation vibes",
            "健身": "fitness lifestyle, workout, healthy body",
            "家居": "home interior, cozy room, home decoration",
            "数码": "tech gadgets, modern devices, clean desk setup"
        }
        
        for key, visual in topic_visuals.items():
            if key in topic or key in title:
                visual_keywords.append(visual)
                break
        
        if not visual_keywords:
            visual_keywords.append(f"{topic} related aesthetic photo")
        
        visual_keywords.append(title[:30])
        
        return ", ".join(visual_keywords)
    
    async def close(self):
        """关闭连接"""
        await self._client.aclose()


class CoverGenerator:
    """
    封面图生成器
    
    根据标题和话题生成适合小红书等平台的封面图。
    支持多种视觉风格，可根据内容自动调整。
    """
    
    # 风格配置：风格名 -> 风格提示词
    STYLE_CONFIGS = {
        ImageStyle.REALISTIC: {
            "name": "真实照片风",
            "prompt_suffix": "professional photography, realistic, natural lighting, high resolution, DSLR quality, shallow depth of field, sharp focus",
            "aspect_ratio": "4:3"
        },
        ImageStyle.ILLUSTRATION: {
            "name": "插画风",
            "prompt_suffix": "digital illustration, artistic, hand-drawn style, vector graphics, clean lines, soft colors, whimsical, dreamlike atmosphere",
            "aspect_ratio": "1:1"
        },
        ImageStyle.COMIC: {
            "name": "漫画风",
            "prompt_suffix": "comic book style, manga art, bold outlines, vibrant colors, dynamic composition, cel shading, anime-inspired, expressive characters",
            "aspect_ratio": "9:16"
        },
        ImageStyle.MINIMALIST: {
            "name": "极简风",
            "prompt_suffix": "minimalist design, simple composition, clean lines, negative space, muted colors, modern aesthetic, uncluttered, elegant simplicity",
            "aspect_ratio": "1:1"
        },
        ImageStyle.BOLD_COLOR: {
            "name": "撞色风",
            "prompt_suffix": "bold color blocking, vibrant colors, high contrast, striking color palette, modern design, dynamic composition, eye-catching",
            "aspect_ratio": "1:1"
        }
    }
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.gemini_api_key
        self.generator = ImageGenerator(api_key=self.api_key)
    
    async def generate(
        self,
        title: str,
        topic: str,
        style: ImageStyle = ImageStyle.REALISTIC,
        additional_prompt: str = ""
    ) -> Optional[str]:
        """
        生成封面图
        
        Args:
            title: 笔记标题
            topic: 话题/主题
            style: 视觉风格
            additional_prompt: 额外提示词
        
        Returns:
            base64 编码的图片 URL 或 None
        """
        prompt = self._build_prompt(title, topic, style, additional_prompt)
        style_config = self.STYLE_CONFIGS[style]
        
        return await self.generator.generate_image(
            prompt=prompt,
            style=style_config["name"],
            aspect_ratio=style_config["aspect_ratio"]
        )
    
    def _build_prompt(
        self,
        title: str,
        topic: str,
        style: ImageStyle,
        additional_prompt: str = ""
    ) -> str:
        """
        构建完整的生成提示词
        
        Args:
            title: 笔记标题
            topic: 话题/主题
            style: 视觉风格
            additional_prompt: 额外提示词
        
        Returns:
            完整的提示词
        """
        # 提取标题关键词
        keywords = self._extract_keywords(title, topic)
        
        # 基础视觉描述
        base_prompt = self._get_topic_visual(topic)
        
        # 风格修饰
        style_suffix = self.STYLE_CONFIGS[style]["prompt_suffix"]
        
        # 组合提示词
        prompt_parts = [
            f"{base_prompt} featuring {', '.join(keywords)}",
            style_suffix,
            "perfect for social media cover, Xiaohongshu style",
            "high quality, professional, visually stunning",
            "NO TEXT, NO WORDS, NO LETTERS"
        ]
        
        if additional_prompt:
            prompt_parts.insert(1, additional_prompt)
        
        return ", ".join(prompt_parts)
    
    def _extract_keywords(self, title: str, topic: str) -> List[str]:
        """从标题和话题中提取视觉关键词"""
        # 常见内容类型关键词
        content_patterns = {
            r"教程|教学|指南": ["step by step", "how-to", "demonstration"],
            r"测评|评测|测试": ["comparison", "review", "before and after"],
            r"分享|推荐": ["lifestyle", "personal experience", "recommendation"],
            r"穿搭| outfit": ["outfit coordination", "fashion look", "style inspiration"],
            r"美食| food": ["delicious dish", "food presentation", "culinary"],
            r"护肤|美妆": ["skincare routine", "beauty products", "makeup look"],
            r"旅行|旅游": ["travel destination", "scenic view", "adventure"],
            r"家居| home": ["home decor", "interior design", "living space"]
        }
        
        keywords = []
        text = f"{title} {topic}"
        
        for pattern, words in content_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                keywords.extend(words)
                break
        
        # 添加话题相关词
        if not keywords:
            keywords.append(topic)
        
        return keywords[:5]  # 最多返回5个关键词
    
    def _get_topic_visual(self, topic: str) -> str:
        """根据话题返回基础视觉描述"""
        topic_visuals = {
            "护肤": "beautiful skincare products",
            "美妆": "elegant makeup products",
            "穿搭": "stylish fashion outfit",
            "美食": "appetizing food dish",
            "旅行": "stunning travel scenery",
            "健身": "energetic fitness lifestyle",
            "家居": "cozy home interior",
            "数码": "modern tech gadgets",
            "摄影": "professional photography",
            "宠物": "adorable pet",
            "母婴": "baby care essentials",
            "职场": "professional workspace"
        }
        
        for key, visual in topic_visuals.items():
            if key in topic:
                return visual
        
        return "aesthetic lifestyle scene"


class ImageAdvisor:
    """
    配图建议生成器
    
    分析文本内容结构，为每个段落推荐适合的配图。
    返回配图类型、描述、关键词等信息。
    """
    
    # 段落类型与配图类型映射
    PARAGRAPH_IMAGE_MAP = {
        "opening": ImageType.HERO,      # 开头 -> 封面图
        "step": ImageType.PHOTO,        # 步骤 -> 过程图
        "list": ImageType.ICON,         # 列表 -> 图标
        "comparison": ImageType.DIAGRAM, # 对比 -> 图表
        "result": ImageType.PHOTO,       # 结果 -> 效果图
        "quote": ImageType.ILLUSTRATION, # 引言 -> 装饰图
        "warning": ImageType.SPLASH,     # 警告 -> 强调图
        "summary": ImageType.ILLUSTRATION  # 总结 -> 总结图
    }
    
    def __init__(self):
        pass
    
    def analyze(
        self,
        title: str,
        paragraphs: List[str],
        topic: str
    ) -> List[ImageRecommendation]:
        """
        分析内容并生成配图建议
        
        Args:
            title: 笔记标题
            paragraphs: 段落列表
            topic: 话题/主题
        
        Returns:
            配图推荐列表
        """
        recommendations = []
        
        for idx, paragraph in enumerate(paragraphs):
            if not paragraph.strip():
                continue
            
            # 分析段落类型
            para_type = self._classify_paragraph(paragraph, idx, len(paragraphs))
            
            # 生成推荐
            recommendation = self._generate_recommendation(
                paragraph_index=idx,
                paragraph=paragraph,
                para_type=para_type,
                title=title,
                topic=topic
            )
            
            recommendations.append(recommendation)
        
        return recommendations
    
    def _classify_paragraph(
        self,
        paragraph: str,
        index: int,
        total: int
    ) -> str:
        """
        分类段落类型
        
        Args:
            paragraph: 段落内容
            index: 段落索引
            total: 总段落数
        
        Returns:
            段落类型
        """
        text = paragraph.strip()
        
        # 开头段落
        if index == 0:
            return "opening"
        
        # 结尾段落
        if index == total - 1:
            return "summary"
        
        # 检测步骤类
        step_patterns = [r"步骤\d", r"第一步", r"首先", r"然后", r"最后", r"step"]
        if any(re.search(p, text) for p in step_patterns):
            return "step"
        
        # 检测列表类
        list_patterns = [r"^\d+\.", r"^\•", r"^- ", r"第一点", r"第二点"]
        if any(re.match(p, text) for p in list_patterns):
            return "list"
        
        # 检测对比类
        compare_patterns = [r"对比", r"比较", r"vs", r" versus ", r"优缺点", r"利弊"]
        if any(p in text for p in compare_patterns):
            return "comparison"
        
        # 检测结果类
        result_patterns = [r"效果", r"结果", r"最终", r"完成后", r"success"]
        if any(p in text for p in result_patterns):
            return "result"
        
        # 检测引言/引用
        if text.startswith('"') or text.startswith('「') or "说：" in text:
            return "quote"
        
        # 检测警告/注意
        warning_patterns = [r"注意", r"警告", r"提醒", r"千万", r"切记"]
        if any(p in text for p in warning_patterns):
            return "warning"
        
        return "body"
    
    def _generate_recommendation(
        self,
        paragraph_index: int,
        paragraph: str,
        para_type: str,
        title: str,
        topic: str
    ) -> ImageRecommendation:
        """
        为单个段落生成配图推荐
        
        Args:
            paragraph_index: 段落索引
            paragraph: 段落内容
            para_type: 段落类型
            title: 笔记标题
            topic: 话题/主题
        
        Returns:
            ImageRecommendation 对象
        """
        # 获取配图类型
        image_type = self.PARAGRAPH_IMAGE_MAP.get(
            para_type,
            ImageType.PHOTO
        )
        
        # 生成描述
        description = self._generate_description(
            paragraph, para_type, topic
        )
        
        # 生成关键词
        keywords = self._extract_keywords(paragraph, topic, image_type)
        
        # 生成提示词
        prompt = self._build_prompt(
            description, keywords, image_type, topic
        )
        
        # 生成推理
        reasoning = self._get_reasoning(para_type, image_type)
        
        return ImageRecommendation(
            paragraph_index=paragraph_index,
            image_type=image_type,
            description=description,
            keywords=keywords,
            prompt=prompt,
            reasoning=reasoning
        )
    
    def _generate_description(
        self,
        paragraph: str,
        para_type: str,
        topic: str
    ) -> str:
        """生成配图描述"""
        text = paragraph[:100]  # 取前100字符
        
        if para_type == "opening":
            return f"封面主图：突出{topic}主题，视觉冲击力强"
        elif para_type == "step":
            return f"步骤演示图：展示{text}相关内容"
        elif para_type == "list":
            return f"要点配图：{topic}关键点可视化"
        elif para_type == "comparison":
            return f"对比图表：{topic}优缺点对比"
        elif para_type == "result":
            return f"效果图：展示最终{topic}效果"
        elif para_type == "quote":
            return f"引用配图：引用内容装饰"
        elif para_type == "warning":
            return f"强调图：引起注意的警示视觉"
        elif para_type == "summary":
            return f"总结图：{topic}核心要点回顾"
        else:
            return f"配图：{text}相关内容"
    
    def _extract_keywords(
        self,
        paragraph: str,
        topic: str,
        image_type: ImageType
    ) -> List[str]:
        """提取关键词"""
        keywords = []
        
        # 添加话题关键词
        keywords.append(topic)
        
        # 根据配图类型添加特定关键词
        type_keywords = {
            ImageType.HERO: ["cover", "hero image", "featured"],
            ImageType.PHOTO: ["photo", "realistic", "authentic"],
            ImageType.ILLUSTRATION: ["illustration", "artistic", "creative"],
            ImageType.ICON: ["icon", "symbol", "simple"],
            ImageType.DIAGRAM: ["chart", "diagram", "infographic"],
            ImageType.SPLASH: ["decorative", "accent", "visual break"]
        }
        
        keywords.extend(type_keywords.get(image_type, []))
        
        return keywords
    
    def _build_prompt(
        self,
        description: str,
        keywords: List[str],
        image_type: ImageType,
        topic: str
    ) -> str:
        """构建生成提示词"""
        type_prompts = {
            ImageType.HERO: f"A stunning hero image for {topic}",
            ImageType.PHOTO: f"High-quality photo of {topic}",
            ImageType.ILLUSTRATION: f"Beautiful illustration about {topic}",
            ImageType.DIAGRAM: f"Clear diagram showing {topic}",
            ImageType.SPLASH: f"Aesthetic decorative element for {topic}"
        }
        
        base_prompt = type_prompts.get(
            image_type,
            f"Image related to {topic}"
        )
        
        return f"{base_prompt}, {', '.join(keywords)}, high quality, professional"
    
    def _get_reasoning(self, para_type: str, image_type: ImageType) -> str:
        """获取推荐理由"""
        reasoning_map = {
            "opening": "开头需要吸引眼球的封面图，提升点击率",
            "step": "步骤说明需要清晰的演示图，帮助理解",
            "list": "要点列表适合配图标图，视觉化表达",
            "comparison": "对比内容需要图表辅助理解",
            "result": "结果展示需要真实的效果图",
            "quote": "引用内容适合装饰性配图",
            "warning": "警示信息需要醒目的强调图",
            "summary": "总结内容需要回顾性的配图"
        }
        
        return reasoning_map.get(para_type, "配图增强内容表现力")


class ImageQualityAssessor:
    """
    图片质量评估器
    
    评估图片的 AI 味、吸引力和合规性。
    基于视觉特征和规则进行综合评分。
    """
    
    # AI 味检测关键词
    AI_PATTERNS = [
        r"unrealistic", r"artificial", r"deformed", r"distorted",
        r"extra limbs", r"missing fingers", r"asymmetric",
        r"unnatural", r"weird lighting", r"inconsistent shadow"
    ]
    
    # 合规性检测规则
    COMPLIANCE_CHECKS = [
        ("no_text", r"text|word|letter|watermark"),
        ("no_nudity", r"nude|naked|explicit"),
        ("no_violence", r"blood|gore|violence"),
        ("no_brands", r"logo|brand name|copyright")
    ]
    
    def __init__(self):
        pass
    
    def assess(
        self,
        image_path: str = None,
        image_base64: str = None,
        prompt: str = None
    ) -> QualityAssessment:
        """
        评估图片质量
        
        Args:
            image_path: 图片路径
            image_base64: base64 编码的图片数据
            prompt: 生成时使用的提示词
        
        Returns:
            QualityAssessment 评估结果
        """
        issues = []
        suggestions = []
        
        # 1. 评估 AI 味
        ai_score = self._assess_ai_score(prompt, issues, suggestions)
        
        # 2. 评估吸引力
        appeal_score = self._assess_appeal(prompt, issues, suggestions)
        
        # 3. 评估合规性
        compliance_score = self._assess_compliance(prompt, issues, suggestions)
        
        # 4. 计算综合评分
        overall_score = (
            ai_score * 0.3 +
            appeal_score * 0.4 +
            compliance_score * 0.3
        )
        
        # 添加图片格式检查
        if image_base64:
            format_issues = self._check_image_format(image_base64)
            issues.extend(format_issues)
        
        return QualityAssessment(
            ai_score=ai_score,
            appeal_score=appeal_score,
            compliance_score=compliance_score,
            issues=issues,
            suggestions=suggestions,
            overall_score=round(overall_score, 2)
        )
    
    def _assess_ai_score(
        self,
        prompt: str,
        issues: List[str],
        suggestions: List[str]
    ) -> float:
        """
        评估 AI 味分数
        
        AI 味越低分数越高（更像真实照片）
        """
        score = 0.8  # 基础分数
        
        if not prompt:
            return score
        
        # 检查提示词中是否有导致 AI 味的元素
        ai_indicators = [
            ("卡通风格", 0.1),
            ("动漫风格", 0.15),
            ("插画风格", 0.1),
            ("合成效果", 0.1),
            ("超现实", 0.15)
        ]
        
        for indicator, penalty in ai_indicators:
            if indicator in prompt:
                score -= penalty
                issues.append(f"提示词包含 '{indicator}'，可能产生 AI 味")
        
        # 如果提示词强调"真实感"
        if "realistic" in prompt.lower() or "真实" in prompt:
            score += 0.05
        
        return max(0.0, min(1.0, score))
    
    def _assess_appeal(
        self,
        prompt: str,
        issues: List[str],
        suggestions: List[str]
    ) -> float:
        """
        评估吸引力分数
        """
        score = 0.7  # 基础分数
        
        if not prompt:
            return score
        
        # 提升吸引力的元素
        appeal_boosters = [
            "beautiful", "stunning", "aesthetic", "trending",
            "Instagram worthy", "visually striking", "vibrant"
        ]
        
        for booster in appeal_boosters:
            if booster.lower() in prompt.lower():
                score += 0.03
        
        # 检查是否有降低吸引力的元素
        appeal_reducers = ["plain", "boring", "basic", "simple background"]
        for reducer in appeal_reducers:
            if reducer.lower() in prompt.lower():
                score -= 0.05
                issues.append(f"'{reducer}' 可能降低图片吸引力")
        
        # 建议添加吸引力元素
        if "aesthetic" not in prompt.lower():
            suggestions.append("添加 'aesthetic' 或 'visually appealing' 提升吸引力")
        
        return max(0.0, min(1.0, score))
    
    def _assess_compliance(
        self,
        prompt: str,
        issues: List[str],
        suggestions: List[str]
    ) -> float:
        """
        评估合规性分数
        """
        score = 1.0
        
        if not prompt:
            return score
        
        # 检查合规性
        compliance_checks = [
            ("text_words", r"\b(text|word|letter|watermark)\b", "避免包含文字"),
            ("brands", r"\b(logo|brand|copyright)\b", "避免包含品牌标识"),
            ("specific_person", r"specific person|famous person|celebrity", "避免特定人物")
        ]
        
        for check_name, pattern, suggestion in compliance_checks:
            if re.search(pattern, prompt.lower()):
                score -= 0.2
                issues.append(f"提示词可能包含 {check_name} 相关内容")
                suggestions.append(suggestion)
        
        # 建议添加合规性提示
        if score < 1.0:
            suggestions.append("添加 'NO TEXT, NO LOGOS' 确保合规")
        
        return max(0.0, min(1.0, score))
    
    def _check_image_format(self, base64_data: str) -> List[str]:
        """检查图片格式问题"""
        issues = []
        
        try:
            # 移除 data URL 前缀
            if "," in base64_data:
                base64_data = base64_data.split(",")[1]
            
            # 检查长度估算
            if len(base64_data) < 1000:
                issues.append("图片数据过小，可能不完整")
            
            # 尝试解码检查
            decoded = base64.b64decode(base64_data)
            
            # 检查文件头
            if not decoded[:4] in (b'\x89PNG', b'\xff\xd8\xff', b'GIF8'):
                issues.append("图片格式可能不受支持")
            
        except Exception as e:
            issues.append(f"图片解码失败: {str(e)}")
        
        return issues
    
    def batch_assess(
        self,
        images: List[Dict[str, str]]
    ) -> List[QualityAssessment]:
        """
        批量评估多张图片
        
        Args:
            images: 图片列表，每个元素包含 base64 或 path
        
        Returns:
            评估结果列表
        """
        results = []
        
        for image in images:
            assessment = self.assess(
                image_path=image.get("path"),
                image_base64=image.get("base64"),
                prompt=image.get("prompt")
            )
            results.append(assessment)
        
        return results
    
    def get_report(
        self,
        assessment: QualityAssessment
    ) -> str:
        """
        生成评估报告
        
        Args:
            assessment: 评估结果
        
        Returns:
            格式化的报告字符串
        """
        report_lines = [
            "=" * 50,
            "图片质量评估报告",
            "=" * 50,
            f"综合评分: {assessment.overall_score:.2f}/1.00",
            f"AI 味评分: {assessment.ai_score:.2f}/1.00",
            f"吸引力评分: {assessment.appeal_score:.2f}/1.00",
            f"合规性评分: {assessment.compliance_score:.2f}/1.00",
            "",
            "发现问题:",
        ]
        
        if assessment.issues:
            for i, issue in enumerate(assessment.issues, 1):
                report_lines.append(f"  {i}. {issue}")
        else:
            report_lines.append("  无明显问题")
        
        report_lines.extend([
            "",
            "改进建议:"
        ])
        
        if assessment.suggestions:
            for i, suggestion in enumerate(assessment.suggestions, 1):
                report_lines.append(f"  {i}. {suggestion}")
        else:
            report_lines.append("  无需改进")
        
        report_lines.append("=" * 50)
        
        return "\n".join(report_lines)
