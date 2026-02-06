import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import type { TaskSpec, ContentItem, ChatMessage, MultiCrowdTestResult } from '../types/api'

// 历史记录类型
export interface HistoryRecord {
  id: string
  timestamp: number
  taskSpec: TaskSpec
  contentA: ContentItem
  contentB: ContentItem
  testResult?: MultiCrowdTestResult
  publishedVersion?: 'A' | 'B'
}

// 应用状态类型
interface AppState {
  // 当前会话
  taskSpec: TaskSpec | null
  contentA: ContentItem
  contentB: ContentItem
  messages: ChatMessage[]
  
  // 历史记录
  historyRecords: HistoryRecord[]
  
  // 方法
  setTaskSpec: (spec: TaskSpec | null) => void
  updateTaskSpec: (updates: Partial<TaskSpec>) => void
  setContentA: (content: ContentItem) => void
  setContentB: (content: ContentItem) => void
  setMessages: (messages: ChatMessage[]) => void
  addMessage: (message: ChatMessage) => void
  clearMessages: () => void
  
  // 历史记录操作
  saveToHistory: (testResult?: MultiCrowdTestResult, publishedVersion?: 'A' | 'B') => void
  loadFromHistory: (record: HistoryRecord) => void
  deleteHistory: (id: string) => void
  clearHistory: () => void
  
  // 重置当前会话
  resetSession: () => void
}

const defaultContent: ContentItem = {
  title: '',
  body: '',
  cover_image: '',
  tags: [],
}

const defaultMessages: ChatMessage[] = [
  {
    role: 'assistant',
    content: '👋 你好！我是 NoteTrial 助手。\n\n告诉我你想创作什么样的小红书内容，我会帮你定义测试目标并生成内容。\n\n例如：\n• 我想写一篇程序员副业的内容\n• 帮我写一篇美食探店笔记\n• 想测试一下护肤心得的文案\n\n你也可以点击下方📎上传产品资料文档。',
  },
]

// localStorage keys
const STORAGE_KEYS = {
  TASK_SPEC: 'notetrial_task_spec',
  CONTENT_A: 'notetrial_content_a',
  CONTENT_B: 'notetrial_content_b',
  MESSAGES: 'notetrial_messages',
  HISTORY: 'notetrial_history',
}

const AppContext = createContext<AppState | undefined>(undefined)

export function AppProvider({ children }: { children: ReactNode }) {
  // 从 localStorage 初始化状态
  const [taskSpec, setTaskSpecState] = useState<TaskSpec | null>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEYS.TASK_SPEC)
      return saved ? JSON.parse(saved) : null
    } catch {
      return null
    }
  })
  
  const [contentA, setContentAState] = useState<ContentItem>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEYS.CONTENT_A)
      return saved ? JSON.parse(saved) : defaultContent
    } catch {
      return defaultContent
    }
  })
  
  const [contentB, setContentBState] = useState<ContentItem>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEYS.CONTENT_B)
      return saved ? JSON.parse(saved) : defaultContent
    } catch {
      return defaultContent
    }
  })
  
  const [messages, setMessagesState] = useState<ChatMessage[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEYS.MESSAGES)
      return saved ? JSON.parse(saved) : defaultMessages
    } catch {
      return defaultMessages
    }
  })
  
  const [historyRecords, setHistoryRecords] = useState<HistoryRecord[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEYS.HISTORY)
      return saved ? JSON.parse(saved) : []
    } catch {
      return []
    }
  })
  
  // 自动保存到 localStorage
  useEffect(() => {
    if (taskSpec) {
      localStorage.setItem(STORAGE_KEYS.TASK_SPEC, JSON.stringify(taskSpec))
    } else {
      localStorage.removeItem(STORAGE_KEYS.TASK_SPEC)
    }
  }, [taskSpec])
  
  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.CONTENT_A, JSON.stringify(contentA))
  }, [contentA])
  
  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.CONTENT_B, JSON.stringify(contentB))
  }, [contentB])
  
  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.MESSAGES, JSON.stringify(messages))
  }, [messages])
  
  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.HISTORY, JSON.stringify(historyRecords))
  }, [historyRecords])
  
  // 方法实现
  const setTaskSpec = (spec: TaskSpec | null) => {
    setTaskSpecState(spec)
  }
  
  const updateTaskSpec = (updates: Partial<TaskSpec>) => {
    if (taskSpec) {
      setTaskSpecState({ ...taskSpec, ...updates })
    }
  }
  
  const setContentA = (content: ContentItem) => {
    setContentAState(content)
  }
  
  const setContentB = (content: ContentItem) => {
    setContentBState(content)
  }
  
  const setMessages = (msgs: ChatMessage[]) => {
    setMessagesState(msgs)
  }
  
  const addMessage = (message: ChatMessage) => {
    setMessagesState(prev => [...prev, message])
  }
  
  const clearMessages = () => {
    setMessagesState(defaultMessages)
  }
  
  const saveToHistory = (testResult?: MultiCrowdTestResult, publishedVersion?: 'A' | 'B') => {
    if (!taskSpec) return
    
    const record: HistoryRecord = {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: Date.now(),
      taskSpec: { ...taskSpec },
      contentA: { ...contentA },
      contentB: { ...contentB },
      testResult,
      publishedVersion,
    }
    
    setHistoryRecords(prev => [record, ...prev].slice(0, 50)) // 最多保存50条
  }
  
  const loadFromHistory = (record: HistoryRecord) => {
    setTaskSpecState(record.taskSpec)
    setContentAState(record.contentA)
    setContentBState(record.contentB)
  }
  
  const deleteHistory = (id: string) => {
    setHistoryRecords(prev => prev.filter(r => r.id !== id))
  }
  
  const clearHistory = () => {
    setHistoryRecords([])
  }
  
  const resetSession = () => {
    setTaskSpecState(null)
    setContentAState(defaultContent)
    setContentBState(defaultContent)
    setMessagesState(defaultMessages)
  }
  
  const value: AppState = {
    taskSpec,
    contentA,
    contentB,
    messages,
    historyRecords,
    setTaskSpec,
    updateTaskSpec,
    setContentA,
    setContentB,
    setMessages,
    addMessage,
    clearMessages,
    saveToHistory,
    loadFromHistory,
    deleteHistory,
    clearHistory,
    resetSession,
  }
  
  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  )
}

export function useApp() {
  const context = useContext(AppContext)
  if (context === undefined) {
    throw new Error('useApp must be used within an AppProvider')
  }
  return context
}
