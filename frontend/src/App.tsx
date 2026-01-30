import { useEffect, useState, useRef, useCallback } from 'react'
import { 
  Zap, Send, Loader2, Sparkles, Play, Image as ImageIcon, Wand2,
  Share2, Paperclip, X, FileText, Upload, Plus, Search,
  Layout, Smartphone, ChevronRight, UserCircle2, BarChart3, GripVertical
} from 'lucide-react'
import { useApp } from './contexts/AppContext'
import { healthCheck, sendChatMessage, generateVariant, searchImages, runCrowdTest, publishContent } from './services/api'
import type { ContentItem, CrowdTestResult } from './types/api'

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
  
  const [isConnected, setIsConnected] = useState(false)
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isGeneratingB, setIsGeneratingB] = useState(false)
  const [testResult, setTestResult] = useState<CrowdTestResult | null>(null)
  const [isRunningTest, setIsRunningTest] = useState(false)
  const [isPublishing, setIsPublishing] = useState(false)
  const [uploadedFile, setUploadedFile] = useState<{ name: string; content: string } | null>(null)
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

  // 发送消息
  const handleSend = async () => {
    if ((!input.trim() && !uploadedFile) || isLoading) return
    
    // 构建消息内容
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

  // 处理文件上传 (Chat) - 支持更多文件格式
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    
    // 支持的文件格式
    const textTypes = ['.txt', '.md', '.json', '.csv', '.xml', '.html', '.css', '.js', '.ts']
    const docTypes = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
    const ext = file.name.toLowerCase().slice(file.name.lastIndexOf('.'))
    
    const isTextFile = textTypes.includes(ext) || file.type.startsWith('text/')
    const isDocFile = docTypes.includes(ext)
    
    if (!isTextFile && !isDocFile) {
      alert('支持的文件格式：\n• 文本：txt, md, json, csv\n• 文档：pdf, doc, docx, xls, xlsx, ppt, pptx')
      return
    }
    
    // 文档类文件限制 5MB，文本类限制 500KB
    const maxSize = isDocFile ? 5 * 1024 * 1024 : 500 * 1024
    if (file.size > maxSize) {
      alert(`文件大小不能超过 ${isDocFile ? '5MB' : '500KB'}`)
      return
    }
    
    if (isDocFile) {
      // 对于 PDF/Office 文件，只记录文件名（后端需要处理解析）
      setUploadedFile({ 
        name: file.name, 
        content: `[文档文件: ${file.name}]\n\n注意：这是一个 ${ext.toUpperCase()} 文件。请在对话中描述文件的主要内容，或者将关键信息复制粘贴到这里。` 
      })
    } else {
      // 文本文件直接读取内容
      const reader = new FileReader()
      reader.onload = (event) => {
        const content = event.target?.result as string
        setUploadedFile({ name: file.name, content })
      }
      reader.readAsText(file)
    }
    e.target.value = ''
  }

  // 生成版本B
  const handleGenerateB = async () => {
    if (!taskSpec || !contentA.title) return
    setIsGeneratingB(true)
    try {
      const variant = await generateVariant({
        task_spec: taskSpec,
        base_content: contentA,
        variant_type: 'alternative',
      })
      setContentB(variant)
    } catch (error) {
      console.error('生成变体失败:', error)
    } finally {
      setIsGeneratingB(false)
    }
  }

  // 运行测试
  const handleRunTest = async () => {
    if (!taskSpec || !contentA.title || !contentB.title) return
    setIsRunningTest(true)
    setTestResult(null)
    try {
      const result = await runCrowdTest({
        task_spec: taskSpec,
        content_a: contentA,
        content_b: contentB,
        max_users: 20,
      })
      setTestResult(result)
    } catch (error) {
      console.error('测试失败:', error)
    } finally {
      setIsRunningTest(false)
    }
  }

  // 发布
  const handlePublish = async (version: 'A' | 'B') => {
    const content = version === 'A' ? contentA : contentB
    if (!content.title || !content.body) {
      alert('请先填写标题和正文')
      return
    }
    if (!content.cover_image) {
      alert('请先添加封面图片')
      return
    }
    if (!confirm(`确定要发布版本 ${version} 吗？`)) return
    
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
    setTaskSpec(null)
    setTestResult(null)
  }

  return (
    <div className="h-screen flex flex-col bg-slate-50 font-sans text-slate-900">
      {/* 顶栏 - 专业风格 */}
      <header className="h-14 bg-white border-b border-slate-200 px-6 flex items-center justify-between flex-shrink-0 shadow-sm z-10 w-full">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-[#ff2442] rounded-lg flex items-center justify-center shadow-md">
            <Zap className="w-5 h-5 text-white fill-current" />
          </div>
          <div>
            <h1 className="font-bold text-slate-800 text-lg leading-tight tracking-tight">NoteTrial</h1>
            <p className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">A/B Testing Platform</p>
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
              const hasFile = msg.role === 'user' && fileMatch
              const fileName = hasFile ? fileMatch[1] : null
              // 提取用户实际输入的文字（文件内容之后的部分）
              let userText = msg.content
              if (hasFile) {
                // 找到文件内容后的用户文字（最后一个\n\n之后的内容）
                const parts = msg.content.split('\n\n')
                userText = parts.length > 2 ? parts[parts.length - 1] : ''
              }
              
              return (
                <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className="max-w-[90%] space-y-2">
                    {/* 文件附件卡片 - 独立显示在消息上方 */}
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
                {/* 发送按钮修正：绝对定位 + 垂直居中 */}
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
              {contentA.title && (
                <button
                  onClick={handleGenerateB}
                  disabled={isGeneratingB}
                  className="flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-white text-[#ff2442] border border-red-200 rounded-lg hover:bg-red-50 hover:border-red-300 transition-all disabled:opacity-50 shadow-sm"
                >
                  {isGeneratingB ? <Loader2 className="w-3 h-3 animate-spin" /> : <Wand2 className="w-3 h-3" />}
                  {contentB.title ? '重新生成 B' : '生成版本 B'}
                </button>
              )}
            </div>
          </div>
          
          <div className="flex-1 overflow-hidden p-6">
            <div className="h-full grid grid-cols-2 gap-6 max-w-7xl mx-auto">
              <EditorCard
                version="A"
                label="Version A"
                content={contentA}
                onChange={setContentA}
                onPublish={() => handlePublish('A')}
                isPublishing={isPublishing}
                colorTheme="blue"
              />
              <EditorCard
                version="B"
                label="Version B"
                content={contentB}
                onChange={setContentB}
                onPublish={() => handlePublish('B')}
                isPublishing={isPublishing}
                isEmpty={!contentB.title}
                onGenerate={handleGenerateB}
                isGenerating={isGeneratingB}
                colorTheme="red"
              />
            </div>
          </div>
        </div>
        
        {/* 右侧分隔条 */}
        <Resizer onDrag={handleRightResize} side="right" />

        {/* 右栏：测试面板 - 可拖拽 */}
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
                <button
                  onClick={handleRunTest}
                  disabled={!contentA.title || !contentB.title || isRunningTest}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-[#ff2442] text-white text-sm font-medium rounded-lg hover:bg-[#e61f3d] shadow-sm shadow-red-200 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isRunningTest ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
                  {isRunningTest ? '正在模拟用户反馈...' : '运行 A/B 测试'}
                </button>
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
// 专业编辑器组件 (EditorCard)
// ----------------------------------------------------------------------------

function EditorCard({ 
  label, content, onChange, onPublish, isPublishing, isEmpty, onGenerate, isGenerating, colorTheme
}: { 
  version: 'A' | 'B'
  label: string
  content: ContentItem
  onChange: (c: ContentItem) => void
  onPublish: () => void
  isPublishing: boolean
  isEmpty?: boolean
  onGenerate?: () => void
  isGenerating?: boolean
  colorTheme: 'blue' | 'red'
}) {
  const [activeTab, setActiveTab] = useState<'upload' | 'url' | 'search'>('upload')
  const [showImgMgr, setShowImgMgr] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  // 颜色配置 - 蓝色+小红书红配色
  const theme = {
    blue: { accent: 'text-blue-500', border: 'focus:border-blue-400', ring: 'focus:ring-blue-100', btn: 'bg-blue-500 hover:bg-blue-600', barColor: 'bg-blue-500', labelBg: 'bg-blue-500', labelText: 'text-white' },
    red: { accent: 'text-[#ff2442]', border: 'focus:border-[#ff2442]', ring: 'focus:ring-red-100', btn: 'bg-[#ff2442] hover:bg-[#e61f3d]', barColor: 'bg-[#ff2442]', labelBg: 'bg-[#ff2442]', labelText: 'text-white' }
  }[colorTheme]

  // 图片处理 logic
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

  // 标签处理 logic
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
    return (
      <div className="h-full rounded-2xl border-2 border-dashed border-slate-200 bg-slate-50 flex flex-col items-center justify-center gap-4 transition-all hover:border-slate-300 hover:bg-slate-100">
        <div className="w-16 h-16 rounded-full bg-white shadow-sm flex items-center justify-center">
          <Wand2 className={`w-8 h-8 ${theme.accent}`} />
        </div>
        <div className="text-center">
          <h3 className="font-semibold text-slate-700">版本 B 为空</h3>
          <p className="text-sm text-slate-400 mt-1">点击生成即刻开始测试</p>
        </div>
        <button
          onClick={onGenerate}
          disabled={isGenerating}
          className={`px-6 py-2.5 rounded-lg text-white font-medium text-sm shadow-md shadow-slate-200 transition-all ${theme.btn} disabled:opacity-70`}
        >
          {isGenerating ? 'AI 正在生成内容...' : '一键生成版本 B'}
        </button>
      </div>
    )
  }

  return (
    <div className="h-full bg-white rounded-2xl border border-slate-200 shadow-sm flex flex-col overflow-hidden relative group">
       {/* 顶部标签 */}
      <div className={`h-1 absolute top-0 left-0 right-0 ${theme.barColor}`} />
      
      <div className="flex-1 flex flex-col overflow-y-auto">
        {/* 图片区域 - 小红书风格 3:4 比例 */}
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

          {/* 图片管理器浮窗 */}
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

        {/* 内容编辑区域 */}
        <div className="p-5 flex-1 flex flex-col gap-5">
           {/* 标题 */}
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

           {/* 正文 */}
           <textarea
             value={content.body}
             onChange={(e) => onChange({...content, body: e.target.value})}
             placeholder="在这里输入笔记正文..."
             className="w-full flex-1 resize-none text-sm leading-relaxed text-slate-600 placeholder:text-slate-300 border-none p-0 focus:ring-0 bg-transparent"
           />

           {/* 标签 */}
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
      
      {/* 底部 Action Bar */}
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

function TestResultPanel({ result }: { result: CrowdTestResult }) {
  return (
    <div className="space-y-6">
      {/* 胜出者卡片 */}
      <div className="bg-gradient-to-br from-[#ff2442] to-[#e61f3d] rounded-xl p-4 text-white shadow-md shadow-red-200">
        <div className="flex items-center gap-2 mb-2 opacity-90">
             <Sparkles className="w-4 h-4 text-white" />
             <span className="text-xs font-bold uppercase tracking-wide">获胜版本</span>
        </div>
        <div className="text-2xl font-bold mb-1">
          Version {result.like_confidence.winner}
        </div>
        <div className="text-xs opacity-80 leading-relaxed">
          点击率优于对照组 {(result.like_confidence.confidence * 100).toFixed(0)}%
        </div>
      </div>

       {/* Detailed Stats */}
       <div className="space-y-3">
         <h4 className="flex items-center gap-2 text-xs font-semibold text-slate-700 uppercase tracking-wider">
            <BarChart3 className="w-3 h-3" /> 数据对比
         </h4>
         <StatBar label="点赞数 (Likes)" scoreA={result.version_a_score.like_count} scoreB={result.version_b_score.like_count} max={20} />
         <StatBar label="收藏数 (Saves)" scoreA={result.version_a_score.save_count} scoreB={result.version_b_score.save_count} max={20} />
       </div>
       
       {/* 模拟用户反馈 */}
       <div className="space-y-3">
          <h4 className="flex items-center gap-2 text-xs font-semibold text-slate-700 uppercase tracking-wider">
             <UserCircle2 className="w-3 h-3" /> 模拟用户声音
          </h4>
          <div className="space-y-3">
             {result.suggestions.slice(0,2).map((s,i) => (
               <div key={i} className="bg-slate-50 p-3 rounded-lg border border-slate-100 text-xs">
                 <div className="flex items-center gap-2 mb-1">
                    <div className="w-5 h-5 rounded-full bg-slate-200 flex items-center justify-center text-[10px] text-slate-500 font-bold">U{i+1}</div>
                    <span className="text-slate-400 scale-75">just now</span>
                 </div>
                 <p className="text-slate-600 leading-normal">{s}</p>
               </div>
             ))}
          </div>
       </div>

       <div className="bg-amber-50 rounded-lg p-3 border border-amber-100">
          <h4 className="text-xs font-semibold text-amber-700 mb-1">改进建议</h4>
          <ul className="list-disc pl-4 space-y-1">
             {result.diagnosis.slice(0,3).map((d, i) => (
                <li key={i} className="text-[10px] text-amber-600 leading-tight">{d}</li>
             ))}
          </ul>
       </div>
    </div>
  )
}

function StatBar({ label, scoreA, scoreB, max }: { label: string, scoreA: number, scoreB: number, max: number }) {
  const pA = (scoreA / max) * 100
  const pB = (scoreB / max) * 100
  
  return (
    <div className="bg-white border focus-within:ring-1 border-slate-100 rounded-lg p-3 shadow-sm">
      <div className="flex justify-between mb-2">
        <span className="text-xs font-medium text-slate-500">{label}</span>
      </div>
      <div className="space-y-2">
        {/* A Version */}
        <div className="flex items-center gap-2">
           <span className="text-[10px] w-3 text-blue-500 font-bold">A</span>
           <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
             <div style={{ width: `${pA}%` }} className="h-full bg-blue-500 rounded-full" />
           </div>
           <span className="text-[10px] w-4 text-blue-600 text-right">{scoreA}</span>
        </div>
        {/* B Version */}
        <div className="flex items-center gap-2">
           <span className="text-[10px] w-3 text-[#ff2442] font-bold">B</span>
           <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
             <div style={{ width: `${pB}%` }} className="h-full bg-[#ff2442] rounded-full" />
           </div>
           <span className="text-[10px] w-5 text-[#ff2442] font-bold text-right">{scoreB}</span>
        </div>
      </div>
    </div>
  )
}

export default App
