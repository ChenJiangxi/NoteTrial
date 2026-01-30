import { useState } from 'react'
import { RefreshCw, Wand2, Image, Tag, X, Link, Upload, Sparkles, Send } from 'lucide-react'
import type { ContentItem, TaskSpec } from '../types/api'
import { generateVariant, searchImages, publishContent } from '../services/api'

interface ContentEditorProps {
  contentA: ContentItem
  contentB: ContentItem
  taskSpec: TaskSpec | null
  onContentAChange: (content: ContentItem) => void
  onContentBChange: (content: ContentItem) => void
}

export default function ContentEditor({
  contentA,
  contentB,
  taskSpec,
  onContentAChange,
  onContentBChange,
}: ContentEditorProps) {
  const [isGenerating, setIsGenerating] = useState(false)
  const [activeTab, setActiveTab] = useState<'A' | 'B'>('A')
  const [isSearchingImages, setIsSearchingImages] = useState(false)
  const [suggestedImages, setSuggestedImages] = useState<string[]>([])
  const [showImageInput, setShowImageInput] = useState<'A' | 'B' | null>(null)
  const [isPublishing, setIsPublishing] = useState(false)

  const handleGenerateVariant = async (type: 'alternative' | 'hook' | 'actionable') => {
    if (!taskSpec || !contentA.title) return

    setIsGenerating(true)
    try {
      const variant = await generateVariant({
        task_spec: taskSpec,
        base_content: contentA,
        variant_type: type,
      })
      onContentBChange(variant)
      setActiveTab('B')
    } catch (error) {
      console.error('生成变体失败:', error)
    } finally {
      setIsGenerating(false)
    }
  }

  // 搜索相关图片
  const handleSearchImages = async (version: 'A' | 'B') => {
    const topic = taskSpec?.topic || contentA.title || contentB.title
    if (!topic) {
      alert('请先输入标题或在对话中设定话题')
      return
    }

    setIsSearchingImages(true)
    setShowImageInput(version)  // 先显示加载状态
    setSuggestedImages([])  // 清空之前的图片
    
    try {
      const images = await searchImages(topic, 6)
      setSuggestedImages(images)
      if (images.length === 0) {
        alert(`未找到与「${topic}」相关的图片，请尝试其他关键词`)
        setShowImageInput(null)
      }
    } catch (error) {
      console.error('搜索图片失败:', error)
      alert('搜索图片失败，请稍后重试')
      setShowImageInput(null)
    } finally {
      setIsSearchingImages(false)
    }
  }

  // 处理图片文件上传
  const handleFileUpload = (file: File, onChange: (content: ContentItem) => void, content: ContentItem) => {
    // 创建本地预览 URL
    const reader = new FileReader()
    reader.onload = (e) => {
      const dataUrl = e.target?.result as string
      onChange({ ...content, cover_image: dataUrl })
    }
    reader.readAsDataURL(file)
  }

  // 直接发布内容
  const handlePublish = async (content: ContentItem, version: 'A' | 'B') => {
    if (!content.title || !content.body) {
      alert('请先填写标题和正文')
      return
    }
    if (!content.cover_image) {
      alert('小红书图文必须包含封面图片')
      return
    }
    
    if (!confirm(`确定要将版本 ${version} 发布到小红书吗？`)) {
      return
    }
    
    setIsPublishing(true)
    try {
      const result = await publishContent(content)
      if (result.success) {
        alert(`🎉 发布成功！\n\n笔记已发布到小红书`)
      } else {
        alert(`❌ 发布失败\n\n${result.message || '未知错误'}\n\n请检查：\n1. 是否已登录小红书\n2. 内容是否符合规范\n3. 网络连接是否正常`)
      }
    } catch (error: any) {
      alert(`❌ 发布失败\n\n${error.message || '请稍后重试'}`)
    } finally {
      setIsPublishing(false)
    }
  }

  const ContentForm = ({
    content,
    onChange,
    label,
    color,
  }: {
    content: ContentItem
    onChange: (content: ContentItem) => void
    label: string
    color: string
  }) => (
    <div className="space-y-4">
      {/* 标题输入 */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-medium text-gray-700">标题</label>
          <span className="text-xs text-gray-400">{content.title.length}/20</span>
        </div>
        <input
          type="text"
          value={content.title}
          onChange={(e) => onChange({ ...content, title: e.target.value.slice(0, 20) })}
          placeholder="输入标题（不超过20字）"
          maxLength={20}
          className="w-full border border-gray-200 rounded-lg px-4 py-2.5 text-sm"
        />
      </div>

      {/* 封面图片 */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-medium text-gray-700 flex items-center gap-1.5">
            <Image className="w-4 h-4" />
            封面图片
          </label>
          <div className="flex gap-1">
            <button
              type="button"
              onClick={() => handleSearchImages(label === '版本 A' ? 'A' : 'B')}
              disabled={isSearchingImages}
              className="text-xs px-2 py-1 rounded bg-purple-50 text-purple-600 hover:bg-purple-100 flex items-center gap-1"
            >
              <Sparkles className="w-3 h-3" />
              智能配图
            </button>
          </div>
        </div>
        
        {/* 图片预览或上传区 */}
        {content.cover_image ? (
          <div className="relative rounded-lg overflow-hidden border border-gray-200">
            <img 
              src={content.cover_image} 
              alt="封面预览" 
              className="w-full h-40 object-cover"
            />
            <button
              type="button"
              onClick={() => onChange({ ...content, cover_image: undefined })}
              className="absolute top-2 right-2 p-1.5 bg-black/50 rounded-full text-white hover:bg-black/70"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {/* 上传区域 */}
            <label className="border-2 border-dashed border-gray-200 rounded-lg p-6 text-center hover:border-gray-300 transition-colors cursor-pointer block">
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (file) handleFileUpload(file, onChange, content)
                }}
              />
              <Upload className="w-6 h-6 mx-auto text-gray-400 mb-2" />
              <p className="text-sm text-gray-500">点击上传图片</p>
              <p className="text-xs text-gray-400 mt-1">支持 JPG、PNG、WebP</p>
            </label>
            
            {/* URL 输入 */}
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <Link className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="url"
                  placeholder="或粘贴图片URL..."
                  className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      const url = (e.target as HTMLInputElement).value.trim()
                      if (url) {
                        onChange({ ...content, cover_image: url });
                        (e.target as HTMLInputElement).value = ''
                      }
                    }
                  }}
                />
              </div>
            </div>
          </div>
        )}
        
        {/* 智能配图建议弹窗 */}
        {showImageInput && (
          <div className="mt-3 p-3 bg-purple-50 rounded-lg border border-purple-100">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-purple-700">
                {isSearchingImages ? '正在从小红书搜索相关图片...' : `推荐配图 (点击使用)`}
              </span>
              <button
                type="button"
                onClick={() => {
                  setShowImageInput(null)
                  setSuggestedImages([])
                }}
                className="text-purple-400 hover:text-purple-600"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            
            {/* 加载状态 */}
            {isSearchingImages && (
              <div className="flex flex-col items-center py-8">
                <div className="relative">
                  <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-purple-600"></div>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-xs text-purple-600">🔍</span>
                  </div>
                </div>
                <p className="text-sm text-purple-600 mt-4 font-medium">正在搜索小红书...</p>
                <p className="text-xs text-purple-400 mt-2">MCP正在爬取小红书页面，可能需要10-30秒</p>
                <p className="text-xs text-gray-400 mt-1">请耐心等待，不要关闭页面</p>
              </div>
            )}
            
            {/* 图片网格 */}
            {!isSearchingImages && suggestedImages.length > 0 && (
              <div className="grid grid-cols-3 gap-2">
                {suggestedImages.map((url, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      onChange({ ...content, cover_image: url })
                      setShowImageInput(null)
                      setSuggestedImages([])
                    }}
                    className="aspect-square rounded-lg overflow-hidden border-2 border-transparent hover:border-purple-400 transition-colors"
                  >
                    <img src={url} alt={`推荐 ${idx + 1}`} className="w-full h-full object-cover" />
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* 正文 */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="text-sm font-medium text-gray-700">正文</label>
          <span className="text-xs text-gray-400">{content.body.length}/1000</span>
        </div>
        <textarea
          value={content.body}
          onChange={(e) => onChange({ ...content, body: e.target.value.slice(0, 1000) })}
          placeholder="输入正文内容（不超过1000字）"
          maxLength={1000}
          className="w-full border border-gray-200 rounded-lg px-4 py-3 text-sm h-48 resize-none"
        />
      </div>

      {/* 标签 */}
      <div>
        <label className="text-sm font-medium text-gray-700 flex items-center gap-1.5 mb-2">
          <Tag className="w-4 h-4" />
          标签
        </label>
        <input
          type="text"
          value={content.tags.join(' ')}
          onChange={(e) =>
            onChange({
              ...content,
              tags: e.target.value
                .split(/[\s,，]+/)
                .filter(Boolean)
                .slice(0, 10),
            })
          }
          placeholder="输入标签，空格分隔"
          className="w-full border border-gray-200 rounded-lg px-4 py-2.5 text-sm"
        />
        {content.tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-2">
            {content.tags.map((tag, idx) => (
              <span
                key={idx}
                className={`px-2.5 py-1 rounded-full text-xs ${
                  color === 'red' ? 'bg-red-100 text-red-600' : 'bg-blue-100 text-blue-600'
                }`}
              >
                #{tag}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )

  return (
    <div className="h-full flex flex-col bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg shadow-gray-200/50 border border-white/50 overflow-hidden">
      {/* 头部标签切换 */}
      <div className="flex-shrink-0 px-5 py-4 border-b border-gray-100/50 bg-gradient-to-r from-gray-50/50 to-blue-50/50">
        <div className="flex items-center justify-between">
          <div className="flex gap-2 p-1 bg-gray-100/80 rounded-xl">
            <button
              onClick={() => setActiveTab('A')}
              className={`px-5 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'A'
                  ? 'bg-white text-red-600 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              版本 A
            </button>
            <button
              onClick={() => setActiveTab('B')}
              className={`px-5 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'B'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              版本 B
            </button>
          </div>
          
          {/* AI 生成按钮 */}
          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-400">AI 生成 B 版本：</span>
            <div className="flex gap-1.5">
              <button
                onClick={() => handleGenerateVariant('alternative')}
                disabled={isGenerating || !taskSpec || !contentA.title}
                className="px-3 py-1.5 text-xs bg-gray-100 hover:bg-gray-200 rounded-lg flex items-center gap-1.5 disabled:opacity-50 transition-all"
              >
                <Wand2 className="w-3 h-3" />
                不同角度
              </button>
              <button
                onClick={() => handleGenerateVariant('hook')}
                disabled={isGenerating || !taskSpec || !contentA.title}
                className="px-3 py-1.5 text-xs bg-gray-100 hover:bg-gray-200 rounded-lg flex items-center gap-1.5 disabled:opacity-50 transition-all"
              >
                <RefreshCw className="w-3 h-3" />
                换个开头
              </button>
              <button
                onClick={() => handleGenerateVariant('actionable')}
                disabled={isGenerating || !taskSpec || !contentA.title}
                className="px-3 py-1.5 text-xs bg-green-50 text-green-600 hover:bg-green-100 rounded-lg flex items-center gap-1.5 disabled:opacity-50 transition-all"
              >
                ✅ 可抄版本
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 内容编辑区 */}
      <div className="flex-1 min-h-0 overflow-y-auto p-4">
        {isGenerating ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <RefreshCw className="w-8 h-8 animate-spin text-xhs-red mx-auto mb-3" />
              <p className="text-sm text-gray-500">AI 正在生成变体版本...</p>
            </div>
          </div>
        ) : activeTab === 'A' ? (
          <ContentForm
            content={contentA}
            onChange={onContentAChange}
            label="版本 A"
            color="red"
          />
        ) : (
          <ContentForm
            content={contentB}
            onChange={onContentBChange}
            label="版本 B"
            color="blue"
          />
        )}
      </div>

      {/* 底部对比预览 */}
      {contentA.title && contentB.title && (
        <div className="flex-shrink-0 px-4 py-3 border-t border-gray-100 bg-gray-50">
          <p className="text-xs text-gray-500 mb-2">标题对比预览</p>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-red-50 rounded-lg p-2 border border-red-100">
              <p className="text-xs font-medium text-red-600 mb-1">A</p>
              <p className="text-sm text-gray-800 line-clamp-1">{contentA.title}</p>
            </div>
            <div className="bg-blue-50 rounded-lg p-2 border border-blue-100">
              <p className="text-xs font-medium text-blue-600 mb-1">B</p>
              <p className="text-sm text-gray-800 line-clamp-1">{contentB.title}</p>
            </div>
          </div>
        </div>
      )}

      {/* 直接发布按钮 */}
      <div className="flex-shrink-0 px-4 py-3 border-t border-gray-100 bg-white">
        <div className="flex items-center justify-between">
          <p className="text-xs text-gray-400">无需测试，直接发布到小红书</p>
          <button
            onClick={() => handlePublish(activeTab === 'A' ? contentA : contentB, activeTab)}
            disabled={isPublishing || !(activeTab === 'A' ? contentA : contentB).title}
            className="px-4 py-2 bg-xhs-red hover:bg-red-600 text-white rounded-lg text-sm font-medium flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isPublishing ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                发布中...
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                发布版本 {activeTab}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
