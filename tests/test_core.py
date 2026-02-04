#!/usr/bin/env python3
"""测试 NoteTrial 核心功能的正确性"""

import sys
import asyncio

# 测试导入
def test_imports():
    print("=== 测试 Python 导入 ===")
    
    try:
        # 测试 viral_generator
        sys.path.insert(0, '/home/admin/clawd/NoteTrial/backend')
        from app.services.viral_generator import EnhancedContentGenerator, VIRAL_TITLE_PROMPT, VIRAL_BODY_PROMPT
        print("✅ viral_generator 导入成功")
        print(f"   - PROMPT_TEMPLATES 存在: {hasattr(EnhancedContentGenerator, 'PROMPT_TEMPLATES')}")
    except Exception as e:
        print(f"❌ viral_generator 导入失败: {e}")
        
    try:
        from app.services.image_generator import CoverGenerator, ImageAdvisor
        print("✅ image_generator 导入成功")
    except Exception as e:
        print(f"❌ image_generator 导入失败: {e}")
        
    try:
        from app.services.real_calibrator import RealDataCalibrator
        print("✅ real_calibrator 导入成功")
    except Exception as e:
        print(f"❌ real_calibrator 导入失败: {e}")
        
    try:
        from app.services.scheduler_service import SchedulerService
        print("✅ scheduler_service 导入成功")
    except Exception as e:
        print(f"❌ scheduler_service 导入失败: {e}")
        
    try:
        from app.services.analytics_engine import AnalyticsEngine
        print("✅ analytics_engine 导入成功")
    except Exception as e:
        print(f"❌ analytics_engine 导入失败: {e}")

# 测试类型定义
def test_types():
    print("\n=== 测试类型定义 ===")
    
    try:
        from app.models import (
            User, Content, ABTest, Post, 
            Material, Subscription, TaskSpec, ContentItem
        )
        print("✅ 所有模型导入成功")
        
        # 验证必要字段
        user_fields = [c.name for c in User.__table__.columns]
        print(f"   User 字段: {user_fields[:5]}...")
        
    except Exception as e:
        print(f"❌ 模型导入失败: {e}")

# 测试 Prompt 模板
def test_prompts():
    print("\n=== 测试 Prompt 模板 ===")
    
    from app.services.viral_generator import VIRAL_TITLE_PROMPT, VIRAL_BODY_PROMPT
    
    # 验证模板包含关键内容
    checks = [
        ("VIRAL_TITLE_PROMPT 包含任务", "小红书爆款标题专家" in VIRAL_TITLE_PROMPT),
        ("VIRAL_TITLE_PROMPT 包含 JSON", '"title":' in VIRAL_TITLE_PROMPT),
        ("VIRAL_TITLE_PROMPT 包含字数限制", "20字" in VIRAL_TITLE_PROMPT),
        ("VIRAL_BODY_PROMPT 包含开头 Hook", "开头 Hook" in VIRAL_BODY_PROMPT),
        ("VIRAL_BODY_PROMPT 包含干货", "干货" in VIRAL_BODY_PROMPT),
        ("VIRAL_BODY_PROMPT 包含 CTA", "CTA" in VIRAL_BODY_PROMPT),
    ]
    
    for name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"   {status} {name}")

# 测试 API 路由
def test_routes():
    print("\n=== 测试 API 路由存在 ===")
    
    from app.main import app
    
    routes = [route.path for route in app.routes]
    
    checks = [
        ("/api/auth/register" in routes, "注册路由"),
        ("/api/auth/login" in routes, "登录路由"),
        ("/api/v1/contents" in routes, "内容路由"),
        ("/api/v1/ab-tests" in routes, "A/B测试路由"),
        ("/api/v1/posts" in routes, "发布记录路由"),
        ("/api/v1/analytics" in routes, "数据分析路由"),
    ]
    
    for passed, name in checks:
        status = "✅" if passed else "❌"
        print(f"   {status} {name}")

# 主测试
if __name__ == "__main__":
    print("NoteTrial 核心功能测试\n")
    
    test_imports()
    test_types()
    test_prompts()
    test_routes()
    
    print("\n=== 测试完成 ===")
