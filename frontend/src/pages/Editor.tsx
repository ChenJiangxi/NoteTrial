import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { contentAPI } from '../services/api';
import { useAuthStore } from '../stores/auth';
import {
  ArrowLeft, Save, Image as ImageIcon, Tag, Wand2,
  Play, Loader2, X, Sparkles, Share2, Check
} from 'lucide-react';

export default function Editor() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const isEditing = !!id;

  const [formData, setFormData] = useState({
    title: '',
    body: '',
    tags: [] as string[],
    cover_image: '',
  });
  const [tagInput, setTagInput] = useState('');
  const [showImageManager, setShowImageManager] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  // 获取内容详情
  const { data: content, isLoading } = useQuery({
    queryKey: ['content', id],
    queryFn: async () => {
      if (!id) return null;
      const { data } = await contentAPI.getById(id);
      return data;
    },
    enabled: !!id,
  });

  useEffect(() => {
    if (content) {
      setFormData({
        title: content.title || '',
        body: content.body || '',
        tags: content.tags || [],
        cover_image: content.cover_image || '',
      });
    }
  }, [content]);

  // 保存内容
  const saveMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      if (isEditing) {
        const { data: res } = await contentAPI.update(id, data);
        return res;
      } else {
        const { data: res } = await contentAPI.create(data);
        return res;
      }
    },
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['contents'] });
      if (!isEditing && res.id) {
        navigate(`/editor/${res.id}`);
      }
    },
  });

  // AI 生成内容
  const generateMutation = useMutation({
    mutationFn: async (prompt: string) => {
      const { data } = await contentAPI.create({
        title: prompt,
        body: `AI generated content for: ${prompt}`,
      });
      return data;
    },
    onSuccess: (res) => {
      setFormData({
        title: res.title || '',
        body: res.body || '',
        tags: res.tags || [],
        cover_image: res.cover_image || '',
      });
      setIsGenerating(false);
    },
  });

  const handleSave = () => {
    saveMutation.mutate(formData);
  };

  const handleGenerate = async () => {
    if (!formData.title.trim()) return;
    setIsGenerating(true);
    generateMutation.mutate(formData.title);
  };

  const handleAddTag = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && tagInput.trim()) {
      e.preventDefault();
      if (!formData.tags.includes(tagInput.trim())) {
        setFormData({ ...formData, tags: [...formData.tags, tagInput.trim()] });
      }
      setTagInput('');
    }
  };

  const handleRemoveTag = (tag: string) => {
    setFormData({ ...formData, tags: formData.tags.filter((t) => t !== tag) });
  };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (ev) => {
        setFormData({ ...formData, cover_image: ev.target?.result as string });
        setShowImageManager(false);
      };
      reader.readAsDataURL(file);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-[#ff2442]" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(-1)}
            className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-xl font-bold text-slate-800">
              {isEditing ? '编辑内容' : '新建内容'}
            </h1>
            <p className="text-sm text-slate-500">
              {isEditing ? '更新你的内容' : '创建一篇新内容'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleGenerate}
            disabled={!formData.title.trim() || isGenerating}
            className="flex items-center gap-2 px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-xl transition-colors disabled:opacity-50"
          >
            {isGenerating ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Sparkles className="w-5 h-5 text-[#ff2442]" />
            )}
            AI 生成
          </button>
          <button
            onClick={handleSave}
            disabled={saveMutation.isPending}
            className="flex items-center gap-2 px-5 py-2.5 bg-[#ff2442] text-white font-medium rounded-xl hover:bg-[#e61f3d] transition-colors disabled:opacity-50"
          >
            {saveMutation.isPending ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Save className="w-5 h-5" />
            )}
            保存
          </button>
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {/* Cover Image */}
        <div className="relative h-48 bg-slate-100">
          {formData.cover_image ? (
            <>
              <img
                src={formData.cover_image}
                alt="Cover"
                className="w-full h-full object-cover"
              />
              <button
                onClick={() => setShowImageManager(true)}
                className="absolute bottom-3 right-3 px-3 py-1.5 bg-black/70 text-white text-sm rounded-lg hover:bg-black transition-colors"
              >
                更换图片
              </button>
            </>
          ) : (
            <div
              onClick={() => setShowImageManager(true)}
              className="w-full h-full flex flex-col items-center justify-center cursor-pointer hover:bg-slate-200/50 transition-colors"
            >
              <ImageIcon className="w-10 h-10 text-slate-300 mb-2" />
              <span className="text-sm text-slate-400">上传封面图</span>
            </div>
          )}
        </div>

        {/* Form */}
        <div className="p-6 space-y-6">
          {/* Title */}
          <div>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              placeholder="输入标题..."
              className="w-full text-2xl font-bold text-slate-800 placeholder:text-slate-300 border-none p-0 focus:ring-0 bg-transparent"
            />
          </div>

          {/* Body */}
          <div>
            <textarea
              value={formData.body}
              onChange={(e) => setFormData({ ...formData, body: e.target.value })}
              placeholder="输入正文内容..."
              className="w-full h-64 resize-none text-slate-600 placeholder:text-slate-300 border-none p-0 focus:ring-0 bg-transparent text-base leading-relaxed"
            />
          </div>

          {/* Tags */}
          <div className="border-t border-slate-100 pt-6">
            <div className="flex items-center gap-2 mb-3">
              <Tag className="w-4 h-4 text-slate-400" />
              <span className="text-sm font-medium text-slate-700">标签</span>
            </div>
            <div className="flex flex-wrap gap-2 mb-3">
              {formData.tags.map((tag) => (
                <span
                  key={tag}
                  className="inline-flex items-center gap-1 px-3 py-1 bg-slate-100 text-slate-600 text-sm rounded-full"
                >
                  #{tag}
                  <button
                    onClick={() => handleRemoveTag(tag)}
                    className="text-slate-400 hover:text-red-500"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
            <input
              type="text"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={handleAddTag}
              placeholder="添加标签，按回车确认..."
              className="w-full px-4 py-2 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-red-100 focus:border-[#ff2442]"
            />
          </div>
        </div>
      </div>

      {/* Image Manager Modal */}
      {showImageManager && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-slate-800">选择图片</h3>
              <button
                onClick={() => setShowImageManager(false)}
                className="p-1 text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="space-y-4">
              <label className="flex items-center justify-center gap-2 px-4 py-8 border-2 border-dashed border-slate-300 rounded-xl cursor-pointer hover:border-[#ff2442] hover:bg-red-50/50 transition-colors">
                <ImageIcon className="w-8 h-8 text-slate-300" />
                <span className="text-slate-500">点击上传图片</span>
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleImageUpload}
                  className="hidden"
                />
              </label>
              <p className="text-xs text-slate-400 text-center">
                支持 JPG, PNG, GIF 格式
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
