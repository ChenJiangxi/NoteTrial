import axios, { AxiosError, AxiosInstance, AxiosRequestConfig } from 'axios';
import type { ApiResponse } from '@/types';

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

// 辅助函数 - 返回正确的数据格式
// Health check
export const healthCheck = () => 
  request.get<{ status: string }>('/health');

// Publish content - 返回data部分
export const publishContent = (contentId: string, platform: string = 'xhs') => 
  request.post<{ success: boolean; note_id: string }>(`/contents/${contentId}/publish`, { platform });

// Get note stats
export const getNoteStats = (noteId: string) => 
  request.get<{ likes: number; saves: number; comments: number; shares: number }>(`/notes/${noteId}/stats`);

// Generate cover
export const generateCover = (content: string) => 
  request.post<{ image: string }>('/contents/generate-cover', { content });

// Sync notes
export const syncNotes = () => 
  request.post<{ synced_count: number }>('/notes/sync');

// Auto generate enhanced
export const autoGenerateEnhanced = (topic: string, options?: Record<string, unknown>) => 
  request.post<{ content: string; suggestions: string[] }>('/contents/auto-generate', { topic, ...options });

// Get learning stats
export const getLearningStats = () => 
  request.get<{
    total_posts: number;
    analyzed_posts: number;
    total_engagement: Record<string, number>;
    avg_engagement: Record<string, number>;
    profile_updated: string | null;
    writing_tone: string;
    top_tags: string[];
  }>('/learning/stats');

// Get diversity stats
export const getDiversityStats = () => 
  request.get<{ diversity_score: number; suggestions: string[] }>('/diversity/stats');

// Record content
export const recordContent = (content: Record<string, unknown>) => 
  request.post<{ id: string }>('/contents/record', content);

// Add monitor task
export const addMonitorTask = (task: Record<string, unknown>) => 
  request.post<{ task_id: string }>('/monitor/tasks', task);

// Get login QR code
export const getLoginQRCode = () => 
  request.get<{ qrcode_url: string; token: string }>('/auth/qrcode');

// Check login status
export const checkLoginStatus = (token: string) => 
  request.get<{ logged_in: boolean; user_id?: string }>('/auth/login-status', { 
    headers: { Authorization: `Bearer ${token}` } 
  } as AxiosRequestConfig);

// Generate variant
export const generateVariant = (contentId: string, variantType: string) => 
  request.post<{ variant_id: string; content: string }>(`/contents/${contentId}/variants`, { type: variantType });

// Search images
export const searchImages = (query: string) => 
  request.get<{ images: Array<{ url: string; title: string }> }>('/images/search', { params: { q: query } } as AxiosRequestConfig);

// Run crowd test
export const runCrowdTest = (contentId: string) => 
  request.post<{ test_id: string; status: string }>(`/contents/${contentId}/crowd-test`);

// Get history stats
export const getHistoryStats = () => 
  request.get<{
    total_posts: number;
    analyzed_posts: number;
    total_engagement: Record<string, number>;
    avg_engagement: Record<string, number>;
  }>('/history/stats');

// Get user profile
export const getUserProfile = () => 
  request.get<{
    id: string;
    username: string;
    avatar_url: string;
    followers: number;
    following: number;
    notes_count: number;
    writing_style?: string;
    content_preferences?: string[];
    performance_insights?: Record<string, unknown>;
    last_updated?: string;
  }>('/users/profile');

// Get history posts
export const getHistoryPosts = (params?: { page?: number; page_size?: number }) => 
  request.get<Array<{
    id: string;
    title: string;
    body: string;
    posted_at: string;
    performance: Record<string, number>;
  }>>('/history/posts', { params } as AxiosRequestConfig);

// Analyze history
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

// Send chat message
export const sendChatMessage = (message: string, context?: Record<string, unknown>) => 
  request.post<{
    message: string;
    task_spec?: Record<string, unknown>;
    generated_content?: string;
  }>('/chat/message', { message, context });

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
  writing_style?: string;
  content_preferences?: string[];
  performance_insights?: Record<string, unknown>;
  last_updated?: string;
}

export default api;
