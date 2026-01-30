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
  cover_image?: string
  tags: string[]
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatRequest {
  messages: ChatMessage[]
  current_content?: ContentItem
}

export interface ChatResponse {
  message: string
  task_spec?: TaskSpec
  generated_content?: ContentItem
}

export interface ABTestRequest {
  task_spec: TaskSpec
  content_a: ContentItem
  content_b: ContentItem
  max_users: number
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
}

export interface GenerateVariantRequest {
  task_spec: TaskSpec
  base_content: ContentItem
  variant_type: 'alternative' | 'hook' | 'actionable'
}

// 历史记录
export interface HistoryRecord {
  id: string
  timestamp: number
  taskSpec: TaskSpec
  contentA: ContentItem
  contentB: ContentItem
  testResult?: CrowdTestResult
  publishedVersion?: 'A' | 'B'
}
