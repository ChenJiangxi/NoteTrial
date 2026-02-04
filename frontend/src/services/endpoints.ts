import { request } from './api';
import type { 
  User, 
  LoginRequest, 
  RegisterRequest, 
  AuthResponse,
  Content,
  ContentCreate,
  ContentUpdate,
  ABTest,
  Post,
  Material,
  AnalyticsSummary,
  PaginatedResponse,
} from '@/types';

// Auth API
export const authApi = {
  login: (data: LoginRequest) => 
    request.post<AuthResponse>('/auth/login', data),
    
  register: (data: RegisterRequest) => 
    request.post<AuthResponse>('/auth/register', data),
    
  me: () => 
    request.get<User>('/auth/me'),
    
  logout: () => 
    request.post('/auth/logout'),
    
  refresh: (refreshToken: string) => 
    request.post<{ access_token: string; refresh_token: string }>('/auth/refresh', { refresh_token: refreshToken }),
};

// Contents API
export const contentsApi = {
  // 添加别名
  getAll: (params?: { page?: number; page_size?: number; status?: string }) => 
    contentsApi.list(params),
    
  list: (params?: { page?: number; page_size?: number; status?: string }) => 
    request.get<PaginatedResponse<Content>>('/contents', { params }),
    
  get: (id: string) => 
    request.get<Content>(`/contents/${id}`),
    
  create: (data: ContentCreate) => 
    request.post<Content>('/contents', data),
    
  update: (id: string, data: ContentUpdate) => 
    request.patch<Content>(`/contents/${id}`, data),
    
  delete: (id: string) => 
    request.delete(`/contents/${id}`),
    
  generate: (topic: string, params?: { audience?: string; goal?: string }) => 
    request.post<Content>('/contents/generate', { topic, ...params }),
    
  improve: (id: string, suggestions: string[]) => 
    request.post<Content>(`/contents/${id}/improve`, { suggestions }),
};

// AB Tests API
export const abTestsApi = {
  // 添加别名
  getAll: (params?: { page?: number; page_size?: number }) => 
    abTestsApi.list(params),
    
  list: (params?: { page?: number; page_size?: number }) => 
    request.get<PaginatedResponse<ABTest>>('/ab-tests', { params }),
    
  get: (id: string) => 
    request.get<ABTest>(`/ab-tests/${id}`),
    
  create: (data: {
    content_a_id: string;
    content_b_id?: string;
    task_spec: {
      topic: string;
      audience: string;
      goals: string[];
    };
  }) => 
    request.post<ABTest>('/ab-tests', data),
    
  run: (id: string) => 
    request.post<ABTest>(`/ab-tests/${id}/run`),
    
  delete: (id: string) => 
    request.delete(`/ab-tests/${id}`),
};

// Posts API
export const postsApi = {
  list: (params?: { page?: number; page_size?: number }) => 
    request.get<PaginatedResponse<Post>>('/posts', { params }),
    
  get: (id: string) => 
    request.get<Post>(`/posts/${id}`),
    
  refresh: (id: string) => 
    request.post<Post>(`/posts/${id}/refresh`),
    
  delete: (id: string) => 
    request.delete(`/posts/${id}`),
};

// Materials API
export const materialsApi = {
  list: (params?: { material_type?: string; page?: number; page_size?: number }) => 
    request.get<PaginatedResponse<Material>>('/materials', { params }),
    
  upload: (data: { material_type: string; content: string; tags?: string[] }) => 
    request.post<Material>('/materials', data),
    
  delete: (id: string) => 
    request.delete(`/materials/${id}`),
};

// Analytics API
export const analyticsApi = {
  // 添加别名以匹配组件期望的方法名
  getOverview: () => analyticsApi.summary(),
  getTrend: (params?: { days?: number }) => analyticsApi.trends(params),
  
  summary: () => 
    request.get<AnalyticsSummary>('/analytics/summary'),
    
  trends: (params?: { days?: number }) => 
    request.get<{ data: Array<{ date: string; likes: number; saves: number; comments: number }> }>('/analytics/trends', { params }),
    
  topPosts: (params?: { limit?: number }) => 
    request.get<{ data: Post[] }>('/analytics/top-posts', { params }),
};
