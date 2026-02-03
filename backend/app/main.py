"""
NoteTrial Backend - FastAPI 主应用
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
from pydantic import BaseModel
import asyncio
import uuid

from .config import get_settings
from .models import (
    ABTestRequest, CrowdTestResult, ChatRequest, ChatResponse,
    GenerateVariantRequest, ContentItem, TaskSpec
)
from .services import (
    AudienceSimulator, XiaohongshuCalibrator, ContentGenerator, ImageGenerator,
    LearningEngine, DiversityController, AutoMonitor, HumanizeService,
    humanize_content, get_humanize_prompt, check_humanness,
    get_material_library, get_history_learner
)


settings = get_settings()

# 全局服务实例
simulator: Optional[AudienceSimulator] = None
calibrator: Optional[XiaohongshuCalibrator] = None
generator: Optional[ContentGenerator] = None
image_gen: Optional[ImageGenerator] = None
# P0 新增服务
learning_engine: Optional[LearningEngine] = None
diversity_controller: Optional[DiversityController] = None
auto_monitor: Optional[AutoMonitor] = None
humanize_service: Optional[HumanizeService] = None
crowdtest_jobs: Dict[str, Dict[str, Any]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global simulator, calibrator, generator, image_gen
    global learning_engine, diversity_controller, auto_monitor, humanize_service
    
    # 启动时初始化服务
    simulator = AudienceSimulator()
    calibrator = XiaohongshuCalibrator()
    generator = ContentGenerator()
    image_gen = ImageGenerator()
    
    # P0 新增服务初始化
    learning_engine = LearningEngine()
    diversity_controller = DiversityController()
    auto_monitor = AutoMonitor()
    humanize_service = HumanizeService()
    
    # 设置学习引擎回调：当监控获取到新数据时更新学习
    async def on_stats_update(content_id: str, stats: dict, check_count: int):
        if learning_engine:
            learning_engine.update_performance(content_id, stats)
    
    auto_monitor.add_callback(on_stats_update)
    
    print("✅ NoteTrial Backend 服务启动成功")
    print(f"📍 API 地址: http://localhost:{settings.backend_port}")
    if settings.gemini_api_key:
        print("🎨 Gemini 图片生成已启用")
    print("🧠 学习引擎已启用")
    print("🎯 多样性控制已启用")
    print("🤖 AI检测规避已启用")
    
    yield
    
    # 关闭时清理
    if calibrator:
        await calibrator.close()
    if image_gen:
        await image_gen.close()
    if auto_monitor:
        auto_monitor.stop()
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


@app.get("/api/mcp-tools")
async def list_mcp_tools():
    """列出MCP支持的所有工具"""
    if not calibrator:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    tools = await calibrator.list_tools()
    return {"tools": tools}


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


async def _get_crowdtest_calibration_hints(task_spec: TaskSpec) -> list[str]:
    """获取 CrowdTest 的平台校准提示（MCP 可用时）"""
    if not calibrator or not task_spec.topic:
        return []
    try:
        calibration_data = await calibrator.get_calibration_data(task_spec.topic)
        return calibrator.generate_calibration_hints(calibration_data)
    except Exception as e:
        print(f"校准数据获取失败，使用默认配置: {e}")
        return []


@app.post("/api/crowdtest/start")
async def start_crowdtest(request: ABTestRequest):
    """启动带进度的 CrowdTest 异步任务"""
    if not simulator or not calibrator:
        raise HTTPException(status_code=500, detail="服务未初始化")

    job_id = str(uuid.uuid4())
    crowdtest_jobs[job_id] = {
        "status": "running",
        "progress": 0,
        "result": None,
        "error": None,
    }

    async def on_progress(completed: int, total: int):
        job = crowdtest_jobs.get(job_id)
        if not job:
            return
        total_safe = max(total, 1)
        pct = int((completed / total_safe) * 100)
        job["progress"] = min(99, max(0, pct))

    async def worker():
        try:
            calibration_hints = await _get_crowdtest_calibration_hints(request.task_spec)
            result = await simulator.simulate_ab_test(
                task_spec=request.task_spec,
                content_a=request.content_a,
                content_b=request.content_b,
                max_users=request.max_users,
                audience_tags=request.audience_tags,
                calibration_hints=calibration_hints,
                on_progress=on_progress,
            )
            crowdtest_jobs[job_id]["status"] = "completed"
            crowdtest_jobs[job_id]["progress"] = 100
            crowdtest_jobs[job_id]["result"] = result.model_dump()
        except Exception as e:
            crowdtest_jobs[job_id]["status"] = "failed"
            crowdtest_jobs[job_id]["error"] = str(e)

    asyncio.create_task(worker())
    return {"job_id": job_id, "status": "running"}


@app.get("/api/crowdtest/progress/{job_id}")
async def get_crowdtest_progress(job_id: str):
    """查询 CrowdTest 异步任务进度"""
    job = crowdtest_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job["progress"],
        "result": job["result"],
        "error": job["error"],
    }


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
    calibration_hints = await _get_crowdtest_calibration_hints(request.task_spec)
    
    # 执行A/B测试模拟
    result = await simulator.simulate_ab_test(
        task_spec=request.task_spec,
        content_a=request.content_a,
        content_b=request.content_b,
        max_users=request.max_users,
        audience_tags=request.audience_tags,
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
        # 强制截断标题到20字以内（小红书硬性限制）
        if content.title and len(content.title) > 20:
            print(f"[发布] 标题超长({len(content.title)}字)，截断到20字: {content.title[:20]}")
            content.title = content.title[:20]
        
        # 强制截断正文到1000字以内
        if content.body and len(content.body) > 1000:
            print(f"[发布] 正文超长({len(content.body)}字)，截断到1000字")
            content.body = content.body[:1000]
        
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
                "xsec_token": result.get("xsec_token"),  # 返回 xsec_token
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


@app.get("/api/list-feeds")
async def list_feeds():
    """获取首页 Feeds 列表，用于获取 user_id 和 xsec_token"""
    if not calibrator:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    result = await calibrator._call_tool("list_feeds", {})
    return {"result": result}


@app.get("/api/user-profile")
async def get_user_profile(user_id: str, xsec_token: str):
    """获取用户主页，包括用户信息和笔记列表"""
    if not calibrator:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    result = await calibrator._call_tool("user_profile", {
        "user_id": user_id,
        "xsec_token": xsec_token
    })
    return {"result": result}


class SyncNotesRequest(BaseModel):
    """同步笔记请求"""
    titles: list[str] = []  # 要同步的笔记标题列表


def parse_chinese_number(value) -> int:
    """解析中文数字格式（如"5万"、"1.2万"、"129"）为整数
    
    支持格式：
    - 纯数字: "129" -> 129
    - 万: "5万" -> 50000, "1.2万" -> 12000
    - 千: "5千" -> 5000, "1.5千" -> 1500
    - 亿: "1亿" -> 100000000
    """
    if value is None:
        return 0
    
    # 如果已经是数字，直接返回
    if isinstance(value, (int, float)):
        return int(value)
    
    # 转为字符串处理
    s = str(value).strip()
    if not s:
        return 0
    
    try:
        # 尝试直接解析为数字
        return int(float(s))
    except ValueError:
        pass
    
    # 处理中文数字单位
    import re
    
    # 匹配数字和单位
    match = re.match(r'^([\d.]+)\s*(万|千|亿|w|k|m)?$', s, re.IGNORECASE)
    if match:
        num = float(match.group(1))
        unit = match.group(2)
        
        if unit in ('万', 'w', 'W'):
            return int(num * 10000)
        elif unit in ('千', 'k', 'K'):
            return int(num * 1000)
        elif unit in ('亿',):
            return int(num * 100000000)
        elif unit in ('m', 'M'):
            return int(num * 1000000)
        else:
            return int(num)
    
    # 最后尝试提取纯数字
    digits = re.findall(r'\d+', s)
    if digits:
        return int(digits[0])
    
    return 0


@app.post("/api/sync-notes")
async def sync_notes(request: SyncNotesRequest):
    """通过标题关键词搜索并同步笔记数据
    
    由于 MCP 没有直接获取"我的笔记"的工具，
    我们通过搜索标题关键词来获取笔记数据。
    """
    if not calibrator:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    if not request.titles:
        return {"notes": [], "error": "请提供要同步的笔记标题"}
    
    import json
    notes = []
    
    for title in request.titles:
        if not title or len(title) < 3:
            continue
            
        try:
            # 用标题前几个字符搜索
            keyword = title[:8] if len(title) > 8 else title
            print(f"[同步笔记] 搜索关键词: {keyword}")
            
            search_result = await calibrator._call_tool("search_feeds", {"keyword": keyword})
            search_text = search_result.get("content", [{}])[0].get("text", "")
            
            if not search_text:
                continue
                
            search_data = json.loads(search_text)
            feeds = search_data.get("feeds", []) if isinstance(search_data, dict) else []
            
            for feed in feeds:
                note_card = feed.get("noteCard", {})
                display_title = note_card.get("displayTitle", "")
                
                # 检查标题是否匹配
                if title[:6] in display_title or display_title[:6] in title:
                    interact_info = note_card.get("interactInfo", {})
                    
                    # 使用中文数字解析函数
                    liked_count = parse_chinese_number(interact_info.get("likedCount", 0))
                    collected_count = parse_chinese_number(interact_info.get("collectedCount", 0))
                    comment_count = parse_chinese_number(interact_info.get("commentCount", 0))
                    share_count = parse_chinese_number(interact_info.get("sharedCount", 0))
                    
                    note_data = {
                        "noteId": feed.get("id") or note_card.get("noteId"),
                        "xsecToken": feed.get("xsecToken"),
                        "title": display_title,
                        "likedCount": liked_count,
                        "collectedCount": collected_count,
                        "commentCount": comment_count,
                        "shareCount": share_count,
                        "matchedTitle": title  # 匹配的原始标题
                    }
                    notes.append(note_data)
                    print(f"[同步笔记] 找到匹配: {display_title} -> 👍{liked_count} 🔖{collected_count} 💬{comment_count}")
                    break  # 找到一个匹配就跳出
                    
        except Exception as e:
            print(f"[同步笔记] 搜索 '{title}' 失败: {e}")
            continue
    
    print(f"[同步笔记] 共同步 {len(notes)} 条笔记")
    return {"notes": notes}


@app.get("/api/note-stats/{note_id}")
async def get_note_stats(note_id: str, xsec_token: str = None, title_keyword: str = None):
    """获取单个笔记的效果数据（点赞、收藏、评论等）
    
    参数：
    - note_id: 笔记ID（从发布结果获取）
    - xsec_token: 可选，如果提供则直接用
    - title_keyword: 可选，通过搜索关键词找到笔记获取xsec_token
    """
    if not calibrator:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    # 如果没有xsec_token，尝试通过搜索获取
    token = xsec_token
    if not token and title_keyword:
        try:
            # 搜索关键词找到笔记
            search_result = await calibrator._call_tool("search_feeds", {"keyword": title_keyword})
            if search_result and "content" in search_result:
                import json
                text_content = search_result.get("content", [{}])[0].get("text", "")
                data = json.loads(text_content) if text_content else {}
                feeds = data.get("feeds", []) if isinstance(data, dict) else data if isinstance(data, list) else []
                
                # 从搜索结果中找到匹配的笔记
                for feed in feeds:
                    if feed.get("id") == note_id or feed.get("noteCard", {}).get("noteId") == note_id:
                        token = feed.get("xsecToken") or feed.get("xsec_token")
                        print(f"[笔记统计] 从搜索结果找到xsec_token: {token}")
                        break
        except Exception as e:
            print(f"[笔记统计] 搜索xsec_token失败: {e}")
    
    if not token:
        # 没有xsec_token，无法调用get_feed_detail
        return {
            "result": {
                "error": "无法获取xsec_token，请提供title_keyword参数用于搜索",
                "note": "MCP的get_feed_detail需要xsec_token参数，需要先通过search_feeds获取"
            }
        }
    
    # 调用get_feed_detail获取笔记详情
    result = await calibrator._call_tool("get_feed_detail", {
        "feed_id": note_id,
        "xsec_token": token
    })
    return {"result": result}


@app.post("/api/auto-generate")
async def auto_generate_content(
    topic: str,
    goals: list[str] = ["maximize_save"],
    audience: str = "小红书用户",
    reference_count: int = 10
):
    """
    自动模式：基于话题学习爆款内容并生成低 AI 味的内容
    
    1. 搜索话题下的高赞内容
    2. 分析成功模式
    3. 生成符合小红书风格的内容
    """
    if not generator or not calibrator:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    # 搜索高赞内容作为参考
    reference_samples = []
    try:
        reference_samples = await calibrator.search_topic_samples(topic, limit=reference_count)
    except Exception as e:
        print(f"搜索参考内容失败: {e}")
    
    # 获取校准数据
    calibration_data = await calibrator.get_calibration_data(topic)
    
    # 构建任务规格
    from .models import TaskSpec, OptimizationGoal, Platform
    goal_map = {
        "maximize_save": OptimizationGoal.MAXIMIZE_SAVE,
        "maximize_like": OptimizationGoal.MAXIMIZE_LIKE,
        "maximize_comment": OptimizationGoal.MAXIMIZE_COMMENT,
        "maximize_share": OptimizationGoal.MAXIMIZE_SHARE,
    }
    task_spec = TaskSpec(
        platform=Platform.XIAOHONGSHU,
        goals=[goal_map.get(g, OptimizationGoal.MAXIMIZE_SAVE) for g in goals],
        audience=audience,
        topic=topic,
        tone_constraints=["真实", "不营销", "口语化"]
    )
    
    # 生成内容
    content = await generator.generate_authentic_content(
        task_spec=task_spec,
        reference_samples=reference_samples,
        calibration_data=calibration_data
    )
    
    return {
        "content": content,
        "reference_count": len(reference_samples),
        "calibration": {
            "avg_title_length": calibration_data.avg_title_length,
            "common_patterns": calibration_data.common_opening_patterns,
            "emoji_rate": calibration_data.emoji_usage_rate,
            "common_tags": calibration_data.common_tags
        }
    }


class GenerateImageRequest(BaseModel):
    """图片生成请求"""
    prompt: str
    style: str = "小红书风格"
    aspect_ratio: str = "1:1"


class ExpandTopicRequest(BaseModel):
    """话题扩展请求"""
    brief_input: str  # 简短输入，如 "护肤"


class RecordContentRequest(BaseModel):
    """记录内容请求"""
    content_id: str
    title: str
    body: str
    tags: list[str] = []
    topic: str = ""  # 话题，用于学习引擎分类


class UpdateStatsRequest(BaseModel):
    """更新效果数据请求"""
    content_id: str
    stats: dict  # {likes, collects, comments, shares}


class AddMonitorTaskRequest(BaseModel):
    """添加监控任务请求"""
    content_id: str
    note_id: str


class HumanizeRequest(BaseModel):
    """人性化内容请求"""
    title: str
    body: str
    

@app.post("/api/generate-image")
async def generate_image(request: GenerateImageRequest):
    """
    使用 AI 生成原创图片
    """
    if not image_gen:
        raise HTTPException(status_code=500, detail="图片生成服务未初始化")
    
    if not settings.gemini_api_key:
        raise HTTPException(status_code=500, detail="未配置 Gemini API Key")
    
    try:
        image_data = await image_gen.generate_image(
            prompt=request.prompt,
            style=request.style,
            aspect_ratio=request.aspect_ratio
        )
        
        if image_data:
            return {"success": True, "image": image_data}
        else:
            return {"success": False, "error": "图片生成失败"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图片生成出错: {str(e)}")


@app.post("/api/generate-cover")
async def generate_cover(content: ContentItem, topic: str = ""):
    """
    根据内容自动生成封面图
    """
    if not image_gen:
        raise HTTPException(status_code=500, detail="图片生成服务未初始化")
    
    try:
        image_data = await image_gen.generate_cover_for_content(
            title=content.title,
            body=content.body,
            topic=topic or content.title
        )
        
        if image_data:
            return {"success": True, "image": image_data}
        else:
            return {"success": False, "error": "封面生成失败"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"封面生成出错: {str(e)}")


@app.post("/api/expand-topic")
async def expand_topic(request: ExpandTopicRequest):
    """
    智能扩展话题描述
    将简短的关键词扩展为完整的创作方向
    """
    if not generator:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    brief = request.brief_input.strip()
    
    # 使用 LLM 智能扩展
    prompt = f"""用户想创作关于「{brief}」的小红书内容。

请帮助用户扩展和完善创作方向，输出 JSON 格式：
{{
    "topic": "核心话题（2-4个字）",
    "detailed_topic": "详细的话题描述（10-20字）",
    "suggested_angles": ["创作角度1", "创作角度2", "创作角度3"],
    "target_audiences": ["目标受众1", "目标受众2"],
    "content_types": ["内容类型1", "内容类型2"],
    "hot_keywords": ["热门关键词1", "关键词2", "关键词3", "关键词4", "关键词5"]
}}

要求：
1. 根据小红书的热门趋势给出建议
2. 创作角度要具体可执行
3. 目标受众要精准
4. 关键词要有搜索热度
"""
    
    try:
        completion = await generator.client.chat.completions.create(
            model=generator.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        import json
        result = json.loads(completion.choices[0].message.content)
        return {"success": True, "data": result}
        
    except Exception as e:
        # 返回基础扩展
        return {
            "success": True,
            "data": {
                "topic": brief,
                "detailed_topic": f"{brief}相关内容分享",
                "suggested_angles": [f"{brief}入门指南", f"{brief}避坑攻略", f"{brief}好物推荐"],
                "target_audiences": ["小红书用户", f"{brief}爱好者"],
                "content_types": ["经验分享", "好物推荐", "教程攻略"],
                "hot_keywords": [brief]
            }
        }


# ============ P0 新增 API：学习引擎 ============

@app.get("/api/learning/stats")
async def get_learning_stats():
    """获取学习引擎统计数据"""
    if not learning_engine:
        raise HTTPException(status_code=500, detail="学习引擎未初始化")
    
    return learning_engine.get_stats_summary()


@app.get("/api/learning/hints")
async def get_learning_hints():
    """获取学习引擎的优化建议"""
    if not learning_engine:
        raise HTTPException(status_code=500, detail="学习引擎未初始化")
    
    return {
        "hints": learning_engine.get_optimization_hints(),
        "prompt_enhancement": learning_engine.build_optimized_prompt("基础提示")
    }


@app.post("/api/learning/record")
async def record_content(request: RecordContentRequest):
    """记录新发布的内容"""
    if not learning_engine or not diversity_controller:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    # 记录到学习引擎
    learning_engine.record_content(
        content_id=request.content_id,
        title=request.title,
        body=request.body,
        tags=request.tags,
        topic=getattr(request, 'topic', '') or request.title[:10]  # 使用topic或标题前10字
    )
    
    # 记录到多样性控制器
    diversity_controller.record_content(
        title=request.title,
        tags=request.tags
    )
    
    return {"success": True, "message": "内容已记录"}


@app.post("/api/learning/update-stats")
async def update_content_stats(request: UpdateStatsRequest):
    """更新内容的效果数据"""
    if not learning_engine:
        raise HTTPException(status_code=500, detail="学习引擎未初始化")
    
    learning_engine.update_performance(request.content_id, request.stats)
    
    return {"success": True, "message": "效果数据已更新"}


# ============ P0 新增 API：多样性控制 ============

@app.get("/api/diversity/stats")
async def get_diversity_stats():
    """获取多样性统计"""
    if not diversity_controller:
        raise HTTPException(status_code=500, detail="多样性控制器未初始化")
    
    return diversity_controller.get_stats()


@app.get("/api/diversity/check")
async def check_content_diversity(title: str, body: str = "", tags: str = ""):
    """检查内容的多样性"""
    if not diversity_controller:
        raise HTTPException(status_code=500, detail="多样性控制器未初始化")
    
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    
    return diversity_controller.validate_content(title, body, tag_list)


@app.get("/api/diversity/prompt")
async def get_diversity_prompt():
    """获取多样性提示（用于内容生成）"""
    if not diversity_controller:
        raise HTTPException(status_code=500, detail="多样性控制器未初始化")
    
    return {
        "prompt": diversity_controller.get_diversity_prompt(),
        "suggested_style": diversity_controller.suggest_style_variation()
    }


# ============ P0 新增 API：自动监控 ============

@app.post("/api/monitor/add")
async def add_monitor_task(request: AddMonitorTaskRequest):
    """添加监控任务"""
    if not auto_monitor:
        raise HTTPException(status_code=500, detail="监控服务未初始化")
    
    task = auto_monitor.add_task(request.content_id, request.note_id)
    
    return {
        "success": True,
        "task": {
            "content_id": task.content_id,
            "note_id": task.note_id,
            "status": task.status
        }
    }


@app.get("/api/monitor/tasks")
async def get_monitor_tasks():
    """获取所有监控任务"""
    if not auto_monitor:
        raise HTTPException(status_code=500, detail="监控服务未初始化")
    
    return {
        "tasks": auto_monitor.get_all_tasks(),
        "pending_count": auto_monitor.get_pending_count()
    }


@app.post("/api/monitor/run-once")
async def run_monitor_once():
    """手动执行一次监控检查"""
    if not auto_monitor:
        raise HTTPException(status_code=500, detail="监控服务未初始化")
    
    completed = await auto_monitor.run_once()
    
    return {
        "success": True,
        "completed_count": completed,
        "remaining": auto_monitor.get_pending_count()
    }


# ============ P0 新增 API：AI检测规避 ============

@app.post("/api/humanize/content")
async def humanize_content_api(request: HumanizeRequest):
    """人性化处理内容"""
    if not humanize_service:
        raise HTTPException(status_code=500, detail="人性化服务未初始化")
    
    new_title = humanize_service.humanize_title(request.title)
    new_body = humanize_service.humanize_body(request.body)
    
    # 评估人性化程度
    original_score = humanize_service.score_humanness(request.title + "\n" + request.body)
    new_score = humanize_service.score_humanness(new_title + "\n" + new_body)
    
    return {
        "title": new_title,
        "body": new_body,
        "original_score": original_score,
        "new_score": new_score,
        "improvement": new_score['score'] - original_score['score']
    }


@app.get("/api/humanize/check")
async def check_humanness_api(text: str):
    """检查文本的人性化程度"""
    if not humanize_service:
        raise HTTPException(status_code=500, detail="人性化服务未初始化")
    
    return humanize_service.score_humanness(text)


@app.get("/api/humanize/prompt")
async def get_humanize_prompt_api():
    """获取人性化写作提示"""
    if not humanize_service:
        raise HTTPException(status_code=500, detail="人性化服务未初始化")
    
    return {
        "prompt": humanize_service.generate_prompt_enhancement()
    }


# ============ 增强的自动生成 API（集成P0功能） ============

@app.post("/api/auto-generate-enhanced")
async def auto_generate_enhanced(
    topic: str,
    goals: list[str] = ["maximize_save"],
    audience: str = "小红书用户",
    reference_count: int = 10,
    use_learning: bool = True,
    check_diversity: bool = True,
    humanize: bool = True
):
    """
    增强版自动生成（集成P0优化功能）
    
    1. 搜索话题下的高赞内容
    2. 应用学习引擎的优化建议
    3. 检查多样性避免重复
    4. 生成内容
    5. AI检测规避处理
    """
    if not generator or not calibrator:
        raise HTTPException(status_code=500, detail="服务未初始化")
    
    # 搜索高赞内容作为参考
    reference_samples = []
    try:
        reference_samples = await calibrator.search_topic_samples(topic, limit=reference_count)
    except Exception as e:
        print(f"搜索参考内容失败: {e}")
    
    # 获取校准数据
    calibration_data = await calibrator.get_calibration_data(topic)
    
    # 构建任务规格
    from .models import TaskSpec, OptimizationGoal, Platform
    goal_map = {
        "maximize_save": OptimizationGoal.MAXIMIZE_SAVE,
        "maximize_like": OptimizationGoal.MAXIMIZE_LIKE,
        "maximize_comment": OptimizationGoal.MAXIMIZE_COMMENT,
        "maximize_share": OptimizationGoal.MAXIMIZE_SHARE,
    }
    task_spec = TaskSpec(
        platform=Platform.XIAOHONGSHU,
        goals=[goal_map.get(g, OptimizationGoal.MAXIMIZE_SAVE) for g in goals],
        audience=audience,
        topic=topic,
        tone_constraints=["真实", "不营销", "口语化"]
    )
    
    # P0: 获取学习引擎优化建议
    learning_hints_text = ""
    if use_learning and learning_engine:
        hints = learning_engine.get_optimization_hints()
        if hints:
            parts = []
            if hints.get('title_suggestions'):
                parts.append("标题建议: " + "; ".join(hints['title_suggestions']))
            if hints.get('body_suggestions'):
                parts.append("正文建议: " + "; ".join(hints['body_suggestions']))
            if hints.get('tag_suggestions'):
                parts.append("推荐标签: " + ", ".join(hints['tag_suggestions']))
            learning_hints_text = "\n".join(parts)
    
    # P0: 获取多样性提示
    diversity_prompt = ""
    if check_diversity and diversity_controller:
        diversity_prompt = diversity_controller.get_diversity_prompt()
    
    # P0: 获取人性化写作提示
    humanize_prompt = ""
    if humanize and humanize_service:
        humanize_prompt = humanize_service.generate_prompt_enhancement()
    
    # 合并所有优化提示
    extra_hints = [h for h in [learning_hints_text, diversity_prompt, humanize_prompt] if h]
    
    # 生成内容（传递优化提示）
    content = await generator.generate_authentic_content(
        task_spec=task_spec,
        reference_samples=reference_samples,
        calibration_data=calibration_data,
        extra_hints=extra_hints
    )
    
    # P0: 对生成的内容进行人性化处理
    original_title, original_body = content.title, content.body
    if humanize and humanize_service:
        content.title = humanize_service.humanize_title(content.title)
        content.body = humanize_service.humanize_body(content.body)
    
    # P0: 检查多样性
    diversity_check = None
    if check_diversity and diversity_controller:
        diversity_check = diversity_controller.validate_content(
            content.title, content.body, content.tags
        )
    
    # P0: 评估人性化程度
    humanness_score = None
    if humanize and humanize_service:
        humanness_score = humanize_service.score_humanness(
            content.title + "\n" + content.body
        )
    
    # 统计应用的优化数量
    hints_applied = len(extra_hints) if extra_hints else 0
    
    return {
        "content": content,
        "reference_count": len(reference_samples),
        "calibration": {
            "avg_title_length": calibration_data.avg_title_length,
            "common_patterns": calibration_data.common_opening_patterns,
            "emoji_rate": calibration_data.emoji_usage_rate,
            "common_tags": calibration_data.common_tags
        },
        "p0_enhancements": {
            "learning_hints_applied": hints_applied,
            "diversity_check": diversity_check,
            "humanness_score": humanness_score
        }
    }


# ==================== 素材库 API ====================

class AddImageRequest(BaseModel):
    image_data: str  # base64 或 URL
    filename: Optional[str] = None
    tags: Optional[list] = None
    description: Optional[str] = None
    source: Optional[str] = None


class AddTextRequest(BaseModel):
    content: str
    text_type: str = "copy"  # copy/title/tag/hook
    tags: Optional[list] = None
    description: Optional[str] = None
    source: Optional[str] = None
    performance: Optional[dict] = None


@app.get("/api/materials/stats")
async def get_materials_stats():
    """获取素材库统计"""
    library = get_material_library()
    return library.get_stats()


@app.post("/api/materials/images")
async def add_material_image(request: AddImageRequest):
    """添加图片素材"""
    library = get_material_library()
    result = library.add_image(
        image_data=request.image_data,
        filename=request.filename,
        tags=request.tags,
        description=request.description,
        source=request.source
    )
    return {"success": True, "material": result}


@app.get("/api/materials/images")
async def get_material_images(tags: Optional[str] = None, limit: int = 20, offset: int = 0):
    """获取图片素材列表"""
    library = get_material_library()
    tag_list = tags.split(",") if tags else None
    images = library.get_images(tags=tag_list, limit=limit, offset=offset)
    return {"images": images, "total": len(library.index["images"])}


@app.get("/api/materials/images/{material_id}")
async def get_material_image_data(material_id: str):
    """获取图片数据"""
    library = get_material_library()
    data = library.get_image_data(material_id)
    if not data:
        raise HTTPException(status_code=404, detail="Image not found")
    return {"image_data": data}


@app.delete("/api/materials/images/{material_id}")
async def delete_material_image(material_id: str):
    """删除图片素材"""
    library = get_material_library()
    success = library.delete_image(material_id)
    return {"success": success}


@app.post("/api/materials/texts")
async def add_material_text(request: AddTextRequest):
    """添加文案素材"""
    library = get_material_library()
    result = library.add_text(
        content=request.content,
        text_type=request.text_type,
        tags=request.tags,
        description=request.description,
        source=request.source,
        performance=request.performance
    )
    return {"success": True, "material": result}


@app.get("/api/materials/texts")
async def get_material_texts(
    text_type: Optional[str] = None,
    tags: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """获取文案素材列表"""
    library = get_material_library()
    tag_list = tags.split(",") if tags else None
    texts = library.get_texts(text_type=text_type, tags=tag_list, limit=limit, offset=offset)
    return {"texts": texts, "total": len(library.index["texts"])}


@app.delete("/api/materials/texts/{material_id}")
async def delete_material_text(material_id: str):
    """删除文案素材"""
    library = get_material_library()
    success = library.delete_text(material_id)
    return {"success": success}


@app.get("/api/materials/relevant")
async def get_relevant_materials(topic: str, max_images: int = 5, max_texts: int = 10):
    """获取与话题相关的素材"""
    library = get_material_library()
    materials = library.get_relevant_materials(
        topic=topic,
        max_images=max_images,
        max_texts=max_texts
    )
    return materials


# ==================== 历史发帖学习 API ====================

class AddHistoryPostRequest(BaseModel):
    note_id: str
    title: str
    body: str
    tags: list
    cover_image: Optional[str] = None
    posted_at: Optional[str] = None
    performance: Optional[dict] = None


class ImportHistoryRequest(BaseModel):
    posts: list  # MCP返回的笔记列表


class UpdatePerformanceRequest(BaseModel):
    note_id: str
    performance: dict


@app.get("/api/history/stats")
async def get_history_stats():
    """获取历史发帖统计"""
    learner = get_history_learner()
    return learner.get_stats()


@app.get("/api/history/profile")
async def get_user_profile():
    """获取用户画像"""
    learner = get_history_learner()
    return learner.get_profile()


@app.get("/api/history/style-prompt")
async def get_style_prompt():
    """获取基于用户风格的生成提示词"""
    learner = get_history_learner()
    prompt = learner.get_style_prompt()
    return {"prompt": prompt}


@app.post("/api/history/posts")
async def add_history_post(request: AddHistoryPostRequest):
    """添加历史发帖记录"""
    learner = get_history_learner()
    result = learner.add_post(
        note_id=request.note_id,
        title=request.title,
        body=request.body,
        tags=request.tags,
        cover_image=request.cover_image,
        posted_at=request.posted_at,
        performance=request.performance
    )
    return {"success": True, "post": result}


@app.get("/api/history/posts")
async def get_history_posts(limit: int = 50, offset: int = 0, sort_by: str = "posted_at"):
    """获取历史发帖列表"""
    learner = get_history_learner()
    posts = learner.get_history(limit=limit, offset=offset, sort_by=sort_by)
    return {"posts": posts, "total": len(learner.history)}


@app.post("/api/history/import")
async def import_history_from_xhs(request: ImportHistoryRequest):
    """从小红书导入历史发帖"""
    learner = get_history_learner()
    imported = learner.import_from_xhs(request.posts)
    return {"success": True, "imported_count": imported}


@app.post("/api/history/update-performance")
async def update_post_performance(request: UpdatePerformanceRequest):
    """更新笔记效果数据"""
    learner = get_history_learner()
    success = learner.update_performance(request.note_id, request.performance)
    return {"success": success}


@app.post("/api/history/analyze")
async def analyze_history():
    """手动触发完整分析"""
    learner = get_history_learner()
    learner.analyze_all()
    return {"success": True, "profile": learner.get_profile()}


@app.get("/api/history/reference")
async def get_reference_content(topic: str, max_count: int = 3):
    """获取相关的历史发帖作为参考"""
    learner = get_history_learner()
    refs = learner.get_reference_content(topic=topic, max_count=max_count)
    return {"references": refs}


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
