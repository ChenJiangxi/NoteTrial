import { useEffect, useState, useRef, useCallback } from 'react'
import { 
  Zap, Send, Loader2, Sparkles, Play, Image as ImageIcon, Wand2,
  Share2, Paperclip, X, FileText, Upload, Plus, Search,
  Layout, Smartphone, ChevronRight, UserCircle2, BarChart3, GripVertical, Home
} from 'lucide-react'
import { useApp } from './contexts/AppContext'
import { healthCheck, sendChatMessage, generateVariant, startCrowdTest, getCrowdTestProgress, publishContent, searchImages } from './services/api'
import type { ContentItem, MultiCrowdTestResult } from './types/api'
import WelcomePage from './components/WelcomePage'
import AutoModePage from './components/AutoModePage'

type AppMode = 'welcome' | 'interactive' | 'auto'

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
  
  const [appMode, setAppMode] = useState<AppMode>('welcome')
  
  const [isConnected, setIsConnected] = useState(false)
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isGeneratingB, setIsGeneratingB] = useState(false)
  const [testResult, setTestResult] = useState<MultiCrowdTestResult | null>(null)
  const [isRunningTest, setIsRunningTest] = useState(false)
  const [simulationProgress, setSimulationProgress] = useState(0)
  const [isPublishing, setIsPublishing] = useState(false)
  const audiencePresets = ['核心用户', '泛兴趣用户', '实用流', '互动流', '传播流']
  const [selectedAudienceTags, setSelectedAudienceTags] = useState<string[]>(audiencePresets)
  const [customAudienceInput, setCustomAudienceInput] = useState('')
  const [customAudienceTags, setCustomAudienceTags] = useState<string[]>([])
  const [selectedTestVersions, setSelectedTestVersions] = useState<string[]>(['Version A', 'Version B'])
  const [uploadedFile, setUploadedFile] = useState<{ name: string; content: string } | null>(null)
  const [extraVersions, setExtraVersions] = useState<Array<{ id: string; label: string; content: ContentItem; baseVersionLabel: string }>>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  const [leftWidth, setLeftWidth] = useState(384) // 默认 384px (w-96)
  const [rightWidth, setRightWidth] = useState(384)
  const MIN_WIDTH = 280
  const MAX_WIDTH = 600
  
  const handleLeftResize = useCallback((delta: number) => {
    setLeftWidth(w => Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, w + delta)))
  }, [])
  
  const handleRightResize = useCallback((delta: number) => {
    setRightWidth(w => Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, w + delta)))
  }, [])

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

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    if ((!input.trim() && !uploadedFile) || isLoading) return
    
    let messageContent = input.trim()
    if (uploadedFile) {
      messageContent = `[上传文件: ${uploadedFile.name}]\n\n${uploadedFile.content}\n\n${messageContent}`
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
      if (response.generated_content) setContentA(response.generated_content)
    } catch {
      addMessage({ role: 'assistant', content: '抱歉，服务暂时不可用，请稍后重试。' })
    } finally {
      setIsLoading(false)
    }
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    
    const textTypes = ['.txt', '.md', '.json', '.csv', '.xml', '.html', '.css', '.js', '.ts']
    const docTypes = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
    const ext = file.name.toLowerCase().slice(file.name.lastIndexOf('.'))
    
    const isTextFile = textTypes.includes(ext) || file.type.startsWith('text/')
    const isDocFile = docTypes.includes(ext)
    
    if (!isTextFile && !isDocFile) {
      alert('\u652f\u6301\u7684\u6587\u4ef6\u683c\u5f0f\uff1a\n\u2022 \u6587\u672c\uff1atxt, md, json, csv\n\u2022 \u6587\u6863\uff1apdf, doc, docx, xls, xlsx, ppt, pptx')
      return
    }
    
    const maxSize = isDocFile ? 5 * 1024 * 1024 : 500 * 1024
    if (file.size > maxSize) {
      alert(`\u6587\u4ef6\u5927\u5c0f\u4e0d\u80fd\u8d85\u8fc7 ${isDocFile ? '5MB' : '500KB'}`)
      return
    }
    
    if (isDocFile) {
      setUploadedFile({ 
        name: file.name, 
        content: `[\u6587\u6863\u6587\u4ef6: ${file.name}]\n\n\u6ce8\u610f\uff1a\u8fd9\u662f\u4e00\u4e2a ${ext.toUpperCase()} \u6587\u4ef6\u3002\u8bf7\u5728\u5bf9\u8bdd\u4e2d\u63cf\u8ff0\u6587\u4ef6\u7684\u4e3b\u8981\u5185\u5bb9\uff0c\u6216\u8005\u5c06\u5173\u952e\u4fe1\u606f\u590d\u5236\u7c98\u8d34\u5230\u8fd9\u91cc\u3002`,
      })
    } else {
      const reader = new FileReader()
      reader.onload = (event) => {
        const content = event.target?.result as string
        setUploadedFile({ name: file.name, content })
      }
      reader.readAsText(file)
    }
    e.target.value = ''
  }
  const getNextVersionLabel = (existingCount: number) => {
    return 'Version ' + String.fromCharCode(67 + existingCount)
  }
  const getVersionContentByLabel = (label?: string) => {
    const targetLabel = label && label.trim() ? label : 'Version A'
    if (targetLabel === 'Version A') return contentA
    if (targetLabel === 'Version B') return contentB
    return extraVersions.find(v => v.label === targetLabel)?.content || null
  }

  const getBaseOptionsForExtra = (currentId: string) => {
    const options: string[] = ['Version A']
    if (contentB.title || contentB.body) options.push('Version B')
    for (const v of extraVersions) {
      if (v.id !== currentId && (v.content.title || v.content.body)) {
        options.push(v.label)
      }
    }
    return options
  }

  const normalizeVersions = (nextContentB: ContentItem, nextExtras: Array<{ id: string; label: string; content: ContentItem; baseVersionLabel: string }>) => {
    let contentBNext = nextContentB
    let extrasNext = [...nextExtras]

    if ((!contentBNext.title && !contentBNext.body) && extrasNext.length > 0) {
      const [first, ...rest] = extrasNext
      contentBNext = first.content
      extrasNext = rest
    }

    const relabeled = extrasNext.map((v, idx) => ({
      ...v,
      label: `Version ${String.fromCharCode(67 + idx)}`,
    }))

    const allowed = new Set(['Version A'])
    if (contentBNext.title || contentBNext.body) allowed.add('Version B')
    for (const v of relabeled) allowed.add(v.label)

    const fixed = relabeled.map(v => ({
      ...v,
      baseVersionLabel: v.baseVersionLabel && allowed.has(v.baseVersionLabel)
        ? v.baseVersionLabel
        : (allowed.has('Version B') ? 'Version B' : 'Version A'),
    }))

    return { contentB: contentBNext, extras: fixed }
  }

  const handleDeleteVersionB = () => {
    const emptyB: ContentItem = { title: '', body: '', cover_image: '', tags: [] }
    const normalized = normalizeVersions(emptyB, extraVersions)
    setContentB(normalized.contentB)
    setExtraVersions(normalized.extras)
    setTestResult(null)
  }

  const handleDeleteVersionA = () => {
    if (!contentB.title && !contentB.body) return
    const emptyB: ContentItem = { title: '', body: '', cover_image: '', tags: [] }
    setContentA(contentB)
    const normalized = normalizeVersions(emptyB, extraVersions)
    setContentB(normalized.contentB)
    setExtraVersions(normalized.extras)
    setTestResult(null)
  }

  const nonEmptyCount = [
    contentA,
    contentB,
    ...extraVersions.map(v => v.content),
  ].filter(item => item.title || item.body).length
  const canDeleteAny = nonEmptyCount > 1

  const handleDeleteExtra = (versionId: string) => {
    const filtered = extraVersions.filter(v => v.id !== versionId)
    const normalized = normalizeVersions(contentB, filtered)
    setContentB(normalized.contentB)
    setExtraVersions(normalized.extras)
    setTestResult(null)
  }


  const handleAddVersion = () => {
    const defaultBase = extraVersions.length > 0
      ? extraVersions[extraVersions.length - 1].label
      : (contentB.title ? 'Version B' : 'Version A')

    setExtraVersions(prev => ([
      ...prev,
      {
        id: `v-${Date.now()}-${prev.length}`,
        label: getNextVersionLabel(prev.length),
        content: { title: '', body: '', cover_image: '', tags: [] },
        baseVersionLabel: defaultBase,
      },
    ]))
  }

  const handleStartManualB = () => {
    if (!contentA.title) return
    setContentB({ ...contentA })
    setTestResult(null)
  }

  const withKeywordTags = (content: ContentItem, keywords: string[]) => {
    if (!keywords.length) return content
    const existing = content.tags ?? []
    const merged = [...existing]
    for (const keyword of keywords) {
      const clean = keyword.trim()
      if (clean && !merged.includes(clean)) merged.push(clean)
    }
    return { ...content, tags: merged }
  }

  const handleGenerateBWithKeywords = async (keywords: string[]) => {
    if (!taskSpec || !contentA.title) return
    setIsGeneratingB(true)
    try {
      const variant = await generateVariant({
        task_spec: taskSpec,
        base_content: contentA,
        variant_type: 'alternative',
        mcp_keywords: keywords,
      })
      setContentB(withKeywordTags(variant, keywords))
      setTestResult(null)
    } catch (error) {
      console.error('Generate Version B with MCP failed:', error)
    } finally {
      setIsGeneratingB(false)
    }
  }
  const handleStartManualExtra = (versionId: string, baseVersionLabel?: string) => {
    const baseLabel = baseVersionLabel || 'Version A'
    const baseContent = getVersionContentByLabel(baseLabel)
    if (!baseContent) return

    setExtraVersions(prev => prev.map(v =>
      v.id === versionId
        ? { ...v, content: { ...baseContent }, baseVersionLabel: baseLabel }
        : v
    ))
    setTestResult(null)
  }

  const handleGenerateExtraWithKeywords = async (versionId: string, keywords: string[], baseVersionLabel?: string) => {
    if (!taskSpec) return
    const baseLabel = baseVersionLabel || 'Version A'
    const baseContent = getVersionContentByLabel(baseLabel)
    if (!baseContent || !baseContent.title) return

    setIsGeneratingB(true)
    try {
      const variant = await generateVariant({
        task_spec: taskSpec,
        base_content: baseContent,
        variant_type: 'alternative',
        mcp_keywords: keywords,
      })

      setExtraVersions(prev => prev.map(v =>
        v.id === versionId
          ? { ...v, content: withKeywordTags(variant, keywords), baseVersionLabel: baseLabel }
          : v
      ))
      setTestResult(null)
    } catch (error) {
      console.error('Generate extra version failed:', error)
    } finally {
      setIsGeneratingB(false)
    }
  }

  const mcpKeywordPlaceholder = (() => {
    const broadKeywords = new Set([
      '\u62a4\u80a4', '\u7f8e\u98df', '\u65c5\u6e38', '\u526f\u4e1a', '\u5065\u8eab', '\u7a7f\u642d', '\u5b66\u4e60', '\u804c\u573a', '\u7406\u8d22', '\u60c5\u611f', '\u6444\u5f71',
    ])

    const seeds: string[] = []
    if (taskSpec?.topic?.trim()) seeds.push(taskSpec.topic.trim())
    if (contentA.tags?.length) seeds.push(...contentA.tags.slice(0, 3))
    if (taskSpec?.audience?.trim()) {
      const firstAudience = taskSpec.audience.split(/[\/,\s]+/)[0]?.trim()
      if (firstAudience) seeds.push(firstAudience)
    }

    const refined = Array.from(
      new Set(
        seeds
          .map(s => s.replace(/^#/, '').trim())
          .filter(Boolean),
      ),
    )

    const specific = refined.filter(s => s.length >= 3 && s.length <= 10 && !broadKeywords.has(s))

    let sample = specific[0] || ''
    if (!sample && refined.length >= 2) sample = `${refined[0]}${refined[1]}`
    if (!sample && refined.length >= 1) sample = refined[0]

    if (sample.length > 12) sample = sample.slice(0, 12)

    const placeholder = sample ? `\u5982\uff1a${sample}` : ''
    return Array.from(placeholder).slice(0, 15).join('')
  })()

  const testVersionOptions = [
    { label: 'Version A', content: contentA },
    { label: 'Version B', content: contentB },
    ...extraVersions.map(v => ({ label: v.label, content: v.content })),
  ]
  const hasContent = (item: ContentItem) => Boolean(item.title || item.body)
  const selectedVersionItems = testVersionOptions.filter(option => selectedTestVersions.includes(option.label))
  const canRunTest = selectedTestVersions.length >= 2 && selectedVersionItems.every(option => hasContent(option.content))

  const toggleTestVersion = (label: string) => {
    setSelectedTestVersions(prev => (
      prev.includes(label) ? prev.filter(v => v !== label) : [...prev, label]
    ))
  }

  const handleRunTest = async () => {
    if (!taskSpec) return
    if (selectedTestVersions.length < 2) {
      alert('请至少选择两个版本进行对比测试')
      return
    }
    const selectedVersions = selectedVersionItems
    if (selectedVersions.some(option => !option.content?.title)) return
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
        versions: selectedVersions.map(option => ({ label: option.label, content: option.content })),
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
  const handlePublishContent = async (content: ContentItem, versionLabel: string) => {
    if (!content.title || !content.body) {
      alert('请完善版本标题和正文')
      return
    }
    if (!content.cover_image) {
      alert('\u8bf7\u5148\u6dfb\u52a0\u5c01\u9762\u56fe\u7247')
      return
    }
    if (!confirm(`\u786e\u5b9a\u8981\u53d1\u5e03 ${versionLabel} \u5417\uff1f`)) return

    setIsPublishing(true)
    try {
      const result = await publishContent(content)
      if (result.success) {
        alert('\u53d1\u5e03\u6210\u529f')
      } else {
        alert(`\u53d1\u5e03\u5931\u8d25: ${result.message}`)
      }
    } catch (error: any) {
      alert(`\u53d1\u5e03\u5931\u8d25: ${error.message}`)
    } finally {
      setIsPublishing(false)
    }
  }

  const handlePublish = async (version: 'A' | 'B') => {
    const content = version === 'A' ? contentA : contentB
    await handlePublishContent(content, `Version ${version}`)
  }

  const handleReset = () => {
    setMessages([{ role: 'assistant', content: '👋 你好！我是 NoteTrial 助手。\n\n告诉我想测试什么内容，例如：\n“程序员副业指南”\n“美食探店文案”\n“护肤品种草”\n\n你可以上传产品资料，我会帮你生成更准确的内容。' }])
    setContentA({ title: '', body: '', tags: [] })
    setContentB({ title: '', body: '', tags: [] })
    setTaskSpec(null)
    setTestResult(null)
    setExtraVersions([])
    setSelectedTestVersions(['Version A', 'Version B'])
  }

  const handleModeSelect = (mode: 'interactive' | 'auto') => {
    setAppMode(mode)
  }

  const handleBackToWelcome = () => {
    setAppMode('welcome')
    handleReset()
  }

  if (appMode === 'welcome') {
    return <WelcomePage onSelectMode={handleModeSelect} />
  }

  if (appMode === 'auto') {
    return <AutoModePage onBack={handleBackToWelcome} />
  }

  return (
    <div className="h-screen flex flex-col bg-slate-50 font-sans text-slate-900">
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
          <button onClick={handleReset} className="text-xs font-medium text-slate-500 hover:text-[#ff2442] transition-colors">
            新建项目
          </button>
        </div>
      </header>

      <main className="flex-1 flex min-h-0 overflow-hidden">
        
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
              const fileMatch = msg.content.match(/^\[上传文件: (.+?)\]\n\n/)
              const hasFile = msg.role === 'user' && fileMatch
              const fileName = hasFile ? fileMatch[1] : null
              let userText = msg.content
              if (hasFile) {
                const parts = msg.content.split('\n\n')
                userText = parts.length > 2 ? parts[parts.length - 1] : ''
              }
              
              return (
                <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className="max-w-[90%] space-y-2">
                    {hasFile && fileName && (
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
              <div className="mb-3 flex items-center gap-3 px-4 py-3 bg-white border border-slate-200 rounded-xl shadow-sm">
                <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center flex-shrink-0">
                  <FileText className="w-5 h-5 text-blue-500" />
                </div>
                <div className="flex-1 min-w-0">
                  <span className="block text-sm font-medium text-slate-700 truncate">{uploadedFile.name}</span>
                  <span className="text-xs text-slate-400">准备发送</span>
                </div>
                <button onClick={() => setUploadedFile(null)} className="text-slate-400 hover:text-slate-700 p-1">
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}
            
            <div className="flex gap-2 items-end">
              <input ref={fileInputRef} type="file" accept=".txt,.md,.json,.csv,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,text/*" onChange={handleFileUpload} className="hidden" />
              <button 
                onClick={() => fileInputRef.current?.click()}
                className="mb-1 p-2 text-slate-400 hover:text-[#ff2442] hover:bg-slate-100 rounded-xl transition-all border border-transparent hover:border-slate-200"
                title="上传资料"
              >
                <Paperclip className="w-5 h-5" />
              </button>
              
              <div className="flex-1 relative">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      handleSend()
                    }
                  }}
                  placeholder="输入消息，回车发送..."
                  className="w-full pl-4 pr-12 py-3 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-red-100 focus:border-[#ff2442] focus:bg-white transition-all"
                />
                <button
                  onClick={handleSend}
                  disabled={(!input.trim() && !uploadedFile) || isLoading}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-slate-400 hover:text-[#ff2442] hover:bg-red-50 rounded-lg transition-all disabled:opacity-30 flex items-center justify-center"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
        
        <Resizer onDrag={handleLeftResize} side="left" />

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
              {contentA.title && (
                <button
                  onClick={handleAddVersion}
                  disabled={isGeneratingB}
                  className="flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-white text-[#ff2442] border border-red-200 rounded-lg hover:bg-red-50 hover:border-red-300 transition-all disabled:opacity-50 shadow-sm"
                >
                  {isGeneratingB ? <Loader2 className="w-3 h-3 animate-spin" /> : <Wand2 className="w-3 h-3" />}
                  {'\u65b0\u589e\u7248\u672c'}
                </button>
              )}
            </div>
          </div>
          
          <div className="flex-1 overflow-y-auto p-6">
            <div className="grid gap-6 max-w-7xl mx-auto" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))" }}>
              <EditorCard
                version="A"
                label="Version A"
                content={contentA}
                onChange={setContentA}
                onPublish={() => handlePublish('A')}
                isPublishing={isPublishing}
                onDelete={canDeleteAny ? handleDeleteVersionA : undefined}
                colorTheme="red"
              />
              <EditorCard
                version="B"
                label="Version B"
                content={contentB}
                onChange={setContentB}
                onPublish={() => handlePublish('B')}
                isPublishing={isPublishing}
                isEmpty={!contentB.title}
                onGenerate={handleGenerateBWithKeywords}
                isGenerating={isGeneratingB}
                onStartManual={handleStartManualB}
                mcpKeywordPlaceholder={mcpKeywordPlaceholder}
                onDelete={canDeleteAny ? handleDeleteVersionB : undefined}
                colorTheme="red"
              />
              {extraVersions.map((versionItem) => (
                <EditorCard
                  key={versionItem.id}
                  version={versionItem.label}
                  label={versionItem.label}
                  content={versionItem.content}
                  onChange={(next) => setExtraVersions(prev => prev.map(v => v.id === versionItem.id ? { ...v, content: next } : v))}
                  onPublish={() => handlePublishContent(versionItem.content, versionItem.label)}
                  isPublishing={isPublishing}
                  isEmpty={!versionItem.content.title}
                  onGenerate={(keywords, baseVersionLabel) => handleGenerateExtraWithKeywords(versionItem.id, keywords, baseVersionLabel)}
                  onStartManual={(baseVersionLabel) => handleStartManualExtra(versionItem.id, baseVersionLabel)}
                  mcpKeywordPlaceholder={mcpKeywordPlaceholder}
                  baseVersionOptions={getBaseOptionsForExtra(versionItem.id)}
                  defaultBaseVersion={versionItem.baseVersionLabel}
                  onDelete={canDeleteAny ? () => handleDeleteExtra(versionItem.id) : undefined}
                  colorTheme="red"
                />
              ))}
            </div>
          </div>
        </div>
        
        <Resizer onDrag={handleRightResize} side="right" />

        <div 
          className="border-l border-slate-200 bg-white flex flex-col" 
          style={{ width: rightWidth, flexShrink: 0, flexGrow: 0 }}
        >
           <div className="h-full flex flex-col">
            <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <div className="flex items-center gap-2 text-slate-700">
                <Play className="w-4 h-4 text-[#ff2442]" />
                <span className="font-semibold text-sm">模拟测试</span>
              </div>
            </div>
            
            <div className="flex-1 overflow-y-auto p-5 scrollbar-thin scrollbar-thumb-slate-200">
              <div className="bg-slate-50 rounded-xl p-4 border border-slate-100 mb-6">
                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">操作</h3>
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
                      placeholder="例如：一线城市 25-30 岁职业女性"
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
                <div className="mb-4">
                  <p className="text-xs text-slate-500 mb-2">{'\u6d4b\u8bd5\u7248\u672c\uff08\u53ef\u591a\u9009\uff0c\u81f3\u5c11\u9009 2 \u4e2a\uff09'}</p>
                  <div className="flex flex-wrap gap-2">
                    {testVersionOptions.map(option => {
                      const disabled = !hasContent(option.content)
                      const active = selectedTestVersions.includes(option.label)
                      return (
                        <button
                          key={option.label}
                          type="button"
                          onClick={() => !disabled && toggleTestVersion(option.label)}
                          className={`px-2.5 py-1 text-xs rounded-full border transition-all ${
                            active
                              ? 'bg-red-50 border-red-300 text-[#ff2442]'
                              : 'bg-white border-slate-200 text-slate-500 hover:border-slate-300'
                          } ${disabled ? 'opacity-40 cursor-not-allowed hover:border-slate-200' : ''}`}
                        >
                          {option.label}
                        </button>
                      )
                    })}
                  </div>
                </div>
                <button
                  onClick={handleRunTest}
                  disabled={!canRunTest || isRunningTest}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-[#ff2442] text-white text-sm font-medium rounded-lg hover:bg-[#e61f3d] shadow-sm shadow-red-200 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isRunningTest ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
                  {isRunningTest ? `模拟测试中 ${simulationProgress}%` : '运行对比测试'}
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
                <TestResultPanel result={testResult} />
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
        </div>
      </main>
    </div>
  )
}

// ----------------------------------------------------------------------------
// ----------------------------------------------------------------------------

function EditorCard({ 
  label, content, onChange, onPublish, isPublishing, isEmpty, onGenerate, onStartManual, isGenerating, colorTheme, mcpKeywordPlaceholder, baseVersionOptions, defaultBaseVersion, onDelete
}: { 
  version: string
  label: string
  content: ContentItem
  onChange: (c: ContentItem) => void
  onPublish: () => void
  isPublishing: boolean
  isEmpty?: boolean
  onGenerate?: (keywords: string[], baseVersionLabel?: string) => void
  onStartManual?: (baseVersionLabel?: string) => void
  isGenerating?: boolean
  colorTheme: 'blue' | 'red'
  mcpKeywordPlaceholder?: string
  baseVersionOptions?: string[]
  defaultBaseVersion?: string
  onDelete?: () => void
}) {
  const [activeTab, setActiveTab] = useState<'upload' | 'url' | 'search'>('upload')
  const [showImgMgr, setShowImgMgr] = useState(false)
  const [mcpKeywordInput, setMcpKeywordInput] = useState('')
  const [selectedBaseVersion, setSelectedBaseVersion] = useState(defaultBaseVersion || baseVersionOptions?.[0] || 'Version A')
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (defaultBaseVersion && defaultBaseVersion !== selectedBaseVersion) {
      setSelectedBaseVersion(defaultBaseVersion)
    }
  }, [defaultBaseVersion])
  
  const theme = {
    blue: { accent: 'text-blue-500', border: 'focus:border-blue-400', ring: 'focus:ring-blue-100', btn: 'bg-blue-500 hover:bg-blue-600', barColor: 'bg-blue-500', labelBg: 'bg-blue-500', labelText: 'text-white' },
    red: { accent: 'text-[#ff2442]', border: 'focus:border-[#ff2442]', ring: 'focus:ring-red-100', btn: 'bg-[#ff2442] hover:bg-[#e61f3d]', barColor: 'bg-[#ff2442]', labelBg: 'bg-[#ff2442]', labelText: 'text-white' }
  }[colorTheme]

  const handleLocalUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => {
      onChange({ ...content, cover_image: ev.target?.result as string })
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
  if (isEmpty && onGenerate) {
    const rawKeywordInput = mcpKeywordInput.trim()
    const keywords = !rawKeywordInput
      ? []
      : /[,;\/\s]+/.test(rawKeywordInput)
        ? rawKeywordInput
            .split(/[,;\/\s]+/)
            .map(k => k.trim())
            .filter(Boolean)
        : [rawKeywordInput]

    return (
      <div className="min-h-[640px] rounded-2xl border-2 border-dashed border-slate-200 bg-slate-50 flex flex-col items-center justify-center gap-4 px-6 transition-all hover:border-slate-300 hover:bg-slate-100 relative">
        {onDelete && (
          <button
            onClick={onDelete}
            className="absolute right-3 top-3 z-10 w-7 h-7 rounded-full bg-white border border-slate-200 text-slate-400 hover:text-red-500 hover:border-red-200 shadow-sm flex items-center justify-center"
            title="\u5220\u9664\u7248\u672c"
          >
            <X className="w-4 h-4" />
          </button>
        )}
        <div className="w-16 h-16 rounded-full bg-white shadow-sm flex items-center justify-center">
          <Wand2 className={`w-8 h-8 ${theme.accent}`} />
        </div>
        <div className="text-center">
          <h3 className="font-semibold text-slate-700">{`${label} \u4e3a\u7a7a`}</h3>
          <p className="text-sm text-slate-500 mt-1">
            {'\u53ef\u9009\u62e9\u624b\u52a8\u6539\u5199\uff0c\u6216\u8f93\u5165\u5173\u952e\u8bcd\u6821\u51c6\u751f\u6210\u3002'}
          </p>
        </div>

        <div className="w-full max-w-md space-y-3">
          {baseVersionOptions && baseVersionOptions.length > 0 && (
            <div className="rounded-lg border border-slate-200 bg-white p-3 space-y-2">
              <p className="text-xs text-slate-500">{'\u57fa\u4e8e\u7248\u672c'}</p>
              <select
                value={selectedBaseVersion}
                onChange={(e) => setSelectedBaseVersion(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-red-100 focus:border-[#ff2442] bg-white"
              >
                {baseVersionOptions.map((option) => (
                  <option key={option} value={option}>{option}</option>
                ))}
              </select>
            </div>
          )}
          <button
            onClick={() => onStartManual?.(selectedBaseVersion)}
            disabled={!onStartManual}
            className="w-full px-4 py-2.5 rounded-lg border border-slate-300 bg-white text-slate-700 text-sm font-medium hover:bg-slate-50 disabled:opacity-50"
          >
            {'\u624b\u52a8\u6539\u5199'}
          </button>

          <div className="rounded-lg border border-slate-200 bg-white p-3 space-y-2">
            <p className="text-xs text-slate-500">{'\u5173\u952e\u8bcd\uff1a'}</p>
            <input
              value={mcpKeywordInput}
              onChange={(e) => setMcpKeywordInput(e.target.value)}
              placeholder={mcpKeywordPlaceholder}
              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-red-100 focus:border-[#ff2442]"
            />
            <button
              onClick={() => onGenerate(keywords, selectedBaseVersion)}
              disabled={isGenerating || keywords.length === 0}
              className={`w-full px-4 py-2.5 rounded-lg text-white text-sm font-medium transition-all ${theme.btn} disabled:opacity-60`}
            >
              {isGenerating ? '\u6821\u51c6\u751f\u6210\u4e2d...' : `\u6821\u51c6\u751f\u6210${label}`}
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-[640px] bg-white rounded-2xl border border-slate-200 shadow-sm flex flex-col overflow-hidden relative group">
      {onDelete && (
        <button
          onClick={onDelete}
          className="absolute right-3 top-3 z-10 w-7 h-7 rounded-full bg-white border border-slate-200 text-slate-400 hover:text-red-500 hover:border-red-200 shadow-sm flex items-center justify-center"
          title="\u5220\u9664\u7248\u672c"
        >
          <X className="w-4 h-4" />
        </button>
      )}
      <div className={`h-1 absolute top-0 left-0 right-0 ${theme.barColor}`} />
      
      <div className="flex-1 flex flex-col overflow-y-auto">
        <div className="relative w-full bg-slate-100 border-b border-slate-100 group-image flex-shrink-0" style={{ aspectRatio: '3/4', maxHeight: '280px' }}>
          {content.cover_image ? (
            <>
              <img src={content.cover_image} alt="Cover" className="w-full h-full object-contain bg-slate-50" />
              <button 
                onClick={() => setShowImgMgr(!showImgMgr)}
                className="absolute bottom-3 right-3 bg-black/70 text-white text-xs px-3 py-1.5 rounded-full hover:bg-black transition-colors backdrop-blur-sm"
              >
                更换图片
              </button>
            </>
          ) : (
             <div 
              onClick={() => setShowImgMgr(true)}
              className="w-full h-full flex flex-col items-center justify-center cursor-pointer hover:bg-slate-200/50 transition-colors gap-3"
             >
               <div className="w-12 h-12 rounded-full bg-white shadow-sm flex items-center justify-center text-slate-400">
                 <ImageIcon className="w-6 h-6" />
               </div>
              <span className="text-sm font-medium text-slate-500">上传封面图</span>
             </div>
          )}

          {showImgMgr && (
            <div className="absolute inset-0 bg-white/95 backdrop-blur-md z-20 flex flex-col p-4 animate-in fade-in zoom-in duration-200">
              <div className="flex justify-between items-center mb-4">
                <span className="font-semibold text-slate-700 text-sm">图片管理</span>
                <button onClick={() => setShowImgMgr(false)}><X className="w-4 h-4 text-slate-400" /></button>
              </div>
              
              <div className="flex gap-2 mb-4 p-1 bg-slate-100 rounded-lg">
                {(['upload', 'url', 'search'] as const).map(t => (
                  <button 
                    key={t}
                    onClick={() => setActiveTab(t)}
                    className={`flex-1 py-1.5 text-xs font-medium rounded-md capitalize ${activeTab === t ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                  >
                    {t === 'upload' ? '本地上传' : t === 'url' ? '链接' : '搜索'}
                  </button>
                ))}
              </div>

              <div className="flex-1">
                {activeTab === 'upload' && (
                  <div 
                    onClick={() => fileInputRef.current?.click()}
                    className="h-full border-2 border-dashed border-slate-300 rounded-xl flex flex-col items-center justify-center cursor-pointer hover:border-indigo-400 hover:bg-indigo-50/50 transition-all gap-2"
                  >
                    <Upload className="w-8 h-8 text-slate-300" />
                    <span className="text-xs text-slate-500">点击选择图片文件</span>
                    <input ref={fileInputRef} type="file" accept="image/*" onChange={handleLocalUpload} className="hidden" />
                  </div>
                )}
                
                {activeTab === 'url' && (
                  <div className="space-y-3 pt-4">
                    <input 
                      type="text" 
                      placeholder="https://example.com/image.jpg"
                      onKeyDown={(e) => {
                         if(e.key === 'Enter') {
                            onChange({ ...content, cover_image: e.currentTarget.value })
                            setShowImgMgr(false)
                         }
                      }}
                      className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:border-[#ff2442]"
                    />
                    <p className="text-xs text-slate-400">输入 URL 并回车</p>
                  </div>
                )}

                {activeTab === 'search' && (
                   <ImageSearchPanel onSelect={(url) => { onChange({...content, cover_image: url}); setShowImgMgr(false); }} query={content.title} />
                )}
              </div>
            </div>
          )}
        </div>

        <div className="p-5 flex-1 flex flex-col gap-5">
           <div className="space-y-1">
             <input
               type="text"
               value={content.title}
               onChange={(e) => onChange({...content, title: e.target.value})}
              placeholder="输入一个吸引人的标题..."
               className={`w-full text-lg font-bold text-slate-800 placeholder:text-slate-300 border-none p-0 focus:ring-0 bg-transparent`}
             />
             <div className="h-0.5 w-10 bg-slate-200 rounded-full" />
           </div>

           <textarea
             value={content.body}
             onChange={(e) => onChange({...content, body: e.target.value})}
            placeholder="在这里输入笔记正文..."
             className="w-full flex-1 resize-none text-sm leading-relaxed text-slate-600 placeholder:text-slate-300 border-none p-0 focus:ring-0 bg-transparent"
           />

           <div className="space-y-2 pt-4 border-t border-slate-100">
             <div className="flex flex-wrap gap-2">
               {content.tags.map(tag => (
                 <span key={tag} className="inline-flex items-center gap-1 px-2 py-1 bg-slate-100 text-slate-600 text-xs rounded-md">
                   #{tag}
                   <button onClick={() => onChange({...content, tags: content.tags.filter(t => t !== tag)})} className="hover:text-red-500"><X className="w-3 h-3" /></button>
                 </span>
               ))}
               <div className="flex items-center gap-1 text-slate-400 bg-slate-50 px-2 py-1 rounded-md border border-slate-100 focus-within:border-[#ff2442] focus-within:ring-1 focus-within:ring-red-100 transition-all">
                  <Plus className="w-3 h-3" />
                  <input 
                    type="text" 
                    placeholder="标签" 
                    onKeyDown={handleTagKey}
                    className="w-16 text-xs bg-transparent border-none p-0 focus:ring-0 text-slate-700 placeholder:text-slate-400"
                  />
               </div>
             </div>
           </div>
        </div>
      </div>
      
      <div className="px-5 py-4 border-t border-slate-100 bg-slate-50/50 flex justify-between items-center">
        <span className={`text-sm font-bold ${theme.accent}`}>{label}</span>
        <div className="flex gap-3">
          <button className="text-slate-400 hover:text-slate-600"><Share2 className="w-4 h-4" /></button>
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
  )
}

function ImageSearchPanel({ onSelect, query }: { onSelect: (url: string) => void, query: string }) {
  const [images, setImages] = useState<string[]>([])
  const [loading, setLoading] = useState(false)

  const handleSearch = async () => {
    setLoading(true)
    try {
      const res = await searchImages(query || 'lifestyle', 6)
      setImages(res)
    } catch {
       // ignore
    } finally {
      setLoading(false)
    }
  }

  // Auto search on mount
  useEffect(() => { handleSearch() }, [])

  return (
    <div className="h-full flex flex-col">
       <div className="flex gap-2 mb-2">
         <input 
            className="flex-1 px-2 py-1 text-xs border border-slate-200 rounded" 
            defaultValue={query} 
            onChange={() => { /* no-op for now */ }}
         />
         <button onClick={handleSearch} className="bg-slate-100 p-1 rounded hover:bg-slate-200"><Search className="w-3 h-3 text-slate-600" /></button>
       </div>
       {loading ? (
         <div className="flex-1 flex items-center justify-center"><Loader2 className="w-4 h-4 animate-spin text-slate-400" /></div>
       ) : (
         <div className="grid grid-cols-2 gap-2 overflow-y-auto max-h-[160px]">
           {images.map((img, i) => (
             <img key={i} src={img} className="w-full h-20 object-cover rounded cursor-pointer hover:opacity-80 border border-slate-100" onClick={() => onSelect(img)} />
           ))}
         </div>
       )}
    </div>
  )
}

function TestResultPanel({ result }: { result: MultiCrowdTestResult }) {
  const winnerLabel = result.overall_confidence.winner && result.overall_confidence.winner !== '-' ? result.overall_confidence.winner : '\u2014'
  const totalUsers = Math.max(result.persona_results.length, 1)
  const scoreItems = result.version_scores

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-br from-[#ff2442] to-[#e61f3d] rounded-xl p-4 text-white shadow-md shadow-red-200">
        <div className="flex items-center gap-2 mb-2 opacity-90">
          <Sparkles className="w-4 h-4 text-white" />
          <span className="text-xs font-bold uppercase tracking-wide">{'\u83b7\u80dc\u7248\u672c'}</span>
        </div>
        <div className="text-2xl font-bold mb-1">{winnerLabel}</div>
        <div className="text-xs opacity-80 leading-relaxed">
          {'\u7efc\u5408\u8868\u73b0\u4f18\u4e8e\u5bf9\u7167\u7ec4 '}
          {result.overall_confidence.confidence.toFixed(0)}%
        </div>
      </div>

      <div className="space-y-3">
        <h4 className="flex items-center gap-2 text-xs font-semibold text-slate-700 uppercase tracking-wider">
          <BarChart3 className="w-3 h-3" /> {'\u6570\u636e\u5bf9\u6bd4'}
        </h4>
        <StatBar label={'\u70b9\u8d5e\u6570 (Likes)'} totalUsers={totalUsers} items={scoreItems.map(v => ({ label: v.label, value: v.score.like_count }))} />
        <StatBar label={'\u6536\u85cf\u6570 (Saves)'} totalUsers={totalUsers} items={scoreItems.map(v => ({ label: v.label, value: v.score.save_count }))} />
        <StatBar label={'\u8bc4\u8bba\u6570 (Comments)'} totalUsers={totalUsers} items={scoreItems.map(v => ({ label: v.label, value: v.score.comment_count }))} />
        <StatBar label={'\u5206\u4eab\u6570 (Shares)'} totalUsers={totalUsers} items={scoreItems.map(v => ({ label: v.label, value: v.score.share_count }))} />
        <div className="bg-slate-50 border border-slate-100 rounded-lg p-3 text-xs text-slate-600 flex items-center justify-between">
          <span>{'\u603b\u4f53\u7f6e\u4fe1\u5ea6 (Overall)'}</span>
          <span className="font-semibold text-slate-700">
            {winnerLabel} - {result.overall_confidence.confidence.toFixed(0)}%
          </span>
        </div>
      </div>

      <div className="space-y-3">
        <h4 className="flex items-center gap-2 text-xs font-semibold text-slate-700 uppercase tracking-wider">
          <UserCircle2 className="w-3 h-3" /> {'\u6a21\u62df\u7528\u6237\u58f0\u97f3'}
        </h4>
        <div className="space-y-3">
          {result.suggestions.slice(0, 2).map((s, i) => (
            <div key={i} className="bg-slate-50 p-3 rounded-lg border border-slate-100 text-xs">
              <div className="flex items-center gap-2 mb-1">
                <div className="w-5 h-5 rounded-full bg-slate-200 flex items-center justify-center text-[10px] text-slate-500 font-bold">U{i + 1}</div>
                <span className="text-slate-400 scale-75">just now</span>
              </div>
              <p className="text-slate-600 leading-normal">{s}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-amber-50 rounded-lg p-3 border border-amber-100">
        <h4 className="text-xs font-semibold text-amber-700 mb-1">{'\u6539\u8fdb\u5efa\u8bae'}</h4>
        <ul className="list-disc pl-4 space-y-1">
          {result.diagnosis.slice(0, 3).map((d, i) => (
            <li key={i} className="text-xs text-amber-700 leading-normal">{d}</li>
          ))}
        </ul>
      </div>
    </div>
  )
}

function StatBar({ label, totalUsers, items }: { label: string, totalUsers: number, items: Array<{ label: string, value: number }> }) {
  const base = Math.max(totalUsers, 1)
  const palette = ['#ff2442', '#ff7a90', '#ffa9b6', '#ffd1d8', '#ffe3e7', '#ffeef1']

  return (
    <div className="bg-white border focus-within:ring-1 border-slate-100 rounded-lg p-3 shadow-sm">
      <div className="flex justify-between mb-2">
        <span className="text-xs font-medium text-slate-500">{label}</span>
      </div>
      <div className="space-y-2">
        {items.map((item, index) => {
          const pct = (item.value / base) * 100
          const color = palette[index % palette.length]
          return (
            <div key={item.label} className="flex items-center gap-2">
              <span className="text-[10px] w-16 text-slate-600 font-semibold truncate">{item.label}</span>
              <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                <div style={{ width: `${pct}%`, backgroundColor: color }} className="h-full rounded-full" />
              </div>
              <span className="text-[10px] w-10 text-slate-500 text-right">{pct.toFixed(0)}%</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default App
