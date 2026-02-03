"""
NoteTrial Backend - 图片生成服务
使用 Gemini API 生成原创图片
"""
import base64
import httpx
import json
from typing import Optional, List
from ..config import get_settings

settings = get_settings()


class ImageGenerator:
    """AI 图片生成器"""
    
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
        
        # 构建优化的提示词
        enhanced_prompt = self._enhance_prompt(prompt, style)
        
        try:
            # 使用 Gemini 的 imagen 模型生成图片
            url = f"{self.base_url}/models/imagen-3.0-generate-002:predict"
            
            payload = {
                "instances": [
                    {"prompt": enhanced_prompt}
                ],
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
                    # 获取 base64 图片数据
                    image_data = predictions[0].get("bytesBase64Encoded")
                    if image_data:
                        return f"data:image/png;base64,{image_data}"
            
            # 如果 imagen 不可用，尝试使用 Gemini 2.0 Flash 的图片生成
            return await self._generate_with_gemini_flash(enhanced_prompt)
            
        except Exception as e:
            print(f"[ImageGenerator] 图片生成失败: {e}")
            return await self._generate_with_gemini_flash(enhanced_prompt)
    
    async def _generate_with_gemini_flash(self, prompt: str) -> Optional[str]:
        """使用 Gemini 2.5 Flash Image 生成图片"""
        try:
            # 使用 gemini-2.5-flash-image 模型（经测试可用）
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
            print(f"[ImageGenerator] Gemini 响应状态: {response.status_code}")
            
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
                                print("[ImageGenerator] 图片生成成功")
                                return f"data:{mime_type};base64,{data}"
            else:
                # 打印错误详情便于调试
                print(f"[ImageGenerator] 错误响应: {response.text[:500]}")
            
            return None
            
        except Exception as e:
            print(f"[ImageGenerator] Gemini 生成失败: {e}")
            return None
    
    def _enhance_prompt(self, prompt: str, style: str) -> str:
        """优化提示词，使生成的图片更适合小红书"""
        style_hints = {
            "小红书风格": "aesthetic, soft lighting, lifestyle photography style, Instagram worthy, clean composition, warm tones",
            "清新自然": "natural lighting, fresh and clean, minimal style, soft colors, peaceful atmosphere",
            "精致ins风": "Instagram aesthetic, high quality, professional photography, beautiful composition, trending style",
            "文艺复古": "vintage aesthetic, film photography style, warm nostalgic tones, artistic",
            "简约现代": "minimalist, modern design, clean lines, contemporary style, elegant"
        }
        
        style_suffix = style_hints.get(style, style_hints["小红书风格"])
        
        # 构建完整提示词 - 强调不要包含任何文字
        full_prompt = f"{prompt}, {style_suffix}, high quality, detailed, visually appealing, NO TEXT, NO WORDS, NO LETTERS, NO WATERMARKS, NO CAPTIONS, pure visual image only"
        
        return full_prompt
    
    async def generate_cover_for_content(
        self,
        title: str,
        body: str,
        topic: str
    ) -> Optional[str]:
        """根据内容自动生成封面图"""
        # 从内容中提取关键视觉元素
        prompt = self._extract_visual_prompt(title, body, topic)
        return await self.generate_image(prompt)
    
    def _extract_visual_prompt(self, title: str, body: str, topic: str) -> str:
        """从文本内容提取视觉提示词"""
        # 简单的关键词提取
        visual_keywords = []
        
        # 根据话题添加基础元素
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
        
        # 添加标题中的关键元素
        visual_keywords.append(title[:30])
        
        return ", ".join(visual_keywords)
    
    async def close(self):
        """关闭连接"""
        await self._client.aclose()
