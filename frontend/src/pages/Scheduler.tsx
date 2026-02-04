import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Plus, Calendar, Clock, Edit2, Trash2, AlertCircle,
  RefreshCw, X, Check, ChevronLeft, ChevronRight,
  MoreVertical, Image, FileText, Send
} from 'lucide-react';
import { format, addDays, addHours, startOfDay, setHours, setMinutes } from 'date-fns';
import { zhCN } from 'date-fns/locale';

interface ScheduledTask {
  id: string;
  title: string;
  content_preview: string;
  cover_image?: string;
  scheduled_at: string;
  platform: string;
  status: 'pending' | 'published' | 'failed' | 'cancelled';
  created_at: string;
}

interface CreateTaskData {
  title: string;
  content: string;
  scheduled_at: string;
  platform: string;
  cover_image?: string;
}

const platforms = [
  { id: 'xiaohongshu', name: '小红书', icon: '📕' },
  { id: 'douyin', name: '抖音', icon: '🎵' },
  { id: 'bilibili', name: 'B站', icon: '📺' },
];

const mockTasks: ScheduledTask[] = [
  {
    id: '1',
    title: '春季新品种草笔记',
    content_preview: '春天到了，是时候更新你的衣橱了！今天给大家推荐几款超适合春季的穿搭单品...',
    scheduled_at: new Date(Date.now() + 86400000).toISOString(),
    platform: 'xiaohongshu',
    status: 'pending',
    created_at: new Date().toISOString(),
  },
  {
    id: '2',
    title: '周末探店VLOG',
    content_preview: '周末去了市中心新开的咖啡店，环境超级棒！点了他们家的招牌拿铁...',
    scheduled_at: new Date(Date.now() + 172800000).toISOString(),
    platform: 'douyin',
    status: 'pending',
    created_at: new Date().toISOString(),
  },
  {
    id: '3',
    title: '美妆教程：日常淡妆',
    content_preview: '很多姐妹问我日常上班约会适合什么妆容，今天就出一个详细的教程...',
    cover_image: 'https://via.placeholder.com/100x100',
    scheduled_at: new Date(Date.now() + 259200000).toISOString(),
    platform: 'xiaohongshu',
    status: 'pending',
    created_at: new Date().toISOString(),
  },
];

export default function Scheduler() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedTask, setSelectedTask] = useState<ScheduledTask | null>(null);
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [newTask, setNewTask] = useState<Partial<CreateTaskData>>({
    platform: 'xiaohongshu',
  });

  const queryClient = useQueryClient();

  // 获取定时任务列表
  const { data: tasksData, isLoading, error, refetch } = useQuery({
    queryKey: ['scheduled-tasks'],
    queryFn: async () => {
      return { tasks: mockTasks };
    },
    retry: 2,
  });

  // 创建任务
  const createMutation = useMutation({
    mutationFn: async (data: CreateTaskData) => {
      await new Promise(resolve => setTimeout(resolve, 500));
      return { id: Date.now().toString(), ...data, status: 'pending' as const };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scheduled-tasks'] });
      setShowCreateModal(false);
      setNewTask({ platform: 'xiaohongshu' });
    },
  });

  // 取消任务
  const cancelMutation = useMutation({
    mutationFn: async (id: string) => {
      await new Promise(resolve => setTimeout(resolve, 500));
      return id;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scheduled-tasks'] });
    },
  });

  // 删除任务
  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await new Promise(resolve => setTimeout(resolve, 500));
      return id;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scheduled-tasks'] });
    },
  });

  const tasks = tasksData?.tasks || [];
  const pendingTasks = tasks.filter(t => t.status === 'pending');

  // 获取日历显示的日期
  const getCalendarDays = () => {
    const start = startOfDay(currentMonth);
    const days: Date[] = [];
    for (let i = 0; i < 35; i++) {
      days.push(addDays(start, i));
    }
    return days;
  };

  const getTasksForDate = (date: Date) => {
    return pendingTasks.filter(task => {
      const taskDate = new Date(task.scheduled_at);
      return format(taskDate, 'yyyy-MM-dd') === format(date, 'yyyy-MM-dd');
    });
  };

  const hasTaskOnDate = (date: Date) => getTasksForDate(date).length > 0;

  // 快捷时间选择
  const quickTimeOptions = [
    { label: '1小时后', getValue: () => addHours(new Date(), 1).toISOString() },
    { label: '明天上午10点', getValue: () => setMinutes(setHours(addDays(new Date(), 1), 10), 0).toISOString() },
    { label: '明天下午2点', getValue: () => setMinutes(setHours(addDays(new Date(), 1), 14), 0).toISOString() },
    { label: '后天上午10点', getValue: () => setMinutes(setHours(addDays(new Date(), 2), 10), 0).toISOString() },
  ];

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
      case 'published':
        return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400';
      case 'failed':
        return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
      case 'cancelled':
        return 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400';
      default:
        return 'bg-slate-100 text-slate-600';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'pending':
        return '待发布';
      case 'published':
        return '已发布';
      case 'failed':
        return '失败';
      case 'cancelled':
        return '已取消';
      default:
        return status;
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
          onClick={() => refetch()}
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
          <h1 className="text-2xl font-bold text-slate-800 dark:text-white">定时发布</h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">管理你的定时发布任务</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-[#ff2442] text-white font-medium rounded-xl hover:bg-[#e61f3d] transition-all shadow-lg shadow-red-200 dark:shadow-none"
        >
          <Plus className="w-5 h-5" />
          新建定时任务
        </button>
      </div>

      {/* Calendar & Tasks */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Calendar */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
          <div className="flex items-center justify-between mb-4">
            <button
              onClick={() => setCurrentMonth(addDays(currentMonth, -30))}
              className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <h3 className="text-lg font-semibold text-slate-800 dark:text-white">
              {format(currentMonth, 'yyyy年M月', { locale: zhCN })}
            </h3>
            <button
              onClick={() => setCurrentMonth(addDays(currentMonth, 30))}
              className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>

          <div className="grid grid-cols-7 gap-1 mb-2">
            {['日', '一', '二', '三', '四', '五', '六'].map((day) => (
              <div key={day} className="text-center text-xs text-slate-400 dark:text-slate-500 py-2">
                {day}
              </div>
            ))}
          </div>

          <div className="grid grid-cols-7 gap-1">
            {getCalendarDays().map((day, index) => {
              const isToday = format(day, 'yyyy-MM-dd') === format(new Date(), 'yyyy-MM-dd');
              const isSelected = selectedDate && format(day, 'yyyy-MM-dd') === format(selectedDate, 'yyyy-MM-dd');
              const hasTasks = hasTaskOnDate(day);
              const dayTasks = getTasksForDate(day);

              return (
                <button
                  key={index}
                  onClick={() => {
                    setSelectedDate(day);
                    setSelectedTask(dayTasks[0] || null);
                  }}
                  className={`
                    relative aspect-square flex items-center justify-center text-sm rounded-lg transition-colors
                    ${isSelected
                      ? 'bg-[#ff2442] text-white'
                      : isToday
                        ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-semibold'
                        : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'
                    }
                  `}
                >
                  {format(day, 'd')}
                  {hasTasks && !isSelected && (
                    <span className={`absolute bottom-1 w-1.5 h-1.5 rounded-full ${isToday ? 'bg-blue-400' : 'bg-[#ff2442]'}`} />
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Tasks List */}
        <div className="lg:col-span-2 space-y-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin w-8 h-8 border-2 border-[#ff2442] border-t-transparent rounded-full" />
            </div>
          ) : selectedDate ? (
            <>
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-slate-800 dark:text-white">
                  {format(selectedDate, 'yyyy年MM月dd日', { locale: zhCN })}
                </h3>
                <span className="text-sm text-slate-500 dark:text-slate-400">
                  {getTasksForDate(selectedDate).length} 个任务
                </span>
              </div>

              {getTasksForDate(selectedDate).length === 0 ? (
                <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-12 flex flex-col items-center">
                  <Calendar className="w-12 h-12 text-slate-300 dark:text-slate-600 mb-4" />
                  <h3 className="text-lg font-medium text-slate-700 dark:text-white mb-2">暂无任务</h3>
                  <p className="text-slate-500 dark:text-slate-400 mb-6">选择其他日期或创建新任务</p>
                  <button
                    onClick={() => setShowCreateModal(true)}
                    className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#ff2442] text-white font-medium rounded-xl hover:bg-[#e61f3d] transition-colors"
                  >
                    <Plus className="w-5 h-5" />
                    新建任务
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  {getTasksForDate(selectedDate).map((task) => (
                    <div
                      key={task.id}
                      className={`bg-white dark:bg-slate-800 rounded-xl border p-4 transition-all ${
                        selectedTask?.id === task.id
                          ? 'border-[#ff2442] shadow-md'
                          : 'border-slate-200 dark:border-slate-700'
                      }`}
                    >
                      <div className="flex items-start gap-4">
                        {task.cover_image ? (
                          <img
                            src={task.cover_image}
                            alt={task.title}
                            className="w-16 h-16 rounded-lg object-cover flex-shrink-0"
                          />
                        ) : (
                          <div className="w-16 h-16 bg-slate-100 dark:bg-slate-700 rounded-lg flex items-center justify-center flex-shrink-0">
                            <Image className="w-6 h-6 text-slate-400 dark:text-slate-500" />
                          </div>
                        )}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs px-2 py-0.5 rounded-full bg-[#ff2442]/10 text-[#ff2442]">
                              {platforms.find(p => p.id === task.platform)?.name}
                            </span>
                            <span className={`text-xs px-2 py-0.5 rounded-full ${getStatusBadge(task.status)}`}>
                              {getStatusText(task.status)}
                            </span>
                          </div>
                          <h4 className="font-medium text-slate-800 dark:text-white truncate">{task.title}</h4>
                          <p className="text-sm text-slate-500 dark:text-slate-400 truncate mt-1">{task.content_preview}</p>
                          <div className="flex items-center gap-3 mt-2 text-xs text-slate-400 dark:text-slate-500">
                            <span className="flex items-center gap-1">
                              <Clock className="w-3.5 h-3.5" />
                              {format(new Date(task.scheduled_at), 'HH:mm')}
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center gap-1">
                          {task.status === 'pending' && (
                            <>
                              <button
                                onClick={() => {
                                  setSelectedTask(task);
                                  setNewTask({
                                    title: task.title,
                                    content: task.content_preview,
                                    platform: task.platform,
                                    scheduled_at: task.scheduled_at,
                                  });
                                  setShowEditModal(true);
                                }}
                                className="p-2 text-slate-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
                              >
                                <Edit2 className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => cancelMutation.mutate(task.id)}
                                className="p-2 text-slate-400 hover:text-amber-500 hover:bg-amber-50 dark:hover:bg-amber-900/30 rounded-lg transition-colors"
                              >
                                <X className="w-4 h-4" />
                              </button>
                            </>
                          )}
                          <button
                            onClick={() => deleteMutation.mutate(task.id)}
                            className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-12 flex flex-col items-center justify-center h-full">
              <Calendar className="w-12 h-12 text-slate-300 dark:text-slate-600 mb-4" />
              <h3 className="text-lg font-medium text-slate-700 dark:text-white mb-2">选择日期</h3>
              <p className="text-slate-500 dark:text-slate-400">点击日历查看当天的定时任务</p>
            </div>
          )}
        </div>
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 overflow-y-auto">
          <div className="bg-white dark:bg-slate-800 rounded-2xl w-full max-w-lg p-6 my-8">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-slate-800 dark:text-white">新建定时任务</h2>
              <button
                onClick={() => setShowCreateModal(false)}
                className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              {/* Platform Selection */}
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  发布平台 <span className="text-red-500">*</span>
                </label>
                <div className="flex gap-2">
                  {platforms.map((platform) => (
                    <button
                      key={platform.id}
                      onClick={() => setNewTask({ ...newTask, platform: platform.id })}
                      className={`flex-1 px-4 py-3 rounded-xl border transition-colors ${
                        newTask.platform === platform.id
                          ? 'border-[#ff2442] bg-[#ff2442]/5 text-[#ff2442]'
                          : 'border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-500'
                      }`}
                    >
                      <span className="text-lg">{platform.icon}</span>
                      <span className="block text-sm mt-1">{platform.name}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Title */}
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  标题 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={newTask.title || ''}
                  onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
                  className="w-full px-4 py-2.5 border border-slate-200 dark:border-slate-600 rounded-xl bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#ff2442] focus:border-transparent"
                  placeholder="输入内容标题"
                />
              </div>

              {/* Content */}
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  内容 <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={newTask.content || ''}
                  onChange={(e) => setNewTask({ ...newTask, content: e.target.value })}
                  className="w-full px-4 py-2.5 border border-slate-200 dark:border-slate-600 rounded-xl bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#ff2442] focus:border-transparent resize-none"
                  rows={4}
                  placeholder="输入内容正文"
                />
              </div>

              {/* Schedule Time */}
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  定时时间 <span className="text-red-500">*</span>
                </label>
                <input
                  type="datetime-local"
                  value={newTask.scheduled_at ? format(new Date(newTask.scheduled_at), "yyyy-MM-dd'T'HH:mm") : ''}
                  onChange={(e) => setNewTask({ ...newTask, scheduled_at: new Date(e.target.value).toISOString() })}
                  className="w-full px-4 py-2.5 border border-slate-200 dark:border-slate-600 rounded-xl bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#ff2442] focus:border-transparent"
                />

                {/* Quick Time Options */}
                <div className="flex flex-wrap gap-2 mt-2">
                  {quickTimeOptions.map((option) => (
                    <button
                      key={option.label}
                      onClick={() => setNewTask({ ...newTask, scheduled_at: option.getValue() })}
                      className="px-3 py-1.5 text-xs text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-700 rounded-lg hover:bg-[#ff2442]/10 hover:text-[#ff2442] transition-colors"
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 mt-6">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
              >
                取消
              </button>
              <button
                onClick={() => createMutation.mutate(newTask as CreateTaskData)}
                disabled={!newTask.title || !newTask.content || !newTask.scheduled_at || createMutation.isPending}
                className="px-4 py-2 text-sm font-medium text-white bg-[#ff2442] rounded-lg hover:bg-[#e61f3d] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {createMutation.isPending && (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                )}
                创建任务
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {showEditModal && selectedTask && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-800 rounded-2xl w-full max-w-lg p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-slate-800 dark:text-white">修改定时任务</h2>
              <button
                onClick={() => setShowEditModal(false)}
                className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  标题
                </label>
                <input
                  type="text"
                  value={newTask.title || ''}
                  onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
                  className="w-full px-4 py-2.5 border border-slate-200 dark:border-slate-600 rounded-xl bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#ff2442]"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  定时时间
                </label>
                <input
                  type="datetime-local"
                  value={newTask.scheduled_at ? format(new Date(newTask.scheduled_at), "yyyy-MM-dd'T'HH:mm") : ''}
                  onChange={(e) => setNewTask({ ...newTask, scheduled_at: new Date(e.target.value).toISOString() })}
                  className="w-full px-4 py-2.5 border border-slate-200 dark:border-slate-600 rounded-xl bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#ff2442]"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 mt-6">
              <button
                onClick={() => setShowEditModal(false)}
                className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
              >
                取消
              </button>
              <button
                onClick={() => {
                  // Handle edit
                  setShowEditModal(false);
                }}
                className="px-4 py-2 text-sm font-medium text-white bg-[#ff2442] rounded-lg hover:bg-[#e61f3d] transition-colors flex items-center gap-2"
              >
                <Check className="w-4 h-4" />
                保存
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
