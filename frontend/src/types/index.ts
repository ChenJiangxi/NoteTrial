// API 响应类型
export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

// 分页类型
export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

// 用户相关
export interface User {
  id: string;
  email: string;
  nickname: string;
  username?: string; // 添加username作为nickname的别名
  avatar_url?: string;
  subscription_tier: 'free' | 'pro' | 'enterprise';
  credits: number;
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  nickname: string;
}

export interface AuthResponse {
  user: User;
  access_token: string;
  token_type: string;
}

// 内容相关
export interface Content {
  id: string;
  user_id: string;
  title: string;
  body: string;
  tags: string[];
  status: 'draft' | 'published' | 'archived';
  topic?: string;
  goal?: string;
  created_at: string;
  updated_at: string;
}

export interface ContentCreate {
  title: string;
  body: string;
  tags?: string[];
  topic?: string;
  goal?: string;
}

export interface ContentUpdate {
  title?: string;
  body?: string;
  tags?: string[];
  status?: 'draft' | 'published' | 'archived';
}

// A/B 测试相关
export interface TaskSpec {
  platform: string;
  goals: string[];
  audience: string;
  tone_constraints: string[];
  topic: string;
}

export interface ABTest {
  id: string;
  user_id: string;
  content_a: Content;
  content_b: Content;
  task_spec: TaskSpec;
  result: ABTestResult;
  status: 'running' | 'completed' | 'failed';
  created_at: string;
}

export interface ABTestResult {
  version_a_score: EngagementScore;
  version_b_score: EngagementScore;
  winner: string;
  confidence: number;
  diagnosis: string[];
  suggestions: string[];
}

export interface EngagementScore {
  like_count: number;
  save_count: number;
  comment_count: number;
  share_count: number;
  total: number;
}

// 发布记录相关
export interface Post {
  id: string;
  user_id: string;
  content_id: string;
  platform: string;
  note_id: string;
  title: string;
  stats: PostStats;
  posted_at: string;
  created_at: string;
}

export interface PostStats {
  liked_count: number;
  collected_count: number;
  comment_count: number;
  shared_count: number;
  view_count?: number;
}

// 素材相关
export interface Material {
  id: string;
  user_id: string;
  material_type: 'image' | 'text';
  content: string;
  tags?: string[];
  source?: string;
  created_at: string;
}

// 统计相关
export interface AnalyticsSummary {
  total_posts: number;
  total_likes: number;
  total_saves: number;
  total_comments: number;
  avg_engagement_rate: number;
  top_performing_post?: Post;
  weekly_change: {
    likes: number;
    saves: number;
    comments: number;
  };
}

export interface TrendData {
  date: string;
  likes: number;
  saves: number;
  comments: number;
}

// 套餐相关
export interface SubscriptionPlan {
  id: string;
  name: string;
  price_monthly: number;
  price_yearly: number;
  features: string[];
  limits: {
    ab_tests_per_month: number;
    batch_generation: number;
    history_days: number;
    team_members: number;
  };
}

export interface UserSubscription {
  plan: 'free' | 'pro' | 'enterprise';
  credits: number;
  starts_at?: string;
  expires_at?: string;
}
