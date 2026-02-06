"""
NoteTrial Backend - 数据模型定义
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class Platform(str, Enum):
    """支持的平台"""
    XIAOHONGSHU = "xiaohongshu"


class OptimizationGoal(str, Enum):
    """优化目标"""
    MAXIMIZE_LIKE = "maximize_like"
    MAXIMIZE_SAVE = "maximize_save"
    MAXIMIZE_COMMENT = "maximize_comment"
    MAXIMIZE_SHARE = "maximize_share"


class TaskSpec(BaseModel):
    """任务规格 - 从用户对话中结构化提取"""
    platform: Platform = Platform.XIAOHONGSHU
    goals: List[OptimizationGoal] = Field(default=[OptimizationGoal.MAXIMIZE_SAVE], description="优化目标列表，支持多个")
    audience: str = Field(..., description="目标受众描述")
    tone_constraints: List[str] = Field(default_factory=list, description="语气约束，如['不营销', '真实']")
    test_type: str = "A/B"
    topic: str = Field(default="", description="选题/话题")


class ContentItem(BaseModel):
    """单个内容版本"""
    title: str = Field(..., description="标题（不超过20字）")
    body: str = Field(..., description="正文（不超过1000字）")
    cover_image: Optional[str] = Field(None, description="封面图片URL或Base64")
    tags: List[str] = Field(default_factory=list, description="标签列表")


class ABTestRequest(BaseModel):
    """A/B测试请求"""
    task_spec: TaskSpec
    content_a: ContentItem
    content_b: ContentItem
    max_users: int = Field(default=20, ge=5, le=100, description="模拟用户数量")
    audience_tags: Optional[List[str]] = Field(default=None, description="前端选择的测试人群标签")


class ContentVariant(BaseModel):
    """多版本内容定义"""
    label: str = Field(..., description="版本标签，例: Version A")
    content: ContentItem


class MultiTestRequest(BaseModel):
    """多版本对比测试请求"""
    task_spec: TaskSpec
    versions: List[ContentVariant]
    max_users: int = Field(default=20, ge=5, le=100, description="模拟用户数量")
    audience_tags: Optional[List[str]] = Field(default=None, description="前端选择的测试人群标签")


class PersonaSimulationResult(BaseModel):
    """单个Persona的模拟结果"""
    persona_id: str
    persona_description: str
    version_preference: str  # "A" or "B"
    like: bool
    save: bool
    comment: bool
    share: bool
    reasoning: str


class EngagementScore(BaseModel):
    """互动分数"""
    like_count: int = 0
    save_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    total: int = 0


class StatisticalConfidence(BaseModel):
    """统计置信度"""
    winner: str  # "A", "B", or "-"
    confidence: float  # 0-100


class CrowdTestResult(BaseModel):
    """CrowdTest 结果"""
    version_a_score: EngagementScore
    version_b_score: EngagementScore
    
    # 各维度置信度
    like_confidence: StatisticalConfidence
    save_confidence: StatisticalConfidence
    comment_confidence: StatisticalConfidence
    share_confidence: StatisticalConfidence
    overall_confidence: StatisticalConfidence
    
    # 诊断解释
    diagnosis: List[str]
    
    # 改写建议
    suggestions: List[str]
    
    # 详细的persona结果
    persona_results: List[PersonaSimulationResult]


class VersionScore(BaseModel):
    """多版本得分"""
    label: str
    score: EngagementScore


class MultiCrowdTestResult(BaseModel):
    """多版本模拟结果"""
    version_scores: List[VersionScore]
    like_confidence: StatisticalConfidence
    save_confidence: StatisticalConfidence
    comment_confidence: StatisticalConfidence
    share_confidence: StatisticalConfidence
    overall_confidence: StatisticalConfidence
    diagnosis: List[str]
    suggestions: List[str]
    persona_results: List[PersonaSimulationResult]


class CalibrationData(BaseModel):
    """小红书平台校准数据"""
    topic: str
    avg_title_length: float
    common_opening_patterns: List[str]
    emoji_usage_rate: float
    avg_like_save_ratio: float
    common_tags: List[str]
    sample_count: int


class ChatMessage(BaseModel):
    """对话消息"""
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """对话请求"""
    messages: List[ChatMessage]
    current_content: Optional[ContentItem] = None


class ChatResponse(BaseModel):
    """对话响应"""
    message: str
    task_spec: Optional[TaskSpec] = None
    generated_content: Optional[ContentItem] = None


class GenerateVariantRequest(BaseModel):
    """生成变体请求"""
    task_spec: TaskSpec
    base_content: ContentItem
    variant_type: str = Field(default="alternative", description="变体类型：alternative/hook/actionable")
    mcp_keywords: Optional[List[str]] = Field(
        default=None,
        description="Optional MCP search keywords for extra calibration",
    )


class SuggestionItem(BaseModel):
    """改写建议项"""
    type: str  # "title", "hook", "structure"
    original: Optional[str] = None
    suggestions: List[str]
    reason: str
