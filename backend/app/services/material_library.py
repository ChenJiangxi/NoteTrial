"""
素材库服务 - Material Library Service
支持用户上传和管理图片、文案素材，用于内容生成时参考
"""
import os
import json
import uuid
import base64
import hashlib
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path


class MaterialLibrary:
    """素材库管理器"""
    
    def __init__(self, storage_path: str = "data/materials"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 子目录
        self.images_path = self.storage_path / "images"
        self.texts_path = self.storage_path / "texts"
        self.images_path.mkdir(exist_ok=True)
        self.texts_path.mkdir(exist_ok=True)
        
        # 素材索引文件
        self.index_file = self.storage_path / "index.json"
        self.index = self._load_index()
    
    def _load_index(self) -> Dict[str, Any]:
        """加载素材索引"""
        if self.index_file.exists():
            with open(self.index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "images": [],
            "texts": [],
            "tags": {},
            "collections": [],
            "videos": []  # 新增视频素材支持
        }
    
    def _save_index(self):
        """保存素材索引"""
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)
    
    # ==================== 图片素材管理 ====================
    
    def add_image(
        self,
        image_data: str,  # base64 或 URL
        filename: Optional[str] = None,
        tags: Optional[List[str]] = None,
        description: Optional[str] = None,
        source: Optional[str] = None,
        xhs_note_id: Optional[str] = None  # 关联的小红书笔记ID（采集来源）
    ) -> Dict[str, Any]:
        """
        添加图片素材
        
        Args:
            image_data: base64编码的图片数据或图片URL
            filename: 原文件名
            tags: 标签列表
            description: 描述
            source: 来源（如：upload上传、collect采集、ai_generate AI生成）
            xhs_note_id: 采集自小红书的笔记ID
        
        Returns:
            添加的图片信息
        """
        material_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().isoformat()
        
        # 处理图片数据
        if image_data.startswith("data:image"):
            # base64 数据
            header, data = image_data.split(",", 1)
            ext = header.split("/")[1].split(";")[0]
            image_bytes = base64.b64decode(data)
        elif image_data.startswith("http"):
            # URL - 暂存URL，不下载
            ext = "url"
            image_bytes = None
        else:
            # 纯 base64
            ext = "png"
            image_bytes = base64.b64decode(image_data)
        
        # 保存图片文件
        if image_bytes:
            file_hash = hashlib.md5(image_bytes).hexdigest()[:8]
            save_filename = f"{material_id}_{file_hash}.{ext}"
            save_path = self.images_path / save_filename
            
            with open(save_path, "wb") as f:
                f.write(image_bytes)
            
            stored_path = str(save_path)
        else:
            stored_path = image_data  # URL
        
        # 创建素材记录
        material = {
            "id": material_id,
            "type": "image",
            "filename": filename or f"image_{material_id}.{ext}",
            "path": stored_path,
            "tags": tags or [],
            "description": description or "",
            "source": source or "upload",
            "xhs_note_id": xhs_note_id,
            "created_at": timestamp,
            "used_count": 0
        }
        
        self.index["images"].append(material)
        
        # 更新标签索引
        for tag in (tags or []):
            if tag not in self.index["tags"]:
                self.index["tags"][tag] = []
            self.index["tags"][tag].append(material_id)
        
        self._save_index()
        
        return material
    
    def get_images(
        self,
        tags: Optional[List[str]] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取图片素材列表"""
        images = self.index["images"]
        
        # 按标签筛选
        if tags:
            images = [
                img for img in images 
                if any(t in img.get("tags", []) for t in tags)
            ]
        
        # 按时间倒序
        images = sorted(images, key=lambda x: x.get("created_at", ""), reverse=True)
        
        return images[offset:offset + limit]
    
    def get_image_data(self, material_id: str) -> Optional[str]:
        """获取图片数据（base64）"""
        for img in self.index["images"]:
            if img["id"] == material_id:
                path = img["path"]
                if path.startswith("http"):
                    return path
                if os.path.exists(path):
                    with open(path, "rb") as f:
                        data = base64.b64encode(f.read()).decode()
                        ext = path.split(".")[-1]
                        return f"data:image/{ext};base64,{data}"
        return None
    
    def delete_image(self, material_id: str) -> bool:
        """删除图片素材"""
        for i, img in enumerate(self.index["images"]):
            if img["id"] == material_id:
                # 删除文件
                path = img.get("path", "")
                if path and os.path.exists(path) and not path.startswith("http"):
                    os.remove(path)
                
                # 从索引移除
                self.index["images"].pop(i)
                
                # 从标签索引移除
                for tag in img.get("tags", []):
                    if tag in self.index["tags"]:
                        if material_id in self.index["tags"][tag]:
                            self.index["tags"][tag].remove(material_id)
                
                self._save_index()
                return True
        return False
    
    # ==================== 文案素材管理 ====================
    
    def add_text(
        self,
        content: str,
        text_type: str = "copy",  # copy/title/tag/hook
        tags: Optional[List[str]] = None,
        description: Optional[str] = None,
        source: Optional[str] = None,
        performance: Optional[Dict[str, int]] = None  # 效果数据
    ) -> Dict[str, Any]:
        """
        添加文案素材
        
        Args:
            content: 文案内容
            text_type: 类型（copy=正文, title=标题, tag=标签, hook=开头金句）
            tags: 标签
            description: 描述
            source: 来源
            performance: 效果数据 {likes, collects, comments}
        
        Returns:
            添加的文案信息
        """
        material_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().isoformat()
        
        material = {
            "id": material_id,
            "type": "text",
            "text_type": text_type,
            "content": content,
            "tags": tags or [],
            "description": description or "",
            "source": source or "manual",
            "performance": performance or {},
            "created_at": timestamp,
            "used_count": 0
        }
        
        self.index["texts"].append(material)
        
        # 更新标签索引
        for tag in (tags or []):
            if tag not in self.index["tags"]:
                self.index["tags"][tag] = []
            self.index["tags"][tag].append(material_id)
        
        self._save_index()
        
        return material
    
    def get_texts(
        self,
        text_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取文案素材列表"""
        texts = self.index["texts"]
        
        # 按类型筛选
        if text_type:
            texts = [t for t in texts if t.get("text_type") == text_type]
        
        # 按标签筛选
        if tags:
            texts = [
                t for t in texts 
                if any(tag in t.get("tags", []) for tag in tags)
            ]
        
        # 按时间倒序
        texts = sorted(texts, key=lambda x: x.get("created_at", ""), reverse=True)
        
        return texts[offset:offset + limit]
    
    def delete_text(self, material_id: str) -> bool:
        """删除文案素材"""
        for i, text in enumerate(self.index["texts"]):
            if text["id"] == material_id:
                self.index["texts"].pop(i)
                
                # 从标签索引移除
                for tag in text.get("tags", []):
                    if tag in self.index["tags"]:
                        if material_id in self.index["tags"][tag]:
                            self.index["tags"][tag].remove(material_id)
                
                self._save_index()
                return True
        return False
    
    # ==================== 素材集合管理 ====================
    
    def create_collection(
        self,
        name: str,
        description: Optional[str] = None,
        material_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """创建素材集合（用于组织相关素材）"""
        collection_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().isoformat()
        
        collection = {
            "id": collection_id,
            "name": name,
            "description": description or "",
            "material_ids": material_ids or [],
            "created_at": timestamp
        }
        
        self.index["collections"].append(collection)
        self._save_index()
        
        return collection
    
    def add_to_collection(self, collection_id: str, material_id: str) -> bool:
        """添加素材到集合"""
        for collection in self.index["collections"]:
            if collection["id"] == collection_id:
                if material_id not in collection["material_ids"]:
                    collection["material_ids"].append(material_id)
                    self._save_index()
                return True
        return False
    
    def get_collections(self) -> List[Dict[str, Any]]:
        """获取所有集合"""
        return self.index["collections"]
    
    def get_collection_materials(self, collection_id: str) -> List[Dict[str, Any]]:
        """获取集合中的所有素材"""
        for collection in self.index["collections"]:
            if collection["id"] == collection_id:
                materials = []
                for mid in collection["material_ids"]:
                    # 查找图片
                    for img in self.index["images"]:
                        if img["id"] == mid:
                            materials.append(img)
                            break
                    # 查找文案
                    for text in self.index["texts"]:
                        if text["id"] == mid:
                            materials.append(text)
                            break
                return materials
        return []
    
    # ==================== 内容生成辅助 ====================
    
    def get_relevant_materials(
        self,
        topic: str,
        text_types: Optional[List[str]] = None,
        max_images: int = 5,
        max_texts: int = 10
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取与话题相关的素材，用于内容生成参考
        
        Args:
            topic: 话题关键词
            text_types: 需要的文案类型
            max_images: 最大图片数
            max_texts: 最大文案数
        
        Returns:
            {images: [...], texts: [...]}
        """
        topic_keywords = topic.lower().split()
        
        # 匹配图片
        matched_images = []
        for img in self.index["images"]:
            tags = [t.lower() for t in img.get("tags", [])]
            desc = img.get("description", "").lower()
            
            score = 0
            for kw in topic_keywords:
                if any(kw in t for t in tags):
                    score += 2
                if kw in desc:
                    score += 1
            
            if score > 0:
                matched_images.append((score, img))
        
        matched_images.sort(key=lambda x: x[0], reverse=True)
        
        # 匹配文案
        matched_texts = []
        for text in self.index["texts"]:
            if text_types and text.get("text_type") not in text_types:
                continue
            
            tags = [t.lower() for t in text.get("tags", [])]
            content = text.get("content", "").lower()
            
            score = 0
            for kw in topic_keywords:
                if any(kw in t for t in tags):
                    score += 2
                if kw in content:
                    score += 1
            
            if score > 0:
                matched_texts.append((score, text))
        
        matched_texts.sort(key=lambda x: x[0], reverse=True)
        
        return {
            "images": [x[1] for x in matched_images[:max_images]],
            "texts": [x[1] for x in matched_texts[:max_texts]]
        }
    
    def record_usage(self, material_id: str):
        """记录素材使用"""
        for img in self.index["images"]:
            if img["id"] == material_id:
                img["used_count"] = img.get("used_count", 0) + 1
                self._save_index()
                return
        
        for text in self.index["texts"]:
            if text["id"] == material_id:
                text["used_count"] = text.get("used_count", 0) + 1
                self._save_index()
                return
    
    # ==================== 视频素材管理 ====================
    
    def add_video(
        self,
        video_url: str,
        thumbnail: Optional[str] = None,  # 缩略图 URL 或 base64
        filename: Optional[str] = None,
        tags: Optional[List[str]] = None,
        description: Optional[str] = None,
        source: Optional[str] = None,
        duration: Optional[int] = None,  # 时长（秒）
        xhs_note_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        添加视频素材
        
        Args:
            video_url: 视频URL
            thumbnail: 缩略图
            filename: 文件名
            tags: 标签列表
            description: 描述
            source: 来源
            duration: 时长（秒）
            xhs_note_id: 采集自小红书的笔记ID
        
        Returns:
            添加的视频信息
        """
        # 确保 videos 列表存在
        if "videos" not in self.index:
            self.index["videos"] = []
        
        material_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().isoformat()
        
        material = {
            "id": material_id,
            "type": "video",
            "url": video_url,
            "thumbnail": thumbnail or "",
            "filename": filename or f"video_{material_id}",
            "tags": tags or [],
            "description": description or "",
            "source": source or "upload",
            "duration": duration,
            "xhs_note_id": xhs_note_id,
            "created_at": timestamp,
            "used_count": 0
        }
        
        self.index["videos"].append(material)
        
        # 更新标签索引
        for tag in (tags or []):
            if tag not in self.index["tags"]:
                self.index["tags"][tag] = []
            self.index["tags"][tag].append(material_id)
        
        self._save_index()
        return material
    
    def get_videos(
        self,
        tags: Optional[List[str]] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取视频素材列表"""
        videos = self.index.get("videos", [])
        
        # 按标签筛选
        if tags:
            videos = [
                v for v in videos
                if any(t in v.get("tags", []) for t in tags)
            ]
        
        # 按时间倒序
        videos = sorted(videos, key=lambda x: x.get("created_at", ""), reverse=True)
        
        return videos[offset:offset + limit]
    
    def delete_video(self, material_id: str) -> bool:
        """删除视频素材"""
        videos = self.index.get("videos", [])
        for i, video in enumerate(videos):
            if video["id"] == material_id:
                videos.pop(i)
                
                # 从标签索引移除
                for tag in video.get("tags", []):
                    if tag in self.index["tags"]:
                        if material_id in self.index["tags"][tag]:
                            self.index["tags"][tag].remove(material_id)
                
                self._save_index()
                return True
        return False
    
    # ==================== 小红书素材采集 ====================
    
    async def collect_from_xhs(
        self,
        note_data: Dict[str, Any],
        collect_images: bool = True,
        collect_video: bool = True,
        auto_tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        从小红书笔记采集素材
        
        Args:
            note_data: 小红书笔记数据（从 MCP 获取）
            collect_images: 是否采集图片
            collect_video: 是否采集视频
            auto_tags: 自动添加的标签
        
        Returns:
            采集结果 {images: [...], video: {...}, text: {...}}
        """
        result = {"images": [], "video": None, "text": None}
        
        note_card = note_data.get("noteCard", note_data)
        note_id = note_card.get("noteId", note_data.get("id", ""))
        title = note_card.get("displayTitle", note_card.get("title", ""))
        desc = note_card.get("desc", "")
        
        # 提取标签
        tags = auto_tags or []
        if title:
            # 从标题提取关键词作为标签
            import re
            keywords = re.findall(r'[\u4e00-\u9fa5a-zA-Z]{2,}', title)
            tags.extend(keywords[:3])
        
        # 采集图片
        if collect_images:
            # 封面图
            cover = note_card.get("cover", {})
            cover_url = cover.get("url") or cover.get("urlDefault", "")
            if cover_url:
                img_material = self.add_image(
                    image_data=cover_url,
                    filename=f"xhs_{note_id}_cover",
                    tags=tags,
                    description=f"采集自小红书: {title[:30]}",
                    source="xhs_collect",
                    xhs_note_id=note_id
                )
                result["images"].append(img_material)
            
            # 图片列表（如果有）
            images_list = note_card.get("imageList", [])
            for i, img in enumerate(images_list[:9]):  # 最多9张
                img_url = img.get("url") or img.get("urlDefault", "")
                if img_url and img_url != cover_url:
                    img_material = self.add_image(
                        image_data=img_url,
                        filename=f"xhs_{note_id}_{i}",
                        tags=tags,
                        description=f"采集自小红书: {title[:30]}",
                        source="xhs_collect",
                        xhs_note_id=note_id
                    )
                    result["images"].append(img_material)
        
        # 采集视频
        if collect_video:
            video = note_card.get("video", {})
            video_url = video.get("url") or video.get("media", {}).get("stream", {}).get("h264", [{}])[0].get("masterUrl", "")
            if video_url:
                thumbnail = note_card.get("cover", {}).get("url", "")
                duration = video.get("duration", 0)
                
                video_material = self.add_video(
                    video_url=video_url,
                    thumbnail=thumbnail,
                    filename=f"xhs_{note_id}_video",
                    tags=tags,
                    description=f"采集自小红书: {title[:30]}",
                    source="xhs_collect",
                    duration=duration,
                    xhs_note_id=note_id
                )
                result["video"] = video_material
        
        # 采集文案
        if title or desc:
            # 添加标题
            if title:
                title_material = self.add_text(
                    content=title,
                    text_type="title",
                    tags=tags,
                    description=f"采集自小红书笔记",
                    source="xhs_collect",
                    performance=self._extract_performance(note_card)
                )
                result["text"] = title_material
            
            # 添加正文
            if desc:
                self.add_text(
                    content=desc,
                    text_type="copy",
                    tags=tags,
                    description=f"采集自小红书笔记: {title[:20]}",
                    source="xhs_collect",
                    performance=self._extract_performance(note_card)
                )
        
        return result
    
    def _extract_performance(self, note_card: Dict) -> Dict[str, int]:
        """从笔记数据提取效果数据"""
        interact = note_card.get("interactInfo", {})
        return {
            "likes": self._parse_count(interact.get("likedCount", 0)),
            "collects": self._parse_count(interact.get("collectedCount", 0)),
            "comments": self._parse_count(interact.get("commentCount", 0))
        }
    
    def _parse_count(self, value) -> int:
        """解析数量（支持 '1.2万' 格式）"""
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            value = value.strip()
            if '万' in value:
                return int(float(value.replace('万', '')) * 10000)
            if 'k' in value.lower():
                return int(float(value.lower().replace('k', '')) * 1000)
            try:
                return int(value)
            except:
                return 0
        return 0
    
    # ==================== 智能素材推荐 ====================
    
    def recommend_materials(
        self,
        topic: str,
        content_type: str = "image",  # image/video/text
        limit: int = 5,
        prefer_high_performance: bool = True
    ) -> List[Dict[str, Any]]:
        """
        智能推荐素材
        
        根据话题和效果数据推荐最合适的素材
        """
        topic_keywords = topic.lower().split()
        
        if content_type == "image":
            candidates = self.index["images"]
        elif content_type == "video":
            candidates = self.index.get("videos", [])
        else:
            candidates = self.index["texts"]
        
        # 计算匹配分数
        scored = []
        for item in candidates:
            score = 0
            
            # 标签匹配
            item_tags = [t.lower() for t in item.get("tags", [])]
            for kw in topic_keywords:
                if any(kw in t for t in item_tags):
                    score += 3
            
            # 描述匹配
            desc = item.get("description", "").lower()
            for kw in topic_keywords:
                if kw in desc:
                    score += 1
            
            # 效果加权（针对文案）
            if prefer_high_performance and "performance" in item:
                perf = item["performance"]
                score += min(perf.get("likes", 0) / 100, 5)
                score += min(perf.get("collects", 0) / 50, 5)
            
            # 使用次数（优先推荐未使用过的）
            used = item.get("used_count", 0)
            if used == 0:
                score += 2
            
            if score > 0:
                scored.append((score, item))
        
        # 排序返回
        scored.sort(key=lambda x: x[0], reverse=True)
        return [x[1] for x in scored[:limit]]
    
    # ==================== 统计信息 ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """获取素材库统计"""
        return {
            "total_images": len(self.index["images"]),
            "total_videos": len(self.index.get("videos", [])),
            "total_texts": len(self.index["texts"]),
            "total_collections": len(self.index["collections"]),
            "tags": list(self.index["tags"].keys()),
            "text_types": {
                "copy": len([t for t in self.index["texts"] if t.get("text_type") == "copy"]),
                "title": len([t for t in self.index["texts"] if t.get("text_type") == "title"]),
                "tag": len([t for t in self.index["texts"] if t.get("text_type") == "tag"]),
                "hook": len([t for t in self.index["texts"] if t.get("text_type") == "hook"])
            },
            "sources": {
                "upload": len([i for i in self.index["images"] if i.get("source") == "upload"]),
                "xhs_collect": len([i for i in self.index["images"] if i.get("source") == "xhs_collect"]),
                "ai_generate": len([i for i in self.index["images"] if i.get("source") == "ai_generate"])
            }
        }


# 全局实例
_material_library: Optional[MaterialLibrary] = None

def get_material_library() -> MaterialLibrary:
    """获取素材库单例"""
    global _material_library
    if _material_library is None:
        _material_library = MaterialLibrary()
    return _material_library
