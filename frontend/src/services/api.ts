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

// 启动带进度的 CrowdTest 任务
export async function startCrowdTest(request: ABTestRequest): Promise<{
  job_id: string
  status: 'running'
}> {
  const response = await api.post('/crowdtest/start', request)
  return response.data
}

// 查询 CrowdTest 任务进度
export async function getCrowdTestProgress(jobId: string): Promise<{
  job_id: string
  status: 'running' | 'completed' | 'failed'
  progress: number
  result?: CrowdTestResult
  error?: string
}> {
  const response = await api.get(`/crowdtest/progress/${jobId}`)
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

// 搜索相关图片（智能配图）- 已废弃
export async function searchImages(topic: string, limit: number = 5): Promise<string[]> {
  const response = await api.get<{ images: string[]; topic: string }>('/search-images', {
    params: { topic, limit }
  })
  return response.data.images
}

// 使用 AI 生成图片（用于自动配图）
export async function generateImage(topic: string, style: string = '小红书风格'): Promise<string> {
  const response = await api.post<{ image: string; topic: string; success: boolean }>('/generate-image', {
    topic,
    style
  })
  return response.data.image
}

// 生成多页内容大纲 (RedInk 风格)
export async function generateOutline(
  topic: string,
  pageCount: number = 6,
  style: string = '小红书风格'
): Promise<{
  success: boolean
  title: string
  pages: Array<{
    index: number
    type: 'cover' | 'content' | 'summary'
    content: string
  }>
}> {
  const response = await api.post('/generate-outline', {
    topic,
    page_count: pageCount,
    style
  })
  return response.data
}

// 批量生成多页图片 (封面优先策略)
export async function generateBatchImages(
  pages: Array<{ index: number; type: string; content: string }>,
  topic: string = '',
  fullOutline: string = ''
): Promise<{
  success: boolean
  pages: Array<{
    index: number
    type: string
    content: string
    image?: string
    status: 'done' | 'error' | 'pending'
    error?: string
  }>
  stats: {
    total: number
    success: number
    failed: number
  }
}> {
  const response = await api.post('/generate-batch-images', {
    pages,
    topic,
    full_outline: fullOutline
  })
  return response.data
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

// 通过标题同步笔记数据
export async function syncNotes(titles: string[]): Promise<{
  notes: Array<{
    noteId: string
    xsecToken: string
    title: string
    likedCount: number
    collectedCount: number
    commentCount: number
    shareCount: number
    matchedTitle: string
  }>
  error?: string
}> {
  const response = await api.post('/sync-notes', { titles })
  return response.data
}

// 获取单个笔记的效果数据
export async function getNoteStats(
  noteId: string, 
  options?: { xsecToken?: string; titleKeyword?: string }
): Promise<{
  result: any
}> {
  const params: { xsec_token?: string; title_keyword?: string } = {}
  if (options?.xsecToken) {
    params.xsec_token = options.xsecToken
  }
  if (options?.titleKeyword) {
    params.title_keyword = options.titleKeyword
  }
  const response = await api.get(`/note-stats/${noteId}`, { params })
  return response.data
}

// 自动生成内容（低AI味）
export async function autoGenerateContent(
  topic: string,
  goals: string[] = ['maximize_save'],
  audience: string = '小红书用户',
  referenceCount: number = 10
): Promise<{
  content: ContentItem
  reference_count: number
  calibration: {
    avg_title_length: number
    common_patterns: string[]
    emoji_rate: number
    common_tags: string[]
  }
}> {
  const response = await api.post('/auto-generate', null, {
    params: { topic, goals, audience, reference_count: referenceCount }
  })
  return response.data
}

// 根据内容生成封面图
export async function generateCover(
  content: ContentItem,
  topic: string = ''
): Promise<{
  success: boolean
  image?: string
  error?: string
}> {
  const response = await api.post('/generate-cover', content, {
    params: { topic }
  })
  return response.data
}

// 智能扩展话题
export async function expandTopic(briefInput: string): Promise<{
  success: boolean
  data: {
    topic: string
    detailed_topic: string
    suggested_angles: string[]
    target_audiences: string[]
    content_types: string[]
    hot_keywords: string[]
  }
}> {
  const response = await api.post('/expand-topic', { brief_input: briefInput })
  return response.data
}


// ============ P0 新增 API：学习引擎 ============

// 获取学习引擎统计
export async function getLearningStats(): Promise<{
  total_records: number
  analyzed_records: number
  good_patterns: Record<string, number>
  bad_patterns: Record<string, number>
  performance_stats: {
    avg_score: number
    best_score: number
    worst_score: number
  }
}> {
  const response = await api.get('/learning/stats')
  return response.data
}

// 获取学习引擎优化建议
export async function getLearningHints(): Promise<{
  hints: string[]
  prompt_enhancement: string
}> {
  const response = await api.get('/learning/hints')
  return response.data
}

// 记录内容到学习引擎
export async function recordContent(
  contentId: string,
  title: string,
  body: string,
  tags: string[] = [],
  topic: string = ''
): Promise<{ success: boolean; message: string }> {
  const response = await api.post('/learning/record', {
    content_id: contentId,
    title,
    body,
    tags,
    topic
  })
  return response.data
}

// 更新内容效果数据
export async function updateContentStats(
  contentId: string,
  stats: { likes?: number; collects?: number; comments?: number; shares?: number }
): Promise<{ success: boolean; message: string }> {
  const response = await api.post('/learning/update-stats', {
    content_id: contentId,
    stats
  })
  return response.data
}


// ============ P0 新增 API：多样性控制 ============

// 获取多样性统计
export async function getDiversityStats(): Promise<{
  total_titles: number
  recent_titles_count: number
  unique_tags: number
  top_tags: [string, number][]
  recent_styles: string[]
}> {
  const response = await api.get('/diversity/stats')
  return response.data
}

// 检查内容多样性
export async function checkContentDiversity(
  title: string,
  body?: string,
  tags?: string
): Promise<{
  is_valid: boolean
  issues: string[]
  suggestions: string[]
}> {
  const response = await api.get('/diversity/check', {
    params: { title, body, tags }
  })
  return response.data
}

// 获取多样性提示
export async function getDiversityPrompt(): Promise<{
  prompt: string
  suggested_style: string
}> {
  const response = await api.get('/diversity/prompt')
  return response.data
}


// ============ P0 新增 API：自动监控 ============

// 添加监控任务
export async function addMonitorTask(
  contentId: string,
  noteId: string
): Promise<{
  success: boolean
  task: { content_id: string; note_id: string; status: string }
}> {
  const response = await api.post('/monitor/add', {
    content_id: contentId,
    note_id: noteId
  })
  return response.data
}

// 获取监控任务列表
export async function getMonitorTasks(): Promise<{
  tasks: Array<{
    content_id: string
    note_id: string
    status: string
    check_count: number
    total_checks: number
    created_at: string
    last_check: string | null
    stats: Record<string, number> | null
  }>
  pending_count: number
}> {
  const response = await api.get('/monitor/tasks')
  return response.data
}

// 手动执行一次监控检查
export async function runMonitorOnce(): Promise<{
  success: boolean
  completed_count: number
  remaining: number
}> {
  const response = await api.post('/monitor/run-once')
  return response.data
}


// ============ P0 新增 API：AI检测规避 ============

// 人性化处理内容
export async function humanizeContent(
  title: string,
  body: string
): Promise<{
  title: string
  body: string
  original_score: { score: number; issues: string[]; ai_patterns_found: number }
  new_score: { score: number; issues: string[]; ai_patterns_found: number }
  improvement: number
}> {
  const response = await api.post('/humanize/content', { title, body })
  return response.data
}

// 检查文本人性化程度
export async function checkHumanness(text: string): Promise<{
  score: number
  issues: string[]
  ai_patterns_found: number
}> {
  const response = await api.get('/humanize/check', { params: { text } })
  return response.data
}

// 获取人性化写作提示
export async function getHumanizePrompt(): Promise<{
  prompt: string
}> {
  const response = await api.get('/humanize/prompt')
  return response.data
}


// ============ 增强版自动生成（集成P0功能）============

export async function autoGenerateEnhanced(
  topic: string,
  goals: string[] = ['maximize_save'],
  audience: string = '小红书用户',
  referenceCount: number = 10,
  useLearning: boolean = true,
  checkDiversity: boolean = true,
  humanize: boolean = true
): Promise<{
  content: ContentItem
  reference_count: number
  calibration: {
    avg_title_length: number
    common_patterns: string[]
    emoji_rate: number
    common_tags: string[]
  }
  p0_enhancements: {
    learning_hints_applied: number
    diversity_check: { is_valid: boolean; issues: string[]; suggestions: string[] } | null
    humanness_score: { score: number; issues: string[]; ai_patterns_found: number } | null
  }
}> {
  const response = await api.post('/auto-generate-enhanced', null, {
    params: {
      topic,
      goals,
      audience,
      reference_count: referenceCount,
      use_learning: useLearning,
      check_diversity: checkDiversity,
      humanize
    }
  })
  return response.data
}

// ==================== 素材库 API ====================

export interface MaterialImage {
  id: string
  type: string
  filename: string
  path: string
  tags: string[]
  description: string
  source: string
  created_at: string
  used_count: number
}

export interface MaterialText {
  id: string
  type: string
  text_type: string
  content: string
  tags: string[]
  description: string
  source: string
  performance: Record<string, number>
  created_at: string
  used_count: number
}

export async function getMaterialStats(): Promise<{
  total_images: number
  total_texts: number
  total_collections: number
  tags: string[]
  text_types: Record<string, number>
}> {
  const response = await api.get('/materials/stats')
  return response.data
}

export async function addMaterialImage(
  imageData: string,
  options?: {
    filename?: string
    tags?: string[]
    description?: string
    source?: string
  }
): Promise<{ success: boolean; material: MaterialImage }> {
  const response = await api.post('/materials/images', {
    image_data: imageData,
    ...options
  })
  return response.data
}

export async function getMaterialImages(
  tags?: string[],
  limit: number = 20,
  offset: number = 0
): Promise<{ images: MaterialImage[]; total: number }> {
  const response = await api.get('/materials/images', {
    params: { tags: tags?.join(','), limit, offset }
  })
  return response.data
}

export async function getMaterialImageData(materialId: string): Promise<{ image_data: string }> {
  const response = await api.get(`/materials/images/${materialId}`)
  return response.data
}

export async function deleteMaterialImage(materialId: string): Promise<{ success: boolean }> {
  const response = await api.delete(`/materials/images/${materialId}`)
  return response.data
}

export async function addMaterialText(
  content: string,
  textType: string = 'copy',
  options?: {
    tags?: string[]
    description?: string
    source?: string
    performance?: Record<string, number>
  }
): Promise<{ success: boolean; material: MaterialText }> {
  const response = await api.post('/materials/texts', {
    content,
    text_type: textType,
    ...options
  })
  return response.data
}

export async function getMaterialTexts(
  textType?: string,
  tags?: string[],
  limit: number = 50,
  offset: number = 0
): Promise<{ texts: MaterialText[]; total: number }> {
  const response = await api.get('/materials/texts', {
    params: { text_type: textType, tags: tags?.join(','), limit, offset }
  })
  return response.data
}

export async function deleteMaterialText(materialId: string): Promise<{ success: boolean }> {
  const response = await api.delete(`/materials/texts/${materialId}`)
  return response.data
}

export async function getRelevantMaterials(
  topic: string,
  maxImages: number = 5,
  maxTexts: number = 10
): Promise<{ images: MaterialImage[]; texts: MaterialText[] }> {
  const response = await api.get('/materials/relevant', {
    params: { topic, max_images: maxImages, max_texts: maxTexts }
  })
  return response.data
}

// ==================== 历史发帖学习 API ====================

export interface HistoryPost {
  note_id: string
  title: string
  body: string
  tags: string[]
  cover_image?: string
  posted_at: string
  performance: Record<string, number>
  analyzed: boolean
}

export interface UserProfile {
  writing_style: {
    tone: string
    emoji_density: number
    avg_title_length: number
    avg_body_length: number
    paragraph_style: string
    punctuation_style: string
  }
  content_preferences: {
    favorite_topics: string[]
    favorite_tags: string[]
    common_hooks: string[]
    common_endings: string[]
  }
  performance_insights: {
    best_performing_topics: string[]
    best_performing_tags: string[]
    optimal_title_length: number
    optimal_body_length: number
    best_posting_time: string | null
  }
  last_updated: string | null
}

export async function getHistoryStats(): Promise<{
  total_posts: number
  analyzed_posts: number
  total_engagement: Record<string, number>
  avg_engagement: Record<string, number>
  profile_updated: string | null
  writing_tone: string
  top_tags: string[]
}> {
  const response = await api.get('/history/stats')
  return response.data
}

export async function getUserProfile(): Promise<UserProfile> {
  const response = await api.get('/history/profile')
  return response.data
}

export async function getStylePrompt(): Promise<{ prompt: string }> {
  const response = await api.get('/history/style-prompt')
  return response.data
}

export async function addHistoryPost(post: {
  note_id: string
  title: string
  body: string
  tags: string[]
  cover_image?: string
  posted_at?: string
  performance?: Record<string, number>
}): Promise<{ success: boolean; post: HistoryPost }> {
  const response = await api.post('/history/posts', post)
  return response.data
}

export async function getHistoryPosts(
  limit: number = 50,
  offset: number = 0,
  sortBy: string = 'posted_at'
): Promise<{ posts: HistoryPost[]; total: number }> {
  const response = await api.get('/history/posts', {
    params: { limit, offset, sort_by: sortBy }
  })
  return response.data
}

export async function importHistoryFromXHS(
  posts: Array<Record<string, unknown>>
): Promise<{ success: boolean; imported_count: number }> {
  const response = await api.post('/history/import', { posts })
  return response.data
}

export async function updatePostPerformance(
  noteId: string,
  performance: Record<string, number>
): Promise<{ success: boolean }> {
  const response = await api.post('/history/update-performance', {
    note_id: noteId,
    performance
  })
  return response.data
}

export async function analyzeHistory(): Promise<{ success: boolean; profile: UserProfile }> {
  const response = await api.post('/history/analyze')
  return response.data
}

export async function getReferenceContent(
  topic: string,
  maxCount: number = 3
): Promise<{ references: HistoryPost[] }> {
  const response = await api.get('/history/reference', {
    params: { topic, max_count: maxCount }
  })
  return response.data
}


// ==================== 多源内容生成 API ====================

export interface MultiSourceGenerateRequest {
  topic: string
  goals?: string[]
  audience?: string
  user_materials?: string
  use_xhs_samples?: boolean
  use_web_search?: boolean
  use_material_library?: boolean
  humanize?: boolean
}

export interface MultiSourceGenerateResponse {
  content: ContentItem
  sources_used: {
    xhs_samples: number
    web_knowledge: boolean
    material_texts: number
    user_materials: boolean
  }
  calibration: {
    avg_title_length: number
    common_patterns: string[]
    emoji_rate: number
    common_tags: string[]
  }
}

export async function generateMultiSource(
  request: MultiSourceGenerateRequest
): Promise<MultiSourceGenerateResponse> {
  const response = await api.post('/generate-multi-source', request)
  return response.data
}


// ==================== 话题研究 API ====================

export interface TopicResearch {
  topic_summary: string
  key_knowledge: string[]
  common_questions: string[]
  hot_angles: string[]
  search_sources?: string[]
}

export async function researchTopic(topic: string): Promise<{
  topic: string
  research: TopicResearch
}> {
  const response = await api.get('/research/topic', {
    params: { topic }
  })
  return response.data
}


// ==================== 视频素材 API ====================

export interface MaterialVideo {
  id: string
  type: 'video'
  video_url: string
  thumbnail: string
  filename: string
  tags: string[]
  description: string
  source: string
  duration: number
  created_at: string
  used_count: number
  xhs_note_id?: string
}

export async function addMaterialVideo(
  videoUrl: string,
  options?: {
    thumbnail?: string
    filename?: string
    tags?: string[]
    description?: string
    duration?: number
  }
): Promise<{ success: boolean; material: MaterialVideo }> {
  const response = await api.post('/materials/videos', {
    video_url: videoUrl,
    thumbnail: options?.thumbnail || '',
    filename: options?.filename || '',
    tags: options?.tags || [],
    description: options?.description || '',
    duration: options?.duration || 0
  })
  return response.data
}

export async function getMaterialVideos(
  tags?: string[],
  limit: number = 20,
  offset: number = 0
): Promise<{ videos: MaterialVideo[]; total: number }> {
  const response = await api.get('/materials/videos', {
    params: { tags: tags?.join(','), limit, offset }
  })
  return response.data
}

export async function deleteMaterialVideo(materialId: string): Promise<{ success: boolean }> {
  const response = await api.delete(`/materials/videos/${materialId}`)
  return response.data
}


// ==================== 小红书素材采集 API ====================

export interface CollectFromXhsRequest {
  note_id: string
  collect_images?: boolean
  collect_video?: boolean
  auto_tags?: string[]
}

export interface CollectedMaterials {
  images: MaterialImage[]
  video?: MaterialVideo
  text?: MaterialText
}

export async function collectMaterialsFromXhs(
  request: CollectFromXhsRequest
): Promise<{
  success: boolean
  collected: {
    images: number
    video: boolean
    text: boolean
  }
  materials: CollectedMaterials
}> {
  const response = await api.post('/materials/collect-xhs', request)
  return response.data
}


// ==================== 智能素材推荐 API ====================

export interface MaterialRecommendation {
  material: MaterialImage | MaterialVideo | MaterialText
  score: number
  reason: string
}

export async function recommendMaterials(
  topic: string,
  contentType: 'image' | 'video' | 'text' = 'image',
  limit: number = 5
): Promise<{ recommendations: MaterialRecommendation[]; topic: string }> {
  const response = await api.get('/materials/recommend', {
    params: { topic, content_type: contentType, limit }
  })
  return response.data
}


// ==================== 增强版素材统计 ====================

export async function getMaterialStatsEnhanced(): Promise<{
  total_images: number
  total_texts: number
  total_videos: number
  total_collections: number
  tags: string[]
  text_types: Record<string, number>
  sources: Record<string, number>
}> {
  const response = await api.get('/materials/stats')
  return response.data
}
