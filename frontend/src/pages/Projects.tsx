import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Plus, MoreVertical, Users, Settings, Trash2, Edit2,
  FolderOpen, Calendar, AlertCircle, RefreshCw, X, Check
} from 'lucide-react';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';

interface Project {
  id: string;
  name: string;
  description?: string;
  status: 'active' | 'archived' | 'draft';
  member_count: number;
  content_count: number;
  created_at: string;
  updated_at: string;
  owner: {
    id: string;
    nickname: string;
    avatar_url?: string;
  };
  members?: Array<{
    user_id: string;
    nickname: string;
    avatar_url?: string;
    role: 'owner' | 'admin' | 'member';
  }>;
}

interface CreateProjectData {
  name: string;
  description?: string;
}

interface EditProjectData extends CreateProjectData {
  id: string;
}

// 模拟 API 调用
const mockProjects: Project[] = [
  {
    id: '1',
    name: '小红书营销项目',
    description: '主品牌官方账号运营',
    status: 'active',
    member_count: 3,
    content_count: 28,
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-02-10T14:30:00Z',
    owner: { id: '1', nickname: '张明' },
    members: [
      { user_id: '1', nickname: '张明', role: 'owner' },
      { user_id: '2', nickname: '李华', role: 'admin' },
      { user_id: '3', nickname: '王芳', role: 'member' },
    ],
  },
  {
    id: '2',
    name: '抖音带货测试',
    description: '新号起号测试项目',
    status: 'active',
    member_count: 2,
    content_count: 15,
    created_at: '2024-02-01T09:00:00Z',
    updated_at: '2024-02-12T16:45:00Z',
    owner: { id: '1', nickname: '张明' },
    members: [
      { user_id: '1', nickname: '张明', role: 'owner' },
      { user_id: '4', nickname: '赵磊', role: 'admin' },
    ],
  },
  {
    id: '3',
    name: '历史内容归档',
    description: '',
    status: 'archived',
    member_count: 1,
    content_count: 56,
    created_at: '2023-06-01T08:00:00Z',
    updated_at: '2023-12-31T23:59:59Z',
    owner: { id: '1', nickname: '张明' },
  },
];

export default function Projects() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showMembersModal, setShowMembersModal] = useState(false);
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [newProject, setNewProject] = useState<CreateProjectData>({ name: '', description: '' });
  const [editProject, setEditProject] = useState<EditProjectData>({ id: '', name: '', description: '' });
  const [filter, setFilter] = useState<'all' | 'active' | 'archived'>('all');

  const queryClient = useQueryClient();

  // 获取项目列表
  const { data: projectsData, isLoading, error, refetch } = useQuery({
    queryKey: ['projects'],
    queryFn: async () => {
      // 模拟 API 调用
      return { projects: mockProjects };
    },
    retry: 2,
  });

  // 创建项目
  const createMutation = useMutation({
    mutationFn: async (data: CreateProjectData) => {
      // 模拟 API 调用
      await new Promise(resolve => setTimeout(resolve, 500));
      return { id: Date.now().toString(), ...data, status: 'active' as const };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      setShowCreateModal(false);
      setNewProject({ name: '', description: '' });
    },
  });

  // 编辑项目
  const editMutation = useMutation({
    mutationFn: async (data: EditProjectData) => {
      await new Promise(resolve => setTimeout(resolve, 500));
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      setShowEditModal(false);
      setSelectedProject(null);
    },
  });

  // 删除项目
  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await new Promise(resolve => setTimeout(resolve, 500));
      return id;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });

  const projects = projectsData?.projects || [];
  const filteredProjects = filter === 'all'
    ? projects
    : projects.filter(p => p.status === filter);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400';
      case 'archived':
        return 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400';
      default:
        return 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'active':
        return '进行中';
      case 'archived':
        return '已归档';
      default:
        return status;
    }
  };

  const openEditModal = (project: Project) => {
    setSelectedProject(project);
    setEditProject({ id: project.id, name: project.name, description: project.description || '' });
    setShowEditModal(true);
  };

  const openMembersModal = (project: Project) => {
    setSelectedProject(project);
    setShowMembersModal(true);
  };

  const openSettingsModal = (project: Project) => {
    setSelectedProject(project);
    setShowSettingsModal(true);
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
          <h1 className="text-2xl font-bold text-slate-800 dark:text-white">项目管理</h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">管理你的内容项目团队</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-[#ff2442] text-white font-medium rounded-xl hover:bg-[#e61f3d] transition-all shadow-lg shadow-red-200 dark:shadow-none"
        >
          <Plus className="w-5 h-5" />
          新建项目
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => setFilter('all')}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            filter === 'all'
              ? 'bg-[#ff2442] text-white'
              : 'text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          全部
        </button>
        <button
          onClick={() => setFilter('active')}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            filter === 'active'
              ? 'bg-[#ff2442] text-white'
              : 'text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          进行中
        </button>
        <button
          onClick={() => setFilter('archived')}
          className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
            filter === 'archived'
              ? 'bg-[#ff2442] text-white'
              : 'text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          已归档
        </button>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin w-8 h-8 border-2 border-[#ff2442] border-t-transparent rounded-full" />
        </div>
      )}

      {/* Projects Grid */}
      {!isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 lg:gap-6">
          {filteredProjects.length === 0 ? (
            <div className="col-span-full flex flex-col items-center justify-center py-12">
              <FolderOpen className="w-12 h-12 text-slate-300 dark:text-slate-600 mb-4" />
              <h3 className="text-lg font-medium text-slate-700 dark:text-white mb-2">暂无项目</h3>
              <p className="text-slate-500 dark:text-slate-400 mb-6">创建你的第一个项目开始管理内容</p>
              <button
                onClick={() => setShowCreateModal(true)}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#ff2442] text-white font-medium rounded-xl hover:bg-[#e61f3d] transition-colors"
              >
                <Plus className="w-5 h-5" />
                新建项目
              </button>
            </div>
          ) : (
            filteredProjects.map((project: Project) => (
              <div
                key={project.id}
                className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6 hover:shadow-lg transition-all group"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-slate-800 dark:text-white truncate">{project.name}</h3>
                    {project.description && (
                      <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 truncate">{project.description}</p>
                    )}
                  </div>
                  <div className="relative">
                    <button className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors">
                      <MoreVertical className="w-5 h-5" />
                    </button>
                  </div>
                </div>

                <div className="flex items-center gap-4 mb-4">
                  <span className={`text-xs px-2.5 py-1 rounded-full ${getStatusBadge(project.status)}`}>
                    {getStatusText(project.status)}
                  </span>
                  <span className="text-xs text-slate-400 dark:text-slate-500 flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {format(new Date(project.updated_at), 'MM月dd日', { locale: zhCN })}
                  </span>
                </div>

                <div className="flex items-center justify-between pt-4 border-t border-slate-100 dark:border-slate-700">
                  <div className="flex items-center gap-4 text-sm text-slate-500 dark:text-slate-400">
                    <span className="flex items-center gap-1">
                      <FolderOpen className="w-4 h-4" />
                      {project.content_count}
                    </span>
                    <span className="flex items-center gap-1">
                      <Users className="w-4 h-4" />
                      {project.member_count}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => openMembersModal(project)}
                      className="p-2 text-slate-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
                      title="成员管理"
                    >
                      <Users className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => openSettingsModal(project)}
                      className="p-2 text-slate-400 hover:text-green-500 hover:bg-green-50 dark:hover:bg-green-900/30 rounded-lg transition-colors"
                      title="项目设置"
                    >
                      <Settings className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-800 rounded-2xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-slate-800 dark:text-white">新建项目</h2>
              <button
                onClick={() => setShowCreateModal(false)}
                className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  项目名称 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={newProject.name}
                  onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
                  className="w-full px-4 py-2.5 border border-slate-200 dark:border-slate-600 rounded-xl bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#ff2442] focus:border-transparent"
                  placeholder="输入项目名称"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  项目描述
                </label>
                <textarea
                  value={newProject.description}
                  onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
                  className="w-full px-4 py-2.5 border border-slate-200 dark:border-slate-600 rounded-xl bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#ff2442] focus:border-transparent resize-none"
                  rows={3}
                  placeholder="输入项目描述（可选）"
                />
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
                onClick={() => createMutation.mutate(newProject)}
                disabled={!newProject.name || createMutation.isPending}
                className="px-4 py-2 text-sm font-medium text-white bg-[#ff2442] rounded-lg hover:bg-[#e61f3d] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {createMutation.isPending && (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                )}
                创建
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {showEditModal && selectedProject && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-800 rounded-2xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-slate-800 dark:text-white">编辑项目</h2>
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
                  项目名称 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={editProject.name}
                  onChange={(e) => setEditProject({ ...editProject, name: e.target.value })}
                  className="w-full px-4 py-2.5 border border-slate-200 dark:border-slate-600 rounded-xl bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#ff2442] focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                  项目描述
                </label>
                <textarea
                  value={editProject.description}
                  onChange={(e) => setEditProject({ ...editProject, description: e.target.value })}
                  className="w-full px-4 py-2.5 border border-slate-200 dark:border-slate-600 rounded-xl bg-white dark:bg-slate-700 text-slate-800 dark:text-white focus:outline-none focus:ring-2 focus:ring-[#ff2442] focus:border-transparent resize-none"
                  rows={3}
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
                onClick={() => editMutation.mutate(editProject)}
                disabled={!editProject.name || editMutation.isPending}
                className="px-4 py-2 text-sm font-medium text-white bg-[#ff2442] rounded-lg hover:bg-[#e61f3d] transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {editMutation.isPending && (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                )}
                保存
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Members Modal */}
      {showMembersModal && selectedProject && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-800 rounded-2xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-slate-800 dark:text-white">成员管理</h2>
              <button
                onClick={() => setShowMembersModal(false)}
                className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3">
              {selectedProject.members?.map((member) => (
                <div key={member.user_id} className="flex items-center gap-3 p-3 bg-slate-50 dark:bg-slate-700/50 rounded-xl">
                  <div className="w-10 h-10 bg-[#ff2442] rounded-full flex items-center justify-center text-white font-medium">
                    {member.nickname.charAt(0)}
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-slate-800 dark:text-white">{member.nickname}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {member.role === 'owner' ? '所有者' : member.role === 'admin' ? '管理员' : '成员'}
                    </p>
                  </div>
                  {member.role !== 'owner' && (
                    <button className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>

            <button className="w-full mt-4 px-4 py-2.5 border border-dashed border-slate-300 dark:border-slate-600 text-slate-500 dark:text-slate-400 rounded-xl hover:border-[#ff2442] hover:text-[#ff2442] transition-colors flex items-center justify-center gap-2">
              <Plus className="w-4 h-4" />
              添加成员
            </button>

            <div className="flex items-center justify-end gap-3 mt-6">
              <button
                onClick={() => setShowMembersModal(false)}
                className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
              >
                关闭
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Settings Modal */}
      {showSettingsModal && selectedProject && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-800 rounded-2xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-slate-800 dark:text-white">项目设置</h2>
              <button
                onClick={() => setShowSettingsModal(false)}
                className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div className="p-4 bg-slate-50 dark:bg-slate-700/50 rounded-xl">
                <h3 className="font-medium text-slate-800 dark:text-white mb-2">编辑项目</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400 mb-3">修改项目名称和描述</p>
                <button
                  onClick={() => {
                    setShowSettingsModal(false);
                    openEditModal(selectedProject);
                  }}
                  className="flex items-center gap-2 px-4 py-2 bg-[#ff2442] text-white rounded-lg hover:bg-[#e61f3d] transition-colors"
                >
                  <Edit2 className="w-4 h-4" />
                  编辑
                </button>
              </div>

              <div className="p-4 bg-slate-50 dark:bg-slate-700/50 rounded-xl">
                <h3 className="font-medium text-slate-800 dark:text-white mb-2">归档项目</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400 mb-3">将项目移到归档，停止活跃运营</p>
                <button className="flex items-center gap-2 px-4 py-2 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-600 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors">
                  <FolderOpen className="w-4 h-4" />
                  归档
                </button>
              </div>

              <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-xl">
                <h3 className="font-medium text-red-700 dark:text-red-400 mb-2">删除项目</h3>
                <p className="text-sm text-red-600 dark:text-red-400 mb-3">删除项目及其所有内容，此操作不可恢复</p>
                <button className="flex items-center gap-2 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors">
                  <Trash2 className="w-4 h-4" />
                  删除
                </button>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 mt-6">
              <button
                onClick={() => setShowSettingsModal(false)}
                className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
              >
                关闭
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
