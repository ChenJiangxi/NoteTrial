import { useEffect, useState, useRef, useCallback } from 'react'
import { 
  Zap, Send, Loader2, Sparkles, Play, Image as ImageIcon, Wand2,
  Paperclip, X, FileText, Upload, Plus,
  Layout, Smartphone, ChevronRight, BarChart3, GripVertical, Home,
  ChevronLeft, ListPlus
} from 'lucide-react'
import { useApp } from './contexts/AppContext'
import { healthCheck, sendChatMessage, generateVariant, startCrowdTest, getCrowdTestProgress, publishContent, generateImage, generateOutline } from './services/api'
import type { ContentItem, MultiCrowdTestResult, PageImage } from './types/api'
import WelcomePage from './components/WelcomePage'
import AutoModePage from './components/AutoModePage'
import CrowdTestResultPanel from './components/CrowdTestResultPanel'

// 应用模式类型
type AppMode = 'welcome' | 'interactive' | 'auto'
type VersionCard = {
  id: string
  label: string
  content: ContentItem
  colorTheme: 'blue' | 'red'
  locked?: boolean
}

// 分隔条组件
function Resizer({ onDrag, side }: { onDrag: (delta: number) => void; side: 'left' | 'right' }) {
  const [isDragging, setIsDragging] = useState(false)
  const startX = useRef(0)
  
  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault()
    setIsDragging(true)
    startX.current = e.clientX
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
  }
  
  useEffect(() => {
    if (!isDragging) return
    
    const handleMouseMove = (e: MouseEvent) => {
      const delta = e.clientX - startX.current
      startX.current = e.clientX
      // 左侧分隔条向右拖动增加宽度，右侧分隔条向左拖动增加宽度
      onDrag(side === 'left' ? delta : -delta)
    }
    
    const handleMouseUp = () => {
      setIsDragging(false)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
    
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
    
    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isDragging, onDrag, side])
  
  return (
    <div
      onMouseDown={handleMouseDown}
      className={`w-1 hover:w-1.5 bg-transparent hover:bg-[#ff2442] cursor-col-resize flex-shrink-0 transition-all group relative ${
        isDragging ? 'bg-[#ff2442] w-1.5' : ''
      }`}
    >
      <div className={`absolute top-1/2 -translate-y-1/2 ${side === 'left' ? '-right-2' : '-left-2'} opacity-0 group-hover:opacity-100 transition-opacity`}>
        <GripVertical className="w-4 h-4 text-slate-400" />
      </div>
    </div>
  )
}

function App() {
  const {
    taskSpec, contentA, contentB, messages,
    setTaskSpec, setContentA, setContentB, addMessage, setMessages,
  } = useApp()
  
  // 应用模式状态
  const [appMode, setAppMode] = useState<AppMode>('welcome')
  
  const [isConnected, setIsConnected] = useState(false)
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showTestPanel, setShowTestPanel] = useState(false)
  const [extraVersions, setExtraVersions] = useState<VersionCard[]>([])
  const [generatingVersionId, setGeneratingVersionId] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<MultiCrowdTestResult | null>(null)
  const [isRunningTest, setIsRunningTest] = useState(false)
  const [simulationProgress, setSimulationProgress] = useState(0)
  const [isPublishing, setIsPublishing] = useState(false)
  const audiencePresets = ['核心用户', '泛兴趣用户', '实用派', '互动派', '传播派']
  const [selectedAudienceTags, setSelectedAudienceTags] = useState<string[]>(audiencePresets)
  const [selectedTestVersions, setSelectedTestVersions] = useState<string[]>(['Version A', 'Version B'])
  const [customAudienceInput, setCustomAudienceInput] = useState('')
  const [customAudienceTags, setCustomAudienceTags] = useState<string[]>([])
  const [uploadedFile, setUploadedFile] = useState<{ name: string; content: string; type?: string } | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  // 三栏宽度状态
  const [leftWidth, setLeftWidth] = useState(384) // 默认 384px (w-96)
  const [rightWidth, setRightWidth] = useState(384)
  const MIN_WIDTH = 280
  const MAX_WIDTH = 600
  
  // 拖拽处理
  const handleLeftResize = useCallback((delta: number) => {
    setLeftWidth(w => Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, w + delta)))
  }, [])
  
  const handleRightResize = useCallback((delta: number) => {
    setRightWidth(w => Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, w + delta)))
  }, [])

  const allVersions: VersionCard[] = [
    { id: 'A', label: 'Version A', content: contentA, colorTheme: 'blue', locked: true },
    { id: 'B', label: 'Version B', content: contentB, colorTheme: 'red', locked: true },
    ...extraVersions,
  ]

  // 检查服务连接
  useEffect(() => {
    const check = async () => {
      try {
        const health = await healthCheck()
        setIsConnected(health.status === 'healthy')
      } catch {
        setIsConnected(false)
      }
    }
    check()
    const interval = setInterval(check, 30000)
    return () => clearInterval(interval)
  }, [])

  // 自动滚动到最新消息
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    setSelectedTestVersions(prev => {
      const labels = allVersions.map(version => version.label)
      const next = prev.filter(label => labels.includes(label))
      return next.length > 0 ? next : labels.slice(0, 2)
    })
  }, [contentA, contentB, extraVersions])

  // 发送消息
  const handleSend = async () => {
    if ((!input.trim() && !uploadedFile) || isLoading) return
    
    // 构建消息内容
    let messageContent = input.trim()
    if (uploadedFile) {
      // 图片文件使用特殊格式，方便解析和显示
      if (uploadedFile.type?.startsWith('image/')) {
        messageContent = `[图片文件: ${uploadedFile.name}]\n${uploadedFile.content}\n\n${messageContent}`
      } else {
        messageContent = `[上传文件: ${uploadedFile.name}]\n\n${uploadedFile.content}\n\n${messageContent}`
      }
    }
    
    const userMessage = { role: 'user' as const, content: messageContent }
    addMessage(userMessage)
    setInput('')
    setUploadedFile(null)
    setIsLoading(true)

    try {
      const response = await sendChatMessage({ messages: [...messages, userMessage] })
      addMessage({ role: 'assistant', content: response.message })
      
      if (response.task_spec) setTaskSpec(response.task_spec)
      if (response.generated_content) {
        // 根据 action 决定如何更新内容
        const action = response.action || 'all'
        
        if (action === 'text_only') {
          // 只改文案，保留原来的图片
          setContentA({
            ...response.generated_content,
            cover_image: contentA.cover_image  // 保留原图
          })
          addMessage({ role: 'assistant', content: '✨ 文案已更新，图片保持不变~' })
        } else if (action === 'image_only') {
          // 只换图片，文案不变
          const topic = response.task_spec?.topic || contentA.title
          if (topic) {
            try {
              addMessage({ role: 'assistant', content: '🎨 正在为你生成新的封面图...' })
              const imagePrompt = `${topic}，${contentA.title}，${(contentA.body || '').slice(0, 80)}`
              const imageUrl = await generateImage(imagePrompt, '小红书风格')
              setContentA({ ...contentA, cover_image: imageUrl })
              addMessage({ role: 'assistant', content: '✨ 封面图已更新，文案保持不变~' })
            } catch (error) {
              console.error('AI配图生成失败:', error)
              addMessage({ role: 'assistant', content: '⚠️ 图片生成失败，你可以手动上传封面图。' })
            }
          }
        } else {
          // action === 'all'，全部重新生成
          setContentA(response.generated_content)
          
          // 自动生成配图
          if (!response.generated_content.cover_image) {
            const topic = response.task_spec?.topic || response.generated_content.title
            if (topic) {
              try {
                console.log('正在使用 AI 为内容生成封面图...')
                addMessage({ role: 'assistant', content: '🎨 正在为你生成专属封面图...' })
                const imagePrompt = `${topic}，${response.generated_content.title}，${(response.generated_content.body || '').slice(0, 80)}`
                const imageUrl = await generateImage(imagePrompt, '小红书风格')
                console.log('AI配图生成成功')
                setContentA({ ...response.generated_content, cover_image: imageUrl })
                addMessage({ role: 'assistant', content: '✨ 已为你生成专属封面图，你也可以更换其他图片。' })
              } catch (error) {
                console.error('AI配图生成失败:', error)
                addMessage({ role: 'assistant', content: '⚠️ 图片生成失败，你可以手动上传封面图。' })
              }
            }
          }
        }
      } else if (response.action === 'image_only' && contentA.title) {
        // 没有返回 generated_content 但意图是换图
        const topic = response.task_spec?.topic || contentA.title
        try {
          addMessage({ role: 'assistant', content: '🎨 正在为你生成新的封面图...' })
          const imagePrompt = `${topic}，${contentA.title}，${(contentA.body || '').slice(0, 80)}`
          const imageUrl = await generateImage(imagePrompt, '小红书风格')
          setContentA({ ...contentA, cover_image: imageUrl })
          addMessage({ role: 'assistant', content: '✨ 封面图已更新~' })
        } catch (error) {
          console.error('AI配图生成失败:', error)
          addMessage({ role: 'assistant', content: '⚠️ 图片生成失败，你可以手动上传封面图。' })
        }
      }
    } catch {
      addMessage({ role: 'assistant', content: '抱歉，服务暂时不可用，请稍后重试。' })
    } finally {
      setIsLoading(false)
    }
  }

  // 处理文件上传 (Chat) - 支持更多文件格式
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    
    // 支持的文件格式
    const textTypes = ['.txt', '.md', '.json', '.csv', '.xml', '.html', '.css', '.js', '.ts']
    const docTypes = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
    const imageTypes = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.heic', '.heif', '.bmp', '.tiff', '.tif']
    const ext = file.name.toLowerCase().slice(file.name.lastIndexOf('.'))
    
    // 优先通过 MIME 类型判断，这样可以支持更多格式
    const isTextFile = file.type.startsWith('text/') || textTypes.includes(ext)
    const isDocFile = docTypes.includes(ext) || file.type.includes('pdf') || file.type.includes('document') || file.type.includes('sheet') || file.type.includes('presentation')
    const isImageFile = file.type.startsWith('image/') || imageTypes.includes(ext)
    
    if (!isTextFile && !isDocFile && !isImageFile) {
      alert('支持的文件格式：\n• 文本：txt, md, json, csv\n• 文档：pdf, doc, docx, xls, xlsx, ppt, pptx\n• 图片：jpg, png, gif, webp, heic 等所有图片格式')
      return
    }
    
    // 图片类文件限制 10MB，文档类文件限制 5MB，文本类限制 500KB
    const maxSize = isImageFile ? 10 * 1024 * 1024 : isDocFile ? 5 * 1024 * 1024 : 500 * 1024
    if (file.size > maxSize) {
      alert(`文件大小不能超过 ${isImageFile ? '10MB' : isDocFile ? '5MB' : '500KB'}`)
      return
    }
    
    if (isDocFile) {
      // 对于 PDF/Office 文件，只记录文件名（后端需要处理解析）
      setUploadedFile({ 
        name: file.name, 
        content: `[文档文件: ${file.name}]\n\n注意：这是一个 ${ext.toUpperCase()} 文件。请在对话中描述文件的主要内容，或者将关键信息复制粘贴到这里。`,
        type: file.type
      })
    } else if (isImageFile) {
      // 图片文件读取为 DataURL
      const reader = new FileReader()
      reader.onload = (event) => {
        const content = event.target?.result as string
        setUploadedFile({ name: file.name, content, type: file.type })
      }
      reader.readAsDataURL(file)
    } else {
      // 文本文件直接读取内容
      const reader = new FileReader()
      reader.onload = (event) => {
        const content = event.target?.result as string
        setUploadedFile({ name: file.name, content, type: file.type })
      }
      reader.readAsText(file)
    }
    e.target.value = ''
  }

  // 运行测试
  const handleRunTest = async () => {
    if (!taskSpec) return
    const versionsForTest = allVersions.filter(version => selectedTestVersions.includes(version.label))
    const validVersions = versionsForTest.filter(version => version.content.title && version.content.body)
    if (validVersions.length < 2) {
      alert('请至少选择两个已填写标题和正文的版本进行测试')
      return
    }
    setIsRunningTest(true)
    setSimulationProgress(0)
    setTestResult(null)
    try {
      const audienceOverrides = [
        ...selectedAudienceTags,
        ...customAudienceTags,
      ]
      const taskSpecForTest = audienceOverrides.length
        ? { ...taskSpec, audience: audienceOverrides.join(' / ') }
        : taskSpec

      const payload = {
        task_spec: taskSpecForTest,
        versions: validVersions.map(version => ({
          label: version.label,
          content: version.content,
        })),
        max_users: 20,
        audience_tags: audienceOverrides,
      }

      const started = await startCrowdTest(payload)
      const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

      while (true) {
        await sleep(400)
        const progress = await getCrowdTestProgress(started.job_id)
        setSimulationProgress(progress.progress ?? 0)

        if (progress.status === 'completed' && progress.result) {
          setSimulationProgress(100)
          setTestResult(progress.result)
          break
        }

        if (progress.status === 'failed') {
          throw new Error(progress.error || '模拟测试失败')
        }
      }
    } catch (error) {
      console.error('测试失败:', error)
    } finally {
      setIsRunningTest(false)
    }
  }

  const toggleAudienceTag = (tag: string) => {
    setSelectedAudienceTags(prev => (
      prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]
    ))
  }

  const addCustomAudienceTag = () => {
    const tag = customAudienceInput.trim()
    if (!tag) return
    setCustomAudienceTags(prev => (prev.includes(tag) ? prev : [...prev, tag]))
    setCustomAudienceInput('')
  }

  const removeCustomAudienceTag = (tag: string) => {
    setCustomAudienceTags(prev => prev.filter(t => t !== tag))
  }

  const getNextVersionLabel = () => `Version ${String.fromCharCode(65 + allVersions.length)}`

  const handleAddEmptyVersion = () => {
    const label = getNextVersionLabel()
    const newVersion: VersionCard = {
      id: `extra-${Date.now()}`,
      label,
      content: { title: '', body: '', tags: [] },
      colorTheme: allVersions.length % 2 === 0 ? 'blue' : 'red',
    }
    setExtraVersions(prev => [...prev, newVersion])
    setSelectedTestVersions(prev => [...prev, label])
  }

  const handleGenerateExtraVersion = async () => {
    if (!taskSpec || !contentA.title) {
      alert('请先准备好 Version A 内容')
      return
    }

    const label = getNextVersionLabel()
    setGeneratingVersionId(label)
    try {
      const variant = await generateVariant({
        task_spec: taskSpec,
        base_content: contentA,
        variant_type: 'alternative',
      })
      const newVersion: VersionCard = {
        id: `extra-${Date.now()}`,
        label,
        content: variant,
        colorTheme: allVersions.length % 2 === 0 ? 'blue' : 'red',
      }
      setExtraVersions(prev => [...prev, newVersion])
      setSelectedTestVersions(prev => [...prev, label])
    } catch (error) {
      console.error('生成额外版本失败:', error)
    } finally {
      setGeneratingVersionId(null)
    }
  }

  const updateExtraVersion = (id: string, content: ContentItem) => {
    setExtraVersions(prev => prev.map(version => (
      version.id === id ? { ...version, content } : version
    )))
  }

  const removeExtraVersion = (id: string) => {
    const target = extraVersions.find(version => version.id === id)
    setExtraVersions(prev => prev.filter(version => version.id !== id))
    if (target) {
      setSelectedTestVersions(prev => prev.filter(label => label !== target.label))
    }
  }

  const toggleTestVersion = (label: string) => {
    setSelectedTestVersions(prev => (
      prev.includes(label) ? prev.filter(item => item !== label) : [...prev, label]
    ))
  }

  // 发布
  const handlePublishVersion = async (label: string, content: ContentItem) => {
    if (!content.title || !content.body) {
      alert('请先填写标题和正文')
      return
    }
    if (!content.cover_image) {
      alert('请先添加封面图片')
      return
    }
    if (!confirm(`确定要发布 ${label} 吗？`)) return
    
    setIsPublishing(true)
    try {
      const result = await publishContent(content)
      if (result.success) {
        alert('🎉 发布成功！')
      } else {
        alert(`发布失败: ${result.message}`)
      }
    } catch (error: any) {
      alert(`发布失败: ${error.message}`)
    } finally {
      setIsPublishing(false)
    }
  }

  const handleReset = () => {
    setMessages([{ role: 'assistant', content: '👋 你好！我是 NoteTrial 助手。\n\n告诉我想测试什么内容，例如：\n• 程序员副业指南\n• 美食探店文案\n• 护肤品种草\n\n你可以上传产品资料，我会帮你生成更准确的内容。' }])
    setContentA({ title: '', body: '', tags: [] })
    setContentB({ title: '', body: '', tags: [] })
    setExtraVersions([])
    setSelectedTestVersions(['Version A', 'Version B'])
    setTaskSpec(null)
    setTestResult(null)
    setShowTestPanel(false)
  }

  // 处理模式选择
  const handleModeSelect = (mode: 'interactive' | 'auto') => {
    setAppMode(mode)
  }

  // 返回欢迎页
  const handleBackToWelcome = () => {
    setAppMode('welcome')
    handleReset()
  }

  // 根据模式渲染不同页面
  if (appMode === 'welcome') {
    return <WelcomePage onSelectMode={handleModeSelect} />
  }

  if (appMode === 'auto') {
    return <AutoModePage onBack={handleBackToWelcome} />
  }

  // 人机交互模式 - 原有界面
  return (
    <div className="h-screen flex flex-col bg-slate-50 font-sans text-slate-900">
      {/* 顶栏 - 专业风格 */}
      <header className="h-14 bg-white border-b border-slate-200 px-6 flex items-center justify-between flex-shrink-0 shadow-sm z-10 w-full">
        <div className="flex items-center gap-3">
          <button 
            onClick={handleBackToWelcome}
            className="w-8 h-8 bg-slate-100 hover:bg-slate-200 rounded-lg flex items-center justify-center transition-colors"
            title="返回首页"
          >
            <Home className="w-4 h-4 text-slate-600" />
          </button>
          <div className="w-8 h-8 bg-[#ff2442] rounded-lg flex items-center justify-center shadow-md">
            <Zap className="w-5 h-5 text-white fill-current" />
          </div>
          <div>
            <h1 className="font-bold text-slate-800 text-lg leading-tight tracking-tight">NoteTrial</h1>
            <p className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">人机交互模式</p>
          </div>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1 bg-slate-100 rounded-full border border-slate-200">
            <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-500' : 'bg-red-500'} animate-pulse`} />
            <span className="text-xs font-medium text-slate-600">
              {isConnected ? '系统正常' : '连接中断'}
            </span>
          </div>
          <button
            onClick={() => setShowTestPanel(v => !v)}
            className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
          >
            <BarChart3 className="w-3.5 h-3.5" />
            {showTestPanel ? '收起模拟测试' : '展开模拟测试'}
          </button>
          <button onClick={handleReset} className="text-xs font-medium text-slate-500 hover:text-[#ff2442] transition-colors">
            新建项目
          </button>
        </div>
      </header>

      {/* 主内容 - 三栏布局 (Chat | Editor | Test) */}
      <main className="flex-1 flex min-h-0 overflow-hidden">
        
        {/* 左栏：AI 助手 (Chat) - 可拖拽 */}
        <div 
          className="border-r border-slate-200 bg-white flex flex-col" 
          style={{ width: leftWidth, flexShrink: 0, flexGrow: 0 }}
        >
          <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-2 bg-slate-50/50">
            <Sparkles className="w-4 h-4 text-[#ff2442]" />
            <span className="font-semibold text-slate-700 text-sm">AI 助手</span>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50/30 scrollbar-thin scrollbar-thumb-slate-200">
            {messages.map((msg, idx) => {
              // 解析消息，检查是否包含文件附件 - 使用更宽松的匹配
              const fileMatch = msg.content.match(/^\[上传文件: (.+?)\]\n\n/)
              const imageMatch = msg.content.match(/^\[图片文件: (.+?)\]\n(data:image\/[^;]+;base64,[^\n]+)/)
              const hasFile = msg.role === 'user' && fileMatch
              const hasImage = msg.role === 'user' && imageMatch
              const fileName = hasFile ? fileMatch[1] : null
              const imageName = hasImage ? imageMatch[1] : null
              const imageData = hasImage ? imageMatch[2] : null
              // 提取用户实际输入的文字（文件内容之后的部分）
              let userText = msg.content
              if (hasFile || hasImage) {
                // 找到文件内容后的用户文字（最后一个\n\n之后的内容）
                const parts = msg.content.split('\n\n')
                userText = parts.length > 2 ? parts[parts.length - 1] : ''
              }
              
              return (
                <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className="max-w-[90%] space-y-2">
                    {/* 图片附件 - 独立显示 */}
                    {hasImage && imageName && imageData && (
                      <div className="flex justify-end">
                        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                          <img src={imageData} alt={imageName} className="max-w-[300px] max-h-[300px] object-contain" />
                          <div className="px-3 py-2 border-t border-slate-100">
                            <span className="text-xs text-slate-500">{imageName}</span>
                          </div>
                        </div>
                      </div>
                    )}
                    {/* 文件附件卡片 - 独立显示在消息上方 */}
                    {hasFile && fileName && !hasImage && (
                      <div className="flex justify-end">
                        <div className="flex items-center gap-3 px-4 py-3 bg-white rounded-xl border border-slate-200 shadow-sm">
                          <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center">
                            <FileText className="w-5 h-5 text-blue-500" />
                          </div>
                          <div className="flex flex-col">
                            <span className="text-sm font-medium text-slate-700">{fileName}</span>
                            <span className="text-xs text-slate-400">已上传</span>
                          </div>
                        </div>
                      </div>
                    )}
                    {/* 消息内容 */}
                    {userText.trim() && (
                      <div 
                        className={`rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
                          msg.role === 'user'
                            ? 'rounded-br-none'
                            : 'bg-white text-slate-600 rounded-bl-none border border-slate-200'
                        }`}
                        style={msg.role === 'user' ? { backgroundColor: '#e2e8f0', color: '#334155' } : {}}
                      >
                        <p className="whitespace-pre-wrap break-words">{userText}</p>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-white rounded-2xl px-4 py-3 border border-slate-200 shadow-sm">
                  <Loader2 className="w-4 h-4 animate-spin text-slate-400" />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
          
          <div className="p-4 border-t border-slate-200 bg-white">
            {uploadedFile && (
              <div className="mb-3 flex items-center gap-3 px-4 py-3 bg-gradient-to-r from-blue-50 to-white border border-blue-200 rounded-xl shadow-sm">
                {uploadedFile.type?.startsWith('image/') ? (
                  <div className="w-16 h-16 rounded-lg overflow-hidden flex-shrink-0 border border-blue-200">
                    <img src={uploadedFile.content} alt={uploadedFile.name} className="w-full h-full object-cover" />
                  </div>
                ) : (
                  <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center flex-shrink-0">
                    <FileText className="w-5 h-5 text-blue-500" />
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <span className="block text-sm font-medium text-slate-700 truncate">{uploadedFile.name}</span>
                  <span className="text-xs text-blue-500">
                    {uploadedFile.type?.startsWith('image/') 
                      ? '📷 AI 将识别图片内容，可在下方输入文字一起发送' 
                      : '📎 可在下方输入文字一起发送'}
                  </span>
                </div>
                <button onClick={() => setUploadedFile(null)} className="text-slate-400 hover:text-slate-700 p-1">
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}
            
            <div className="flex gap-2 items-end">
              <input ref={fileInputRef} type="file" accept="image/*,text/*,.txt,.md,.json,.csv,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx" onChange={handleFileUpload} className="hidden" />
              <button 
                onClick={() => fileInputRef.current?.click()}
                className="mb-1 p-2 text-slate-400 hover:text-[#ff2442] hover:bg-slate-100 rounded-xl transition-all border border-transparent hover:border-slate-200"
                title="上传资料"
              >
                <Paperclip className="w-5 h-5" />
              </button>
              
              <div className="flex-1 relative">
                <textarea
                  value={input}
                  onChange={(e) => {
                    setInput(e.target.value)
                    // 自动调整高度
                    e.target.style.height = 'auto'
                    e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px'
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      handleSend()
                    }
                  }}
                  placeholder="输入消息，回车发送，Shift+回车换行..."
                  rows={1}
                  className="w-full pl-4 pr-12 py-3 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-red-100 focus:border-[#ff2442] focus:bg-white transition-all resize-none overflow-y-auto leading-relaxed"
                  style={{ maxHeight: '150px' }}
                />
                {/* 发送按钮：绝对定位 + 底部对齐 */}
                <button
                  onClick={handleSend}
                  disabled={(!input.trim() && !uploadedFile) || isLoading}
                  className="absolute right-2 bottom-2 p-1.5 text-slate-400 hover:text-[#ff2442] hover:bg-red-50 rounded-lg transition-all disabled:opacity-30 flex items-center justify-center"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
        
        {/* 左侧分隔条 */}
        <Resizer onDrag={handleLeftResize} side="left" />

        {/* 中栏：Split Editor (A/B) - 专业编辑器风格 */}
        <div className="flex-1 flex flex-col min-w-0 bg-slate-100/50">
          <div className="h-14 px-6 border-b border-slate-200 bg-white flex items-center justify-between shadow-sm flex-shrink-0">
            <div className="flex items-center gap-2">
              <Layout className="w-4 h-4 text-slate-500" />
              <span className="font-semibold text-slate-700">内容工坊</span>
              {taskSpec && (
                <>
                  <ChevronRight className="w-4 h-4 text-slate-300" />
                  <span className="text-xs px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full border border-slate-200">
                    {taskSpec.topic}
                  </span>
                </>
              )}
            </div>
            
            <div className="flex items-center gap-3">
              <button
                onClick={handleAddEmptyVersion}
                className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                新增版本
              </button>
              <button
                onClick={handleGenerateExtraVersion}
                disabled={!taskSpec || !contentA.title || generatingVersionId !== null}
                className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-white bg-[#ff2442] hover:bg-[#e61f3d] rounded-lg transition-colors disabled:opacity-50"
              >
                {generatingVersionId ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Wand2 className="w-3.5 h-3.5" />}
                基于 A 生成新版本
              </button>
            </div>
          </div>
          
          <div className="flex-1 overflow-hidden p-6">
            <div className="h-full max-w-5xl mx-auto overflow-y-auto space-y-6">
              {allVersions.map(version => (
                <EditorCard
                  key={version.id}
                  label={version.label}
                  content={version.content}
                  onChange={(content) => {
                    if (version.id === 'A') setContentA(content)
                    else if (version.id === 'B') setContentB(content)
                    else updateExtraVersion(version.id, content)
                  }}
                  onPublish={() => handlePublishVersion(version.label, version.content)}
                  isPublishing={isPublishing}
                  colorTheme={version.colorTheme}
                  onRemove={version.locked ? undefined : () => removeExtraVersion(version.id)}
                />
              ))}
            </div>
          </div>
        </div>
        
        {showTestPanel && <Resizer onDrag={handleRightResize} side="right" />}

        {showTestPanel && <div 
          className="border-l border-slate-200 bg-white flex flex-col" 
          style={{ width: rightWidth, flexShrink: 0, flexGrow: 0 }}
        >
           <div className="h-full flex flex-col">
            <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <div className="flex items-center gap-2 text-slate-700">
                <Play className="w-4 h-4 text-[#ff2442]" />
                <span className="font-semibold text-sm">模拟测试</span>
              </div>
              <button
                onClick={() => setShowTestPanel(false)}
                className="p-1 rounded-md hover:bg-slate-200 transition-colors"
                title="收起模拟测试"
              >
                <X className="w-4 h-4 text-slate-500" />
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-5 scrollbar-thin scrollbar-thumb-slate-200">
              <div className="bg-slate-50 rounded-xl p-4 border border-slate-100 mb-6">
                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">操作</h3>
                <div className="mb-4">
                  <p className="text-xs text-slate-500 mb-2">选择要参与测试的版本（至少 2 个）</p>
                  <div className="space-y-2">
                    {allVersions.map(version => {
                      const checked = selectedTestVersions.includes(version.label)
                      const ready = Boolean(version.content.title && version.content.body)
                      return (
                        <button
                          key={version.id}
                          type="button"
                          onClick={() => toggleTestVersion(version.label)}
                          className={`w-full flex items-center justify-between px-3 py-2 rounded-lg border text-xs transition-all ${
                            checked
                              ? 'bg-red-50 border-red-300 text-[#ff2442]'
                              : 'bg-white border-slate-200 text-slate-600'
                          }`}
                        >
                          <span>{version.label}</span>
                          <span className={ready ? 'text-emerald-600' : 'text-amber-500'}>
                            {ready ? '已就绪' : '未完成'}
                          </span>
                        </button>
                      )
                    })}
                  </div>
                </div>
                <div className="mb-3">
                  <p className="text-xs text-slate-500 mb-2">默认测试人群标签（可多选）</p>
                  <div className="flex flex-wrap gap-2">
                    {audiencePresets.map(tag => (
                      <button
                        key={tag}
                        type="button"
                        onClick={() => toggleAudienceTag(tag)}
                        className={`px-2.5 py-1 text-xs rounded-full border transition-all ${
                          selectedAudienceTags.includes(tag)
                            ? 'bg-red-50 border-red-300 text-[#ff2442]'
                            : 'bg-white border-slate-200 text-slate-500 hover:border-slate-300'
                        }`}
                      >
                        {tag}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="mb-3">
                  <p className="text-xs text-slate-500 mb-2">自定义测试人群（可选）</p>
                  <div className="flex gap-2">
                    <input
                      value={customAudienceInput}
                      onChange={(e) => setCustomAudienceInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault()
                          addCustomAudienceTag()
                        }
                      }}
                      placeholder="例如：一线城市25-30岁职业女性"
                      className="flex-1 px-3 py-2 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-red-100 focus:border-[#ff2442]"
                    />
                    <button
                      type="button"
                      onClick={addCustomAudienceTag}
                      className="px-3 py-2 text-xs rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600"
                    >
                      添加
                    </button>
                  </div>
                  {customAudienceTags.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {customAudienceTags.map(tag => (
                        <span
                          key={tag}
                          className="inline-flex items-center gap-1 px-2.5 py-1 text-xs rounded-full bg-white border border-slate-200 text-slate-600"
                        >
                          {tag}
                          <button
                            type="button"
                            onClick={() => removeCustomAudienceTag(tag)}
                            className="text-slate-400 hover:text-slate-600"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <button
                  onClick={handleRunTest}
                  disabled={isRunningTest || selectedTestVersions.length < 2}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-[#ff2442] text-white text-sm font-medium rounded-lg hover:bg-[#e61f3d] shadow-sm shadow-red-200 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isRunningTest ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
                  {isRunningTest ? `模拟测试中 ${simulationProgress}%` : '版本效果评估'}
                </button>
                {isRunningTest && (
                  <div className="mt-2 h-2 w-full bg-red-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#ff2442] transition-all duration-300"
                      style={{ width: `${simulationProgress}%` }}
                    />
                  </div>
                )}
              </div>

              {testResult ? (
                <CrowdTestResultPanel result={testResult} />
              ) : (
                !isRunningTest && (
                  <div className="flex flex-col items-center justify-center text-center py-10 opacity-40">
                    <Smartphone className="w-12 h-12 text-slate-300 mb-3" />
                    <p className="text-sm font-medium text-slate-500">暂无测试数据</p>
                    <p className="text-xs text-slate-400 mt-1">请完善内容并运行测试</p>
                  </div>
                )
              )}
            </div>
          </div>
        </div>}
      </main>
    </div>
  )
}

// ----------------------------------------------------------------------------
// 专业编辑器组件 (EditorCard) - 支持多图系列
// ----------------------------------------------------------------------------

function EditorCard({ 
  label, content, onChange, onPublish, isPublishing, isEmpty, onGenerate, isGenerating, colorTheme, onRemove
}: { 
  label: string
  content: ContentItem
  onChange: (c: ContentItem) => void
  onPublish: () => void
  isPublishing: boolean
  isEmpty?: boolean
  onGenerate?: () => void
  isGenerating?: boolean
  colorTheme: 'blue' | 'red'
  onRemove?: () => void
}) {
  const [activeTab, setActiveTab] = useState<'upload' | 'url' | 'search'>('upload')
  const [showImgMgr, setShowImgMgr] = useState(false)
  const [showImagePreview, setShowImagePreview] = useState(false)
  const [currentPageIndex, setCurrentPageIndex] = useState(0)
  const [isGeneratingPage, setIsGeneratingPage] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  // 使用本地状态管理 pages，并与 content.images 同步
  const defaultPages: PageImage[] = [
    { index: 0, type: 'cover', content: content.title || '封面', image: content.cover_image, status: content.cover_image ? 'done' : 'pending' }
  ]
  const [localPages, setLocalPages] = useState<PageImage[]>(content.images || defaultPages)
  
  // 同步外部 content.images 变化到本地状态
  useEffect(() => {
    if (content.images && content.images.length > 0) {
      setLocalPages(content.images)
    }
  }, [content.images])
  
  const pages = localPages
  const currentPage = pages[currentPageIndex] || pages[0]
  
  const theme = {
    blue: { accent: 'text-blue-500', btn: 'bg-blue-500 hover:bg-blue-600', barColor: 'bg-blue-500' },
    red: { accent: 'text-[#ff2442]', btn: 'bg-[#ff2442] hover:bg-[#e61f3d]', barColor: 'bg-[#ff2442]' }
  }[colorTheme]

  // 同步更新 images 到 content 和本地状态
  const updatePages = (newPages: PageImage[]) => {
    setLocalPages(newPages)  // 立即更新本地状态
    const coverPage = newPages.find(p => p.type === 'cover')
    onChange({ 
      ...content, 
      images: newPages,
      cover_image: coverPage?.image  // 保持向后兼容
    })
  }

  const handleLocalUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => {
      const newPages = [...pages]
      newPages[currentPageIndex] = { ...currentPage, image: ev.target?.result as string, status: 'done' }
      updatePages(newPages)
      setShowImgMgr(false)
    }
    reader.readAsDataURL(file)
  }

  const handleTagKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      const val = e.currentTarget.value.trim()
      if (val && !content.tags.includes(val)) {
        onChange({ ...content, tags: [...content.tags, val] })
        e.currentTarget.value = ''
      }
    }
  }

  // 添加新页面
  const addPage = () => {
    const newIndex = pages.length
    const newPage: PageImage = {
      index: newIndex,
      type: 'content',
      content: `内容页 ${newIndex}`,
      status: 'pending'
    }
    updatePages([...pages, newPage])
    setCurrentPageIndex(newIndex)
  }

  // AI 生成大纲（RedInk 风格）
  const [isGeneratingOutline, setIsGeneratingOutline] = useState(false)
  const generateOutlineFromTitle = async () => {
    if (!content.title) {
      alert('请先输入标题')
      return
    }
    setIsGeneratingOutline(true)
    try {
      const result = await generateOutline(content.title, 6, '小红书风格')
      if (result.success && result.pages) {
        // 转换为 PageImage 格式
        const newPages: PageImage[] = result.pages.map((p, idx) => ({
          index: idx,
          type: p.type as 'cover' | 'content' | 'summary',
          content: p.content,
          status: 'pending' as const
        }))
        updatePages(newPages)
        setCurrentPageIndex(0)
        // 更新标题
        if (result.title && result.title !== content.title) {
          onChange({ ...content, title: result.title, images: newPages })
        }
      }
    } catch (error) {
      console.error('生成大纲失败:', error)
    } finally {
      setIsGeneratingOutline(false)
    }
  }

  // 删除页面
  const removePage = (index: number) => {
    if (pages.length <= 1) return
    const newPages = pages.filter((_, i) => i !== index).map((p, i) => ({ ...p, index: i }))
    updatePages(newPages)
    if (currentPageIndex >= newPages.length) {
      setCurrentPageIndex(newPages.length - 1)
    }
  }

  // 更新当前页面文案
  const updatePageContent = (newContent: string) => {
    const newPages = [...pages]
    newPages[currentPageIndex] = { ...currentPage, content: newContent }
    updatePages(newPages)
  }

  // 生成当前页图片
  const generateCurrentPageImage = async () => {
    setIsGeneratingPage(true)
    try {
      const prompt = currentPage.content || content.title || '小红书风格图片'
      const imageUrl = await generateImage(prompt, '小红书风格')
      const newPages = [...pages]
      newPages[currentPageIndex] = { ...currentPage, image: imageUrl, status: 'done' }
      updatePages(newPages)
    } catch (error) {
      console.error('生成图片失败:', error)
      const newPages = [...pages]
      newPages[currentPageIndex] = { ...currentPage, status: 'error', error: '生成失败' }
      updatePages(newPages)
    } finally {
      setIsGeneratingPage(false)
    }
  }

  // 批量生成所有图片（逐个生成并实时更新）
  const generateAllImages = async () => {
    setIsGeneratingPage(true)
    
    // 使用当前 pages 的副本，并逐步更新
    let currentPages = [...pages]
    
    // 找到封面页索引
    const coverIdx = currentPages.findIndex(p => p.type === 'cover')
    
    // 第一步：先生成封面
    if (coverIdx >= 0 && !currentPages[coverIdx].image) {
      const coverPage = currentPages[coverIdx]
      // 标记封面正在生成
      currentPages[coverIdx] = { ...coverPage, status: 'generating' }
      updatePages([...currentPages])
      
      try {
        const coverPrompt = `${content.title}\n\n${coverPage.content}`
        const coverImage = await generateImage(coverPrompt, '小红书风格')
        if (coverImage) {
          currentPages[coverIdx] = { ...coverPage, image: coverImage, status: 'done' }
          updatePages([...currentPages])
          console.log('✅ 封面生成成功')
        } else {
          currentPages[coverIdx] = { ...coverPage, status: 'error', error: '封面生成失败' }
          updatePages([...currentPages])
        }
      } catch (e) {
        console.error('封面生成失败:', e)
        currentPages[coverIdx] = { ...coverPage, status: 'error', error: '封面生成异常' }
        updatePages([...currentPages])
      }
    }
    
    // 第二步：逐个生成其他页面
    for (let i = 0; i < currentPages.length; i++) {
      if (i === coverIdx) continue  // 跳过已处理的封面
      
      const page = currentPages[i]
      if (page.status === 'done' && page.image) continue  // 跳过已有图片的
      
      // 标记正在生成
      currentPages[i] = { ...page, status: 'generating' }
      updatePages([...currentPages])
      setCurrentPageIndex(i)  // 切换到当前正在生成的页面
      
      try {
        const prompt = page.content || `内容页 ${i + 1}`
        const imageUrl = await generateImage(prompt, '小红书风格')
        
        if (imageUrl) {
          currentPages[i] = { ...page, image: imageUrl, status: 'done' }
          console.log(`✅ 第 ${i + 1} 页生成成功`)
        } else {
          currentPages[i] = { ...page, status: 'error', error: '生成失败' }
        }
        updatePages([...currentPages])
      } catch (e) {
        console.error(`第 ${i + 1} 页生成失败:`, e)
        currentPages[i] = { ...page, status: 'error', error: '生成异常' }
        updatePages([...currentPages])
      }
    }
    
    setIsGeneratingPage(false)
    const successCount = currentPages.filter(p => p.status === 'done').length
    console.log(`批量生成完成: ${successCount}/${currentPages.length} 成功`)
  }

  if (isEmpty && onGenerate) {
    return (
      <div className="h-full rounded-2xl border-2 border-dashed border-slate-200 bg-slate-50 flex flex-col items-center justify-center gap-4">
        <Wand2 className={`w-8 h-8 ${theme.accent}`} />
        <button onClick={onGenerate} disabled={isGenerating} className={`px-6 py-2.5 rounded-lg text-white font-medium text-sm ${theme.btn} disabled:opacity-70`}>
          {isGenerating ? 'AI 正在生成内容...' : '一键生成版本 B'}
        </button>
      </div>
    )
  }

  return (
    <>
      {/* 图片全屏预览弹窗 */}
      {showImagePreview && currentPage.image && (
        <div 
          className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center cursor-zoom-out backdrop-blur-sm"
          onClick={() => setShowImagePreview(false)}
        >
          <img 
            src={currentPage.image} 
            alt="预览" 
            className="max-w-[90vw] max-h-[90vh] object-contain rounded-lg shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          />
          <button 
            onClick={() => setShowImagePreview(false)}
            className="absolute top-6 right-6 text-white/80 hover:text-white bg-black/50 rounded-full p-2"
          >
            <X className="w-6 h-6" />
          </button>
          {/* 预览时的页面导航 */}
          <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex items-center gap-3 bg-black/50 rounded-full px-4 py-2 backdrop-blur-sm">
            <button 
              onClick={(e) => { e.stopPropagation(); setCurrentPageIndex(Math.max(0, currentPageIndex - 1)) }}
              disabled={currentPageIndex === 0}
              className="text-white disabled:opacity-30"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <span className="text-white text-sm">{currentPageIndex + 1} / {pages.length}</span>
            <button 
              onClick={(e) => { e.stopPropagation(); setCurrentPageIndex(Math.min(pages.length - 1, currentPageIndex + 1)) }}
              disabled={currentPageIndex === pages.length - 1}
              className="text-white disabled:opacity-30"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}

      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        {/* 顶部色条 */}
        <div className={`h-1 ${theme.barColor}`} />
        
        {/* 分栏主体 */}
        <div className="flex min-h-[520px]">
          
          {/* 左侧：页面缩略图列表 */}
          <div className="w-[100px] flex-shrink-0 border-r border-slate-100 bg-slate-50/80 flex flex-col">
            <div className="p-2 border-b border-slate-100">
              <span className="text-[10px] font-medium text-slate-400 uppercase">页面</span>
            </div>
            <div className="flex-1 overflow-y-auto p-2 space-y-2">
              {pages.map((page, idx) => (
                <div 
                  key={idx}
                  onClick={() => setCurrentPageIndex(idx)}
                  className={`relative group cursor-pointer rounded-lg overflow-hidden border-2 transition-all ${
                    currentPageIndex === idx
                      ? 'border-blue-500 shadow-md'
                      : 'border-transparent hover:border-slate-300'
                  }`}
                >
                  {/* 缩略图 */}
                  <div className="aspect-[3/4] bg-slate-100 flex items-center justify-center">
                    {page.image ? (
                      <img src={page.image} alt={`第${idx + 1}页`} className="w-full h-full object-cover" />
                    ) : (
                      <div className="text-center">
                        {page.status === 'generating' ? (
                          <Loader2 className="w-4 h-4 text-slate-400 animate-spin mx-auto" />
                        ) : (
                          <ImageIcon className="w-4 h-4 text-slate-300 mx-auto" />
                        )}
                      </div>
                    )}
                  </div>
                  {/* 页码标签 */}
                  <div className="absolute bottom-1 left-1 bg-black/60 text-white text-[9px] px-1.5 py-0.5 rounded">
                    {idx === 0 ? '封面' : idx}
                  </div>
                  {/* 删除按钮 */}
                  {pages.length > 1 && (
                    <button
                      onClick={(e) => { e.stopPropagation(); removePage(idx) }}
                      className="absolute top-1 right-1 bg-red-500 text-white rounded-full p-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  )}
                </div>
              ))}
            </div>
            {/* 添加页面按钮 */}
            <div className="p-2 border-t border-slate-100 space-y-1.5">
              <button
                onClick={addPage}
                className="w-full py-1.5 rounded-lg border border-slate-200 text-slate-400 hover:border-blue-400 hover:text-blue-500 transition-all flex items-center justify-center gap-1 text-[10px]"
              >
                <Plus className="w-3 h-3" />
                添加页
              </button>
              <button
                onClick={generateOutlineFromTitle}
                disabled={isGeneratingOutline || !content.title}
                className="w-full py-1.5 rounded-lg bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:opacity-90 transition-all flex items-center justify-center gap-1 text-[10px] disabled:opacity-50"
              >
                {isGeneratingOutline ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <ListPlus className="w-3 h-3" />
                )}
                {isGeneratingOutline ? '生成中...' : 'AI大纲'}
              </button>
            </div>
          </div>
          
          {/* 中间：当前页图片区域 */}
          <div className="w-[300px] flex-shrink-0 border-r border-slate-100 bg-slate-50/50 flex flex-col">
            <div className="p-3 border-b border-slate-100 flex items-center justify-between">
              <span className="text-xs font-medium text-slate-600">
                {currentPageIndex === 0 ? '封面图' : `第 ${currentPageIndex} 页`}
              </span>
              <div className="flex items-center gap-1">
                <button 
                  onClick={() => setCurrentPageIndex(Math.max(0, currentPageIndex - 1))}
                  disabled={currentPageIndex === 0}
                  className="p-1 rounded hover:bg-slate-200 disabled:opacity-30 transition-colors"
                >
                  <ChevronLeft className="w-4 h-4 text-slate-500" />
                </button>
                <span className="text-xs text-slate-400">{currentPageIndex + 1}/{pages.length}</span>
                <button 
                  onClick={() => setCurrentPageIndex(Math.min(pages.length - 1, currentPageIndex + 1))}
                  disabled={currentPageIndex === pages.length - 1}
                  className="p-1 rounded hover:bg-slate-200 disabled:opacity-30 transition-colors"
                >
                  <ChevronRight className="w-4 h-4 text-slate-500" />
                </button>
              </div>
            </div>
            
            <div className="relative flex-1 flex items-center justify-center p-3">
              {currentPage.image ? (
                <div className="relative w-full h-full flex items-center justify-center">
                  <img 
                    src={currentPage.image} 
                    alt={`第${currentPageIndex + 1}页`}
                    className="max-w-full max-h-full object-contain rounded-lg cursor-zoom-in hover:shadow-lg transition-shadow"
                    onClick={() => setShowImagePreview(true)}
                  />
                  <div className="absolute bottom-2 right-2 flex gap-1.5">
                    <button 
                      onClick={() => setShowImagePreview(true)}
                      className="bg-black/60 text-white text-[10px] px-2 py-1 rounded-full hover:bg-black/80 transition-colors backdrop-blur-sm"
                    >
                      🔍
                    </button>
                    <button 
                      onClick={() => setShowImgMgr(true)}
                      className="bg-black/60 text-white text-[10px] px-2 py-1 rounded-full hover:bg-black/80 transition-colors backdrop-blur-sm"
                    >
                      换图
                    </button>
                    <button 
                      onClick={generateCurrentPageImage}
                      disabled={isGeneratingPage}
                      className="bg-black/60 text-white text-[10px] px-2 py-1 rounded-full hover:bg-black/80 transition-colors backdrop-blur-sm disabled:opacity-50"
                    >
                      {isGeneratingPage ? '...' : '🎨'}
                    </button>
                  </div>
                </div>
              ) : (
                <div 
                  onClick={() => isGeneratingPage ? null : generateCurrentPageImage()}
                  className={`w-full h-64 border-2 border-dashed border-slate-200 rounded-xl flex flex-col items-center justify-center transition-all gap-2 ${
                    isGeneratingPage ? 'cursor-wait' : 'cursor-pointer hover:border-blue-400 hover:bg-blue-50/30'
                  }`}
                >
                  {isGeneratingPage ? (
                    <>
                      <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
                      <span className="text-xs text-blue-500">AI 生成中...</span>
                    </>
                  ) : (
                    <>
                      <Wand2 className="w-8 h-8 text-slate-300" />
                      <span className="text-xs text-slate-500">点击 AI 生成图片</span>
                      <button
                        onClick={(e) => { e.stopPropagation(); setShowImgMgr(true) }}
                        className="text-[10px] text-blue-500 hover:underline"
                      >
                        或手动上传
                      </button>
                    </>
                  )}
                </div>
              )}

              {/* 图片管理器浮窗 */}
              {showImgMgr && (
                <div className="absolute inset-0 bg-white/98 backdrop-blur-md z-20 flex flex-col p-4 animate-in fade-in zoom-in duration-200">
                  <div className="flex justify-between items-center mb-3">
                    <span className="font-semibold text-sm text-slate-700">图片管理</span>
                    <button onClick={() => setShowImgMgr(false)}><X className="w-4 h-4 text-slate-400 hover:text-slate-600" /></button>
                  </div>
                  
                  <div className="flex gap-1 mb-3 p-1 bg-slate-100 rounded-lg">
                    {(['upload', 'url', 'search'] as const).map(t => (
                      <button 
                        key={t}
                        onClick={() => setActiveTab(t)}
                        className={`flex-1 py-1.5 text-[10px] font-medium rounded-md ${activeTab === t ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                      >
                        {t === 'upload' ? '📁 上传' : t === 'url' ? '🔗 链接' : '🎨 AI'}
                      </button>
                    ))}
                  </div>

                  <div className="flex-1 overflow-hidden">
                    {activeTab === 'upload' && (
                      <div 
                        onClick={() => fileInputRef.current?.click()}
                        className="h-full border-2 border-dashed border-slate-300 rounded-xl flex flex-col items-center justify-center cursor-pointer hover:border-indigo-400 hover:bg-indigo-50/50 transition-all gap-2"
                      >
                        <Upload className="w-6 h-6 text-slate-300" />
                        <span className="text-xs text-slate-500">选择图片</span>
                        <input ref={fileInputRef} type="file" accept="image/*" onChange={handleLocalUpload} className="hidden" />
                      </div>
                    )}
                    
                    {activeTab === 'url' && (
                      <div className="space-y-2 pt-2">
                        <input 
                          type="text" 
                          placeholder="https://..."
                          onKeyDown={(e) => {
                            if(e.key === 'Enter') {
                              const newPages = [...pages]
                              newPages[currentPageIndex] = { ...currentPage, image: e.currentTarget.value, status: 'done' }
                              updatePages(newPages)
                              setShowImgMgr(false)
                            }
                          }}
                          className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs focus:outline-none focus:border-[#ff2442]"
                        />
                        <p className="text-[10px] text-slate-400">粘贴 URL 按回车</p>
                      </div>
                    )}

                    {activeTab === 'search' && (
                      <ImageSearchPanel 
                        onSelect={(url) => { 
                          const newPages = [...pages]
                          newPages[currentPageIndex] = { ...currentPage, image: url, status: 'done' }
                          updatePages(newPages)
                          setShowImgMgr(false)
                        }} 
                        query={currentPage.content || content.title} 
                      />
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* 当前页文案编辑 */}
            <div className="p-3 border-t border-slate-100">
              <label className="text-[10px] font-medium text-slate-400 uppercase mb-1 block">页面描述</label>
              <textarea
                value={currentPage.content}
                onChange={(e) => updatePageContent(e.target.value)}
                placeholder="描述这一页的内容..."
                className="w-full h-16 resize-none text-xs text-slate-600 placeholder:text-slate-300 border border-slate-100 rounded-lg p-2 focus:ring-1 focus:ring-blue-100 focus:border-blue-300 bg-white transition-all"
              />
            </div>
          </div>
          
          {/* 右侧：文本编辑区域 */}
          <div className="flex-1 flex flex-col min-w-0">
            <div className="p-5 flex-1 flex flex-col gap-3">
              {/* 标题 */}
              <div>
                <label className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1 block">标题</label>
                <input
                  type="text"
                  value={content.title}
                  onChange={(e) => onChange({...content, title: e.target.value})}
                  placeholder="输入一个吸引人的标题..."
                  className="w-full text-lg font-bold text-slate-800 placeholder:text-slate-300 border-none p-0 focus:ring-0 bg-transparent"
                />
                <div className="h-px w-full bg-slate-100 mt-2" />
              </div>

              {/* 正文 */}
              <div className="flex-1 flex flex-col">
                <label className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1 block">正文</label>
                <textarea
                  value={content.body}
                  onChange={(e) => onChange({...content, body: e.target.value})}
                  placeholder="在这里输入笔记正文...&#10;&#10;话少一点，梗多一点 🤙"
                  className="w-full flex-1 min-h-[140px] resize-none text-sm leading-relaxed text-slate-600 placeholder:text-slate-300 border border-slate-100 rounded-lg p-3 focus:ring-1 focus:ring-blue-100 focus:border-blue-300 bg-slate-50/50 transition-all"
                />
              </div>

              {/* 标签 */}
              <div className="pt-2 border-t border-slate-100">
                <label className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2 block">标签</label>
                <div className="flex flex-wrap gap-2">
                  {content.tags.map(tag => (
                    <span key={tag} className="inline-flex items-center gap-1 px-2.5 py-1 bg-blue-50 text-blue-600 text-xs font-medium rounded-full border border-blue-100">
                      #{tag}
                      <button onClick={() => onChange({...content, tags: content.tags.filter(t => t !== tag)})} className="hover:text-red-500 transition-colors"><X className="w-3 h-3" /></button>
                    </span>
                  ))}
                  <div className="inline-flex items-center gap-1 text-slate-400 bg-white px-2.5 py-1 rounded-full border border-slate-200 focus-within:border-blue-400 focus-within:ring-1 focus-within:ring-blue-100 transition-all">
                    <Plus className="w-3 h-3" />
                    <input 
                      type="text" 
                      placeholder="添加标签" 
                      onKeyDown={handleTagKey}
                      className="w-20 text-xs bg-transparent border-none p-0 focus:ring-0 text-slate-700 placeholder:text-slate-400"
                    />
                  </div>
                </div>
              </div>
            </div>
            
            {/* 底部操作栏 */}
            <div className="px-5 py-3 border-t border-slate-100 bg-slate-50/50 flex justify-between items-center">
              <div className="flex items-center gap-2">
                <span className={`text-sm font-bold ${theme.accent}`}>{label}</span>
                <span className="text-xs text-slate-400">· {pages.length} 页</span>
                {onRemove && (
                  <button
                    onClick={onRemove}
                    className="p-1 rounded-md hover:bg-slate-200 transition-colors"
                    title={`删除 ${label}`}
                  >
                    <X className="w-3.5 h-3.5 text-slate-400 hover:text-slate-600" />
                  </button>
                )}
              </div>
              <div className="flex gap-2 items-center">
                <button 
                  onClick={generateAllImages}
                  disabled={isGeneratingPage}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100 transition-all disabled:opacity-50 flex items-center gap-1"
                >
                  <Wand2 className="w-3 h-3" />
                  {isGeneratingPage ? '生成中...' : '批量生图'}
                </button>
                <button 
                  onClick={onPublish}
                  disabled={isPublishing || !content.title}
                  className={`px-4 py-1.5 text-xs font-semibold rounded-lg shadow-sm transition-all disabled:opacity-50 disabled:shadow-none hover:opacity-90 ${
                    colorTheme === 'blue' 
                      ? 'bg-blue-500 text-white hover:bg-blue-600' 
                      : 'bg-[#ff2442] text-white hover:bg-[#e61f3d]'
                  }`}
                >
                  {isPublishing ? '发布中...' : '发布笔记'}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

function ImageSearchPanel({ onSelect, query }: { onSelect: (url: string) => void, query: string }) {
  const [image, setImage] = useState<string>('')
  const [loading, setLoading] = useState(false)

  const handleGenerate = async () => {
    setLoading(true)
    try {
      const imageUrl = await generateImage(query || '小红书封面图', '小红书风格')
      setImage(imageUrl)
    } catch (error) {
      console.error('生成图片失败:', error)
      alert('图片生成失败，请稍后重试')
    } finally {
      setLoading(false)
    }
  }

  // Auto generate on mount
  useEffect(() => { handleGenerate() }, [])

  return (
    <div className="h-full flex flex-col">
      {loading && (
        <div className="flex-1 flex flex-col items-center justify-center">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-indigo-600 mb-3"></div>
          <p className="text-sm text-slate-600">AI 正在生成图片...</p>
        </div>
      )}
      {!loading && image && (
        <div className="flex-1 flex flex-col gap-3">
          <img src={image} alt="AI生成" className="w-full rounded-lg border border-slate-200" />
          <button
            onClick={() => onSelect(image)}
            className="w-full py-2 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 transition-colors"
          >
            使用这张图片
          </button>
          <button
            onClick={handleGenerate}
            className="w-full py-2 bg-white border border-slate-200 text-slate-600 rounded-lg hover:bg-slate-50 transition-colors"
          >
            重新生成
          </button>
        </div>
      )}
    </div>
  )
}

export default App
