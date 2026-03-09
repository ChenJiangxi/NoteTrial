// API 类型定义

export type Platform = 'xiaohongshu'

export type OptimizationGoal = 'maximize_like' | 'maximize_save' | 'maximize_comment' | 'maximize_share'

export interface TaskSpec {
  platform: Platform
  goals: OptimizationGoal[]  // 支持多个优化目标
  goal?: OptimizationGoal    // 保持向后兼容
  audience: string
  tone_constraints: string[]
  test_type: string
  topic: string
}

export interface ContentItem {
  title: string
  body: string
  cover_image?: string  // 封面图（向后兼容）
  images?: PageImage[]  // 多图内容页
  tags: string[]
}

// 单页图片
export interface PageImage {
  index: number        // 页面索引（0=封面, 1,2,3...=内容页）
  type: 'cover' | 'content' | 'summary'  // 页面类型（封面、内容、总结）
  content: string      // 该页的文案描述
  image?: string       // 图片 base64 或 URL
  status: 'pending' | 'generating' | 'done' | 'error'
  error?: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  images?: string[]  // 支持多张图片（base64 或 URL）
}

export interface ChatRequest {
  messages: ChatMessage[]
  current_content?: ContentItem
}

export interface ChatResponse {
  message: string
  task_spec?: TaskSpec
  generated_content?: ContentItem
  action?: 'all' | 'text_only' | 'image_only' | 'none'  // 用户意图
}

export interface ABTestRequest {
  task_spec: TaskSpec
  content_a: ContentItem
  content_b: ContentItem
  max_users: number
  audience_tags?: string[]
}

export interface ContentVariant {
  label: string
  content: ContentItem
}

export interface MultiTestRequest {
  task_spec: TaskSpec
  versions: ContentVariant[]
  max_users: number
  audience_tags?: string[]
}

export interface PersonaSimulationResult {
  persona_id: string
  persona_description: string
  version_preference: string
  like: boolean
  save: boolean
  comment: boolean
  share: boolean
  reasoning: string
}

export interface EngagementScore {
  like_count: number
  save_count: number
  comment_count: number
  share_count: number
  total: number
}

export interface StatisticalConfidence {
  winner: string
  confidence: number
}

export interface MCPEvidenceSignal {
  score: number
  sample_count: number
  matched_keywords: string[]
  matched_tags: string[]
  reasons: string[]
  source_keywords: string[]
}

export interface CrowdTestResult {
  version_a_score: EngagementScore
  version_b_score: EngagementScore
  like_confidence: StatisticalConfidence
  save_confidence: StatisticalConfidence
  comment_confidence: StatisticalConfidence
  share_confidence: StatisticalConfidence
  overall_confidence: StatisticalConfidence
  diagnosis: string[]
  suggestions: string[]
  persona_results: PersonaSimulationResult[]
  version_evidence?: Record<string, MCPEvidenceSignal>
  evaluation_mode?: string
}

export interface VersionScore {
  label: string
  score: EngagementScore
  evidence_score?: number
  composite_score?: number
  mcp_evidence?: MCPEvidenceSignal
}

export interface MultiCrowdTestResult {
  version_scores: VersionScore[]
  like_confidence: StatisticalConfidence
  save_confidence: StatisticalConfidence
  comment_confidence: StatisticalConfidence
  share_confidence: StatisticalConfidence
  overall_confidence: StatisticalConfidence
  diagnosis: string[]
  suggestions: string[]
  persona_results: PersonaSimulationResult[]
  version_evidence?: Record<string, MCPEvidenceSignal>
  evaluation_mode?: string
}

export interface GenerateVariantRequest {
  task_spec: TaskSpec
  base_content: ContentItem
  variant_type: 'alternative' | 'hook' | 'actionable'
  mcp_keywords?: string[]
}

// 历史记录
export interface HistoryRecord {
  id: string
  timestamp: number
  taskSpec: TaskSpec
  contentA: ContentItem
  contentB: ContentItem
  testResult?: MultiCrowdTestResult
  publishedVersion?: 'A' | 'B'
}
