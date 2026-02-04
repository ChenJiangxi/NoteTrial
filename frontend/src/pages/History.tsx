import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { contentAPI, experimentAPI } from '../services/api';
import {
  Clock, FileText, BarChart3, Play, Trash2,
  ChevronRight, Search
} from 'lucide-react';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';

interface ContentItem {
  id: string;
  title: string;
  status: 'draft' | 'published' | 'testing';
  created_at: string;
  updated_at: string;
}

interface ExperimentItem {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed';
  winner?: string;
  confidence?: number;
  created_at: string;
  completed_at?: string;
}

export default function History() {
  const [activeTab, setActiveTab] = useState<'contents' | 'experiments'>('contents');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const queryClient = useQueryClient();

  // 获取内容列表
  const { data: contentsData, isLoading: contentsLoading } = useQuery({
    queryKey: ['contents'],
    queryFn: async () => {
      const result = await contentAPI.getAll({ page: 1, page_size: 100 });
      return result;
    },
  });

  // 获取实验列表
  const { data: experimentsData, isLoading: experimentsLoading } = useQuery({
    queryKey: ['experiments'],
    queryFn: async () => {
      const result = await experimentAPI.getAll();
      return result;
    },
  });

  // 删除内容
  const deleteContentMutation = useMutation({
    mutationFn: (id: string) => contentAPI.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contents'] });
    },
  });

  // 运行实验
  const runExperimentMutation = useMutation({
    mutationFn: (id: string) => experimentAPI.run(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['experiments'] });
    },
  });

  const contents = Array.isArray(contentsData) ? contentsData : [];
  const experiments = Array.isArray(experimentsData) ? experimentsData : [];

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      draft: 'bg-slate-100 text-slate-600',
      published: 'bg-green-100 text-green-700',
      testing: 'bg-yellow-100 text-yellow-700',
      pending: 'bg-slate-100 text-slate-600',
      running: 'bg-blue-100 text-blue-700',
      completed: 'bg-green-100 text-green-700',
    };
    const labels: Record<string, string> = {
      draft: '草稿',
      published: '已发布',
      testing: '测试中',
      pending: '待运行',
      running: '运行中',
      completed: '已完成',
    };
    return (
      <span className={`px-2 py-0.5 text-xs rounded-full ${colors[status] || 'bg-slate-100'}`}>
        {labels[status] || status}
      </span>
    );
  };

  const filteredContents = contents.filter((item: ContentItem) => {
    const matchesSearch = item.title.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === 'all' || item.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const filteredExperiments = experiments.filter((exp: any) =>
    exp.name?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">历史记录</h1>
          <p className="text-slate-500 mt-1">管理你的内容和实验历史</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-4 border-b border-slate-200">
        <button
          onClick={() => setActiveTab('contents')}
          className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-colors ${
            activeTab === 'contents'
              ? 'border-[#ff2442] text-[#ff2442]'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          <FileText className="w-5 h-5" />
          内容历史
        </button>
        <button
          onClick={() => setActiveTab('experiments')}
          className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-colors ${
            activeTab === 'experiments'
              ? 'border-[#ff2442] text-[#ff2442]'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          <BarChart3 className="w-5 h-5" />
          实验历史
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4 bg-white p-4 rounded-xl border border-slate-200">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索..."
            className="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-100 focus:border-[#ff2442]"
          />
        </div>
        {activeTab === 'contents' && (
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-4 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-100"
          >
            <option value="all">全部状态</option>
            <option value="draft">草稿</option>
            <option value="published">已发布</option>
            <option value="testing">测试中</option>
          </select>
        )}
      </div>

      {/* Content List */}
      {activeTab === 'contents' && (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          {contentsLoading ? (
            <div className="p-8 text-center text-slate-500">
              <div className="animate-spin w-8 h-8 border-2 border-[#ff2442] border-t-transparent rounded-full mx-auto mb-4" />
              加载中...
            </div>
          ) : filteredContents.length === 0 ? (
            <div className="p-12 text-center text-slate-500">
              <Clock className="w-12 h-12 text-slate-300 mx-auto mb-4" />
              <p>暂无内容记录</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {filteredContents.map((item: ContentItem) => (
                <div
                  key={item.id}
                  className="flex items-center gap-4 p-4 hover:bg-slate-50 transition-colors"
                >
                  <div className="w-12 h-12 bg-slate-100 rounded-lg flex items-center justify-center">
                    <FileText className="w-6 h-6 text-slate-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-slate-800 truncate">{item.title}</h3>
                    <p className="text-sm text-slate-400 mt-0.5">
                      更新于 {format(new Date(item.updated_at), 'yyyy年MM月dd日 HH:mm', { locale: zhCN })}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    {getStatusBadge(item.status)}
                    <button
                      onClick={() => deleteContentMutation.mutate(item.id)}
                      className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                    <ChevronRight className="w-5 h-5 text-slate-300" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Experiment List */}
      {activeTab === 'experiments' && (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          {experimentsLoading ? (
            <div className="p-8 text-center text-slate-500">
              <div className="animate-spin w-8 h-8 border-2 border-[#ff2442] border-t-transparent rounded-full mx-auto mb-4" />
              加载中...
            </div>
          ) : filteredExperiments.length === 0 ? (
            <div className="p-12 text-center text-slate-500">
              <BarChart3 className="w-12 h-12 text-slate-300 mx-auto mb-4" />
              <p>暂无实验记录</p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {filteredExperiments.map((exp: any) => (
                <div
                  key={exp.id}
                  className="flex items-center gap-4 p-4 hover:bg-slate-50 transition-colors"
                >
                  <div className="w-12 h-12 bg-slate-100 rounded-lg flex items-center justify-center">
                    <BarChart3 className="w-6 h-6 text-slate-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-slate-800 truncate">{exp.name}</h3>
                    <p className="text-sm text-slate-400 mt-0.5">
                      创建于 {format(new Date(exp.created_at), 'yyyy年MM月dd日 HH:mm', { locale: zhCN })}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    {getStatusBadge(exp.status)}
                    {exp.winner && (
                      <span className="text-sm text-slate-600">
                        胜出: <span className="font-medium">{exp.winner}</span>
                      </span>
                    )}
                    {exp.status === 'pending' && (
                      <button
                        onClick={() => runExperimentMutation.mutate(exp.id)}
                        className="flex items-center gap-1 px-3 py-1 bg-[#ff2442] text-white text-sm rounded-lg hover:bg-[#e61f3d] transition-colors"
                      >
                        <Play className="w-4 h-4" />
                        运行
                      </button>
                    )}
                    <ChevronRight className="w-5 h-5 text-slate-300" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
