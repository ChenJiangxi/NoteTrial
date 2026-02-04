import { useState, useEffect, useRef } from 'react'
import {
  Image, FileText, Upload, Trash2, Tag,
  FolderOpen, Plus, X, Loader2, Check
} from 'lucide-react'
import {
  getMaterialStats, addMaterialImage, getMaterialImages, deleteMaterialImage,
  addMaterialText, getMaterialTexts, deleteMaterialText,
  type MaterialImage, type MaterialText
} from '../services/api'

interface MaterialLibraryProps {
  onSelectImage?: (imageData: string) => void
  onSelectText?: (text: string) => void
  mode?: 'manage' | 'select'
}

export default function MaterialLibrary({ 
  onSelectImage, 
  onSelectText,
  mode = 'manage' 
}: MaterialLibraryProps) {
  const [activeTab, setActiveTab] = useState<'images' | 'texts'>('images')
  const [images, setImages] = useState<MaterialImage[]>([])
  const [texts, setTexts] = useState<MaterialText[]>([])
  const [stats, setStats] = useState<{
    total_images: number
    total_texts: number
    tags: string[]
  } | null>(null)
  
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [showAddText, setShowAddText] = useState(false)
  
  // 筛选
  const [filterTags, setFilterTags] = useState<string[]>([])
  const [textType, setTextType] = useState<string>('')
  
  // 新增文案表单
  const [newTextContent, setNewTextContent] = useState('')
  const [newTextType, setNewTextType] = useState('copy')
  const [newTextTags, setNewTextTags] = useState('')
  
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    loadData()
  }, [activeTab, filterTags, textType])

  const loadData = async () => {
    setLoading(true)
    try {
      const statsData = await getMaterialStats()
      setStats(statsData)
      
      if (activeTab === 'images') {
        const result = await getMaterialImages(filterTags.length > 0 ? filterTags : undefined)
        setImages(result.images)
      } else {
        const result = await getMaterialTexts(textType || undefined, filterTags.length > 0 ? filterTags : undefined)
        setTexts(result.texts)
      }
    } catch (e) {
      console.error('加载素材失败', e)
    }
    setLoading(false)
  }

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return
    
    setUploading(true)
    
    for (const file of Array.from(files)) {
      const reader = new FileReader()
      reader.onload = async (event) => {
        const base64 = event.target?.result as string
        try {
          await addMaterialImage(base64, {
            filename: file.name,
            source: 'upload',
            tags: filterTags.length > 0 ? filterTags : undefined
          })
        } catch (e) {
          console.error('上传失败', e)
        }
      }
      reader.readAsDataURL(file)
    }
    
    // 延迟刷新
    setTimeout(() => {
      loadData()
      setUploading(false)
    }, 1000)
    
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleDeleteImage = async (id: string) => {
    if (!confirm('确定删除这张图片？')) return
    await deleteMaterialImage(id)
    loadData()
  }

  const handleDeleteText = async (id: string) => {
    if (!confirm('确定删除这条文案？')) return
    await deleteMaterialText(id)
    loadData()
  }

  const handleAddText = async () => {
    if (!newTextContent.trim()) return
    
    setUploading(true)
    try {
      await addMaterialText(newTextContent, newTextType, {
        tags: newTextTags ? newTextTags.split(',').map(t => t.trim()) : undefined,
        source: 'manual'
      })
      setNewTextContent('')
      setNewTextTags('')
      setShowAddText(false)
      loadData()
    } catch (e) {
      console.error('添加文案失败', e)
    }
    setUploading(false)
  }

  const textTypeLabels: Record<string, string> = {
    copy: '正文',
    title: '标题',
    tag: '标签',
    hook: '金句'
  }

  return (
    <div className="bg-gray-800 rounded-xl p-4">
      {/* 头部 */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <FolderOpen className="w-5 h-5 text-orange-500" />
          <h3 className="font-semibold">素材库</h3>
          {stats && (
            <span className="text-xs text-gray-400">
              {stats.total_images} 张图片 · {stats.total_texts} 条文案
            </span>
          )}
        </div>
      </div>

      {/* Tab 切换 */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setActiveTab('images')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors ${
            activeTab === 'images'
              ? 'bg-orange-500 text-white'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          <Image className="w-4 h-4" />
          图片素材
        </button>
        <button
          onClick={() => setActiveTab('texts')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors ${
            activeTab === 'texts'
              ? 'bg-orange-500 text-white'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          <FileText className="w-4 h-4" />
          文案素材
        </button>
      </div>

      {/* 筛选 */}
      {stats && stats.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-4">
          {stats.tags.slice(0, 10).map(tag => (
            <button
              key={tag}
              onClick={() => {
                if (filterTags.includes(tag)) {
                  setFilterTags(filterTags.filter(t => t !== tag))
                } else {
                  setFilterTags([...filterTags, tag])
                }
              }}
              className={`flex items-center gap-1 px-2 py-0.5 rounded text-xs transition-colors ${
                filterTags.includes(tag)
                  ? 'bg-orange-500/30 text-orange-400 border border-orange-500/50'
                  : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
              }`}
            >
              <Tag className="w-3 h-3" />
              {tag}
            </button>
          ))}
        </div>
      )}

      {/* 图片素材 */}
      {activeTab === 'images' && (
        <div>
          {/* 上传按钮 */}
          {mode === 'manage' && (
            <div className="mb-4">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                multiple
                onChange={handleImageUpload}
                className="hidden"
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm transition-colors disabled:opacity-50"
              >
                {uploading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Upload className="w-4 h-4" />
                )}
                上传图片
              </button>
            </div>
          )}

          {/* 图片列表 */}
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
            </div>
          ) : images.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Image className="w-10 h-10 mx-auto mb-2 opacity-50" />
              <p className="text-sm">暂无图片素材</p>
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-2">
              {images.map(img => (
                <div
                  key={img.id}
                  className="relative group aspect-square rounded-lg overflow-hidden bg-gray-700"
                >
                  <img
                    src={img.path.startsWith('http') ? img.path : `/api/materials/images/${img.id}`}
                    alt={img.filename}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="%23666"><rect width="24" height="24" rx="2"/></svg>'
                    }}
                  />
                  <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                    {mode === 'select' && onSelectImage && (
                      <button
                        onClick={() => onSelectImage(img.path)}
                        className="p-2 bg-orange-500 rounded-full hover:bg-orange-600"
                      >
                        <Check className="w-4 h-4" />
                      </button>
                    )}
                    {mode === 'manage' && (
                      <button
                        onClick={() => handleDeleteImage(img.id)}
                        className="p-2 bg-red-500 rounded-full hover:bg-red-600"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                  {img.tags.length > 0 && (
                    <div className="absolute bottom-0 left-0 right-0 p-1 bg-black/60">
                      <div className="flex flex-wrap gap-0.5">
                        {img.tags.slice(0, 2).map(tag => (
                          <span key={tag} className="text-[10px] text-gray-300 bg-gray-700/80 px-1 rounded">
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 文案素材 */}
      {activeTab === 'texts' && (
        <div>
          {/* 类型筛选和添加按钮 */}
          <div className="flex items-center gap-2 mb-4">
            <select
              value={textType}
              onChange={(e) => setTextType(e.target.value)}
              className="bg-gray-700 text-sm rounded-lg px-3 py-1.5 border-none outline-none"
            >
              <option value="">全部类型</option>
              <option value="copy">正文</option>
              <option value="title">标题</option>
              <option value="hook">金句</option>
              <option value="tag">标签</option>
            </select>
            
            {mode === 'manage' && (
              <button
                onClick={() => setShowAddText(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm transition-colors"
              >
                <Plus className="w-4 h-4" />
                添加文案
              </button>
            )}
          </div>

          {/* 添加文案表单 */}
          {showAddText && (
            <div className="mb-4 p-3 bg-gray-700 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">添加文案素材</span>
                <button onClick={() => setShowAddText(false)}>
                  <X className="w-4 h-4 text-gray-400 hover:text-white" />
                </button>
              </div>
              <textarea
                value={newTextContent}
                onChange={(e) => setNewTextContent(e.target.value)}
                placeholder="输入文案内容..."
                className="w-full bg-gray-600 rounded-lg p-2 text-sm mb-2 min-h-[80px] resize-none"
              />
              <div className="flex items-center gap-2 mb-2">
                <select
                  value={newTextType}
                  onChange={(e) => setNewTextType(e.target.value)}
                  className="bg-gray-600 text-sm rounded-lg px-2 py-1"
                >
                  <option value="copy">正文</option>
                  <option value="title">标题</option>
                  <option value="hook">金句</option>
                  <option value="tag">标签</option>
                </select>
                <input
                  type="text"
                  value={newTextTags}
                  onChange={(e) => setNewTextTags(e.target.value)}
                  placeholder="标签（逗号分隔）"
                  className="flex-1 bg-gray-600 rounded-lg px-2 py-1 text-sm"
                />
              </div>
              <button
                onClick={handleAddText}
                disabled={!newTextContent.trim() || uploading}
                className="w-full py-1.5 bg-orange-500 hover:bg-orange-600 rounded-lg text-sm font-medium disabled:opacity-50"
              >
                {uploading ? '添加中...' : '添加'}
              </button>
            </div>
          )}

          {/* 文案列表 */}
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
            </div>
          ) : texts.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <FileText className="w-10 h-10 mx-auto mb-2 opacity-50" />
              <p className="text-sm">暂无文案素材</p>
            </div>
          ) : (
            <div className="space-y-2 max-h-[400px] overflow-y-auto">
              {texts.map(text => (
                <div
                  key={text.id}
                  className="p-3 bg-gray-700 rounded-lg group"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <span className={`text-xs px-1.5 py-0.5 rounded mr-2 ${
                        text.text_type === 'title' ? 'bg-blue-500/30 text-blue-400' :
                        text.text_type === 'hook' ? 'bg-purple-500/30 text-purple-400' :
                        text.text_type === 'tag' ? 'bg-green-500/30 text-green-400' :
                        'bg-gray-600 text-gray-400'
                      }`}>
                        {textTypeLabels[text.text_type] || text.text_type}
                      </span>
                      <p className="text-sm mt-1.5 line-clamp-3">{text.content}</p>
                      {text.tags.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {text.tags.map(tag => (
                            <span key={tag} className="text-[10px] text-gray-400 bg-gray-600 px-1.5 py-0.5 rounded">
                              #{tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      {mode === 'select' && onSelectText && (
                        <button
                          onClick={() => onSelectText(text.content)}
                          className="p-1.5 bg-orange-500 rounded hover:bg-orange-600"
                        >
                          <Check className="w-3.5 h-3.5" />
                        </button>
                      )}
                      {mode === 'manage' && (
                        <button
                          onClick={() => handleDeleteText(text.id)}
                          className="p-1.5 bg-red-500 rounded hover:bg-red-600"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
