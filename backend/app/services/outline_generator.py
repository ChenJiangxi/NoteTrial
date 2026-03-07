"""
NoteTrial Backend - 大纲生成服务
参考 RedInk 的多图大纲生成机制，生成带 <page> 分隔符的结构化内容
"""
import re
from typing import List, Dict, Any, Optional
import httpx
from ..config import get_settings

settings = get_settings()


class OutlineGenerator:
    """大纲生成器 - 生成多页小红书内容大纲"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.openai_api_key
        self.base_url = settings.openai_base_url or "https://openrouter.ai/api/v1"
        self.model = settings.default_model or "openai/gpt-4o"
        self._client = httpx.AsyncClient(timeout=120.0)
    
    async def generate_outline(
        self,
        topic: str,
        page_count: int = 6,
        style: str = "小红书风格"
    ) -> Dict[str, Any]:
        """
        生成多页内容大纲
        
        Args:
            topic: 用户输入的主题/需求
            page_count: 期望页数 (2-15)
            style: 风格说明
        
        Returns:
            {
                "title": "主标题",
                "pages": [
                    {"index": 0, "type": "cover", "content": "封面内容..."},
                    {"index": 1, "type": "content", "content": "第一页内容..."},
                    ...
                    {"index": n, "type": "summary", "content": "总结页..."}
                ]
            }
        """
        page_count = max(2, min(15, page_count))
        
        prompt = self._build_outline_prompt(topic, page_count, style)
        
        try:
            response = await self._client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.8,
                    "max_tokens": 4000
                },
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://notetrial.app",
                    "X-Title": "NoteTrial"
                }
            )
            
            if response.status_code != 200:
                print(f"[OutlineGenerator] API错误: {response.status_code}")
                return self._fallback_outline(topic, page_count)
            
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            if not content:
                return self._fallback_outline(topic, page_count)
            
            return self._parse_outline(content, topic)
            
        except Exception as e:
            print(f"[OutlineGenerator] 生成大纲失败: {e}")
            return self._fallback_outline(topic, page_count)
    
    def _build_outline_prompt(self, topic: str, page_count: int, style: str) -> str:
        """构建大纲生成提示词"""
        return f"""你是一个小红书内容创作专家。请为以下主题生成一个小红书图文内容大纲。

用户主题：{topic}

要求：
1. 生成 {page_count} 页内容（包含封面页和总结页）
2. 第一页必须是封面页，标注 [封面]
3. 中间页是内容页，标注 [内容]
4. 最后一页是总结页，标注 [总结]
5. 每页内容简洁有力，适合配图展示
6. 使用小红书风格的语言（亲切、有趣、emoji）
7. 文字要精炼，每页控制在50-100字

输出格式：
- 用 <page> 标签分割每一页
- 每页第一行是页面类型：[封面]、[内容] 或 [总结]
- 封面页需要: 标题、副标题、背景描述
- 内容页需要: 要点标题、主要内容、配图建议
- 总结页需要: 总结文案、行动号召

示例格式：
[封面]
标题：如何5分钟做出完美冰美式☕
副标题：新手也能轻松搞定！
背景：简约厨房场景，咖啡器具

<page>
[内容]
✨ 准备材料
需要的东西超级简单：
• 咖啡豆/咖啡粉
• 冰块
• 牛奶（可选）
配图：整齐摆放的材料特写

<page>
[总结]
恭喜你学会了！🎉
现在就去试试吧～
记得收藏+关注哦💕

现在请为「{topic}」生成大纲："""
    
    def _parse_outline(self, content: str, topic: str) -> Dict[str, Any]:
        """解析大纲内容"""
        # 用 <page> 分割
        pages_raw = re.split(r'<page>', content, flags=re.IGNORECASE)
        pages_raw = [p.strip() for p in pages_raw if p.strip()]
        
        if not pages_raw:
            return self._fallback_outline(topic, 6)
        
        pages = []
        title = topic
        
        for idx, page_content in enumerate(pages_raw):
            # 解析页面类型
            page_type = "content"
            if re.search(r'\[封面\]', page_content):
                page_type = "cover"
                # 尝试提取标题
                title_match = re.search(r'标题[：:]\s*(.+?)(?:\n|$)', page_content)
                if title_match:
                    title = title_match.group(1).strip()
            elif re.search(r'\[总结\]', page_content):
                page_type = "summary"
            
            # 清理内容
            clean_content = re.sub(r'\[(封面|内容|总结)\]', '', page_content).strip()
            
            pages.append({
                "index": idx,
                "type": page_type,
                "content": clean_content
            })
        
        return {
            "title": title,
            "pages": pages
        }
    
    def _fallback_outline(self, topic: str, page_count: int) -> Dict[str, Any]:
        """生成回退大纲（当 API 失败时）"""
        pages = [
            {"index": 0, "type": "cover", "content": f"标题：{topic}\n副标题：干货分享✨"}
        ]
        
        for i in range(1, page_count - 1):
            pages.append({
                "index": i,
                "type": "content", 
                "content": f"要点 {i}\n这里是第 {i} 页的内容\n配图建议：相关场景图"
            })
        
        pages.append({
            "index": page_count - 1,
            "type": "summary",
            "content": "总结\n希望对你有帮助！\n记得点赞收藏哦💕"
        })
        
        return {
            "title": topic,
            "pages": pages
        }
    
    async def close(self):
        await self._client.aclose()


# 全局实例
_outline_generator: Optional[OutlineGenerator] = None


def get_outline_generator() -> OutlineGenerator:
    global _outline_generator
    if _outline_generator is None:
        _outline_generator = OutlineGenerator()
    return _outline_generator
