import { useState, useEffect, useRef, useCallback } from 'react'
import {
  Image, FileText, Upload, Trash2, Tag, Search, Video, Download,
  FolderOpen, Plus, X, Loader2, Check, ChevronDown, Sparkles, 
  ExternalLink, Copy, RefreshCw, Wand2
} from 'lucide-react'
import {
  getMaterialStats, addMaterialImage, getMaterialImages, deleteMaterialImage,
  addMaterialText, getMaterialTexts, deleteMaterialText,
  getMaterialVideos, addMaterialVideo, deleteMaterialVideo,
  collectMaterialsFromXhs, recommendMaterials,
  type MaterialImage, type MaterialText, type MaterialVideo, type MaterialRecommendation
} from '../services/api'

interface MaterialLibraryProps {
  onSelectImage?: (imageData: string) => void
  onSelectText?: (text: string) => void
  onSelectVideo?: (videoUrl: string) => void
  mode?: 'manage' | 'select'
  recommendTopic?: string  // 用于智能推荐的话题
}

export default function MaterialLibrary({ 
  onSelectImage, 
  onSelectText,
  onSelectVideo,
  mode = 'manage',
  recommendTopic
}: MaterialLibraryProps) {
  const [activeTab, setActiveTab] = useState<'images' | 'texts' | 'videos' | 'collect'>('images')
  const [images, setImages] = useState<MaterialImage[]>([])
  const [texts, setTexts] = useState<MaterialText[]>([])
  const [videos, setVideos] = useState<MaterialVideo[]>([])
  const [stats, setStats] = useState<{
    total_images: number
    total_texts: number
    total_videos?: number
    tags: string[]
    sources?: Record<string, number>
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
  
  // 视频上传
  const [showAddVideo, setShowAddVideo] = useState(false)
  const [newVideoUrl, setNewVideoUrl] = useState('')
  const [newVideoTags, setNewVideoTags] = useState('')
  
  // 小红书采集
  const [collectNoteId, setCollectNoteId] = useState('')
  const [collectOptions, setCollectOptions] = useState({
    images: true,
    video: true
  })
  const [collecting, setCollecting] = useState(false)
  const [collectResult, setCollectResult] = useState<{
    images: number
    video: boolean
    text: boolean
  } | null>(null)
  
  // 智能推荐
  const [recommendations, setRecommendations] = useState<MaterialRecommendation[]>([])
  const [loadingRecommend, setLoadingRecommend] = useState(false)
  
  // 拖拽上传
  const [isDragging, setIsDragging] = useState(false)
  
  const fileInputRef = useRef<HTMLInputElement>(null)
  const dropZoneRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadData()
  }, [activeTab, filterTags, textType])
  
  // 加载智能推荐
  useEffect(() => {
    if (recommendTopic && activeTab !== 'collect') {
      loadRecommendations(recommendTopic)
    }
  }, [recommendTopic, activeTab])

  const loadData = async () => {
    setLoading(true)
    try {
      const statsData = await getMaterialStats()
      setStats(statsData)
      
      if (activeTab === 'images') {
        const result = await getMaterialImages(filterTags.length > 0 ? filterTags : undefined)
        setImages(result.images)
      } else if (activeTab === 'texts') {
        const result = await getMaterialTexts(textType || undefined, filterTags.length > 0 ? filterTags : undefined)
        setTexts(result.texts)
      } else if (activeTab === 'videos') {
        const result = await getMaterialVideos(filterTags.length > 0 ? filterTags : undefined)
        setVideos(result.videos)
      }
    } catch (e) {
      console.error('加载素材失败', e)
    }
    setLoading(false)
  }
  
  const loadRecommendations = async (topic: string) => {
    setLoadingRecommend(true)
    try {
      const contentType = activeTab === 'texts' ? 'text' : activeTab === 'videos' ? 'video' : 'image'
      const result = await recommendMaterials(topic, contentType as 'image' | 'video' | 'text', 5)
      setRecommendations(result.recommendations)
    } catch (e) {
      console.error('加载推荐失败', e)
    }
    setLoadingRecommend(false)
  }

  // 拖拽处理
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }, [])
  
  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }, [])
  
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }, [])
  
  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
    
    const files = e.dataTransfer.files
    if (files.length > 0) {
      await processFiles(files)
    }
  }, [filterTags])

  const processFiles = async (files: FileList) => {
    setUploading(true)
    
    const imageFiles = Array.from(files).filter(f => f.type.startsWith('image/'))
    
    for (const file of imageFiles) {
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
    
    setTimeout(() => {
      loadData()
      setUploading(false)
    }, 1000)
  }

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return
    await processFiles(files)
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
  
  const handleDeleteVideo = async (id: string) => {
    if (!confirm('确定删除这个视频？')) return
    await deleteMaterialVideo(id)
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
  
  const handleAddVideo = async () => {
    if (!newVideoUrl.trim()) return
    
    setUploading(true)
    try {
      await addMaterialVideo(newVideoUrl, {
        tags: newVideoTags ? newVideoTags.split(',').map(t => t.trim()) : undefined
      })
      setNewVideoUrl('')
      setNewVideoTags('')
      setShowAddVideo(false)
      loadData()
    } catch (e) {
      console.error('添加视频失败', e)
    }
    setUploading(false)
  }
  
  // 从小红书采集素材
  const handleCollectFromXhs = async () => {
    if (!collectNoteId.trim()) return
    
    // 从链接中提取 note_id
    let noteId = collectNoteId.trim()
    const match = noteId.match(/\/([a-f0-9]{24})(?:\?|$)/)
    if (match) {
      noteId = match[1]
    }
    
    setCollecting(true)
    setCollectResult(null)
    
    try {
      const result = await collectMaterialsFromXhs({
        note_id: noteId,
        collect_images: collectOptions.images,
        collect_video: collectOptions.video
      })
      
      if (result.success) {
        setCollectResult(result.collected)
        loadData()
      }
    } catch (e) {
      console.error('采集失败', e)
      alert('采集失败，请检查笔记ID或链接是否正确')
    }
    
    setCollecting(false)
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
              {stats.total_images} 图片 · {stats.total_texts} 文案
              {stats.total_videos !== undefined && ` · ${stats.total_videos} 视频`}
            </span>
          )}
        </div>
        
        {/* 智能推荐提示 */}
        {recommendTopic && (
          <div className="flex items-center gap-1.5 text-xs text-purple-400">
            <Sparkles className="w-3.5 h-3.5" />
            <span>为「{recommendTopic.slice(0, 10)}...」推荐</span>
          </div>
        )}
      </div>

      {/* Tab 切换 */}
      <div className="flex gap-2 mb-4 flex-wrap">
        <button
          onClick={() => setActiveTab('images')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors ${
            activeTab === 'images'
              ? 'bg-orange-500 text-white'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          <Image className="w-4 h-4" />
          图片
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
          文案
        </button>
        <button
          onClick={() => setActiveTab('videos')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors ${
            activeTab === 'videos'
              ? 'bg-orange-500 text-white'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          <Video className="w-4 h-4" />
          视频
        </button>
        {mode === 'manage' && (
          <button
            onClick={() => setActiveTab('collect')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors ${
              activeTab === 'collect'
                ? 'bg-purple-500 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            <Download className="w-4 h-4" />
            采集
          </button>
        )}
      </div>

      {/* 智能推荐区域 */}
      {recommendTopic && activeTab !== 'collect' && recommendations.length > 0 && (
        <div className="mb-4 p-3 bg-purple-900/30 border border-purple-500/30 rounded-lg">
          <div className="flex items-center gap-2 mb-2">
            <Wand2 className="w-4 h-4 text-purple-400" />
            <span className="text-sm font-medium text-purple-300">智能推荐</span>
            <button 
              onClick={() => loadRecommendations(recommendTopic)}
              className="ml-auto text-xs text-purple-400 hover:text-purple-300"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingRecommend ? 'animate-spin' : ''}`} />
            </button>
          </div>
          <div className="flex gap-2 overflow-x-auto pb-2">
            {recommendations.map((rec, idx) => (
              <div 
                key={idx}
                className="flex-shrink-0 w-24 cursor-pointer group"
                onClick={() => {
                  if ('path' in rec.material && onSelectImage) {
                    onSelectImage((rec.material as MaterialImage).path)
                  } else if ('content' in rec.material && onSelectText) {
                    onSelectText((rec.material as MaterialText).content)
                  } else if ('video_url' in rec.material && onSelectVideo) {
                    onSelectVideo((rec.material as MaterialVideo).video_url)
                  }
                }}
              >
                {'path' in rec.material ? (
                  <div className="aspect-square rounded-lg overflow-hidden bg-gray-700">
                    <img 
                      src={`/api/materials/images/${rec.material.id}`}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                    />
                  </div>
                ) : 'content' in rec.material ? (
                  <div className="aspect-square rounded-lg bg-gray-700 p-2 text-[10px] overflow-hidden">
                    {(rec.material as MaterialText).content.slice(0, 60)}...
                  </div>
                ) : (
                  <div className="aspect-square rounded-lg bg-gray-700 flex items-center justify-center">
                    <Video className="w-6 h-6 text-gray-500" />
                  </div>
                )}
                <p className="text-[10px] text-purple-400 mt-1 truncate">{rec.reason}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 筛选 */}
      {stats && stats.tags.length > 0 && activeTab !== 'collect' && (
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
        <div
          ref={dropZoneRef}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          className={`relative ${isDragging ? 'ring-2 ring-orange-500 ring-dashed rounded-lg' : ''}`}
        >
          {/* 拖拽提示 */}
          {isDragging && (
            <div className="absolute inset-0 bg-orange-500/20 rounded-lg flex items-center justify-center z-10">
              <div className="text-center">
                <Upload className="w-10 h-10 text-orange-400 mx-auto mb-2" />
                <p className="text-orange-400 font-medium">松开鼠标上传图片</p>
              </div>
            </div>
          )}
          
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
                上传图片（支持拖拽）
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
              <p className="text-xs text-gray-600 mt-1">点击上传或拖拽图片到此处</p>
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
                  {img.source === 'xhs' && (
                    <div className="absolute top-1 right-1 bg-red-500/80 text-white text-[10px] px-1.5 py-0.5 rounded">
                      小红书
                    </div>
                  )}
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
                      <div className="flex items-center gap-2">
                        <span className={`text-xs px-1.5 py-0.5 rounded ${
                          text.text_type === 'title' ? 'bg-blue-500/30 text-blue-400' :
                          text.text_type === 'hook' ? 'bg-purple-500/30 text-purple-400' :
                          text.text_type === 'tag' ? 'bg-green-500/30 text-green-400' :
                          'bg-gray-600 text-gray-400'
                        }`}>
                          {textTypeLabels[text.text_type] || text.text_type}
                        </span>
                        {text.source === 'xhs' && (
                          <span className="text-[10px] bg-red-500/30 text-red-400 px-1.5 py-0.5 rounded">
                            小红书
                          </span>
                        )}
                      </div>
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
                      <button
                        onClick={() => navigator.clipboard.writeText(text.content)}
                        className="p-1.5 bg-gray-600 rounded hover:bg-gray-500"
                        title="复制文案"
                      >
                        <Copy className="w-3.5 h-3.5" />
                      </button>
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
      
      {/* 视频素材 */}
      {activeTab === 'videos' && (
        <div>
          {/* 添加视频按钮 */}
          {mode === 'manage' && (
            <div className="mb-4">
              <button
                onClick={() => setShowAddVideo(true)}
                className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm transition-colors"
              >
                <Plus className="w-4 h-4" />
                添加视频
              </button>
            </div>
          )}
          
          {/* 添加视频表单 */}
          {showAddVideo && (
            <div className="mb-4 p-3 bg-gray-700 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">添加视频素材</span>
                <button onClick={() => setShowAddVideo(false)}>
                  <X className="w-4 h-4 text-gray-400 hover:text-white" />
                </button>
              </div>
              <input
                type="text"
                value={newVideoUrl}
                onChange={(e) => setNewVideoUrl(e.target.value)}
                placeholder="视频URL..."
                className="w-full bg-gray-600 rounded-lg p-2 text-sm mb-2"
              />
              <input
                type="text"
                value={newVideoTags}
                onChange={(e) => setNewVideoTags(e.target.value)}
                placeholder="标签（逗号分隔）"
                className="w-full bg-gray-600 rounded-lg p-2 text-sm mb-2"
              />
              <button
                onClick={handleAddVideo}
                disabled={!newVideoUrl.trim() || uploading}
                className="w-full py-1.5 bg-orange-500 hover:bg-orange-600 rounded-lg text-sm font-medium disabled:opacity-50"
              >
                {uploading ? '添加中...' : '添加'}
              </button>
            </div>
          )}
          
          {/* 视频列表 */}
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
            </div>
          ) : videos.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Video className="w-10 h-10 mx-auto mb-2 opacity-50" />
              <p className="text-sm">暂无视频素材</p>
              <p className="text-xs text-gray-600 mt-1">可从小红书笔记采集视频</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              {videos.map(video => (
                <div
                  key={video.id}
                  className="relative group rounded-lg overflow-hidden bg-gray-700"
                >
                  {video.thumbnail ? (
                    <img
                      src={video.thumbnail}
                      className="w-full aspect-video object-cover"
                    />
                  ) : (
                    <div className="w-full aspect-video flex items-center justify-center bg-gray-600">
                      <Video className="w-8 h-8 text-gray-500" />
                    </div>
                  )}
                  <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                    {mode === 'select' && onSelectVideo && (
                      <button
                        onClick={() => onSelectVideo(video.video_url)}
                        className="p-2 bg-orange-500 rounded-full hover:bg-orange-600"
                      >
                        <Check className="w-4 h-4" />
                      </button>
                    )}
                    <a
                      href={video.video_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-2 bg-blue-500 rounded-full hover:bg-blue-600"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                    {mode === 'manage' && (
                      <button
                        onClick={() => handleDeleteVideo(video.id)}
                        className="p-2 bg-red-500 rounded-full hover:bg-red-600"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                  {video.source === 'xhs' && (
                    <div className="absolute top-1 right-1 bg-red-500/80 text-white text-[10px] px-1.5 py-0.5 rounded">
                      小红书
                    </div>
                  )}
                  <div className="p-2">
                    <p className="text-xs text-gray-400 truncate">{video.filename || '视频素材'}</p>
                    {video.duration > 0 && (
                      <span className="text-[10px] text-gray-500">{Math.floor(video.duration / 60)}:{String(video.duration % 60).padStart(2, '0')}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      
      {/* 小红书采集 */}
      {activeTab === 'collect' && (
        <div className="space-y-4">
          <div className="p-4 bg-gradient-to-r from-red-900/30 to-pink-900/30 border border-red-500/30 rounded-lg">
            <h4 className="font-medium text-red-300 mb-3 flex items-center gap-2">
              <Download className="w-4 h-4" />
              从小红书笔记采集素材
            </h4>
            
            <input
              type="text"
              value={collectNoteId}
              onChange={(e) => setCollectNoteId(e.target.value)}
              placeholder="输入笔记链接或 note_id..."
              className="w-full bg-gray-700 rounded-lg p-3 text-sm mb-3"
            />
            
            <div className="flex items-center gap-4 mb-3">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={collectOptions.images}
                  onChange={(e) => setCollectOptions({ ...collectOptions, images: e.target.checked })}
                  className="rounded bg-gray-700 border-gray-600 text-orange-500 focus:ring-orange-500"
                />
                采集图片
              </label>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={collectOptions.video}
                  onChange={(e) => setCollectOptions({ ...collectOptions, video: e.target.checked })}
                  className="rounded bg-gray-700 border-gray-600 text-orange-500 focus:ring-orange-500"
                />
                采集视频
              </label>
            </div>
            
            <button
              onClick={handleCollectFromXhs}
              disabled={!collectNoteId.trim() || collecting}
              className="w-full py-2 bg-red-500 hover:bg-red-600 rounded-lg text-sm font-medium disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {collecting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  采集中...
                </>
              ) : (
                <>
                  <Download className="w-4 h-4" />
                  开始采集
                </>
              )}
            </button>
            
            {collectResult && (
              <div className="mt-3 p-2 bg-green-900/30 border border-green-500/30 rounded-lg text-sm text-green-300">
                ✓ 采集完成：{collectResult.images} 张图片
                {collectResult.video && '、1 个视频'}
                {collectResult.text && '、1 条文案'}
              </div>
            )}
          </div>
          
          <div className="text-xs text-gray-500">
            <p>使用说明：</p>
            <ul className="list-disc list-inside mt-1 space-y-1">
              <li>支持直接粘贴小红书笔记链接或 note_id</li>
              <li>采集的素材会自动标记来源</li>
              <li>图片和视频会下载到本地素材库</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}
