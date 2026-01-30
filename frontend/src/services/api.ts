import axios from 'axios'
import type {
  ChatRequest,
  ChatResponse,
  ABTestRequest,
  CrowdTestResult,
  GenerateVariantRequest,
  ContentItem,
} from '../types/api'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// 对话接口
export async function sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
  const response = await api.post<ChatResponse>('/chat', request)
  return response.data
}

// 生成变体
export async function generateVariant(request: GenerateVariantRequest): Promise<ContentItem> {
  const response = await api.post<ContentItem>('/generate-variant', request)
  return response.data
}

// 执行 CrowdTest
export async function runCrowdTest(request: ABTestRequest): Promise<CrowdTestResult> {
  const response = await api.post<CrowdTestResult>('/crowdtest', request)
  return response.data
}

// 改进内容
export async function improveContent(
  content: ContentItem,
  suggestions: string[]
): Promise<ContentItem> {
  const response = await api.post<ContentItem>('/improve-content', {
    content,
    suggestions,
  })
  return response.data
}

// 检查 MCP 状态
export async function checkMCPStatus(): Promise<{ available: boolean; url: string }> {
  const response = await api.get('/mcp-status')
  return response.data
}

// 获取 MCP 工具列表
export async function getMCPTools(): Promise<{ tools: Array<{ name: string; description: string }> }> {
  const response = await api.get('/mcp-tools')
  return response.data
}

// 搜索相关图片（智能配图）
export async function searchImages(topic: string, limit: number = 5): Promise<string[]> {
  const response = await api.get<{ images: string[]; topic: string }>('/search-images', {
    params: { topic, limit }
  })
  return response.data.images
}

// 搜索小红书内容
export async function searchFeeds(keyword: string, limit: number = 20): Promise<{
  feeds: Array<{
    id: string
    title: string
    desc?: string
    likes?: number
    collects?: number
  }>
  count: number
}> {
  const response = await api.get('/search-feeds', {
    params: { keyword, limit }
  })
  return response.data
}

// 健康检查
export async function healthCheck(): Promise<{
  status: string
  services: {
    simulator: boolean
    calibrator: boolean
    generator: boolean
    xiaohongshu_mcp: boolean
  }
}> {
  const response = await api.get('/health')
  return response.data
}

// 发布内容到小红书
export async function publishContent(content: ContentItem): Promise<{
  success: boolean
  message?: string
  note_id?: string
  data?: any
}> {
  const response = await api.post('/publish-content', content)
  return response.data
}

// 获取登录二维码
export async function getLoginQRCode(): Promise<any> {
  const response = await api.get('/login-qrcode')
  return response.data
}

// 检查登录状态
export async function checkLoginStatus(): Promise<{
  result: any
}> {
  const response = await api.get('/xhs-login-status')
  return response.data
}
