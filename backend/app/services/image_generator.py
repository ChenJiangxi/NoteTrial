"""
NoteTrial Backend - 图片生成服务
使用 OpenRouter + google/gemini-3.1-flash-image-preview 生成小红书风格图片
"""
import base64
import httpx
import json
import re
from typing import Optional, List
from ..config import get_settings

settings = get_settings()


class ImageGenerator:
    """AI 图片生成器 - 通过 OpenRouter 调用 Gemini 3.1 Flash Image Preview"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.openai_api_key  # OpenRouter key
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = "google/gemini-3.1-flash-image-preview"
        self._client = httpx.AsyncClient(timeout=180.0)
    
    async def generate_image(
        self,
        prompt: str,
        style: str = "小红书风格",
        aspect_ratio: str = "1:1"
    ) -> Optional[str]:
        """生成图片"""
        if not self.api_key:
            print("[ImageGenerator] 未配置 OpenRouter API Key")
            return None
        
        enhanced_prompt = self._build_prompt(prompt, style)
        
        try:
            url = f"{self.base_url}/chat/completions"
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": enhanced_prompt
                    }
                ],
                "modalities": ["image", "text"],  # 关键：必须指定输出包含图片
                "temperature": 0.8,
                "max_tokens": 8192
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://notetrial.app",
                "X-Title": "NoteTrial"
            }
            
            print(f"[ImageGenerator] 正在调用 {self.model} ...")
            response = await self._client.post(url, json=payload, headers=headers)
            print(f"[ImageGenerator] 响应状态: {response.status_code}")
            
            if response.status_code != 200:
                print(f"[ImageGenerator] 错误响应: {response.text[:500]}")
                return None
            
            result = response.json()
            
            # 提取图片
            image_data = self._extract_image(result)
            
            if image_data:
                print("[ImageGenerator] ✅ 图片生成成功")
                return image_data
            else:
                resp_str = json.dumps(result, ensure_ascii=False)[:2000]
                print(f"[ImageGenerator] ❌ 未能提取图片，响应: {resp_str}")
                return None
            
        except Exception as e:
            print(f"[ImageGenerator] 图片生成失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _extract_image(self, result: dict) -> Optional[str]:
        """从 OpenRouter 响应中提取图片"""
        try:
            choices = result.get("choices", [])
            if not choices:
                return None
            
            message = choices[0].get("message", {})
            
            # OpenRouter gemini-3.1-flash-image-preview 返回格式：message.images 数组
            images = message.get("images", [])
            if images:
                for img in images:
                    if isinstance(img, dict):
                        # 格式: {"image_url": {"url": "data:image/..."}} 或 {"image_url": "data:image/..."}
                        image_url = img.get("image_url")
                        if isinstance(image_url, dict):
                            url = image_url.get("url")
                            if url:
                                return url
                        elif isinstance(image_url, str):
                            return image_url
            
            content = message.get("content")
            
            # content 是字符串 - 可能含 base64 或 markdown 图片
            if isinstance(content, str) and content.strip():
                # markdown 图片: ![...](data:image/...)
                match = re.search(r'!\[.*?\]\((data:image/[^)]+)\)', content)
                if match:
                    return match.group(1)
                
                # 直接 data URL
                if content.strip().startswith('data:image/'):
                    return content.strip()
                
                # 裸 base64
                b64 = re.search(r'([A-Za-z0-9+/]{200,}={0,2})', content)
                if b64:
                    data = b64.group(1)
                    if data.startswith('iVBORw0KGgo'):
                        return f"data:image/png;base64,{data}"
                    elif data.startswith('/9j/'):
                        return f"data:image/jpeg;base64,{data}"
            
            # content 是列表（多模态响应）
            if isinstance(content, list):
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    # image_url 格式
                    if "image_url" in part:
                        url = part["image_url"]
                        return url.get("url") if isinstance(url, dict) else url
                    # inline_data 格式
                    if "inline_data" in part:
                        d = part["inline_data"]
                        data = d.get("data")
                        mime = d.get("mime_type", "image/png")
                        if data:
                            return f"data:{mime};base64,{data}"
            
            # 递归搜索
            return self._find_image_recursive(result)
            
        except Exception as e:
            print(f"[ImageGenerator] 解析响应失败: {e}")
            return None
    
    def _find_image_recursive(self, obj, depth=0) -> Optional[str]:
        """递归搜索图片数据"""
        if depth > 10:
            return None
        if isinstance(obj, dict):
            if "data" in obj:
                data = obj["data"]
                if isinstance(data, str) and len(data) > 200:
                    if data.startswith('iVBORw0KGgo'):
                        return f"data:image/png;base64,{data}"
                    elif data.startswith('/9j/'):
                        return f"data:image/jpeg;base64,{data}"
            for v in obj.values():
                r = self._find_image_recursive(v, depth + 1)
                if r:
                    return r
        elif isinstance(obj, list):
            for item in obj:
                r = self._find_image_recursive(item, depth + 1)
                if r:
                    return r
        return None
    
    def _build_prompt(self, prompt: str, style: str) -> str:
        """构建图片生成提示词"""
        style_desc = {
            "小红书风格": "小红书风格插画，粉色/渐变背景，温馨可爱，带装饰元素",
            "清新自然": "清新自然风格，简洁干净，柔和色调",
            "精致ins风": "Instagram 风格，时尚精致，高级感",
            "文艺复古": "复古文艺风格，怀旧色调，艺术感",
            "简约现代": "极简现代风格，干净留白，高端感"
        }.get(style, "小红书风格插画")
        
        return f"""Generate a beautiful image for Chinese social media (Xiaohongshu/小红书).

Style: {style_desc}
Content: {prompt}

Design requirements:
1. Include clear, readable Chinese text/title prominently displayed
2. Warm and inviting color palette (pink, pastel gradients)
3. Professional layout with cute decorative elements
4. High quality, visually appealing, suitable for social media posting
5. The image should look like a well-designed infographic or card

Generate the image now."""
    
    async def generate_cover_for_content(
        self,
        title: str,
        body: str,
        topic: str
    ) -> Optional[str]:
        """根据内容自动生成封面图"""
        prompt = f"标题：{title}\n话题：{topic}\n内容：{body[:80]}"
        return await self.generate_image(prompt)
    
    async def generate_with_reference(
        self,
        prompt: str,
        reference_image: str,
        page_type: str = "content",
        full_outline: str = ""
    ) -> Optional[str]:
        """
        生成与参考图片风格一致的图片（RedInk 封面优先策略）
        
        Args:
            prompt: 当前页内容
            reference_image: 封面图片 base64 data URL
            page_type: 页面类型 (cover/content/summary)
            full_outline: 完整大纲用于上下文
        """
        if not self.api_key:
            return None
        
        # 构建多模态消息
        messages = []
        
        # 如果有参考图，先传入参考图
        if reference_image and reference_image.startswith("data:image"):
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": reference_image}
                    },
                    {
                        "type": "text",
                        "text": self._build_reference_prompt(prompt, page_type, full_outline)
                    }
                ]
            })
        else:
            # 无参考图，直接生成
            messages.append({
                "role": "user",
                "content": self._build_prompt(prompt, "小红书风格")
            })
        
        try:
            response = await self._client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": messages,
                    "modalities": ["image", "text"],
                    "temperature": 0.8,
                    "max_tokens": 8192
                },
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://notetrial.app",
                    "X-Title": "NoteTrial"
                }
            )
            
            if response.status_code != 200:
                print(f"[ImageGenerator] 带参考图生成失败: {response.status_code}")
                return None
            
            result = response.json()
            return self._extract_image(result)
            
        except Exception as e:
            print(f"[ImageGenerator] 带参考图生成异常: {e}")
            return None
    
    def _build_reference_prompt(self, prompt: str, page_type: str, full_outline: str) -> str:
        """构建带参考图的提示词"""
        type_instructions = {
            "cover": "这是封面页，标题要大且醒目，有视觉冲击力",
            "content": "这是内容页，信息层次分明，要点清晰",
            "summary": "这是总结页，总结性文字突出，有行动号召"
        }.get(page_type, "内容页")
        
        return f"""请参考上面这张图片的视觉风格（配色、排版、字体、装饰元素），生成一张风格一致的新图片。

页面内容：
{prompt}

页面类型：{type_instructions}

重要要求：
1. 必须保持与参考图相同的视觉风格和设计语言
2. 配色方案要与参考图协调一致
3. 排版和装饰元素的风格要统一
4. 文字清晰可读，使用中文
5. 竖版 3:4 比例

{f"完整内容大纲参考：{full_outline[:500]}" if full_outline else ""}

Generate the image now."""
    
    async def generate_batch(
        self,
        pages: List[dict],
        user_topic: str = "",
        full_outline: str = ""
    ) -> List[dict]:
        """
        批量生成多页图片（封面优先策略）
        
        Args:
            pages: 页面列表 [{"index": 0, "type": "cover", "content": "..."}, ...]
            user_topic: 用户原始主题
            full_outline: 完整大纲
        
        Returns:
            更新后的页面列表，每个页面包含 "image" 字段
        """
        import asyncio
        
        results = list(pages)  # 复制列表
        cover_image = None
        
        # 第一步：找到并生成封面
        cover_idx = next((i for i, p in enumerate(results) if p.get("type") == "cover"), 0)
        cover_page = results[cover_idx]
        
        print(f"[ImageGenerator] 开始批量生成 {len(pages)} 页图片...")
        print(f"[ImageGenerator] 第1步：生成封面...")
        
        cover_prompt = f"{user_topic}\n\n{cover_page.get('content', '')}"
        cover_image = await self.generate_image(cover_prompt, "小红书风格")
        
        if cover_image:
            results[cover_idx] = {**cover_page, "image": cover_image, "status": "done"}
            print(f"[ImageGenerator] ✅ 封面生成成功")
        else:
            results[cover_idx] = {**cover_page, "status": "error", "error": "封面生成失败"}
            print(f"[ImageGenerator] ❌ 封面生成失败")
        
        # 第二步：生成其他页面（使用封面作为参考）
        other_pages = [(i, p) for i, p in enumerate(results) if i != cover_idx]
        
        print(f"[ImageGenerator] 第2步：生成 {len(other_pages)} 个内容页...")
        
        for idx, page in other_pages:
            page_content = page.get("content", f"内容页 {idx}")
            page_type = page.get("type", "content")
            
            print(f"[ImageGenerator] 生成第 {idx + 1} 页 ({page_type})...")
            
            if cover_image:
                # 使用参考图生成
                image = await self.generate_with_reference(
                    prompt=page_content,
                    reference_image=cover_image,
                    page_type=page_type,
                    full_outline=full_outline
                )
            else:
                # 无参考图，直接生成
                image = await self.generate_image(page_content, "小红书风格")
            
            if image:
                results[idx] = {**page, "image": image, "status": "done"}
                print(f"[ImageGenerator] ✅ 第 {idx + 1} 页生成成功")
            else:
                results[idx] = {**page, "status": "error", "error": f"第 {idx + 1} 页生成失败"}
                print(f"[ImageGenerator] ❌ 第 {idx + 1} 页生成失败")
            
            # 添加小延迟避免 API 限流
            await asyncio.sleep(0.5)
        
        success_count = sum(1 for p in results if p.get("status") == "done")
        print(f"[ImageGenerator] 批量生成完成: {success_count}/{len(pages)} 成功")
        
        return results
    
    async def close(self):
        """关闭连接"""
        await self._client.aclose()
