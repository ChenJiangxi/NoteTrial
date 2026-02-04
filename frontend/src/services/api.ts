import axios, { AxiosError, AxiosInstance, AxiosRequestConfig } from 'axios';
import type { ApiResponse } from '@/types';
import type { ContentItem, TaskSpec, CrowdTestResult } from '../types/api';

// 创建 axios 实例
const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器 - 添加 Token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器 - 处理错误
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiResponse<unknown>>) => {
    if (error.response?.status === 401) {
      // Token 过期，尝试刷新
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post(
            `${import.meta.env.VITE_API_URL}/api/auth/refresh`,
            { refresh_token: refreshToken }
          );
          
          const { access_token, refresh_token } = response.data.data;
          localStorage.setItem('access_token', access_token);
          localStorage.setItem('refresh_token', refresh_token);
          
          // 重试原请求
          if (error.config) {
            error.config.headers.Authorization = `Bearer ${access_token}`;
            return api.request(error.config);
          }
        } catch {
          // 刷新失败，清除 Token 跳转登录
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      } else {
        // 没有刷新 Token，跳转登录
        localStorage.removeItem('access_token');
        window.location.href = '/login';
      }
    }
    
    // 显示错误消息
    const message = error.response?.data?.message || error.message || '请求失败';
    console.error('API Error:', message);
    
    return Promise.reject(error);
  }
);

// 封装请求方法 - 返回data而不是完整的AxiosResponse
export const request = {
  get: <T>(url: string, config?: AxiosRequestConfig) =>
    api.get<ApiResponse<T>>(url, config).then((res) => res.data.data),
    
  post: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    api.post<ApiResponse<T>>(url, data, config).then((res) => res.data.data),
    
  put: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    api.put<ApiResponse<T>>(url, data, config).then((res) => res.data.data),
    
  patch: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    api.patch<ApiResponse<T>>(url, data, config).then((res) => res.data.data),
    
  delete: <T>(url: string, config?: AxiosRequestConfig) =>
    api.delete<ApiResponse<T>>(url, config).then((res) => res.data.data),
};

// 从 endpoints.ts 导入各个 API 对象
import { authApi, contentsApi, abTestsApi, postsApi, materialsApi, analyticsApi } from './endpoints';

// 导出各个 API 对象（使用组件期望的名称）
export const authAPI = authApi;
export const contentAPI = contentsApi;
export const experimentAPI = abTestsApi;
export const postAPI = postsApi;
export const materialAPI = materialsApi;
export const analyticsAPI = analyticsApi;

// Health check
export const healthCheck = () => 
  request.get<{ status: string; services?: Record<string, boolean> }>('/health');

// Publish content - 返回包装后的结果
export const publishContent = (content: ContentItem) => 
  request.post<{ success: boolean; note_id: string; message?: string; data?: { xsecToken?: string } }>('/contents/publish', content);

// Get note stats
export const getNoteStats = (noteId: string, options?: { xsecToken?: string; titleKeyword?: string }) => 
  request.get<{ result: { content: string } }>(`/notes/${noteId}/stats`, { params: options } as AxiosRequestConfig);

// Generate cover
export const generateCover = (content: ContentItem, topic: string) => 
  request.post<{ success: boolean; image?: string; error?: string }>('/contents/generate-cover', { content, topic });

// Sync notes
export const syncNotes = (titles: string[]) => 
  request.post<{ error?: string; notes: Array<{ matchedTitle?: string; title?: string; noteId?: string; xsecToken?: string; likedCount?: string | number; collectedCount?: string | number; commentCount?: string | number }> }>('/notes/sync', { titles });

// Auto generate enhanced
export const autoGenerateEnhanced = (
  topic: string, 
  goals: string[], 
  audience: string, 
  count: number,
  useLearning: boolean,
  checkDiversity: boolean,
  useHumanize: boolean
) => 
  request.post<{ 
    content: ContentItem; 
    reference_count?: number;
    p0_enhancements?: {
      learning_hints_applied?: number;
      diversity_check?: { is_valid: boolean; issues: string[] };
      humanness_score?: { score: number; issues: string[] };
    };
  }>('/contents/auto-generate', { topic, goals, audience, count, use_learning: useLearning, check_diversity: checkDiversity, use_humanize: useHumanize });

// Get learning stats
export const getLearningStats = () => 
  request.get<{
    total_records: number;
    analyzed_posts?: number;
    total_engagement?: Record<string, number>;
    avg_engagement?: Record<string, number>;
    profile_updated?: string | null;
    writing_tone?: string;
    top_tags?: string[];
  }>('/learning/stats');

// Get diversity stats
export const getDiversityStats = () => 
  request.get<{ unique_tags?: number; diversity_score?: number; suggestions?: string[] }>('/diversity/stats');

// Record content
export const recordContent = (id: string, title: string, body: string, tags: string[], topic: string) => 
  request.post<{ id: string }>('/contents/record', { id, title, body, tags, topic });

// Add monitor task
export const addMonitorTask = (id: string, noteId: string) => 
  request.post<{ task_id: string }>('/monitor/tasks', { id, note_id: noteId });

// Get login QR code
export const getLoginQRCode = () => 
  request.get<{ qrcode_url?: string; token?: string; result?: { content?: Array<{ text?: string }> } }>('/auth/qrcode');

// Check login status
export const checkLoginStatus = () => 
  request.get<{ logged_in: boolean; user_id?: string; result?: { content?: Array<{ text?: string }> } }>('/auth/login-status');

// Generate variant - 修复签名以匹配组件调用
export const generateVariant = (data: { task_spec: TaskSpec; base_content: ContentItem; variant_type: string }) => 
  request.post<{ variant_id: string; content: string }>('/contents/variants', data);

// Search images - 修复返回类型，提取url数组
export const searchImages = async (query: string, limit?: number): Promise<string[]> => {
  const result = await request.get<Array<{ url: string; title: string }>>('/images/search', { params: { q: query, limit } } as AxiosRequestConfig);
  return result.map(item => item.url);
};

// Run crowd test - 简单版本，返回 test_id
export const runCrowdTest = (contentId: string) => 
  request.post<{ test_id: string; status: string }>(`/contents/${contentId}/crowd-test`);

// Run crowd test - 完整版本用于组件
export const runCrowdTestFull = (data: { task_spec: TaskSpec; content_a: ContentItem; content_b: ContentItem; max_users: number }) => 
  request.post<CrowdTestResult>('/contents/crowd-test', data);

// Get history stats - 添加可选字段
export const getHistoryStats = () => 
  request.get<{
    total_posts: number;
    analyzed_posts: number;
    total_engagement: Record<string, number>;
    avg_engagement: Record<string, number>;
    profile_updated?: string | null;
    writing_tone?: string;
    top_tags?: string[];
  }>('/history/stats');

// Get user profile - 返回正确的类型
export const getUserProfile = () => 
  request.get<{
    id: string;
    username: string;
    avatar_url: string;
    followers: number;
    following: number;
    notes_count: number;
    writing_style?: {
      tone: string;
      paragraph_style: string;
      emoji_density: number;
      avg_title_length: number;
      avg_body_length: number;
    };
    content_preferences?: {
      favorite_tags: string[];
    };
    performance_insights?: {
      optimal_title_length: number;
      best_performing_tags: string[];
    };
    last_updated?: string;
  }>('/users/profile');

// Get history posts - 返回正确的类型
export const getHistoryPosts = (params?: { page?: number; page_size?: number }) => 
  request.get<Array<{
    id: string;
    title: string;
    body: string;
    posted_at: string;
    performance: Record<string, number>;
  }>>('/history/posts', { params } as AxiosRequestConfig);

// Analyze history - 需要传入内容
export const analyzeHistory = (content: string) => 
  request.post<{ analysis: string; suggestions: string[] }>('/history/analyze', { content });

// Import history from XHS
export const importHistoryFromXHS = (data: { url: string; cookies?: string }) => 
  request.post<{ imported_count: number }>('/history/import/xhs', data);

// Get style prompt
export const getStylePrompt = () => 
  request.get<{ prompt: string }>('/learning/style-prompt');

// Get my notes
export const getMyNotes = (params?: { page?: number; page_size?: number }) => 
  request.get<Array<{
    id: string;
    title: string;
    status: string;
    created_at: string;
  }>>('/notes/my', { params } as AxiosRequestConfig);

// Material functions
export const getMaterialStats = () => 
  request.get<{
    total_images: number;
    total_texts: number;
    tags: string[];
  }>('/materials/stats');

export const addMaterialImage = (data: { url: string; tags?: string[] }) => 
  request.post<{ id: string; url: string }>('/materials/images', data);

export const getMaterialImages = (params?: { page?: number; page_size?: number }) => 
  request.get<Array<{
    id: string;
    url: string;
    path?: string;
    filename?: string;
    tags: string[];
    created_at: string;
  }>>('/materials/images', { params } as AxiosRequestConfig);

export const deleteMaterialImage = (id: string) => 
  request.delete<{ success: boolean }>(`/materials/images/${id}`);

export const addMaterialText = (data: { content: string; tags?: string[] }) => 
  request.post<{ id: string; content: string }>('/materials/texts', data);

export const getMaterialTexts = (params?: { page?: number; page_size?: number }) => 
  request.get<Array<{
    id: string;
    content: string;
    text_type?: string;
    tags: string[];
    created_at: string;
  }>>('/materials/texts', { params } as AxiosRequestConfig);

export const deleteMaterialText = (id: string) => 
  request.delete<{ success: boolean }>(`/materials/texts/${id}`);

// Send chat message - 修复签名以匹配组件调用
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export const sendChatMessage = (data: { messages: ChatMessage[]; current_content?: ContentItem }) => 
  request.post<{
    message: string;
    task_spec?: TaskSpec;
    generated_content?: ContentItem;
  }>('/chat/message', data);

// Types for materials
export interface MaterialImage {
  id: string;
  url: string;
  path?: string;
  filename?: string;
  tags: string[];
  created_at: string;
}

export interface MaterialText {
  id: string;
  content: string;
  text_type?: string;
  tags: string[];
  created_at: string;
}

export interface HistoryPost {
  id: string;
  title?: string;
  body?: string;
  note_id?: string;
  posted_at?: string;
  performance?: Record<string, number>;
  stats?: {
    likes: number;
    saves: number;
    comments: number;
    shares: number;
  };
  created_at?: string;
  content?: string;
}

export interface UserProfile {
  id: string;
  username: string;
  avatar_url: string;
  followers: number;
  following: number;
  notes_count: number;
  writing_style?: {
    tone: string;
    paragraph_style: string;
    emoji_density: number;
    avg_title_length: number;
    avg_body_length: number;
  };
  content_preferences?: {
    favorite_tags: string[];
  };
  performance_insights?: {
    optimal_title_length: number;
    best_performing_tags: string[];
  };
  last_updated?: string;
}

// Analytics types
export interface AnalyticsSummary {
  stats: {
    total_views: number;
    total_likes: number;
    total_comments: number;
    total_shares: number;
    views_change: number;
    likes_change: number;
    comments_change: number;
    shares_change: number;
  };
  top_contents: Array<{
    id: string;
    title: string;
    views: number;
    likes: number;
    comments: number;
    shares: number;
    engagement_rate: number;
  }>;
}

export interface TrendData {
  date: string;
  views: number;
  likes: number;
  comments: number;
  shares: number;
}

export interface Content {
  id: string;
  title: string;
  status: 'draft' | 'published' | 'testing';
  created_at: string;
  updated_at: string;
  cover_image?: string;
}

export default api;
