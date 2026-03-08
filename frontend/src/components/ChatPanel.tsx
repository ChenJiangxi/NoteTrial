import React, { useState, useRef, useEffect } from 'react'
import { Send, Sparkles, Loader2, Image, X } from 'lucide-react'
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
  const [selectedImages, setSelectedImages] = useState<string[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if ((!input.trim() && selectedImages.length === 0) || isLoading) return

    const userMessage: ChatMessage = { 
      role: 'user', 
      content: input.trim() || '（发送了图片）',
      images: selectedImages.length > 0 ? selectedImages : undefined
    }
    addMessage(userMessage)
    setInput('')
    setSelectedImages([])
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
              {msg.images && msg.images.length > 0 && (
                <div className="mb-2 flex flex-wrap gap-2">
                  {msg.images.map((img, imgIdx) => (
                    <img
                      key={imgIdx}
                      src={img}
                      alt="上传的图片"
                      className="max-w-[200px] max-h-[200px] rounded-lg object-cover"
                    />
                  ))}
                </div>
              )}
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
        {/* 图片预览 */}
        {selectedImages.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-2">
            {selectedImages.map((img, idx) => (
              <div key={idx} className="relative group">
                <img
                  src={img}
                  alt={`预览 ${idx + 1}`}
                  className="w-20 h-20 rounded-lg object-cover border border-gray-200"
                />
                <button
                  onClick={() => setSelectedImages(selectedImages.filter((_, i) => i !== idx))}
                  className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        )}
        <div className="flex gap-3 items-end">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            multiple
            onChange={(e) => {
              const files = e.target.files
              if (files) {
                Array.from(files).forEach((file) => {
                  const reader = new FileReader()
                  reader.onload = (e) => {
                    const result = e.target?.result as string
                    setSelectedImages((prev) => [...prev, result])
                  }
                  reader.readAsDataURL(file)
                })
              }
              e.target.value = ''
            }}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="bg-white border border-gray-200 text-gray-600 p-3.5 rounded-xl hover:bg-gray-50 hover:border-xhs-red transition-all"
            title="上传图片"
          >
            <Image className="w-5 h-5" />
          </button>
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
            disabled={(!input.trim() && selectedImages.length === 0) || isLoading}
            className="bg-gradient-to-br from-xhs-red to-pink-500 text-white p-3.5 rounded-xl hover:shadow-lg hover:shadow-red-200/50 transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  )
}
