import { useQuery } from '@tanstack/react-query';
import { analyticsAPI } from '../services/api';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import {
  TrendingUp, TrendingDown, Eye, Heart, MessageCircle,
  BarChart3, Calendar, ArrowUpRight
} from 'lucide-react';
import { format, subDays } from 'date-fns';
import { zhCN } from 'date-fns/locale';

export default function Analytics() {
  const today = new Date();
  const thirtyDaysAgo = subDays(today, 30);

  // 获取概览数据
  const { data: overview } = useQuery({
    queryKey: ['analytics-overview'],
    queryFn: async () => {
      const { data } = await analyticsAPI.getOverview({
        start_date: format(thirtyDaysAgo, 'yyyy-MM-dd'),
        end_date: format(today, 'yyyy-MM-dd'),
      });
      return data;
    },
  });

  // 获取趋势数据
  const { data: trendData } = useQuery({
    queryKey: ['analytics-trend'],
    queryFn: async () => {
      const { data } = await analyticsAPI.getTrend({ days: 30 });
      return data;
    },
  });

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

  const trend = trendData || [];

  const formatChartData = (data: any[]) => {
    return data.map((item: any) => ({
      ...item,
      date: format(new Date(item.date), 'MM月dd日', { locale: zhCN }),
    }));
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
    icon: any;
    color: string;
  }) => (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${color}`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
        <div className={`flex items-center gap-1 text-sm ${change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
          {change >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
          {Math.abs(change)}%
        </div>
      </div>
      <h3 className="text-3xl font-bold text-slate-800">{value.toLocaleString()}</h3>
      <p className="text-slate-500 text-sm mt-1">{title}</p>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">数据分析</h1>
          <p className="text-slate-500 mt-1">查看你的内容表现和趋势</p>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-xl text-sm text-slate-600">
          <Calendar className="w-4 h-4" />
          最近30天
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
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

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Views Trend */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">浏览量趋势</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={formatChartData(trend)}>
                <defs>
                  <linearGradient id="viewsGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" tick={{ fontSize: 12, fill: '#94a3b8' }} />
                <YAxis tick={{ fontSize: 12, fill: '#94a3b8' }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#fff',
                    border: '1px solid #e2e8f0',
                    borderRadius: '8px',
                    fontSize: '12px',
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
          </div>
        </div>

        {/* Engagement Trend */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">互动趋势</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={formatChartData(trend)}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" tick={{ fontSize: 12, fill: '#94a3b8' }} />
                <YAxis tick={{ fontSize: 12, fill: '#94a3b8' }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#fff',
                    border: '1px solid #e2e8f0',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                />
                <Legend />
                <Bar dataKey="likes" name="点赞" fill="#ff2442" radius={[4, 4, 0, 0]} />
                <Bar dataKey="comments" name="评论" fill="#22c55e" radius={[4, 4, 0, 0]} />
                <Bar dataKey="shares" name="分享" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Top Content */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h3 className="text-lg font-semibold text-slate-800 mb-4">表现最佳的内容</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-100">
                <th className="text-left py-3 px-4 text-sm font-medium text-slate-500">标题</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-slate-500">浏览量</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-slate-500">点赞</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-slate-500">评论</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-slate-500">互动率</th>
              </tr>
            </thead>
            <tbody>
              {overview?.top_contents?.map((item: any, index: number) => (
                <tr key={item.id} className="border-b border-slate-50 hover:bg-slate-50">
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-3">
                      <span className="w-6 h-6 rounded-full bg-slate-100 flex items-center justify-center text-xs text-slate-500">
                        {index + 1}
                      </span>
                      <span className="font-medium text-slate-800 truncate max-w-xs">
                        {item.title}
                      </span>
                    </div>
                  </td>
                  <td className="text-right py-3 px-4 text-slate-600">{item.views.toLocaleString()}</td>
                  <td className="text-right py-3 px-4 text-slate-600">{item.likes.toLocaleString()}</td>
                  <td className="text-right py-3 px-4 text-slate-600">{item.comments.toLocaleString()}</td>
                  <td className="text-right py-3 px-4 text-slate-600">
                    {((item.likes + item.comments) / Math.max(item.views, 1) * 100).toFixed(1)}%
                  </td>
                </tr>
              )) || (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-500">
                    暂无数据
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
