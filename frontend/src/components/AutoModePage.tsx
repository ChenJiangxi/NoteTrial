import { useState, useEffect, useRef, useCallback } from 'react'
import { 
  Home, RefreshCw, TrendingUp, 
  CheckCircle2, AlertCircle, Clock, Zap, BarChart3,
  Loader2, Sparkles, Play, Pause, Square,
  ThumbsUp, Bookmark, MessageCircle, Eye,
  Settings, ChevronDown, ChevronUp, Brain, Shuffle, Shield,
  RotateCcw, QrCode, User, LogIn
} from 'lucide-react'
import { 
  healthCheck, publishContent,
  getNoteStats, generateCover, syncNotes,
  autoGenerateEnhanced, getLearningStats, getDiversityStats,
  recordContent, addMonitorTask, getLoginQRCode, checkLoginStatus
} from '../services/api'
import type { ContentItem } from '../types/api'

// 持久化的会话状态
interface SessionState {
  topic: string
  goals: string[]
  publishInterval: number
  autoPublish: boolean
  useLearning: boolean
  checkDiversity: boolean
  useHumanize: boolean
  materialText: string  // 素材文本
  logs: string[]
  cycleCount: number
  currentContent: ContentItem | null
  currentImage: string
  autoStatus: AutoStatus
  currentPhase: CurrentPhase  // 当前阶段
  countdown: number  // 倒计时秒数
  lastActiveTime: string
  publishedNotes: PublishedNote[]  // 添加发布历史
  learningStats: any  // 学习统计
  diversityStats: any  // 多样性统计
  humannessScore: number | null  // AI检测评分
}

/**
 * 解析中文数字格式（如"5万"、"1.2万"、"129"）为整数
 * 支持格式：纯数字、万、千、亿、w、k、m
 */
function parseChineseNumber(value: string | number | null | undefined): number {
  if (value === null || value === undefined) return 0
  
  // 如果已经是数字，直接返回
  if (typeof value === 'number') return Math.floor(value)
  
  const s = String(value).trim()
  if (!s) return 0
  
  // 尝试直接解析为数字
  const directNum = parseFloat(s)
  if (!isNaN(directNum) && !/[万千亿wkmWKM]/.test(s)) {
    return Math.floor(directNum)
  }
  
  // 处理中文数字单位
  const match = s.match(/^([\d.]+)\s*(万|千|亿|w|k|m)?$/i)
  if (match) {
    const num = parseFloat(match[1])
    const unit = match[2]?.toLowerCase()
    
    if (unit === '万' || unit === 'w') return Math.floor(num * 10000)
    if (unit === '千' || unit === 'k') return Math.floor(num * 1000)
    if (unit === '亿') return Math.floor(num * 100000000)
    if (unit === 'm') return Math.floor(num * 1000000)
    return Math.floor(num)
  }
  
  // 最后尝试提取纯数字
  const digits = s.match(/\d+/)
  if (digits) return parseInt(digits[0])
  
  return 0
}

interface AutoModePageProps {
  onBack: () => void
}

// 发布的笔记记录
interface PublishedNote {
  id: string
  noteId?: string
  xsecToken?: string  // 用于后续获取笔记详情
  content: ContentItem
  publishedAt: string
  stats?: {
    likes: number
    collects: number
    comments: number
    views: number
  }
  lastUpdated?: string
}

// 自动化状态
type AutoStatus = 'idle' | 'running' | 'paused' | 'error'

// 当前执行阶段
type CurrentPhase = 'waiting' | 'learning' | 'generating' | 'image' | 'publishing' | 'monitoring' | 'cooldown'

export default function AutoModePage({ onBack }: AutoModePageProps) {
  // MCP 状态
  const [mcpStatus, setMcpStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking')
  
  // 自动化控制
  const [autoStatus, setAutoStatus] = useState<AutoStatus>('idle')
  const [currentPhase, setCurrentPhase] = useState<CurrentPhase>('waiting')
  const [cycleCount, setCycleCount] = useState(0)
  
  // 配置（简化为最少必填项）
  const [topic, setTopic] = useState('')
  const [goals, setGoals] = useState<string[]>(['maximize_save'])
  const [showConfig, setShowConfig] = useState(true)
  const [publishInterval, setPublishInterval] = useState(30) // 发布间隔（分钟）
  const [autoPublish, setAutoPublish] = useState(true) // 是否自动发布
  
  // P0 功能开关
  const [useLearning, setUseLearning] = useState(true)
  const [checkDiversity, setCheckDiversity] = useState(true)
  const [useHumanize, setUseHumanize] = useState(true)
  
  // P0 统计数据
  const [learningStats, setLearningStats] = useState<any>(null)
  const [diversityStats, setDiversityStats] = useState<any>(null)
  const [humannessScore, setHumannessScore] = useState<number | null>(null)
  
  // 当前生成的内容
  const [currentContent, setCurrentContent] = useState<ContentItem | null>(null)
  const [currentImage, setCurrentImage] = useState<string>('')
  
  // 发布历史
  const [publishedNotes, setPublishedNotes] = useState<PublishedNote[]>([])
  
  // 素材输入
  const [materialText, setMaterialText] = useState('')
  
  // 日志
  const [logs, setLogs] = useState<string[]>([])
  const logRef = useRef<HTMLDivElement>(null)
  
  // 倒计时
  const [countdown, setCountdown] = useState(0)
  
  // 登录状态
  const [loginStatus, setLoginStatus] = useState<'checking' | 'logged_in' | 'logged_out'>('checking')
  const [loginQRCode, setLoginQRCode] = useState<string>('')
  const [showLoginModal, setShowLoginModal] = useState(false)
  const [loginUserName, setLoginUserName] = useState<string>('')
  
  // 是否有可恢复的会话
  const [hasResumableSession, setHasResumableSession] = useState(false)
  
  // 自动循环 ref
  const autoLoopRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null)
  
  // 使用ref跟踪运行状态（避免闭包问题）
  const isRunningRef = useRef(false)

  // 保存会话状态
  const saveSessionState = useCallback(() => {
    const state: SessionState = {
      topic,
      goals,
      publishInterval,
      autoPublish,
      useLearning,
      checkDiversity,
      useHumanize,
      materialText,
      logs,
      cycleCount,
      currentContent,
      currentImage,
      autoStatus,
      currentPhase,
      countdown,
      lastActiveTime: new Date().toISOString(),
      publishedNotes,
      learningStats,
      diversityStats,
      humannessScore
    }
    localStorage.setItem('automode_session', JSON.stringify(state))
  }, [topic, goals, publishInterval, autoPublish, useLearning, checkDiversity, useHumanize, materialText, logs, cycleCount, currentContent, currentImage, autoStatus, currentPhase, countdown, publishedNotes, learningStats, diversityStats, humannessScore])
  
  // 恢复会话状态
  const restoreSession = useCallback(() => {
    const saved = localStorage.getItem('automode_session')
    if (saved) {
      try {
        const state: SessionState = JSON.parse(saved)
        setTopic(state.topic)
        setGoals(state.goals)
        setPublishInterval(state.publishInterval)
        setAutoPublish(state.autoPublish)
        setUseLearning(state.useLearning)
        setCheckDiversity(state.checkDiversity)
        setUseHumanize(state.useHumanize)
        if (state.materialText) setMaterialText(state.materialText)
        setLogs(state.logs)
        setCycleCount(state.cycleCount)
        setCurrentContent(state.currentContent)
        setCurrentImage(state.currentImage)
        // 恢复阶段和倒计时
        if (state.currentPhase) setCurrentPhase(state.currentPhase)
        if (state.countdown) setCountdown(state.countdown)
        // 恢复发布历史和统计数据
        if (state.publishedNotes) {
          setPublishedNotes(state.publishedNotes)
        }
        if (state.learningStats) {
          setLearningStats(state.learningStats)
        }
        if (state.diversityStats) {
          setDiversityStats(state.diversityStats)
        }
        if (state.humannessScore !== undefined) {
          setHumannessScore(state.humannessScore)
        }
        // 不恢复运行状态，让用户手动继续
        setAutoStatus('paused')
        setShowConfig(false)
        setHasResumableSession(false)
        
        // 根据恢复的状态给出明确提示
        addLog('📂 已恢复上次会话')
        if (state.currentPhase === 'cooldown' && state.countdown > 0) {
          addLog(`⏰ 上次冷却剩余 ${Math.floor(state.countdown / 60)}分${state.countdown % 60}秒`)
          addLog('💡 点击「继续」恢复倒计时，或直接开始新一轮')
        } else {
          addLog('💡 点击「继续」开始下一轮生成')
        }
      } catch (e) {
        console.error('恢复会话失败', e)
      }
    }
  }, [])
  
  // 清除会话
  const clearSession = () => {
    localStorage.removeItem('automode_session')
    setHasResumableSession(false)
  }
  
  // 检查登录状态
  const checkLogin = async () => {
    try {
      const result = await checkLoginStatus()
      const text = result.result?.content?.[0]?.text || ''
      if (text.includes('已登录') || text.includes('登录成功')) {
        setLoginStatus('logged_in')
        // 尝试提取用户名
        const match = text.match(/用户[名：:]*[「「]?([^」」\s]+)/)
        if (match) setLoginUserName(match[1])
      } else {
        setLoginStatus('logged_out')
      }
    } catch {
      setLoginStatus('logged_out')
    }
  }
  
  // 获取登录二维码
  const fetchLoginQRCode = async () => {
    try {
      const result = await getLoginQRCode()
      const text = result.result?.content?.[0]?.text || ''
      // 从返回中提取二维码URL或base64
      if (text.includes('http')) {
        const urlMatch = text.match(/(https?:\/\/[^\s"']+)/)
        if (urlMatch) setLoginQRCode(urlMatch[1])
      }
    } catch (e) {
      console.error('获取二维码失败', e)
    }
  }

  // 检查服务状态
  useEffect(() => {
    const check = async () => {
      try {
        const health = await healthCheck()
        setMcpStatus(health.services.xiaohongshu_mcp ? 'connected' : 'disconnected')
        
        // 检查登录状态
        await checkLogin()
        
        // P0: 加载学习引擎和多样性统计
        try {
          const learning = await getLearningStats()
          setLearningStats(learning)
        } catch (e) {
          console.log('学习统计暂无数据')
        }
        
        try {
          const diversity = await getDiversityStats()
          setDiversityStats(diversity)
        } catch (e) {
          console.log('多样性统计暂无数据')
        }
      } catch {
        setMcpStatus('disconnected')
      }
    }
    check()
    
    // 从本地存储加载发布历史
    const savedNotes = localStorage.getItem('automode_published_notes')
    if (savedNotes) setPublishedNotes(JSON.parse(savedNotes))
    
    // 检查是否有可恢复的会话
    const savedSession = localStorage.getItem('automode_session')
    if (savedSession) {
      try {
        const state: SessionState = JSON.parse(savedSession)
        // 只有在有实际内容时才提示恢复
        if (state.topic && (state.logs.length > 0 || state.cycleCount > 0)) {
          setHasResumableSession(true)
        }
      } catch (e) {
        localStorage.removeItem('automode_session')
      }
    }
  }, [])

  // 自动滚动日志
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight
    }
  }, [logs])

  // 保存到本地存储
  useEffect(() => {
    localStorage.setItem('automode_published_notes', JSON.stringify(publishedNotes))
  }, [publishedNotes])
  
  // 自动保存会话状态（当有变化时）
  useEffect(() => {
    if (autoStatus !== 'idle' || logs.length > 0 || cycleCount > 0 || publishedNotes.length > 0) {
      saveSessionState()
    }
  }, [autoStatus, logs, cycleCount, currentContent, publishedNotes, saveSessionState])

  // 清理定时器
  useEffect(() => {
    return () => {
      if (autoLoopRef.current) clearTimeout(autoLoopRef.current)
      if (countdownRef.current) clearInterval(countdownRef.current)
    }
  }, [])

  const addLog = (message: string) => {
    const time = new Date().toLocaleTimeString()
    setLogs(prev => [...prev.slice(-99), `[${time}] ${message}`])
  }

  // 执行一次完整的自动循环
  const runOneCycle = async () => {
    // 使用ref检查是否应该继续运行
    if (!isRunningRef.current) {
      console.log('isRunningRef为false，跳过本轮')
      return
    }
    
    setCycleCount(prev => prev + 1)
    addLog(`━━━ 第 ${cycleCount + 1} 轮自动生成开始 ━━━`)
    
    try {
      // 1. 学习阶段
      setCurrentPhase('learning')
      addLog('🔍 学习小红书爆款内容...')
      if (useLearning) {
        addLog('🧠 应用学习引擎优化...')
      }
      if (checkDiversity) {
        addLog('🎲 检查内容多样性...')
      }
      
      // 2. 生成内容（使用增强版 API）
      setCurrentPhase('generating')
      addLog('📝 AI 生成原创内容...')
      
      // 构建受众描述，包含素材信息
      const audienceWithMaterial = materialText 
        ? `小红书用户\n\n【参考素材】\n${materialText}`
        : '小红书用户'
      
      const result = await autoGenerateEnhanced(
        topic, 
        goals, 
        audienceWithMaterial, 
        15,
        useLearning,
        checkDiversity,
        useHumanize
      )
      setCurrentContent(result.content)
      addLog(`✓ 内容生成完成：${result.content.title}`)
      addLog(`  参考了 ${result.reference_count} 条高赞笔记`)
      
      // P0: 显示增强功能结果
      if (result.p0_enhancements) {
        const p0 = result.p0_enhancements
        if (p0.learning_hints_applied > 0) {
          addLog(`  🧠 应用了 ${p0.learning_hints_applied} 条学习建议`)
        }
        if (p0.diversity_check) {
          if (p0.diversity_check.is_valid) {
            addLog(`  ✅ 多样性检查通过`)
          } else {
            addLog(`  ⚠️ 多样性提醒: ${p0.diversity_check.issues.join(', ')}`)
          }
        }
        if (p0.humanness_score) {
          setHumannessScore(p0.humanness_score.score)
          addLog(`  🤖 AI检测规避评分: ${p0.humanness_score.score}/100`)
          if (p0.humanness_score.issues.length > 0) {
            addLog(`     待优化: ${p0.humanness_score.issues.slice(0, 2).join(', ')}`)
          }
        }
      }
      
      // 3. 生成封面图
      setCurrentPhase('image')
      addLog('🎨 AI 生成原创封面图...')
      
      let imageData = ''
      try {
        const imageResult = await generateCover(result.content, topic)
        if (imageResult.success && imageResult.image) {
          imageData = imageResult.image
          setCurrentImage(imageData)
          addLog('✓ 封面图生成成功')
        } else {
          addLog('⚠ 封面图生成失败: ' + (imageResult.error || '未知错误'))
        }
      } catch (err) {
        addLog('⚠ 封面图生成出错: ' + err)
      }
      
      // 4. 发布
      const contentId = Date.now().toString()
      
      if (autoPublish) {
        setCurrentPhase('publishing')
        addLog('📤 发布到小红书...')
        
        const contentToPublish: ContentItem = {
          ...result.content,
          cover_image: imageData
        }
        
        const publishResult = await publishContent(contentToPublish)
        
        if (publishResult.success) {
          addLog('✓ 发布成功！')
          
          // 检查是否获取到noteId
          if (publishResult.note_id) {
            addLog(`  📝 笔记ID: ${publishResult.note_id}`)
          } else {
            addLog('  ⚠️ 未获取到笔记ID，稍后可手动刷新')
          }
          
          const newNote: PublishedNote = {
            id: contentId,
            noteId: publishResult.note_id,
            xsecToken: publishResult.data?.xsecToken,  // 从 data 中获取 xsec_token（如果有的话）
            content: result.content,
            publishedAt: new Date().toISOString(),
            stats: { likes: 0, collects: 0, comments: 0, views: 0 }
          }
          setPublishedNotes(prev => [newNote, ...prev])
          
          // P0: 记录到学习引擎
          try {
            await recordContent(contentId, result.content.title, result.content.body, result.content.tags || [], topic)
            addLog('  📊 已记录到学习引擎')
          } catch (e) {
            console.log('记录学习数据失败', e)
          }
          
          // P0: 添加监控任务
          if (publishResult.note_id) {
            try {
              await addMonitorTask(contentId, publishResult.note_id)
              addLog('  👁️ 已添加效果监控任务')
              
              // 30秒后尝试获取初始数据
              setTimeout(async () => {
                addLog('🔄 尝试获取初始数据...')
                await refreshNoteStats(newNote)
              }, 30000)
            } catch (e) {
              console.log('添加监控任务失败', e)
            }
          }
        } else {
          addLog(`⚠ 发布失败: ${publishResult.message}`)
        }
      } else {
        addLog('📋 内容已生成（未启用自动发布）')
      }
      
      // 5. 进入冷却期
      setCurrentPhase('cooldown')
      const waitMinutes = publishInterval
      addLog(`⏰ 等待 ${waitMinutes} 分钟后进入下一轮...`)
      
      // 开始倒计时
      setCountdown(waitMinutes * 60)
      
      // 使用一个变量跟踪剩余时间
      let remainingSeconds = waitMinutes * 60
      
      countdownRef.current = setInterval(() => {
        // 检查是否仍在运行
        if (!isRunningRef.current) {
          if (countdownRef.current) clearInterval(countdownRef.current)
          return
        }
        
        remainingSeconds -= 1
        setCountdown(remainingSeconds)
        
        if (remainingSeconds <= 0) {
          if (countdownRef.current) clearInterval(countdownRef.current)
          // 倒计时结束，触发下一轮
          runOneCycle()
        }
      }, 1000)
      
    } catch (error) {
      addLog(`✗ 本轮执行出错: ${error}`)
      isRunningRef.current = false
      setAutoStatus('error')
      setCurrentPhase('waiting')
    }
  }

  // 启动自动模式
  const handleStart = () => {
    if (!topic.trim()) {
      alert('请输入创作话题')
      return
    }
    if (mcpStatus !== 'connected') {
      alert('小红书 MCP 未连接')
      return
    }
    
    // 设置运行状态
    isRunningRef.current = true
    setAutoStatus('running')
    setShowConfig(false)
    setLogs([])
    addLog('🚀 自动模式已启动')
    addLog(`📌 话题：${topic}`)
    addLog(`🎯 目标：${goals.map(g => goalLabels[g]).join('、')}`)
    addLog(`⏱ 发布间隔：${publishInterval} 分钟`)
    
    // 立即开始第一轮
    runOneCycle()
  }

  // 暂停
  const handlePause = () => {
    isRunningRef.current = false
    setAutoStatus('paused')
    if (autoLoopRef.current) clearTimeout(autoLoopRef.current)
    if (countdownRef.current) clearInterval(countdownRef.current)
    addLog('⏸ 已暂停')
  }

  // 继续运行
  const handleResume = () => {
    isRunningRef.current = true
    setAutoStatus('running')
    addLog('▶ 继续运行')
    
    // 判断当前应该做什么
    if (currentPhase === 'cooldown' && countdown > 0) {
      // 还在冷却期，恢复倒计时
      addLog(`⏰ 继续等待 ${Math.floor(countdown / 60)}分${countdown % 60}秒...`)
      let remainingSeconds = countdown
      
      countdownRef.current = setInterval(() => {
        if (!isRunningRef.current) {
          if (countdownRef.current) clearInterval(countdownRef.current)
          return
        }
        remainingSeconds -= 1
        setCountdown(remainingSeconds)
        
        if (remainingSeconds <= 0) {
          if (countdownRef.current) clearInterval(countdownRef.current)
          runOneCycle()
        }
      }, 1000)
    } else {
      // 如果不在冷却期或倒计时已结束，直接开始下一轮
      addLog('📝 开始新一轮生成...')
      runOneCycle()
    }
  }

  // 停止
  const handleStop = () => {
    isRunningRef.current = false
    setAutoStatus('idle')
    setCurrentPhase('waiting')
    if (autoLoopRef.current) clearTimeout(autoLoopRef.current)
    if (countdownRef.current) clearInterval(countdownRef.current)
    setCountdown(0)
    setShowConfig(true)
    addLog('⏹ 已停止')
    // 清除会话，下次重新开始
    clearSession()
  }

  // 刷新笔记数据
  const refreshNoteStats = async (note: PublishedNote) => {
    if (!note.noteId) {
      console.log('笔记没有noteId，跳过刷新:', note.content.title)
      return
    }
    
    try {
      // 优先使用保存的 xsecToken，否则用标题关键词搜索
      const result = await getNoteStats(note.noteId, {
        xsecToken: note.xsecToken,
        titleKeyword: note.content.title.slice(0, 8)
      })
      console.log('MCP返回笔记数据:', result)
      
      // 检查是否有错误 - API 直接返回数据，不再包装在 result 中
      const content = typeof result === 'string' ? result : (result as any).result?.content?.[0]?.text || (result as any).content
      
      if (content) {
        let newStats = { likes: 0, collects: 0, comments: 0, views: 0 }
        
        try {
          // 尝试解析JSON
          const data = JSON.parse(content)
          console.log('解析的笔记数据:', data)
          
          // 尝试多种可能的数据结构
          const interactInfo = data.interactInfo || data.interact_info || data.noteCard?.interactInfo || {}
          const noteData = data.noteCard || data
          
          // 使用中文数字解析函数
          newStats = {
            likes: parseChineseNumber(interactInfo.likedCount || interactInfo.liked_count || noteData.likedCount),
            collects: parseChineseNumber(interactInfo.collectedCount || interactInfo.collected_count || noteData.collectedCount),
            comments: parseChineseNumber(interactInfo.commentCount || interactInfo.comment_count || noteData.commentCount),
            views: parseChineseNumber(noteData.viewCount || noteData.view_count || data.viewCount)
          }
        } catch {
          // 如果不是JSON，尝试从文本中提取数字
          console.log('非JSON格式，尝试文本解析:', content)
          const likesMatch = content.match(/(点赞|喜欢)[\uff1a:]*\s*([\d.]+万?千?)/i)
          const collectsMatch = content.match(/收藏[\uff1a:]*\s*([\d.]+万?千?)/i)
          const commentsMatch = content.match(/评论[\uff1a:]*\s*([\d.]+万?千?)/i)
          const viewsMatch = content.match(/(浏览|观看)[\uff1a:]*\s*([\d.]+万?千?)/i)
          
          if (likesMatch) newStats.likes = parseChineseNumber(likesMatch[2])
          if (collectsMatch) newStats.collects = parseChineseNumber(collectsMatch[1])
          if (commentsMatch) newStats.comments = parseChineseNumber(commentsMatch[1])
          if (viewsMatch) newStats.views = parseChineseNumber(viewsMatch[2])
        }
        
        setPublishedNotes(prev => prev.map(n => 
          n.id === note.id 
            ? { ...n, stats: newStats, lastUpdated: new Date().toISOString() }
            : n
        ))
        
        addLog(`📊 ${note.content.title.slice(0,10)}... → 👍${newStats.likes} 🔖${newStats.collects} 💬${newStats.comments}`)
      } else {
        console.log('未获取到笔记内容')
      }
    } catch (e) {
      console.error('刷新笔记数据失败:', e)
    }
  }

  // 从小红书同步笔记数据（通过标题搜索）
  const syncAllNotes = async () => {
    if (publishedNotes.length === 0) {
      addLog('⚠ 没有已发布的笔记')
      return
    }
    
    addLog('🔄 从小红书同步数据...')
    
    try {
      // 提取所有笔记的标题
      const titles = publishedNotes.map(n => n.content.title).filter(t => t && t.length >= 3)
      
      if (titles.length === 0) {
        addLog('⚠ 没有有效的笔记标题')
        return
      }
      
      addLog(`📝 正在搜索 ${titles.length} 条笔记...`)
      
      const result = await syncNotes(titles)
      console.log('同步笔记API返回:', result)
      
      if (result.error) {
        addLog(`⚠ ${result.error}`)
        return
      }
      
      const syncedNotes = result.notes || []
      if (syncedNotes.length === 0) {
        addLog('⚠ 未在小红书找到匹配的笔记（可能搜索排名靠后或刚发布）')
        return
      }
      
      // 遍历本地发布记录，匹配并更新数据
      let updated = 0
      setPublishedNotes(prev => prev.map(note => {
        // 通过 matchedTitle 匹配
        const matched = syncedNotes.find(n => 
          n.matchedTitle === note.content.title ||
          (n.title && note.content.title && 
            (n.title.includes(note.content.title.slice(0, 6)) || 
             note.content.title.includes(n.title.slice(0, 6))))
        )
        
        if (matched) {
          updated++
          const newStats = {
            likes: parseChineseNumber(matched.likedCount),
            collects: parseChineseNumber(matched.collectedCount),
            comments: parseChineseNumber(matched.commentCount),
            views: 0
          }
          console.log(`匹配笔记: ${note.content.title} -> 👍${newStats.likes} 🔖${newStats.collects}`)
          return {
            ...note,
            noteId: note.noteId || matched.noteId,
            xsecToken: matched.xsecToken,
            stats: newStats,
            lastUpdated: new Date().toISOString()
          }
        }
        return note
      }))
      
      addLog(`✓ 已同步 ${updated}/${publishedNotes.length} 条笔记数据`)
      
    } catch (e) {
      console.error('同步失败:', e)
      addLog('⚠ 同步失败，请检查MCP连接')
    }
  }

  // 批量刷新所有笔记数据
  const refreshAllStats = async () => {
    await syncAllNotes()
  }

  const goalLabels: Record<string, string> = {
    'maximize_save': '高收藏',
    'maximize_like': '高点赞',
    'maximize_comment': '高评论',
    'maximize_share': '高分享'
  }

  // 格式化倒计时
  const formatCountdown = (seconds: number) => {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `${m}:${s.toString().padStart(2, '0')}`
  }

  // 获取阶段描述
  const getPhaseText = () => {
    switch (currentPhase) {
      case 'learning': return '学习爆款中...'
      case 'generating': return '生成内容中...'
      case 'image': return '生成封面图...'
      case 'publishing': return '发布中...'
      case 'monitoring': return '监控效果中...'
      case 'cooldown': return `下一轮: ${formatCountdown(countdown)}`
      default: return '等待中'
    }
  }

  // 计算总数据
  const totalStats = publishedNotes.reduce((acc, note) => ({
    likes: acc.likes + (note.stats?.likes || 0),
    collects: acc.collects + (note.stats?.collects || 0),
    comments: acc.comments + (note.stats?.comments || 0),
    views: acc.views + (note.stats?.views || 0)
  }), { likes: 0, collects: 0, comments: 0, views: 0 })

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      {/* 登录弹窗 */}
      {showLoginModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-white border border-gray-200 rounded-xl p-6 max-w-sm w-full mx-4">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <QrCode className="w-5 h-5 text-orange-500" />
              扫码登录小红书
            </h3>
            
            {loginQRCode ? (
              <div className="bg-white p-4 rounded-lg mb-4">
                <img src={loginQRCode} alt="登录二维码" className="w-full" />
              </div>
            ) : (
              <div className="bg-gray-50 border border-gray-200 p-8 rounded-lg mb-4 flex flex-col items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-gray-400 mb-2" />
                <span className="text-sm text-gray-400">加载二维码中...</span>
              </div>
            )}
            
            <p className="text-sm text-gray-400 mb-4 text-center">
              请使用小红书 App 扫描二维码登录
            </p>
            
            <div className="flex gap-2">
              <button
                onClick={() => {
                  checkLogin()
                  if (loginStatus === 'logged_in') setShowLoginModal(false)
                }}
                className="flex-1 py-2 bg-orange-600 rounded-lg hover:bg-orange-700"
              >
                我已扫码
              </button>
              <button
                onClick={() => setShowLoginModal(false)}
                className="flex-1 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
              >
                取消
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* 会话恢复提示 */}
      {hasResumableSession && (
        <div className="fixed top-16 left-1/2 -translate-x-1/2 bg-orange-600 text-white px-4 py-3 rounded-lg shadow-lg z-40 flex items-center gap-4">
          <RotateCcw className="w-5 h-5" />
          <span>检测到上次未完成的会话</span>
          <button
            onClick={restoreSession}
            className="px-3 py-1 bg-white text-orange-600 rounded font-medium hover:bg-gray-100"
          >
            恢复
          </button>
          <button
            onClick={clearSession}
            className="px-3 py-1 bg-orange-700 rounded hover:bg-orange-800"
          >
            忽略
          </button>
        </div>
      )}

      {/* 顶部导航 */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={onBack} className="flex items-center gap-2 text-gray-500 hover:text-gray-700">
              <Home className="w-5 h-5" />
            </button>
            <span className="text-gray-600">|</span>
            <div className="flex items-center gap-2">
              <Zap className="w-5 h-5 text-orange-500" />
              <span className="font-medium">全自动模式</span>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            {/* 登录状态 */}
            <button
              onClick={() => {
                if (loginStatus === 'logged_out') {
                  fetchLoginQRCode()
                  setShowLoginModal(true)
                }
              }}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-sm ${
                loginStatus === 'logged_in' ? 'bg-green-900/50 text-green-400' :
                loginStatus === 'logged_out' ? 'bg-gray-100 text-gray-700 hover:bg-gray-200 cursor-pointer' :
                'bg-gray-100 text-gray-500'
              }`}
            >
              {loginStatus === 'checking' && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              {loginStatus === 'logged_in' && <User className="w-3.5 h-3.5" />}
              {loginStatus === 'logged_out' && <LogIn className="w-3.5 h-3.5" />}
              <span>
                {loginStatus === 'logged_in' ? (loginUserName || '已登录') : 
                 loginStatus === 'logged_out' ? '点击登录' : '检查中'}
              </span>
            </button>
            
            {/* MCP 状态 */}
            <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-sm ${
              mcpStatus === 'connected' ? 'bg-green-900/50 text-green-400' :
              mcpStatus === 'disconnected' ? 'bg-red-50 text-red-600' :
              'bg-gray-100 text-gray-500'
            }`}>
              {mcpStatus === 'checking' && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              {mcpStatus === 'connected' && <CheckCircle2 className="w-3.5 h-3.5" />}
              {mcpStatus === 'disconnected' && <AlertCircle className="w-3.5 h-3.5" />}
              <span>MCP</span>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto p-4">
        {/* 状态面板 */}
        <div className="bg-white border border-gray-200 rounded-xl p-6 mb-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-4">
              {/* 运行状态指示器 */}
              <div className={`w-3 h-3 rounded-full ${
                autoStatus === 'running' ? 'bg-green-500 animate-pulse' :
                autoStatus === 'paused' ? 'bg-yellow-500' :
                autoStatus === 'error' ? 'bg-red-500' :
                'bg-gray-500'
              }`} />
              
              <div>
                <div className="text-lg font-semibold">
                  {autoStatus === 'idle' && '准备就绪'}
                  {autoStatus === 'running' && getPhaseText()}
                  {autoStatus === 'paused' && '已暂停'}
                  {autoStatus === 'error' && '出现错误'}
                </div>
                {autoStatus === 'running' && (
                  <div className="text-sm text-gray-500">
                    已完成 {cycleCount} 轮 · 发布 {publishedNotes.length} 篇
                  </div>
                )}
              </div>
            </div>

            {/* 控制按钮 */}
            <div className="flex items-center gap-2">
              {autoStatus === 'idle' && (
                <button
                  onClick={handleStart}
                  disabled={mcpStatus !== 'connected' || !topic.trim()}
                  className="flex items-center gap-2 px-6 py-2.5 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Play className="w-5 h-5" />
                  启动
                </button>
              )}
              
              {autoStatus === 'running' && (
                <button
                  onClick={handlePause}
                  className="flex items-center gap-2 px-4 py-2.5 bg-yellow-600 text-white rounded-lg font-medium hover:bg-yellow-700"
                >
                  <Pause className="w-5 h-5" />
                  暂停
                </button>
              )}
              
              {autoStatus === 'paused' && (
                <>
                  <button
                    onClick={handleResume}
                    className="flex items-center gap-2 px-4 py-2.5 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700"
                  >
                    <Play className="w-5 h-5" />
                    继续
                  </button>
                  <button
                    onClick={handleStop}
                    className="flex items-center gap-2 px-4 py-2.5 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700"
                  >
                    <Square className="w-5 h-5" />
                    停止
                  </button>
                </>
              )}
              
              {(autoStatus === 'running' || autoStatus === 'error') && (
                <button
                  onClick={handleStop}
                  className="flex items-center gap-2 px-4 py-2.5 bg-gray-100 text-gray-800 rounded-lg font-medium hover:bg-gray-200"
                >
                  <Square className="w-5 h-5" />
                  停止
                </button>
              )}
            </div>
          </div>

          {/* 配置区域 */}
          {showConfig && (
            <div className="border-t border-gray-200 pt-4 mt-4">
              <button
                onClick={() => setShowConfig(!showConfig)}
                className="flex items-center gap-2 text-gray-500 hover:text-gray-700 mb-3"
              >
                <Settings className="w-4 h-4" />
                配置
                {showConfig ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </button>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* 话题输入 */}
                <div>
                  <label className="block text-sm text-gray-600 mb-1.5">
                    创作话题 <span className="text-red-400">*</span>
                  </label>
                  <input
                    type="text"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="如：护肤、穿搭、美食探店..."
                    className="w-full px-4 py-2.5 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-100 focus:border-orange-500 outline-none"
                  />
                </div>

                {/* 发布间隔 */}
                <div>
                  <label className="block text-sm text-gray-600 mb-1.5">发布间隔（分钟）</label>
                  <input
                    type="number"
                    value={publishInterval}
                    onChange={(e) => setPublishInterval(Math.max(5, parseInt(e.target.value) || 30))}
                    min={5}
                    className="w-full px-4 py-2.5 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-100 focus:border-orange-500 outline-none"
                  />
                </div>

                {/* 素材/参考信息 */}
                <div className="md:col-span-2">
                  <label className="block text-sm text-gray-600 mb-1.5">
                    素材/参考信息 <span className="text-gray-500 text-xs">（可选，产品信息、卖点等）</span>
                  </label>
                  <textarea
                    value={materialText}
                    onChange={(e) => setMaterialText(e.target.value)}
                    placeholder="粘贴产品资料、品牌信息、个人经历等，AI会参考这些内容创作..."
                    rows={3}
                    className="w-full px-4 py-2.5 bg-white border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-100 focus:border-orange-500 outline-none resize-none"
                  />
                </div>

                {/* 优化目标 */}
                <div className="md:col-span-2">
                  <label className="block text-sm text-gray-600 mb-1.5">优化目标</label>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(goalLabels).map(([value, label]) => (
                      <button
                        key={value}
                        onClick={() => setGoals(prev => 
                          prev.includes(value) ? prev.filter(g => g !== value) : [...prev, value]
                        )}
                        className={`px-4 py-2 rounded-lg text-sm transition-all ${
                          goals.includes(value)
                            ? 'bg-orange-600 text-white'
                            : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                        }`}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* 自动发布开关 */}
                <div className="md:col-span-2">
                  <label className="flex items-center gap-3 cursor-pointer">
                    <div 
                      onClick={() => setAutoPublish(!autoPublish)}
                      className={`w-12 h-6 rounded-full transition-colors cursor-pointer ${autoPublish ? 'bg-orange-600' : 'bg-gray-600'}`}
                    >
                      <div className={`w-5 h-5 rounded-full bg-white mt-0.5 transition-transform ${autoPublish ? 'translate-x-6' : 'translate-x-0.5'}`} />
                    </div>
                    <span className="text-sm text-gray-700">自动发布到小红书</span>
                  </label>
                </div>
                
                {/* P0 智能优化功能开关 */}
                <div className="md:col-span-2 mt-2 pt-4 border-t border-gray-200">
                  <h4 className="text-sm text-gray-600 mb-3 flex items-center gap-2">
                    <Zap className="w-4 h-4 text-yellow-500" />
                    智能优化功能
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    {/* 学习引擎 */}
                    <label className="flex items-center gap-3 cursor-pointer bg-gray-50 border border-gray-200 p-3 rounded-lg hover:bg-gray-100 transition-colors">
                      <div 
                        onClick={() => setUseLearning(!useLearning)}
                        className={`w-10 h-5 rounded-full transition-colors cursor-pointer ${useLearning ? 'bg-purple-600' : 'bg-gray-600'}`}
                      >
                        <div className={`w-4 h-4 rounded-full bg-white mt-0.5 transition-transform ${useLearning ? 'translate-x-5' : 'translate-x-0.5'}`} />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-1.5">
                          <Brain className="w-3.5 h-3.5 text-purple-400" />
                          <span className="text-sm text-gray-800">学习引擎</span>
                        </div>
                        <span className="text-xs text-gray-500">从发布效果中学习</span>
                      </div>
                    </label>
                    
                    {/* 多样性控制 */}
                    <label className="flex items-center gap-3 cursor-pointer bg-gray-50 border border-gray-200 p-3 rounded-lg hover:bg-gray-100 transition-colors">
                      <div 
                        onClick={() => setCheckDiversity(!checkDiversity)}
                        className={`w-10 h-5 rounded-full transition-colors cursor-pointer ${checkDiversity ? 'bg-blue-600' : 'bg-gray-600'}`}
                      >
                        <div className={`w-4 h-4 rounded-full bg-white mt-0.5 transition-transform ${checkDiversity ? 'translate-x-5' : 'translate-x-0.5'}`} />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-1.5">
                          <Shuffle className="w-3.5 h-3.5 text-blue-400" />
                          <span className="text-sm text-gray-800">去重机制</span>
                        </div>
                        <span className="text-xs text-gray-500">避免重复内容</span>
                      </div>
                    </label>
                    
                    {/* AI检测规避 */}
                    <label className="flex items-center gap-3 cursor-pointer bg-gray-50 border border-gray-200 p-3 rounded-lg hover:bg-gray-100 transition-colors">
                      <div 
                        onClick={() => setUseHumanize(!useHumanize)}
                        className={`w-10 h-5 rounded-full transition-colors cursor-pointer ${useHumanize ? 'bg-green-600' : 'bg-gray-600'}`}
                      >
                        <div className={`w-4 h-4 rounded-full bg-white mt-0.5 transition-transform ${useHumanize ? 'translate-x-5' : 'translate-x-0.5'}`} />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-1.5">
                          <Shield className="w-3.5 h-3.5 text-green-400" />
                          <span className="text-sm text-gray-800">降AI味</span>
                        </div>
                        <span className="text-xs text-gray-500">更像真人写作</span>
                      </div>
                    </label>
                  </div>
                  
                  {/* P0 统计面板 */}
                  {(learningStats || diversityStats || humannessScore !== null) && (
                    <div className="mt-3 p-3 bg-gray-50 border border-gray-200 rounded-lg">
                      <div className="grid grid-cols-3 gap-3 text-center">
                        {learningStats && (
                          <div>
                            <div className="text-lg font-bold text-purple-400">{learningStats.total_records || 0}</div>
                            <div className="text-xs text-gray-500">已学习内容</div>
                          </div>
                        )}
                        {diversityStats && (
                          <div>
                            <div className="text-lg font-bold text-blue-400">{diversityStats.unique_tags || 0}</div>
                            <div className="text-xs text-gray-500">已用标签数</div>
                          </div>
                        )}
                        {humannessScore !== null && (
                          <div>
                            <div className={`text-lg font-bold ${humannessScore >= 70 ? 'text-green-400' : humannessScore >= 50 ? 'text-yellow-400' : 'text-red-400'}`}>
                              {humannessScore}
                            </div>
                            <div className="text-xs text-gray-500">人味评分</div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* 左侧：运行日志 */}
          <div className="lg:col-span-2 bg-white border border-gray-200 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-medium flex items-center gap-2">
                <Clock className="w-4 h-4 text-orange-500" />
                运行日志
              </h3>
              {logs.length > 0 && (
                <button onClick={() => setLogs([])} className="text-xs text-gray-500 hover:text-gray-700">
                  清空
                </button>
              )}
            </div>
            
            <div 
              ref={logRef}
              className="font-mono text-sm text-gray-700 space-y-1 h-64 overflow-y-auto bg-gray-50 border border-gray-200 rounded-lg p-3"
            >
              {logs.length === 0 ? (
                <div className="text-gray-500 text-center py-8">
                  启动后将显示运行日志
                </div>
              ) : (
                logs.map((log, i) => (
                  <div key={i} className={
                    log.includes('✓') ? 'text-green-400' :
                    log.includes('✗') || log.includes('⚠') ? 'text-yellow-400' :
                    log.includes('━') ? 'text-orange-400 font-bold' :
                    ''
                  }>{log}</div>
                ))
              )}
            </div>

            {/* 当前生成的内容预览 - 小红书风格卡片 */}
            {currentContent && (
              <div className="mt-4 p-4 bg-gray-50 border border-gray-200 rounded-lg">
                <h4 className="text-sm text-gray-600 mb-3 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-orange-500" />
                  最新生成 · 小红书预览
                </h4>
                
                {/* 小红书风格详情卡片 */}
                <div className="bg-white rounded-xl overflow-hidden max-w-md mx-auto shadow-lg">
                  {/* 封面图 */}
                  <div className="aspect-square bg-gray-100 relative">
                    {currentImage ? (
                      <img src={currentImage} alt="封面" className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex flex-col items-center justify-center text-gray-400">
                        <Loader2 className="w-8 h-8 animate-spin mb-2" />
                        <span className="text-sm">生成封面中...</span>
                      </div>
                    )}
                  </div>
                  
                  {/* 内容区域 */}
                  <div className="p-4">
                    {/* 标题 */}
                    <h3 className="font-bold text-gray-900 text-lg leading-tight mb-3">
                      {currentContent.title}
                    </h3>
                    
                    {/* 完整正文 - 可滚动 */}
                    <div className="max-h-48 overflow-y-auto mb-3 pr-1">
                      <p className="text-gray-700 text-sm whitespace-pre-wrap leading-relaxed">
                        {currentContent.body}
                      </p>
                    </div>
                    
                    {/* 标签 */}
                    <div className="flex flex-wrap gap-1.5 mb-4">
                      {currentContent.tags?.map((tag, i) => (
                        <span key={i} className="text-xs text-[#ff2442] bg-red-50 px-2 py-1 rounded-full">
                          #{tag}
                        </span>
                      ))}
                    </div>
                    
                    {/* 底部互动栏 */}
                    <div className="flex items-center justify-between pt-3 border-t border-gray-100">
                      <div className="flex items-center gap-6">
                        <button className="flex items-center gap-1.5 text-gray-500 hover:text-[#ff2442]">
                          <ThumbsUp className="w-5 h-5" />
                          <span className="text-sm">点赞</span>
                        </button>
                        <button className="flex items-center gap-1.5 text-gray-500 hover:text-[#ff2442]">
                          <Bookmark className="w-5 h-5" />
                          <span className="text-sm">收藏</span>
                        </button>
                        <button className="flex items-center gap-1.5 text-gray-500 hover:text-[#ff2442]">
                          <MessageCircle className="w-5 h-5" />
                          <span className="text-sm">评论</span>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* 右侧：数据统计 */}
          <div className="space-y-4">
            {/* 总数据 */}
            <div className="bg-white border border-gray-200 rounded-xl p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-medium flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-orange-500" />
                  总数据
                </h3>
                <button
                  onClick={refreshAllStats}
                  className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
              </div>
              
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold text-orange-500">{publishedNotes.length}</div>
                  <div className="text-xs text-gray-400">已发布</div>
                </div>
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold">{totalStats.likes}</div>
                  <div className="text-xs text-gray-400 flex items-center justify-center gap-1">
                    <ThumbsUp className="w-3 h-3" /> 点赞
                  </div>
                </div>
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold">{totalStats.collects}</div>
                  <div className="text-xs text-gray-400 flex items-center justify-center gap-1">
                    <Bookmark className="w-3 h-3" /> 收藏
                  </div>
                </div>
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-center">
                  <div className="text-2xl font-bold">{totalStats.views}</div>
                  <div className="text-xs text-gray-400 flex items-center justify-center gap-1">
                    <Eye className="w-3 h-3" /> 浏览
                  </div>
                </div>
              </div>
            </div>

            {/* 发布历史 */}
            <div className="bg-white border border-gray-200 rounded-xl p-4">
              <h3 className="font-medium flex items-center gap-2 mb-3">
                <TrendingUp className="w-4 h-4 text-orange-500" />
                最近发布
              </h3>
              
              {publishedNotes.length === 0 ? (
                <div className="text-center py-6 text-gray-500">
                  <Sparkles className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">启动后自动发布</p>
                </div>
              ) : (
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {publishedNotes.slice(0, 10).map(note => (
                    <div 
                      key={note.id} 
                      className="p-3 bg-gray-50 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-100"
                      onClick={() => refreshNoteStats(note)}
                    >
                      <div className="text-sm font-medium truncate">{note.content.title}</div>
                      <div className="flex items-center gap-3 mt-1.5 text-xs text-gray-400">
                        <span className="flex items-center gap-1">
                          <ThumbsUp className="w-3 h-3" />{note.stats?.likes || 0}
                        </span>
                        <span className="flex items-center gap-1">
                          <Bookmark className="w-3 h-3" />{note.stats?.collects || 0}
                        </span>
                        <span className="flex items-center gap-1">
                          <MessageCircle className="w-3 h-3" />{note.stats?.comments || 0}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
