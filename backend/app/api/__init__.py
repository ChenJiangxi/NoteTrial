"""
NoteTrial API - API 路由模块
"""
from .contents import router as contents_router
from .ab_tests import router as ab_tests_router
from .posts import router as posts_router
from .materials import router as materials_router
from .analytics import router as analytics_router
from .auth import router as auth_router
from .projects import router as projects_router

__all__ = [
    "contents_router",
    "ab_tests_router", 
    "posts_router",
    "materials_router",
    "analytics_router",
    "auth_router",
    "projects_router"
]
