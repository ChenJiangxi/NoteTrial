import React, { useState } from 'react'
import {
  Play,
  Loader2,
  ThumbsUp,
  Bookmark,
  MessageCircle,
  Share2,
  TrendingUp,
  AlertCircle,
  Lightbulb,
  Users,
  ChevronDown,
  ChevronUp,
  Send,
  CheckCircle2,
} from 'lucide-react'
import type { ContentItem, TaskSpec, MultiCrowdTestResult, StatisticalConfidence } from '../types/api'
import { runCrowdTest, publishContent } from '../services/api'

interface CrowdTestPanelProps {
  taskSpec: TaskSpec | null
  contentA: ContentItem
  contentB: ContentItem
}

export default function CrowdTestPanel({ taskSpec, contentA, contentB }: CrowdTestPanelProps) {
  const [isRunning, setIsRunning] = useState(false)
  const [result, setResult] = useState<MultiCrowdTestResult | null>(null)
  const [maxUsers, setMaxUsers] = useState(20)
  const [showPersonas, setShowPersonas] = useState(false)
  const [isPublishing, setIsPublishing] = useState(false)
  const [publishSuccess, setPublishSuccess] = useState(false)

  const canRun = taskSpec && contentA.title && contentA.body && contentB.title && contentB.body
  const emptyScore = { like_count: 0, save_count: 0, comment_count: 0, share_count: 0, total: 0 }
  const scoreA = result?.version_scores.find(v => v.label === 'Version A')?.score ?? emptyScore
  const scoreB = result?.version_scores.find(v => v.label === 'Version B')?.score ?? emptyScore
  const winnerLabel = result?.overall_confidence.winner || '-'

  const handleRunTest = async () => {
    if (!canRun || !taskSpec) return

    setIsRunning(true)
    setResult(null)
    setPublishSuccess(false)

    try {
      const testResult = await runCrowdTest({
        task_spec: taskSpec,
        versions: [
          { label: 'Version A', content: contentA },
          { label: 'Version B', content: contentB },
        ],
        max_users: maxUsers,
      })
      setResult(testResult)
    } catch (error) {
      console.error('测试执行失败:', error)
    } finally {
      setIsRunning(false)
    }
  }

  const handlePublish = async (version: 'A' | 'B') => {
    const contentToPublish = version === 'A' ? contentA : contentB
    
    setIsPublishing(true)
    try {
      // 调用真实的发布API
      const result = await publishContent(contentToPublish)
      
      if (result.success) {
        setPublishSuccess(true)
        alert(`✅ 发布成功！\n笔记ID: ${result.note_id || '未知'}\n\n请到小红书查看您的笔记`)
        
        // 3秒后重置状态
        setTimeout(() => {
          setPublishSuccess(false)
        }, 3000)
      } else {
        alert(`❌ 发布失败\n${result.message || '未知错误'}\n\n请检查：\n1. 是否已登录小红书\n2. 内容是否符合规范\n3. 网络连接是否正常`)
      }
      
      console.log('发布结果:', result)
    } catch (error: any) {
      console.error('发布失败:', error)
      const errorMsg = error.response?.data?.detail || error.message || '未知错误'
      
      if (errorMsg.includes('未登录') || errorMsg.includes('401')) {
        alert('❌ 未登录小红书\n\n请先在MCP Inspector中登录小红书账号')
      } else {
        alert(`❌ 发布失败\n${errorMsg}`)
      }
    } finally {
      setIsPublishing(false)
    }
  }

  const MetricCard = ({
    icon: Icon,
    label,
    scoreA,
    scoreB,
    confidence,
    iconColor,
  }: {
    icon: React.ElementType
    label: string
    scoreA: number
    scoreB: number
    confidence: StatisticalConfidence
    iconColor: string
  }) => {
    const total = scoreA + scoreB
    const percentA = total > 0 ? (scoreA / total) * 100 : 50
    const percentB = total > 0 ? (scoreB / total) * 100 : 50

    return (
      <div className="bg-gray-50 rounded-lg p-3">
        <div className="flex items-center gap-2 mb-2">
          <Icon className={`w-4 h-4 ${iconColor}`} />
          <span className="text-sm font-medium text-gray-700">{label}</span>
        </div>
        <div className="flex items-center gap-2 mb-2">
          <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden flex">
            <div
              className="h-full bg-red-400 transition-all duration-500"
              style={{ width: `${percentA}%` }}
            />
            <div
              className="h-full bg-blue-400 transition-all duration-500"
              style={{ width: `${percentB}%` }}
            />
          </div>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-red-600">A: {scoreA}</span>
          <span className="text-blue-600">B: {scoreB}</span>
        </div>
        {confidence.winner !== '-' && (
          <p className="text-xs text-gray-500 mt-1 text-center">
            {confidence.winner} 胜出 ({confidence.confidence.toFixed(1)}% 置信度)
          </p>
        )}
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg shadow-gray-200/50 border border-white/50 overflow-hidden">
      {/* 头部 */}
      <div className="flex-shrink-0 px-5 py-4 border-b border-gray-100/50 bg-gradient-to-r from-purple-50/50 to-blue-50/50">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-blue-500 rounded-lg flex items-center justify-center">
            <Users className="w-4 h-4 text-white" />
          </div>
          <div>
            <h2 className="font-semibold text-gray-800">CrowdTest</h2>
            <p className="text-xs text-gray-500">模拟真实用户的互动反应</p>
          </div>
        </div>
      </div>

      {/* 控制区 */}
      <div className="flex-shrink-0 px-4 py-4 border-b border-gray-100/50">
        <div className="space-y-3">
          <div>
            <label className="text-xs text-gray-500 block mb-1.5">模拟用户数</label>
            <input
              type="number"
              value={maxUsers}
              onChange={(e) => setMaxUsers(Math.min(100, Math.max(5, parseInt(e.target.value) || 20)))}
              min={5}
              max={100}
              step={5}
              className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm bg-white"
            />
          </div>
          <button
            onClick={handleRunTest}
            disabled={!canRun || isRunning}
            className="w-full btn-gradient px-4 py-3 flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {isRunning ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                测试中...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                开始测试
              </>
            )}
          </button>
        </div>
        {!canRun && (
          <p className="text-xs text-amber-600 mt-3 flex items-center gap-1.5 bg-amber-50 px-3 py-2 rounded-lg">
            <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
            请先完成对话设定任务，并填写 A/B 两个版本的内容
          </p>
        )}
      </div>

      {/* 结果区 */}
      <div className="flex-1 min-h-0 overflow-y-auto p-4">
        {!result && !isRunning && (
          <div className="h-full flex items-center justify-center text-center">
            <div className="animate-float">
              <div className="w-16 h-16 mx-auto bg-gradient-to-br from-gray-100 to-gray-50 rounded-2xl flex items-center justify-center mb-4">
                <Users className="w-8 h-8 text-gray-300" />
              </div>
              <p className="text-gray-500 text-sm font-medium">点击开始测试</p>
              <p className="text-gray-400 text-xs mt-1.5">AI 将模拟多个用户画像评估你的内容</p>
            </div>
          </div>
        )}

        {isRunning && (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <div className="relative w-16 h-16 mx-auto mb-4">
                <div className="absolute inset-0 bg-gradient-to-br from-xhs-red/20 to-pink-500/20 rounded-full animate-ping" />
                <div className="relative w-16 h-16 bg-gradient-to-br from-xhs-red to-pink-500 rounded-full flex items-center justify-center">
                  <Loader2 className="w-8 h-8 animate-spin text-white" />
                </div>
              </div>
              <p className="text-gray-700 font-medium">正在模拟用户反应...</p>
              <p className="text-gray-400 text-sm mt-1.5">这可能需要一些时间</p>
            </div>
          </div>
        )}

        {result && (
          <div className="space-y-4">
            {/* 总体结果 */}
            <div className="bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50 rounded-2xl p-5 border border-purple-100/50">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-gray-800 flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-purple-500" />
                  总体结果
                </h3>
                <span
                  className={`px-4 py-1.5 rounded-full text-sm font-semibold shadow-sm ${
                    result.overall_confidence.winner === 'A'
                      ? 'bg-gradient-to-r from-red-500 to-pink-500 text-white'
                      : result.overall_confidence.winner === 'B'
                      ? 'bg-gradient-to-r from-blue-500 to-indigo-500 text-white'
                      : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {result.overall_confidence.winner === '-'
                    ? '势均力敌'
                    : `版本 ${result.overall_confidence.winner} 胜出`}
                </span>
              </div>
              <p className="text-sm text-gray-600 mb-4">
                置信度: <span className="font-semibold text-purple-600">{result.overall_confidence.confidence.toFixed(1)}%</span>
              </p>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-white/80 rounded-xl p-4 text-center border border-red-100">
                  <p className="text-xs text-gray-500 mb-1">版本 A 总互动</p>
                  <p className="text-3xl font-bold text-red-500">{scoreA.total}</p>
                </div>
                <div className="bg-white/80 rounded-xl p-4 text-center border border-blue-100">
                  <p className="text-xs text-gray-500 mb-1">版本 B 总互动</p>
                  <p className="text-3xl font-bold text-blue-500">{scoreB.total}</p>
                </div>
              </div>
            </div>

            {/* 各维度分数 */}
            <div className="grid grid-cols-2 gap-3">
              <MetricCard
                icon={ThumbsUp}
                label="点赞"
                scoreA={scoreA.like_count}
                scoreB={scoreB.like_count}
                confidence={result.like_confidence}
                iconColor="text-pink-500"
              />
              <MetricCard
                icon={Bookmark}
                label="收藏"
                scoreA={scoreA.save_count}
                scoreB={scoreB.save_count}
                confidence={result.save_confidence}
                iconColor="text-yellow-500"
              />
              <MetricCard
                icon={MessageCircle}
                label="评论"
                scoreA={scoreA.comment_count}
                scoreB={scoreB.comment_count}
                confidence={result.comment_confidence}
                iconColor="text-blue-500"
              />
              <MetricCard
                icon={Share2}
                label="分享"
                scoreA={scoreA.share_count}
                scoreB={scoreB.share_count}
                confidence={result.share_confidence}
                iconColor="text-green-500"
              />
            </div>

            {/* 诊断解释 */}
            {result.diagnosis.length > 0 && (
              <div className="bg-amber-50 rounded-xl p-4">
                <h3 className="font-semibold text-gray-800 flex items-center gap-2 mb-3">
                  <AlertCircle className="w-5 h-5 text-amber-500" />
                  诊断分析
                </h3>
                <ul className="space-y-2">
                  {result.diagnosis.map((item, idx) => (
                    <li key={idx} className="text-sm text-gray-700 flex items-start gap-2">
                      <span className="text-amber-500 mt-0.5">•</span>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* 改写建议 */}
            {result.suggestions.length > 0 && (
              <div className="bg-green-50 rounded-xl p-4">
                <h3 className="font-semibold text-gray-800 flex items-center gap-2 mb-3">
                  <Lightbulb className="w-5 h-5 text-green-500" />
                  改写建议
                </h3>
                <ul className="space-y-2">
                  {result.suggestions.map((item, idx) => (
                    <li key={idx} className="text-sm text-gray-700">
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Persona 详情（可折叠） */}
            <div className="border border-gray-200 rounded-xl overflow-hidden">
              <button
                onClick={() => setShowPersonas(!showPersonas)}
                className="w-full px-4 py-3 bg-gray-50 flex items-center justify-between hover:bg-gray-100 transition-colors"
              >
                <span className="font-medium text-gray-700 flex items-center gap-2">
                  <Users className="w-4 h-4" />
                  用户画像详情 ({result.persona_results.length})
                </span>
                {showPersonas ? (
                  <ChevronUp className="w-5 h-5 text-gray-400" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-gray-400" />
                )}
              </button>
              {showPersonas && (
                <div className="p-4 space-y-3 max-h-64 overflow-y-auto">
                  {result.persona_results.map((persona, idx) => (
                    <div key={idx} className="bg-gray-50 rounded-lg p-3">
                      <div className="flex items-start justify-between mb-2">
                        <p className="text-sm font-medium text-gray-700">
                          {persona.persona_description}
                        </p>
                        <span
                          className={`px-2 py-0.5 rounded text-xs ${
                            persona.version_preference === 'A'
                              ? 'bg-red-100 text-red-600'
                              : 'bg-blue-100 text-blue-600'
                          }`}
                        >
                          偏好 {persona.version_preference}
                        </span>
                      </div>
                      <div className="flex gap-3 text-xs text-gray-500 mb-2">
                        {persona.like && <span>👍 点赞</span>}
                        {persona.save && <span>⭐ 收藏</span>}
                        {persona.comment && <span>💬 评论</span>}
                        {persona.share && <span>🔄 分享</span>}
                      </div>
                      <p className="text-xs text-gray-600 italic">"{persona.reasoning}"</p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* 发布按钮 */}
            <div className="bg-gradient-to-br from-xhs-red via-pink-500 to-rose-500 rounded-2xl p-5 shadow-lg shadow-red-200/50">
              <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
                <Send className="w-5 h-5" />
                准备发布
              </h3>
              <p className="text-xs text-white/80 mb-4">
                选择测试效果更好的版本发布到小红书
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => handlePublish('A')}
                  disabled={isPublishing}
                  className="flex-1 bg-white text-gray-800 px-4 py-3 rounded-xl font-medium hover:bg-gray-50 hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {isPublishing ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : publishSuccess ? (
                    <>
                      <CheckCircle2 className="w-4 h-4 text-green-500" />
                      已发布
                    </>
                  ) : (
                    <>发布版本 A</>
                  )}
                </button>
                <button
                  onClick={() => handlePublish('B')}
                  disabled={isPublishing}
                  className="flex-1 bg-white text-gray-800 px-4 py-3 rounded-xl font-medium hover:bg-gray-50 hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {isPublishing ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : publishSuccess ? (
                    <>
                      <CheckCircle2 className="w-4 h-4 text-green-500" />
                      已发布
                    </>
                  ) : (
                    <>发布版本 B</>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
