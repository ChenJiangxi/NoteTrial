import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { analyticsAPI } from '../services/api';
import {
  AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
  PieChart, Pie, Cell
} from 'recharts';
import {
  TrendingUp, TrendingDown, Eye, Heart, MessageCircle,
  BarChart3, ArrowUpRight, Users, Target
} from 'lucide-react';
import { format, subDays, subMonths, startOfMonth, endOfMonth } from 'date-fns';
import { zhCN } from 'date-fns/locale';

type TimeRange = 'day' | 'week' | 'month';

interface TrendData {
  date: string;
  views: number;
  likes: number;
  comments: number;
  shares: number;
}

interface TopContent {
  id: string;
  title: string;
  views: number;
  likes: number;
  comments: number;
  shares: number;
  engagement_rate: number;
}

interface FunnelData {
  name: string;
  value: number;
  rate: number;
}

interface AudienceData {
  age_group: string;
  percentage: number;
}

const COLORS = ['#ff2442', '#3b82f6', '#22c55e', '#f59e0b', '#8b5cf6', '#ec4899'];

export default function Analytics() {
  const [timeRange, setTimeRange] = useState<TimeRange>('week');

  // 根据时间范围计算日期
  const getDateRange = () => {
    const today = new Date();
    let startDate: Date;
    let endDate = today;

    switch (timeRange) {
      case 'day':
        startDate = subDays(today, 1);
        break;
      case 'week':
        startDate = subDays(today, 7);
        break;
      case 'month':
        startDate = startOfMonth(subMonths(today, 1));
        endDate = endOfMonth(subMonths(today, 1));
        break;
      default:
        startDate = subDays(today, 7);
    }

    return {
      start_date: format(startDate, 'yyyy-MM-dd'),
      end_date: format(endDate, 'yyyy-MM-dd'),
    };
  };

  const dateRange = getDateRange();

  // 获取概览数据
  const { data: overview, isLoading: overviewLoading } = useQuery({
    queryKey: ['analytics-overview', timeRange],
    queryFn: async () => {
      const { data } = await analyticsAPI.getOverview(dateRange);
      return data;
    },
    retry: 2,
  });

  // 获取趋势数据
  const { data: trendData, isLoading: trendLoading } = useQuery({
    queryKey: ['analytics-trend', timeRange],
    queryFn: async () => {
      const days = timeRange === 'day' ? 1 : timeRange === 'week' ? 7 : 30;
      const { data } = await analyticsAPI.getTrend({ days });
      return data;
    },
  });

  // 模拟转化漏斗数据
  const funnelData: FunnelData[] = [
    { name: '曝光', value: 10000, rate: 100 },
    { name: '点击', value: 3500, rate: 35 },
    { name: '阅读', value: 2100, rate: 21 },
    { name: '互动', value: 840, rate: 8.4 },
    { name: '转化', value: 168, rate: 1.68 },
  ];

  // 模拟受众分析数据
  const audienceData: AudienceData[] = [
    { age_group: '18-24岁', percentage: 28 },
    { age_group: '25-30岁', percentage: 35 },
    { age_group: '31-35岁', percentage: 22 },
    { age_group: '36-40岁', percentage: 10 },
    { age_group: '40岁以上', percentage: 5 },
  ];

  const stats = overview?.stats || {
    total_views: 0,
    total_likes: 0,
    total_comments: 0,
    total_shares: 0,
    views_change: 0,
    likes_change: 0,
    comments_change: 0,
    shares_change: 0,
  };

  const trend: TrendData[] = trendData || [];
  const topContents: TopContent[] = overview?.top_contents || [];

  const isLoading = overviewLoading || trendLoading;

  const formatChartData = (data: TrendData[]) => {
    return data.map((item) => ({
      ...item,
      date: format(new Date(item.date), timeRange === 'day' ? 'HH:mm' : 'MM月dd日', { locale: zhCN }),
    }));
  };

  const formatNumber = (num: number) => {
    if (num >= 10000) {
      return (num / 10000).toFixed(1) + '万';
    }
    return num.toLocaleString();
  };

  const StatCard = ({
    title,
    value,
    change,
    icon: Icon,
    color,
  }: {
    title: string;
    value: number;
    change: number;
    icon: React.ComponentType<{ className?: string }>;
    color: string;
  }) => (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${color}`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
        <div className={`flex items-center gap-1 text-sm ${change >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
          {change >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
          {Math.abs(change)}%
        </div>
      </div>
      <h3 className="text-3xl font-bold text-slate-800 dark:text-white">
        {isLoading ? (
          <span className="animate-pulse bg-slate-200 dark:bg-slate-700 rounded h-8 w-24 inline-block" />
        ) : (
          formatNumber(value)
        )}
      </h3>
      <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">{title}</p>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 dark:text-white">数据分析</h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">查看你的内容表现和趋势</p>
        </div>
        <div className="flex items-center gap-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-1">
          <button
            onClick={() => setTimeRange('day')}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              timeRange === 'day'
                ? 'bg-[#ff2442] text-white'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-white'
            }`}
          >
            日
          </button>
          <button
            onClick={() => setTimeRange('week')}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              timeRange === 'week'
                ? 'bg-[#ff2442] text-white'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-white'
            }`}
          >
            周
          </button>
          <button
            onClick={() => setTimeRange('month')}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              timeRange === 'month'
                ? 'bg-[#ff2442] text-white'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-white'
            }`}
          >
            月
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-6">
        <StatCard
          title="总浏览量"
          value={stats.total_views}
          change={stats.views_change}
          icon={Eye}
          color="bg-blue-500"
        />
        <StatCard
          title="总点赞数"
          value={stats.total_likes}
          change={stats.likes_change}
          icon={Heart}
          color="bg-[#ff2442]"
        />
        <StatCard
          title="总评论数"
          value={stats.total_comments}
          change={stats.comments_change}
          icon={MessageCircle}
          color="bg-green-500"
        />
        <StatCard
          title="总分享数"
          value={stats.total_shares}
          change={stats.shares_change}
          icon={ArrowUpRight}
          color="bg-purple-500"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Views Trend */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="text-lg font-semibold text-slate-800 dark:text-white mb-4">浏览量趋势</h3>
          <div className="h-72">
            {isLoading ? (
              <div className="flex items-center justify-center h-full">
                <div className="animate-spin w-8 h-8 border-2 border-[#ff2442] border-t-transparent rounded-full" />
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={formatChartData(trend)}>
                  <defs>
                    <linearGradient id="viewsGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" className="dark:stroke-slate-700" />
                  <XAxis dataKey="date" tick={{ fontSize: 12, fill: '#94a3b8' }} />
                  <YAxis tick={{ fontSize: 12, fill: '#94a3b8' }} />
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
                    fill="url(#viewsGradient)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Engagement Trend */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
          <h3 className="text-lg font-semibold text-slate-800 dark:text-white mb-4">互动趋势</h3>
          <div className="h-72">
            {isLoading ? (
              <div className="flex items-center justify-center h-full">
                <div className="animate-spin w-8 h-8 border-2 border-[#ff2442] border-t-transparent rounded-full" />
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={formatChartData(trend)}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" className="dark:stroke-slate-700" />
                  <XAxis dataKey="date" tick={{ fontSize: 12, fill: '#94a3b8' }} />
                  <YAxis tick={{ fontSize: 12, fill: '#94a3b8' }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      border: 'none',
                      borderRadius: '8px',
                      color: '#fff',
                    }}
                  />
                  <Legend />
                  <Bar dataKey="likes" name="点赞" fill="#ff2442" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="comments" name="评论" fill="#22c55e" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="shares" name="分享" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* Funnel & Audience Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Conversion Funnel */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Target className="w-5 h-5 text-[#ff2442]" />
            <h3 className="text-lg font-semibold text-slate-800 dark:text-white">转化漏斗</h3>
          </div>
          <div className="space-y-3">
            {funnelData.map((item, index) => (
              <div key={item.name} className="relative">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-300">{item.name}</span>
                  <span className="text-sm text-slate-500 dark:text-slate-400">{formatNumber(item.value)} ({item.rate.toFixed(1)}%)</span>
                </div>
                <div className="h-6 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${item.rate}%`,
                      backgroundColor: COLORS[index],
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Audience Analysis */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Users className="w-5 h-5 text-blue-500" />
            <h3 className="text-lg font-semibold text-slate-800 dark:text-white">受众分析</h3>
          </div>
          <div className="flex items-center gap-6">
            <div className="w-40 h-40">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={audienceData}
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={70}
                    paddingAngle={2}
                    dataKey="percentage"
                  >
                    {audienceData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      border: 'none',
                      borderRadius: '8px',
                      color: '#fff',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex-1 space-y-2">
              {audienceData.map((item, index) => (
                <div key={item.age_group} className="flex items-center gap-3">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: COLORS[index % COLORS.length] }}
                  />
                  <span className="text-sm text-slate-600 dark:text-slate-400 flex-1">{item.age_group}</span>
                  <span className="text-sm font-medium text-slate-800 dark:text-white">{item.percentage}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Top 10 Content */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 className="w-5 h-5 text-green-500" />
          <h3 className="text-lg font-semibold text-slate-800 dark:text-white">TOP 10 笔记</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-100 dark:border-slate-700">
                <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">排名</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">标题</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">浏览量</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">点赞</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">评论</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-slate-500 dark:text-slate-400">互动率</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center">
                    <div className="flex items-center justify-center">
                      <div className="animate-spin w-6 h-6 border-2 border-[#ff2442] border-t-transparent rounded-full" />
                    </div>
                  </td>
                </tr>
              ) : topContents.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500 dark:text-slate-400">
                    暂无数据
                  </td>
                </tr>
              ) : (
                topContents.slice(0, 10).map((item, index) => (
                  <tr key={item.id} className="border-b border-slate-50 dark:border-slate-700/50 hover:bg-slate-50 dark:hover:bg-slate-700/30">
                    <td className="py-3 px-4">
                      <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                        index < 3
                          ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400'
                          : 'bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400'
                      }`}>
                        {index + 1}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className="font-medium text-slate-800 dark:text-white truncate max-w-xs inline-block">
                        {item.title}
                      </span>
                    </td>
                    <td className="text-right py-3 px-4 text-slate-600 dark:text-slate-400">{formatNumber(item.views)}</td>
                    <td className="text-right py-3 px-4 text-slate-600 dark:text-slate-400">{formatNumber(item.likes)}</td>
                    <td className="text-right py-3 px-4 text-slate-600 dark:text-slate-400">{formatNumber(item.comments)}</td>
                    <td className="text-right py-3 px-4 text-slate-600 dark:text-slate-400">
                      {item.engagement_rate.toFixed(1)}%
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
