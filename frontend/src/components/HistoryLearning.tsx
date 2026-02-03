import { useState, useEffect } from 'react'
import {
  BookOpen, User, RefreshCw,
  Loader2, FileText, Clock, Sparkles,
  ChevronDown, ChevronUp, Download
} from 'lucide-react'
import {
  getHistoryStats, getUserProfile, getHistoryPosts, analyzeHistory,
  importHistoryFromXHS, getStylePrompt, getMyNotes, getNoteStats,
  type HistoryPost, type UserProfile
} from '../services/api'

export default function HistoryLearning() {
  const [stats, setStats] = useState<{
    total_posts: number
    analyzed_posts: number
    total_engagement: Record<string, number>
    avg_engagement: Record<string, number>
    profile_updated: string | null
    writing_tone: string
    top_tags: string[]
  } | null>(null)
  
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [posts, setPosts] = useState<HistoryPost[]>([])
  const [stylePrompt, setStylePrompt] = useState('')
  
  const [loading, setLoading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [importing, setImporting] = useState(false)
  
  const [showPosts, setShowPosts] = useState(false)
  const [showProfile, setShowProfile] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [statsData, profileData, promptData] = await Promise.all([
        getHistoryStats(),
        getUserProfile(),
        getStylePrompt()
      ])
      setStats(statsData)
      setProfile(profileData)
      setStylePrompt(promptData.prompt)
      
      // 加载最近发帖
      const postsData = await getHistoryPosts(10, 0, 'posted_at')
      setPosts(postsData.posts)
    } catch (e) {
      console.error('加载历史数据失败', e)
    }
    setLoading(false)
  }

  const handleAnalyze = async () => {
    setAnalyzing(true)
    try {
      const result = await analyzeHistory()
      setProfile(result.profile)
      await loadData()
    } catch (e) {
      console.error('分析失败', e)
    }
    setAnalyzing(false)
  }

  // 从MCP获取小红书账号的历史发帖并导入
  const handleImportFromAccount = async () => {
    setImporting(true)
    try {
      // 1. 调用MCP获取我的笔记列表
      const result = await getMyNotes(50)
      const text = result.result?.content?.[0]?.text || ''
      
      // 解析返回的笔记列表
      // MCP返回格式可能是JSON或文本，需要解析
      let notes: Array<Record<string, unknown>> = []
      
      try {
        // 尝试解析JSON
        const jsonMatch = text.match(/\[[\s\S]*\]/)
        if (jsonMatch) {
          notes = JSON.parse(jsonMatch[0])
        }
      } catch {
        // 如果不是JSON，尝试解析文本格式
        console.log('解析笔记列表:', text)
      }
      
      if (notes.length === 0) {
        // 尝试从文本中提取笔记信息
        const noteMatches = text.matchAll(/笔记ID[：:]\s*([^\s,，]+)/g)
        const titleMatches = text.matchAll(/标题[：:]\s*([^\n]+)/g)
        const noteIds = [...noteMatches].map(m => m[1])
        const titles = [...titleMatches].map(m => m[1])
        
        if (noteIds.length > 0) {
          // 获取每个笔记的详细信息
          for (let i = 0; i < Math.min(noteIds.length, 20); i++) {
            try {
              const detail = await getNoteStats(noteIds[i])
              const detailText = detail.result?.content?.[0]?.text || ''
              
              // 解析笔记详情
              const note: Record<string, unknown> = {
                note_id: noteIds[i],
                title: titles[i] || '未知标题',
                desc: '',
                likes: 0,
                collects: 0,
                comments: 0
              }
              
              // 尝试提取正文和互动数据
              const descMatch = detailText.match(/正文[：:]\s*([\s\S]*?)(?=点赞|收藏|$)/)
              if (descMatch) note.desc = descMatch[1].trim()
              
              const likesMatch = detailText.match(/点赞[：:]\s*(\d+)/)
              if (likesMatch) note.likes = parseInt(likesMatch[1])
              
              const collectsMatch = detailText.match(/收藏[：:]\s*(\d+)/)
              if (collectsMatch) note.collects = parseInt(collectsMatch[1])
              
              const commentsMatch = detailText.match(/评论[：:]\s*(\d+)/)
              if (commentsMatch) note.comments = parseInt(commentsMatch[1])
              
              notes.push(note)
            } catch (e) {
              console.error('获取笔记详情失败:', noteIds[i], e)
            }
          }
        }
      }
      
      if (notes.length > 0) {
        // 2. 导入到历史学习系统
        const importResult = await importHistoryFromXHS(notes)
        alert(`成功导入 ${importResult.imported_count} 条历史发帖！`)
        await loadData()
      } else {
        alert('未能获取到笔记列表，请确保已登录小红书账号')
      }
    } catch (e) {
      console.error('导入失败', e)
      alert('导入失败，请确保已登录小红书账号')
    }
    setImporting(false)
  }

  const toneLabels: Record<string, string> = {
    casual: '轻松随意',
    cute: '可爱俏皮',
    professional: '专业严谨',
    neutral: '自然平实'
  }

  const paragraphLabels: Record<string, string> = {
    short: '短段落',
    medium: '中等段落',
    long: '长段落',
    mixed: '混合风格'
  }

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-xl p-4 flex items-center justify-center h-48">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    )
  }

  return (
    <div className="bg-gray-800 rounded-xl p-4">
      {/* 头部 */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-purple-500" />
          <h3 className="font-semibold">历史发帖学习</h3>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleImportFromAccount}
            disabled={importing}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm transition-colors disabled:opacity-50"
            title="从已登录的小红书账号导入历史发帖"
          >
            {importing ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Download className="w-4 h-4" />
            )}
            导入账号
          </button>
          <button
            onClick={handleAnalyze}
            disabled={analyzing || !stats || stats.total_posts < 3}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-500 hover:bg-purple-600 rounded-lg text-sm transition-colors disabled:opacity-50"
          >
            {analyzing ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4" />
            )}
            分析风格
          </button>
        </div>
      </div>

      {/* 统计概览 */}
      {stats && (
        <div className="grid grid-cols-4 gap-3 mb-4">
          <div className="bg-gray-700 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-purple-400">{stats.total_posts}</div>
            <div className="text-xs text-gray-400">历史发帖</div>
          </div>
          <div className="bg-gray-700 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-orange-400">{stats.total_engagement.likes}</div>
            <div className="text-xs text-gray-400">总点赞</div>
          </div>
          <div className="bg-gray-700 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-yellow-400">{stats.total_engagement.collects}</div>
            <div className="text-xs text-gray-400">总收藏</div>
          </div>
          <div className="bg-gray-700 rounded-lg p-3 text-center">
            <div className="text-2xl font-bold text-blue-400">{stats.total_engagement.comments}</div>
            <div className="text-xs text-gray-400">总评论</div>
          </div>
        </div>
      )}

      {/* 写作风格 */}
      {profile && profile.last_updated && (
        <div className="mb-4">
          <button
            onClick={() => setShowProfile(!showProfile)}
            className="flex items-center justify-between w-full p-3 bg-gray-700 rounded-lg hover:bg-gray-600 transition-colors"
          >
            <div className="flex items-center gap-2">
              <User className="w-4 h-4 text-purple-400" />
              <span className="text-sm font-medium">你的写作风格</span>
              <span className={`text-xs px-2 py-0.5 rounded ${
                profile.writing_style.tone === 'cute' ? 'bg-pink-500/30 text-pink-400' :
                profile.writing_style.tone === 'casual' ? 'bg-green-500/30 text-green-400' :
                profile.writing_style.tone === 'professional' ? 'bg-blue-500/30 text-blue-400' :
                'bg-gray-600 text-gray-400'
              }`}>
                {toneLabels[profile.writing_style.tone] || profile.writing_style.tone}
              </span>
            </div>
            {showProfile ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
          
          {showProfile && (
            <div className="mt-2 p-3 bg-gray-700/50 rounded-lg space-y-3">
              {/* 风格指标 */}
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">段落风格</span>
                  <span>{paragraphLabels[profile.writing_style.paragraph_style]}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">emoji密度</span>
                  <span>{profile.writing_style.emoji_density.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">平均标题长度</span>
                  <span>{Math.round(profile.writing_style.avg_title_length)} 字</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">平均正文长度</span>
                  <span>{Math.round(profile.writing_style.avg_body_length)} 字</span>
                </div>
              </div>
              
              {/* 常用标签 */}
              {profile.content_preferences.favorite_tags.length > 0 && (
                <div>
                  <div className="text-xs text-gray-400 mb-1.5">常用标签</div>
                  <div className="flex flex-wrap gap-1">
                    {profile.content_preferences.favorite_tags.slice(0, 8).map(tag => (
                      <span key={tag} className="text-xs bg-gray-600 text-gray-300 px-2 py-0.5 rounded">
                        #{tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              {/* 效果优化建议 */}
              {profile.performance_insights.optimal_title_length > 0 && (
                <div className="p-2 bg-purple-500/10 border border-purple-500/30 rounded-lg">
                  <div className="flex items-center gap-1.5 text-xs text-purple-400 mb-1">
                    <Sparkles className="w-3.5 h-3.5" />
                    效果优化建议
                  </div>
                  <ul className="text-xs text-gray-300 space-y-0.5">
                    <li>• 标题 {profile.performance_insights.optimal_title_length} 字左右效果最好</li>
                    {profile.performance_insights.best_performing_tags.length > 0 && (
                      <li>• 高效果标签：{profile.performance_insights.best_performing_tags.slice(0, 3).join('、')}</li>
                    )}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* 风格提示词 */}
      {stylePrompt && (
        <div className="mb-4 p-3 bg-gradient-to-r from-purple-500/10 to-pink-500/10 border border-purple-500/30 rounded-lg">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="w-4 h-4 text-purple-400" />
            <span className="text-sm font-medium text-purple-400">AI 生成时将应用以下风格</span>
          </div>
          <pre className="text-xs text-gray-300 whitespace-pre-wrap font-mono leading-relaxed">
            {stylePrompt}
          </pre>
        </div>
      )}

      {/* 最近发帖 */}
      <div>
        <button
          onClick={() => setShowPosts(!showPosts)}
          className="flex items-center justify-between w-full p-3 bg-gray-700 rounded-lg hover:bg-gray-600 transition-colors"
        >
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-gray-400" />
            <span className="text-sm font-medium">最近发帖</span>
            <span className="text-xs text-gray-500">({posts.length})</span>
          </div>
          {showPosts ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
        
        {showPosts && (
          <div className="mt-2 space-y-2 max-h-[300px] overflow-y-auto">
            {posts.length === 0 ? (
              <div className="text-center py-6 text-gray-500 text-sm">
                暂无历史发帖记录
                <p className="mt-1">点击「导入账号」从小红书获取历史数据</p>
              </div>
            ) : (
              posts.map(post => (
                <div key={post.note_id} className="p-3 bg-gray-700/50 rounded-lg">
                  <div className="font-medium text-sm mb-1 line-clamp-1">{post.title}</div>
                  <p className="text-xs text-gray-400 line-clamp-2 mb-2">{post.body}</p>
                  <div className="flex items-center justify-between text-xs text-gray-500">
                    <div className="flex items-center gap-3">
                      <span>👍 {post.performance.likes || 0}</span>
                      <span>🔖 {post.performance.collects || 0}</span>
                      <span>💬 {post.performance.comments || 0}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {new Date(post.posted_at).toLocaleDateString()}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* 空状态提示 */}
      {stats && stats.total_posts < 3 && (
        <div className="mt-4 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
          <p className="text-xs text-yellow-400">
            💡 至少需要 3 条历史发帖才能分析你的写作风格。点击「导入账号」从小红书获取历史数据。
          </p>
        </div>
      )}
    </div>
  )
}
