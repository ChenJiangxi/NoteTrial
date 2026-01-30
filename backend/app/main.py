"""
NoteTrial Backend - FastAPI 主应用
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional

from .config import get_settings
from .models import (
    ABTestRequest, CrowdTestResult, ChatRequest, ChatResponse,
    GenerateVariantRequest, ContentItem, TaskSpec
)
from .services import AudienceSimulator, XiaohongshuCalibrator, ContentGenerator


settings = get_settings()

# 全局服务实例
simulator: Optional[AudienceSimulator] = None
calibrator: Optional[XiaohongshuCalibrator] = None
generator: Optional[ContentGenerator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global simulator, calibrator, generator
    
    # 启动时初始化服务
    simulator = AudienceSimulator()
    calibrator = XiaohongshuCalibrator()
    generator = ContentGenerator()
    
    print("✅ NoteTrial Backend 服务启动成功")
    print(f"📍 API 地址: http://localhost:{settings.backend_port}")
    
    yield
    
    # 关闭时清理
    if calibrator:
        await calibrator.close()
    print("👋 NoteTrial Backend 服务已关闭")


app = FastAPI(
    title="NoteTrial API",
    description="小红书内容A/B测试平台 - 发帖前模拟真实用户反应",
    version="0.1.0",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "NoteTrial API",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/api/health")
async def health_check():
    """健康检查"""
    mcp_status = await calibrator.check_mcp_status() if calibrator else False
    
    return {
        "status": "healthy",
        "services": {
            "simulator": simulator is not None,
            "calibrator": calibrator is not None,
            "generator": generator is not None,
            "xiaohongshu_mcp": mcp_status
        }
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    对话接口 - 帮助用户定义测试任务
    """
    if not generator:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    message, task_spec, generated_content = await generator.parse_task_from_chat(
        request.messages,
        request.current_content
    )
    
    return ChatResponse(
        message=message,
        task_spec=task_spec,
        generated_content=generated_content
    )


@app.post("/api/generate-variant", response_model=ContentItem)
async def generate_variant(request: GenerateVariantRequest):
    """
    生成内容变体 - 基于A版本生成B版本
    
    会先调用MCP搜索该话题的高赞内容作为参考，
    让生成的Version B更贴近真实爆款风格，降低AI味
    """
    if not generator:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    # 尝试获取高赞内容作为参考
    reference_samples = []
    if calibrator and request.task_spec.topic:
        try:
            print(f"[Version B] 搜索高赞参考内容: {request.task_spec.topic}")
            reference_samples = await calibrator.search_topic_samples(
                request.task_spec.topic, 
                limit=10
            )
            if reference_samples:
                print(f"[Version B] 找到 {len(reference_samples)} 条高赞参考内容")
            else:
                print(f"[Version B] 未找到参考内容，使用纯AI生成")
        except Exception as e:
            print(f"[Version B] 获取参考内容失败: {e}，使用纯AI生成")
    
    variant = await generator.generate_variant(
        request.task_spec,
        request.base_content,
        request.variant_type,
        reference_samples=reference_samples
    )
    
    return variant


@app.post("/api/crowdtest", response_model=CrowdTestResult)
async def run_crowdtest(request: ABTestRequest):
    """
    执行 CrowdTest - 核心功能
    
    流程：
    1. 根据话题获取小红书平台校准数据（如果MCP可用）
    2. 生成校准提示
    3. 执行多persona受众模拟
    4. 计算统计置信度
    5. 生成诊断和建议
    """
    if not simulator or not calibrator:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    # 获取校准数据
    calibration_hints = []
    if request.task_spec.topic:
        try:
            calibration_data = await calibrator.get_calibration_data(request.task_spec.topic)
            calibration_hints = calibrator.generate_calibration_hints(calibration_data)
        except Exception as e:
            print(f"校准数据获取失败，使用默认配置: {e}")
    
    # 执行A/B测试模拟
    result = await simulator.simulate_ab_test(
        task_spec=request.task_spec,
        content_a=request.content_a,
        content_b=request.content_b,
        max_users=request.max_users,
        calibration_hints=calibration_hints
    )
    
    return result


@app.post("/api/improve-content", response_model=ContentItem)
async def improve_content(
    content: ContentItem,
    suggestions: list[str],
    task_spec: Optional[TaskSpec] = None
):
    """
    根据建议改进内容
    """
    if not generator:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    improved = await generator.improve_content(content, suggestions, task_spec)
    return improved


@app.get("/api/mcp-status")
async def mcp_status():
    """
    检查小红书MCP服务状态
    """
    if not calibrator:
        return {"available": False, "error": "服务未初始化"}
    
    available = await calibrator.check_mcp_status()
    return {
        "available": available,
        "url": settings.xiaohongshu_mcp_url
    }


@app.get("/api/mcp-tools")
async def mcp_tools():
    """
    获取MCP可用工具列表
    """
    if not calibrator:
        return {"tools": [], "error": "服务未初始化"}
    
    tools = await calibrator.list_tools()
    return {"tools": tools}


@app.get("/api/search-images")
async def search_images(topic: str, limit: int = 5):
    """
    搜索话题相关的图片（用于自动配图）
    """
    if not calibrator:
        return {"images": [], "error": "服务未初始化"}
    
    images = await calibrator.search_images_for_topic(topic, limit)
    return {"images": images, "topic": topic}


@app.get("/api/search-feeds")
async def search_feeds(keyword: str, limit: int = 20):
    """
    搜索小红书内容（通过MCP）
    """
    if not calibrator:
        return {"feeds": [], "error": "服务未初始化"}
    
    feeds = await calibrator.search_topic_samples(keyword, limit)
    return {"feeds": feeds, "keyword": keyword, "count": len(feeds)}


@app.get("/api/xhs-login-status")
async def xhs_login_status():
    """检查小红书登录状态"""
    if not calibrator:
        return {"logged_in": False, "error": "服务未初始化"}
    
    result = await calibrator._call_tool("check_login_status", {})
    return {"result": result}


@app.post("/api/publish-content")
async def publish_content(content: ContentItem):
    """发布内容到小红书"""
    if not calibrator:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    try:
        # 检查登录状态
        login_status = await calibrator._call_tool("check_login_status", {})
        login_text = login_status.get("content", [{}])[0].get("text", "")
        # 检查返回文本中是否包含"已登录"
        is_logged_in = "已登录" in login_text or "登录成功" in login_text
        if not is_logged_in:
            raise HTTPException(status_code=401, detail="未登录小红书，请先登录")
        
        # 调用MCP发布工具
        result = await calibrator.publish_content(content)
        
        if result.get("success"):
            return {
                "success": True,
                "message": "发布成功",
                "note_id": result.get("note_id"),
                "data": result
            }
        else:
            return {
                "success": False,
                "message": result.get("error", "发布失败"),
                "data": result
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发布失败: {str(e)}")


@app.get("/api/login-qrcode")
async def get_login_qrcode():
    """获取小红书登录二维码"""
    if not calibrator:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    result = await calibrator._call_tool("get_login_qrcode", {})
    return {"result": result}


# 应用入口
def main():
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.backend_port,
        reload=settings.debug
    )


if __name__ == "__main__":
    main()
