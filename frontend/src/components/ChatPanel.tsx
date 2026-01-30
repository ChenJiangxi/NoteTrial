import React, { useState, useRef, useEffect } from 'react'
import { Send, Sparkles, Loader2 } from 'lucide-react'
import type { ChatMessage, TaskSpec, ContentItem } from '../types/api'
import { sendChatMessage } from '../services/api'
import { useApp } from '../contexts/AppContext'

interface ChatPanelProps {
  onTaskSpecUpdate: (spec: TaskSpec) => void
  onContentGenerated: (content: ContentItem) => void
}

export default function ChatPanel({ onTaskSpecUpdate, onContentGenerated }: ChatPanelProps) {
  const { messages, addMessage } = useApp()
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: ChatMessage = { role: 'user', content: input.trim() }
    addMessage(userMessage)
    setInput('')
    setIsLoading(true)

    try {
      const response = await sendChatMessage({
        messages: [...messages, userMessage],
      })

      addMessage({ role: 'assistant', content: response.message })

      if (response.task_spec) {
        onTaskSpecUpdate(response.task_spec)
      }

      if (response.generated_content) {
        onContentGenerated(response.generated_content)
      }
    } catch (error) {
      addMessage({
        role: 'assistant',
        content: '抱歉，服务暂时不可用，请稍后重试。',
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="h-full flex flex-col bg-white/80 backdrop-blur-sm rounded-2xl shadow-lg shadow-gray-200/50 border border-white/50 overflow-hidden">
      {/* 头部 */}
      <div className="flex-shrink-0 px-5 py-4 border-b border-gray-100/50 bg-gradient-to-r from-red-50/50 to-pink-50/50">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 bg-gradient-to-br from-xhs-red to-pink-500 rounded-lg flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div>
            <h2 className="font-semibold text-gray-800">对话 / 任务定义</h2>
            <p className="text-xs text-gray-500">描述你的内容创意和目标受众</p>
          </div>
        </div>
      </div>

      {/* 消息列表 */}
      <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                msg.role === 'user'
                  ? 'bg-gradient-to-br from-xhs-red to-pink-500 text-white shadow-lg shadow-red-200/50'
                  : 'bg-gray-50 text-gray-700 border border-gray-100'
              }`}
            >
              <p className="text-sm whitespace-pre-wrap leading-relaxed">{msg.content}</p>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-50 rounded-2xl px-4 py-3 border border-gray-100">
              <div className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-xhs-red" />
                <span className="text-sm text-gray-500">思考中...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 输入框 */}
      <div className="flex-shrink-0 p-4 border-t border-gray-100/50 bg-gray-50/50">
        <div className="flex gap-3 items-end">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="描述你想创作的内容..."
            className="flex-1 resize-none border border-gray-200 rounded-xl px-4 py-3 text-sm bg-white focus:ring-2 focus:ring-xhs-red/10 focus:border-xhs-red transition-all"
            rows={2}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="bg-gradient-to-br from-xhs-red to-pink-500 text-white p-3.5 rounded-xl hover:shadow-lg hover:shadow-red-200/50 transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  )
}
