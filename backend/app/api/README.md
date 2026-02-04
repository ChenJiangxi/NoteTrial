# NoteTrial API 模块文档

## 概述

本目录包含 NoteTrial 后端的 API 路由模块，采用模块化设计，每个模块独立文件。

## 模块结构

```
api/
├── __init__.py          # 模块导出
├── auth.py             # JWT 认证
├── schemas.py          # 数据模型定义
├── contents.py         # 内容管理 API
├── ab_tests.py         # A/B 测试管理 API
├── posts.py            # 发布记录 API
├── materials.py        # 素材库管理 API
└── analytics.py        # 数据分析 API
```

## API 端点

### 认证模块 (auth)
| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v1/auth/login` | 用户登录 |
| POST | `/api/v1/auth/register` | 用户注册 |
| GET | `/api/v1/auth/me` | 获取当前用户 |
| POST | `/api/v1/auth/refresh` | 刷新 Token |
| POST | `/api/v1/auth/logout` | 退出登录 |

### 内容管理 (contents)
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/contents` | 获取内容列表（分页） |
| GET | `/api/v1/contents/{id}` | 获取内容详情 |
| POST | `/api/v1/contents` | 创建内容 |
| PUT | `/api/v1/contents/{id}` | 更新内容 |
| DELETE | `/api/v1/contents/{id}` | 删除内容 |
| POST | `/api/v1/contents/generate` | AI 生成内容 |
| POST | `/api/v1/contents/{id}/duplicate` | 复制内容 |
| POST | `/api/v1/contents/{id}/status` | 更新状态 |

### A/B 测试 (ab_tests)
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/ab-tests` | 获取测试列表 |
| GET | `/api/v1/ab-tests/{id}` | 获取测试详情 |
| POST | `/api/v1/ab-tests` | 创建测试 |
| PUT | `/api/v1/ab-tests/{id}` | 更新测试 |
| DELETE | `/api/v1/ab-tests/{id}` | 删除测试 |
| POST | `/api/v1/ab-tests/{id}/run` | 运行测试 |
| POST | `/api/v1/ab-tests/{id}/cancel` | 取消测试 |
| GET | `/api/v1/ab-tests/{id}/progress` | 获取进度 |
| GET | `/api/v1/ab-tests/{id}/comparison` | 版本对比 |

### 发布记录 (posts)
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/posts` | 获取发布记录 |
| GET | `/api/v1/posts/{id}` | 获取记录详情 |
| POST | `/api/v1/posts` | 创建记录 |
| DELETE | `/api/v1/posts/{id}` | 删除记录 |
| POST | `/api/v1/posts/publish` | MCP 发布 |
| GET | `/api/v1/posts/mcp/status` | MCP 状态 |
| POST | `/api/v1/posts/{id}/result` | 更新发布结果 |
| POST | `/api/v1/posts/sync` | 从平台同步 |

### 素材库 (materials)
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/materials/images` | 图片列表 |
| GET | `/api/v1/materials/images/{id}` | 图片详情 |
| POST | `/api/v1/materials/images` | 添加图片 |
| DELETE | `/api/v1/materials/images/{id}` | 删除图片 |
| GET | `/api/v1/materials/texts` | 文案列表 |
| GET | `/api/v1/materials/texts/{id}` | 文案详情 |
| POST | `/api/v1/materials/texts` | 添加文案 |
| DELETE | `/api/v1/materials/texts/{id}` | 删除文案 |
| POST | `/api/v1/materials/search` | 搜索素材 |
| GET | `/api/v1/materials/stats` | 素材统计 |
| GET | `/api/v1/materials/relevant` | 相关素材 |

### 数据分析 (analytics)
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/v1/analytics/overview` | 数据概览 |
| GET | `/api/v1/analytics/trends/{metric}` | 趋势数据 |
| GET | `/api/v1/analytics/top-content` | 热门内容 |
| POST | `/api/v1/analytics/compare` | 对比分析 |
| GET | `/api/v1/analytics/content/{id}` | 内容分析 |
| GET | `/api/v1/analytics/audience` | 受众分析 |
| GET | `/api/v1/analytics/topics` | 话题分析 |
| GET | `/api/v1/analytics/export` | 导出数据 |
| GET | `/api/v1/analytics/performance-breakdown` | 性能分解 |

## 特性

### JWT 认证
- 所有 API 端点（认证相关除外）都需要 Bearer Token
- Token 有效期：24 小时

### 分页支持
- 所有列表接口支持 `page` 和 `page_size` 参数
- 响应包含分页元信息

### 标准化响应
```json
{
  "status": "success",
  "message": "操作成功",
  "data": {...},
  "error": null
}
```

分页响应：
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "total_pages": 5,
  "has_next": true,
  "has_prev": false
}
```
