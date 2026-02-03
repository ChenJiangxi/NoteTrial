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
            "collections": []
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
        source: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        添加图片素材
        
        Args:
            image_data: base64编码的图片数据或图片URL
            filename: 原文件名
            tags: 标签列表
            description: 描述
            source: 来源（如：上传、采集、AI生成）
        
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
    
    # ==================== 统计信息 ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """获取素材库统计"""
        return {
            "total_images": len(self.index["images"]),
            "total_texts": len(self.index["texts"]),
            "total_collections": len(self.index["collections"]),
            "tags": list(self.index["tags"].keys()),
            "text_types": {
                "copy": len([t for t in self.index["texts"] if t.get("text_type") == "copy"]),
                "title": len([t for t in self.index["texts"] if t.get("text_type") == "title"]),
                "tag": len([t for t in self.index["texts"] if t.get("text_type") == "tag"]),
                "hook": len([t for t in self.index["texts"] if t.get("text_type") == "hook"])
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
