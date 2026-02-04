"""
NoteTrial API - 多项目管理模块
项目 CRUD + 成员管理 + 内容关联
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

from .auth import get_current_user
from .schemas import StandardResponse, PaginatedResponse

router = APIRouter(prefix="/projects", tags=["项目管理"])

# ============ 枚举定义 ============

class ProjectRole(str, Enum):
    """项目成员角色"""
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


# ============ Pydantic Models ============

class ProjectBase(BaseModel):
    """项目基础模型"""
    name: str = Field(..., max_length=100, description="项目名称")
    description: Optional[str] = Field(None, description="项目描述")


class ProjectCreate(ProjectBase):
    """创建项目请求"""
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="项目设置")


class ProjectUpdate(BaseModel):
    """更新项目请求"""
    name: Optional[str] = Field(None, max_length=100, description="项目名称")
    description: Optional[str] = Field(None, description="项目描述")
    settings: Optional[Dict[str, Any]] = Field(None, description="项目设置")


class Project(ProjectBase):
    """项目完整模型"""
    id: str
    owner_id: str
    settings: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProjectMemberBase(BaseModel):
    """项目成员基础模型"""
    user_id: str = Field(..., description="用户 ID")
    role: ProjectRole = Field(..., description="角色")


class ProjectMemberCreate(ProjectMemberBase):
    """添加成员请求"""
    pass


class ProjectMemberResponse(BaseModel):
    """成员响应模型"""
    id: str
    project_id: str
    user_id: str
    username: Optional[str] = None
    role: ProjectRole
    created_at: datetime


class ProjectContentAdd(BaseModel):
    """添加内容到项目请求"""
    content_id: str = Field(..., description="内容 ID")


class ProjectContentResponse(BaseModel):
    """项目内容关联响应"""
    id: str
    project_id: str
    content_id: str
    added_at: datetime


# ============ 模拟数据存储 ============

# 项目存储
projects_db: Dict[str, Project] = {}

# 项目成员存储
project_members_db: Dict[str, ProjectMemberResponse] = {}

# 项目内容关联存储
project_contents_db: Dict[str, List[ProjectContentResponse]] = {}

# 用户信息缓存（模拟）
users_info_cache: Dict[str, str] = {}


def get_user_username(user_id: str) -> str:
    """获取用户名（模拟）"""
    if user_id in users_info_cache:
        return users_info_cache[user_id]
    # 模拟返回
    return f"user_{user_id[:8]}"


def check_project_permission(
    project_id: str, 
    user_id: str, 
    required_roles: List[ProjectRole] = None
) -> ProjectMemberResponse:
    """检查用户在项目中的权限"""
    member_key = f"{project_id}_{user_id}"
    
    if member_key not in project_members_db:
        raise HTTPException(
            status_code=403,
            detail="您不是该项目成员"
        )
    
    member = project_members_db[member_key]
    
    if required_roles and member.role not in required_roles:
        raise HTTPException(
            status_code=403,
            detail=f"需要 {required_roles} 角色权限"
        )
    
    return member


def is_project_owner(project_id: str, user_id: str) -> bool:
    """检查是否是项目所有者"""
    if project_id not in projects_db:
        return False
    return projects_db[project_id].owner_id == user_id


# ============ API Endpoints ============

@router.get("", response_model=PaginatedResponse[Project])
async def list_projects(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: dict = Depends(get_current_user)
) -> PaginatedResponse[Project]:
    """获取当前用户参与的项目列表"""
    user_id = current_user["user_id"]
    
    # 获取用户参与的所有项目
    user_projects = []
    for project in projects_db.values():
        # 检查是否是成员
        member_key = f"{project.id}_{user_id}"
        if member_key in project_members_db or project.owner_id == user_id:
            user_projects.append(project)
    
    # 按更新时间降序排序
    user_projects.sort(key=lambda x: x.updated_at, reverse=True)
    
    total = len(user_projects)
    start = (page - 1) * page_size
    end = start + page_size
    items = user_projects[start:end]
    
    return PaginatedResponse.create(items, total, page, page_size)


@router.post("", response_model=StandardResponse[Project])
async def create_project(
    request: ProjectCreate,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse[Project]:
    """创建新项目（创建者自动成为 owner）"""
    user_id = current_user["user_id"]
    project_id = str(uuid.uuid4())
    
    # 创建项目
    project = Project(
        id=project_id,
        name=request.name,
        description=request.description,
        owner_id=user_id,
        settings=request.settings or {},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    projects_db[project_id] = project
    
    # 创建者自动成为 owner
    member_id = str(uuid.uuid4())
    member = ProjectMemberResponse(
        id=member_id,
        project_id=project_id,
        user_id=user_id,
        username=get_user_username(user_id),
        role=ProjectRole.OWNER,
        created_at=datetime.utcnow()
    )
    project_members_db[f"{project_id}_{user_id}"] = member
    
    # 初始化内容列表
    project_contents_db[project_id] = []
    
    return StandardResponse(
        data=project,
        message="项目创建成功"
    )


@router.get("/{project_id}", response_model=StandardResponse[Project])
async def get_project(
    project_id: str,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse[Project]:
    """获取项目详情"""
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    return StandardResponse(data=projects_db[project_id])


@router.put("/{project_id}", response_model=StandardResponse[Project])
async def update_project(
    project_id: str,
    request: ProjectUpdate,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse[Project]:
    """更新项目信息"""
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    user_id = current_user["user_id"]
    
    # 检查权限（需要 editor 或 owner 权限）
    check_project_permission(
        project_id, 
        user_id, 
        [ProjectRole.OWNER, ProjectRole.EDITOR]
    )
    
    project = projects_db[project_id]
    
    # 更新字段
    if request.name is not None:
        project.name = request.name
    if request.description is not None:
        project.description = request.description
    if request.settings is not None:
        project.settings = request.settings
    
    project.updated_at = datetime.utcnow()
    
    return StandardResponse(
        data=project,
        message="项目更新成功"
    )


@router.delete("/{project_id}", response_model=StandardResponse)
async def delete_project(
    project_id: str,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse:
    """删除项目（仅 owner 可删除）"""
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    user_id = current_user["user_id"]
    
    # 检查是否是 owner
    if not is_project_owner(project_id, user_id):
        raise HTTPException(
            status_code=403,
            detail="只有项目所有者可以删除项目"
        )
    
    # 删除项目
    del projects_db[project_id]
    
    # 删除关联的成员
    members_to_delete = [
        key for key in project_members_db.keys() 
        if key.startswith(f"{project_id}_")
    ]
    for key in members_to_delete:
        del project_members_db[key]
    
    # 删除关联的内容
    if project_id in project_contents_db:
        del project_contents_db[project_id]
    
    return StandardResponse(message="项目删除成功")


@router.get("/{project_id}/members", response_model=StandardResponse[List[ProjectMemberResponse]])
async def get_project_members(
    project_id: str,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse[List[ProjectMemberResponse]]:
    """获取项目成员列表"""
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 检查权限（需要是成员）
    user_id = current_user["user_id"]
    check_project_permission(project_id, user_id)
    
    # 获取所有成员
    members = [
        member for key, member in project_members_db.items()
        if key.startswith(f"{project_id}_")
    ]
    
    return StandardResponse(data=members)


@router.post("/{project_id}/members", response_model=StandardResponse[ProjectMemberResponse])
async def add_project_member(
    project_id: str,
    request: ProjectMemberCreate,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse[ProjectMemberResponse]:
    """添加项目成员（需要 owner 权限）"""
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    operator_id = current_user["user_id"]
    
    # 检查是否是 owner
    check_project_permission(project_id, operator_id, [ProjectRole.OWNER])
    
    member_key = f"{project_id}_{request.user_id}"
    
    # 检查成员是否已存在
    if member_key in project_members_db:
        raise HTTPException(status_code=400, detail="该用户已是项目成员")
    
    member_id = str(uuid.uuid4())
    member = ProjectMemberResponse(
        id=member_id,
        project_id=project_id,
        user_id=request.user_id,
        username=get_user_username(request.user_id),
        role=request.role,
        created_at=datetime.utcnow()
    )
    
    project_members_db[member_key] = member
    
    return StandardResponse(
        data=member,
        message="成员添加成功"
    )


@router.delete("/{project_id}/members/{user_id}", response_model=StandardResponse)
async def remove_project_member(
    project_id: str,
    user_id: str,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse:
    """移除项目成员（需要 owner 权限）"""
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    operator_id = current_user["user_id"]
    
    # 检查是否是 owner
    check_project_permission(project_id, operator_id, [ProjectRole.OWNER])
    
    # 不能移除自己（owner）
    if user_id == operator_id:
        raise HTTPException(status_code=400, detail="不能移除自己")
    
    member_key = f"{project_id}_{user_id}"
    
    if member_key not in project_members_db:
        raise HTTPException(status_code=404, detail="该用户不是项目成员")
    
    # 不能移除 owner
    member = project_members_db[member_key]
    if member.role == ProjectRole.OWNER:
        raise HTTPException(status_code=400, detail="不能移除项目所有者")
    
    del project_members_db[member_key]
    
    return StandardResponse(message="成员移除成功")


@router.get("/{project_id}/contents", response_model=StandardResponse[List[ProjectContentResponse]])
async def get_project_contents(
    project_id: str,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse[List[ProjectContentResponse]]:
    """获取项目关联的内容列表"""
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 检查权限（需要是成员）
    user_id = current_user["user_id"]
    check_project_permission(project_id, user_id)
    
    contents = project_contents_db.get(project_id, [])
    
    return StandardResponse(data=contents)


@router.post("/{project_id}/contents", response_model=StandardResponse[ProjectContentResponse])
async def add_project_content(
    project_id: str,
    request: ProjectContentAdd,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse[ProjectContentResponse]:
    """添加内容到项目（需要 editor 或 owner 权限）"""
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    user_id = current_user["user_id"]
    
    # 检查权限
    check_project_permission(
        project_id, 
        user_id, 
        [ProjectRole.OWNER, ProjectRole.EDITOR]
    )
    
    # 初始化内容列表
    if project_id not in project_contents_db:
        project_contents_db[project_id] = []
    
    # 检查内容是否已关联
    existing = [
        c for c in project_contents_db[project_id]
        if c.content_id == request.content_id
    ]
    if existing:
        raise HTTPException(status_code=400, detail="该内容已在项目中")
    
    # 创建关联
    content_link = ProjectContentResponse(
        id=str(uuid.uuid4()),
        project_id=project_id,
        content_id=request.content_id,
        added_at=datetime.utcnow()
    )
    
    project_contents_db[project_id].append(content_link)
    
    return StandardResponse(
        data=content_link,
        message="内容添加成功"
    )


@router.delete("/{project_id}/contents/{content_id}", response_model=StandardResponse)
async def remove_project_content(
    project_id: str,
    content_id: str,
    current_user: dict = Depends(get_current_user)
) -> StandardResponse:
    """从项目移除内容（需要 editor 或 owner 权限）"""
    if project_id not in projects_db:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    user_id = current_user["user_id"]
    
    # 检查权限
    check_project_permission(
        project_id, 
        user_id, 
        [ProjectRole.OWNER, ProjectRole.EDITOR]
    )
    
    if project_id not in project_contents_db:
        raise HTTPException(status_code=404, detail="项目内容列表不存在")
    
    # 查找并删除关联
    contents = project_contents_db[project_id]
    target = None
    for c in contents:
        if c.content_id == content_id:
            target = c
            break
    
    if not target:
        raise HTTPException(status_code=404, detail="该内容不在项目中")
    
    contents.remove(target)
    
    return StandardResponse(message="内容移除成功")
