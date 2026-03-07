"""
NoteTrial Backend - Services Package
"""
from .audience_simulator import AudienceSimulator
from .xhs_calibrator import XiaohongshuCalibrator
from .content_generator import ContentGenerator
from .image_generator import ImageGenerator
from .learning_engine import LearningEngine
from .diversity_controller import DiversityController
from .auto_monitor import AutoMonitor, MockMCPMonitor
from .humanize_service import HumanizeService, humanize_content, get_humanize_prompt, check_humanness
from .material_library import MaterialLibrary, get_material_library
from .history_learner import HistoryLearner, get_history_learner
from .web_search_service import WebSearchService, get_web_search_service
from .outline_generator import OutlineGenerator, get_outline_generator

__all__ = [
    "AudienceSimulator",
    "XiaohongshuCalibrator", 
    "ContentGenerator",
    "ImageGenerator",
    # P0 新增服务
    "LearningEngine",
    "DiversityController",
    "AutoMonitor",
    "MockMCPMonitor",
    "HumanizeService",
    "humanize_content",
    "get_humanize_prompt",
    "check_humanness",
    # P1 新增服务
    "MaterialLibrary",
    "get_material_library",
    "HistoryLearner",
    "get_history_learner",
    # 网页搜索服务
    "WebSearchService",
    "get_web_search_service",
    # 多图大纲生成
    "OutlineGenerator",
    "get_outline_generator",
]
