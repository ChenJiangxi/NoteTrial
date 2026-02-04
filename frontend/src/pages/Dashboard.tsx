import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { contentAPI, analyticsAPI } from '../services/api';
import {
  Plus, FileText, BarChart3, Clock, TrendingUp,
  Sparkles, ArrowRight, LayoutGrid, List, RefreshCw, AlertCircle
} from 'lucide-react';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import {
  AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';

interface ContentItem {
  id: string;
  title: string;
  status: 'draft' | 'published' | 'testing';
  created_at: string;
  updated_at: string;
  cover_image?: string;
}

interface TrendData {
  date: string;
  views: number;
  likes: number;
}

export default function Dashboard() {
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [timeRange, setTimeRange] = useState<'7d' | '30d'>('30d');

  // 获取内容数据
  const {
    data: contentsData,
    isLoading: contentsLoading,
    error: contentsError,
    refetch: refetchContents
  } = useQuery({
    queryKey: ['contents', { limit: 10 }],
    queryFn: async () => {
      const { data } = await contentAPI.getAll({ limit: 10 });
      return data;
    },
    retry: 2,
    staleTime: 5 * 60 * 1000,
  });

  // 获取统计数据
  const {
    data: analyticsData,
    isLoading: analyticsLoading,
    error: analyticsError
  } = useQuery({
    queryKey: ['analytics-overview'],
    queryFn: async () => {
      const { data } = await analyticsAPI.getOverview();
      return data;
    },
    retry: 2,
    staleTime: 5 * 60 * 1000,
  });

  // 获取趋势数据
  const { data: trendData } = useQuery({
    queryKey: ['analytics-trend', timeRange],
    queryFn: async () => {
      const days = timeRange === '7d' ? 7 : 30;
      const { data } = await analyticsAPI.getTrend({ days });
      return data;
    },
  });

  const contents = contentsData?.contents || [];
  const stats = analyticsData?.stats || {
    total_views: 0,
    total_likes: 0,
    total_experiments: 0,
    views_change: 0,
    likes_change: 0,
  };
  const trend: TrendData[] = trendData || [];

  const isLoading = contentsLoading || analyticsLoading;
  const error = contentsError || analyticsError;

  const formatChartData = (data: TrendData[]) => {
    return data.map((item) => ({
      ...item,
      date: format(new Date(item.date), 'MM月dd日', { locale: zhCN }),
    }));
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'published':
        return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400';
      case 'testing':
        return 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400';
      default:
        return 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'published':
        return '已发布';
      case 'testing':
        return '测试中';
      default:
        return '草稿';
    }
  };

  // 错误状态
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
        <div className="w-16 h-16 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center">
          <AlertCircle className="w-8 h-8 text-red-500 dark:text-red-400" />
        </div>
        <h3 className="text-lg font-medium text-slate-800 dark:text-white">加载失败</h3>
        <p className="text-slate-500 dark:text-slate-400">请检查网络连接或刷新重试</p>
        <button
          onClick={() => refetchContents()}
          className="flex items-center gap-2 px-4 py-2 bg-[#ff2442] text-white rounded-lg hover:bg-[#e61f3d] transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          重新加载
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-white">仪表盘</h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">欢迎回来，查看你的内容表现</p>
        </div>
        <Link
          to="/editor"
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-[#ff2442] text-white font-medium rounded-xl hover:bg-[#e61f3d] transition-all shadow-lg shadow-red-200 dark:shadow-none"
        >
          <Plus className="w-5 h-5" />
          新建内容
        </Link>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 lg:gap-6">
        <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-blue-50 dark:bg-blue-900/30 rounded-xl flex items-center justify-center">
              <FileText className="w-6 h-6 text-blue-500 dark:text-blue-400" />
            </div>
            <span className={`flex items-center gap-1 text-sm ${
              stats.views_change >= 0
                ? 'text-emerald-600 dark:text-emerald-400'
                : 'text-red-600 dark:text-red-400'
            }`}>
              {stats.views_change >= 0 ? (
                <TrendingUp className="w-4 h-4" />
              ) : (
                <Sparkles className="w-4 h-4 rotate-180" />
              )}
              {Math.abs(stats.views_change)}%
            </span>
          </div>
          <h3 className="text-3xl font-bold text-slate-800 dark:text-white">
            {isLoading ? (
              <span className="animate-pulse bg-slate-200 dark:bg-slate-700 rounded h-8 w-24 inline-block" />
            ) : (
              stats.total_views.toLocaleString()
            )}
          </h3>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">总浏览量</p>
        </div>

        <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-red-50 dark:bg-red-900/30 rounded-xl flex items-center justify-center">
              <Sparkles className="w-6 h-6 text-[#ff2442] dark:text-red-400" />
            </div>
            <span className={`flex items-center gap-1 text-sm ${
              stats.likes_change >= 0
                ? 'text-emerald-600 dark:text-emerald-400'
                : 'text-red-600 dark:text-red-400'
            }`}>
              {stats.likes_change >= 0 ? (
                <TrendingUp className="w-4 h-4" />
              ) : (
                <Sparkles className="w-4 h-4 rotate-180" />
              )}
              {Math.abs(stats.likes_change)}%
            </span>
          </div>
          <h3 className="text-3xl font-bold text-slate-800 dark:text-white">
            {isLoading ? (
              <span className="animate-pulse bg-slate-200 dark:bg-slate-700 rounded h-8 w-24 inline-block" />
            ) : (
              stats.total_likes.toLocaleString()
            )}
          </h3>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">总点赞数</p>
        </div>

        <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-green-50 dark:bg-green-900/30 rounded-xl flex items-center justify-center">
              <BarChart3 className="w-6 h-6 text-green-500 dark:text-green-400" />
            </div>
          </div>
          <h3 className="text-3xl font-bold text-slate-800 dark:text-white">
            {isLoading ? (
              <span className="animate-pulse bg-slate-200 dark:bg-slate-700 rounded h-8 w-16 inline-block" />
            ) : (
              stats.total_experiments
            )}
          </h3>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">测试实验数</p>
        </div>
      </div>

      {/* Trend Chart */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm">
        <div className="p-6 border-b border-slate-100 dark:border-slate-700 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <h2 className="text-lg font-semibold text-slate-800 dark:text-white">互动趋势</h2>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setTimeRange('7d')}
              className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                timeRange === '7d'
                  ? 'bg-[#ff2442] text-white'
                  : 'text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
              }`}
            >
              7天
            </button>
            <button
              onClick={() => setTimeRange('30d')}
              className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                timeRange === '30d'
                  ? 'bg-[#ff2442] text-white'
                  : 'text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700'
              }`}
            >
              30天
            </button>
          </div>
        </div>
        <div className="p-6">
          <div className="h-64">
            {isLoading ? (
              <div className="flex items-center justify-center h-full">
                <div className="animate-spin w-8 h-8 border-2 border-[#ff2442] border-t-transparent rounded-full" />
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={formatChartData(trend)}>
                  <defs>
                    <linearGradient id="viewsGradientDark" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" className="dark:stroke-slate-700" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 12, fill: '#94a3b8' }}
                    axisLine={{ stroke: '#e2e8f0', className: 'dark:stroke-slate-700' }}
                  />
                  <YAxis
                    tick={{ fontSize: 12, fill: '#94a3b8' }}
                    axisLine={{ stroke: '#e2e8f0', className: 'dark:stroke-slate-700' }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      border: 'none',
                      borderRadius: '8px',
                      color: '#fff',
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="views"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    fill="url(#viewsGradientDark)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Link
          to="/editor"
          className="flex flex-col items-center gap-2 p-4 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-[#ff2442] hover:shadow-md transition-all"
        >
          <div className="w-10 h-10 bg-red-50 dark:bg-red-900/30 rounded-lg flex items-center justify-center">
            <Plus className="w-5 h-5 text-[#ff2442] dark:text-red-400" />
          </div>
          <span className="text-sm font-medium text-slate-700 dark:text-slate-300">新建内容</span>
        </Link>
        <Link
          to="/analytics"
          className="flex flex-col items-center gap-2 p-4 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-[#ff2442] hover:shadow-md transition-all"
        >
          <div className="w-10 h-10 bg-blue-50 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
            <BarChart3 className="w-5 h-5 text-blue-500 dark:text-blue-400" />
          </div>
          <span className="text-sm font-medium text-slate-700 dark:text-slate-300">数据分析</span>
        </Link>
        <Link
          to="/scheduler"
          className="flex flex-col items-center gap-2 p-4 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-[#ff2442] hover:shadow-md transition-all"
        >
          <div className="w-10 h-10 bg-green-50 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
            <Clock className="w-5 h-5 text-green-500 dark:text-green-400" />
          </div>
          <span className="text-sm font-medium text-slate-700 dark:text-slate-300">定时发布</span>
        </Link>
        <Link
          to="/projects"
          className="flex flex-col items-center gap-2 p-4 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-[#ff2442] hover:shadow-md transition-all"
        >
          <div className="w-10 h-10 bg-purple-50 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
            <FileText className="w-5 h-5 text-purple-500 dark:text-purple-400" />
          </div>
          <span className="text-sm font-medium text-slate-700 dark:text-slate-300">项目管理</span>
        </Link>
      </div>

      {/* Recent Contents */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm">
        <div className="p-6 border-b border-slate-100 dark:border-slate-700 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <h2 className="text-lg font-semibold text-slate-800 dark:text-white">最近内容</h2>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 rounded-lg transition-colors ${
                viewMode === 'grid'
                  ? 'bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-white'
                  : 'text-slate-400 hover:text-slate-600 dark:text-slate-500'
              }`}
            >
              <LayoutGrid className="w-5 h-5" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 rounded-lg transition-colors ${
                viewMode === 'list'
                  ? 'bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-white'
                  : 'text-slate-400 hover:text-slate-600 dark:text-slate-500'
              }`}
            >
              <List className="w-5 h-5" />
            </button>
          </div>
        </div>

        {isLoading ? (
          <div className="p-12 flex flex-col items-center justify-center">
            <div className="animate-spin w-8 h-8 border-2 border-[#ff2442] border-t-transparent rounded-full mb-4" />
            <p className="text-slate-500 dark:text-slate-400">加载中...</p>
          </div>
        ) : contents.length === 0 ? (
          <div className="p-12 flex flex-col items-center">
            <FileText className="w-12 h-12 text-slate-300 dark:text-slate-600 mb-4" />
            <h3 className="text-lg font-medium text-slate-700 dark:text-white mb-2">暂无内容</h3>
            <p className="text-slate-500 dark:text-slate-400 mb-6">创建你的第一篇内容开始测试吧</p>
            <Link
              to="/editor"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#ff2442] text-white font-medium rounded-xl hover:bg-[#e61f3d] transition-colors"
            >
              <Plus className="w-5 h-5" />
              新建内容
            </Link>
          </div>
        ) : viewMode === 'grid' ? (
          <div className="p-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {contents.map((item: ContentItem) => (
              <Link
                key={item.id}
                to={`/editor/${item.id}`}
                className="group border border-slate-200 dark:border-slate-700 rounded-xl p-4 hover:border-[#ff2442] hover:shadow-md transition-all bg-white dark:bg-slate-800"
              >
                <div className="aspect-video bg-slate-100 dark:bg-slate-700 rounded-lg mb-3 overflow-hidden">
                  <img
                    src={item.cover_image || 'https://via.placeholder.com/300x200'}
                    alt={item.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                  />
                </div>
                <h3 className="font-medium text-slate-800 dark:text-white mb-2 line-clamp-2 group-hover:text-[#ff2442] transition-colors">
                  {item.title}
                </h3>
                <div className="flex items-center justify-between">
                  <span className={`text-xs px-2 py-1 rounded-full ${getStatusColor(item.status)}`}>
                    {getStatusText(item.status)}
                  </span>
                  <span className="text-xs text-slate-400 dark:text-slate-500 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {format(new Date(item.updated_at), 'MM月dd日', { locale: zhCN })}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="divide-y divide-slate-100 dark:divide-slate-700">
            {contents.map((item: ContentItem) => (
              <Link
                key={item.id}
                to={`/editor/${item.id}`}
                className="flex items-center gap-4 p-4 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
              >
                <div className="w-16 h-12 bg-slate-100 dark:bg-slate-700 rounded-lg overflow-hidden flex-shrink-0">
                  <img
                    src={item.cover_image || 'https://via.placeholder.com/100x75'}
                    alt={item.title}
                    className="w-full h-full object-cover"
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium text-slate-800 dark:text-white truncate group-hover:text-[#ff2442] transition-colors">
                    {item.title}
                  </h3>
                  <p className="text-sm text-slate-400 dark:text-slate-500 mt-0.5">
                    更新于 {format(new Date(item.updated_at), 'yyyy年MM月dd日 HH:mm', { locale: zhCN })}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-xs px-2.5 py-1 rounded-full ${getStatusColor(item.status)}`}>
                    {getStatusText(item.status)}
                  </span>
                  <ArrowRight className="w-5 h-5 text-slate-300 dark:text-slate-600 group-hover:text-[#ff2442] transition-colors" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
