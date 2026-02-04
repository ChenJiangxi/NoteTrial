import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { contentAPI } from '../services/api';
import {
  ArrowLeft, Save, Tag, Sparkles,
  Loader2, X, Lightbulb,
  Undo, Redo, Eye, Edit3, MessageCircle,
  ThumbsUp, ThumbsDown, Check,
  Send, BarChart3, Layout, Moon, Sun, GripVertical,
  Plus
} from 'lucide-react';

// Types
interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  extractedFields?: Record<string, string>;
}

interface ContentBlock {
  id: string;
  type: 'title' | 'paragraph' | 'heading' | 'list';
  content: string;
  version: 'A' | 'B';
}

interface AISuggestion {
  id: string;
  type: 'improvement' | 'style' | 'structure' | 'grammar';
  content: string;
  aiScore: number;
  applied: boolean;
}

// Mock AI score calculator
const calculateAIScore = (text: string): number => {
  const wordCount = text.split(/\s+/).length;
  const sentenceCount = text.split(/[.!?]+/).length;
  const avgSentenceLength = wordCount / Math.max(sentenceCount, 1);
  
  let score = 70;
  score += Math.min(text.length / 100, 15);
  score += Math.abs(avgSentenceLength - 15) < 5 ? 10 : -5;
  score += /[!?]/.test(text) ? 5 : 0;
  
  return Math.min(Math.max(Math.round(score), 0), 100);
};

// Drag and drop hook
const useDragAndDrop = <T,>(items: T[], onReorder: (items: T[]) => void) => {
  const [draggedItem, setDraggedItem] = useState<number | null>(null);
  const dragOverItem = useRef<number | null>(null);

  const handleDragStart = (index: number) => {
    setDraggedItem(index);
  };

  const handleDragEnter = (index: number) => {
    dragOverItem.current = index;
  };

  const handleDragEnd = useCallback(() => {
    if (draggedItem !== null && dragOverItem.current !== null && draggedItem !== dragOverItem.current) {
      const newItems = [...items];
      const [removed] = newItems.splice(draggedItem, 1);
      newItems.splice(dragOverItem.current, 0, removed);
      onReorder(newItems);
    }
    setDraggedItem(null);
    dragOverItem.current = null;
  }, [draggedItem, items, onReorder]);

  return { draggedItem, dragOverItem, handleDragStart, handleDragEnter, handleDragEnd };
};

// Auto-save hook
const useAutoSave = <T,>(data: T, saveFn: (data: T) => void, delay: number = 3000) => {
  const savedData = useRef<T>(data);
  const timeoutRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    if (JSON.stringify(data) !== JSON.stringify(savedData.current)) {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      timeoutRef.current = setTimeout(() => {
        savedData.current = data;
        saveFn(data);
      }, delay);
    }
  }, [data, saveFn, delay]);

  return () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
  };
};

export default function Editor() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const isEditing = !!id;
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [darkMode, setDarkMode] = useState(false);
  const [activeTab, setActiveTab] = useState<'edit' | 'preview'>('edit');
  const [showAddBlock, setShowAddBlock] = useState(false);

  // State
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [contentBlocks, setContentBlocks] = useState<ContentBlock[]>([
    { id: '1', type: 'title', content: '', version: 'A' },
    { id: '2', type: 'paragraph', content: '', version: 'A' },
  ]);
  const [suggestions, setSuggestions] = useState<AISuggestion[]>([]);
  const [aiScore, setAiScore] = useState(0);
  const [formData, setFormData] = useState({
    title: '',
    body: '',
    tags: [] as string[],
    cover_image: '',
    targetAudience: '',
    focusPoint: '',
    tone: 'professional',
  });
  const [tagInput, setTagInput] = useState('');
  const [history, setHistory] = useState<typeof contentBlocks[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  // Undo/Redo
  const pushToHistory = useCallback((blocks: ContentBlock[]) => {
    setHistory(prev => [...prev.slice(0, historyIndex + 1), blocks]);
    setHistoryIndex(prev => prev + 1);
  }, [historyIndex]);

  const undo = useCallback(() => {
    if (historyIndex > 0) {
      setHistoryIndex(prev => prev - 1);
      setContentBlocks(history[historyIndex - 1]);
    }
  }, [history, historyIndex]);

  const redo = useCallback(() => {
    if (historyIndex < history.length - 1) {
      setHistoryIndex(prev => prev + 1);
      setContentBlocks(history[historyIndex + 1]);
    }
  }, [history, historyIndex]);

  // Drag and drop
  const { draggedItem, dragOverItem, handleDragStart, handleDragEnter, handleDragEnd } = 
    useDragAndDrop(contentBlocks, (newBlocks) => {
      pushToHistory(newBlocks);
      setContentBlocks(newBlocks);
    });

  // Auto-save
  useAutoSave(formData, (data) => {
    console.log('Auto-saving...', data);
  }, 5000);

  // Fetch content
  const { data: content, isLoading } = useQuery({
    queryKey: ['content', id],
    queryFn: async () => {
      if (!id) return null;
      const data = await contentAPI.get(id);
      return data;
    },
    enabled: !!id,
  });

  useEffect(() => {
    if (content) {
      setFormData({
        title: content.title || '',
        body: content.body || '',
        tags: content.tags || [],
        cover_image: content.cover_image || '',
        targetAudience: content.targetAudience || '',
        focusPoint: content.focusPoint || '',
        tone: content.tone || 'professional',
      });
    }
  }, [content]);

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Generate suggestions when content changes
  useEffect(() => {
    const score = calculateAIScore(formData.body);
    setAiScore(score);
    
    if (formData.body.length > 50) {
      setSuggestions([
        {
          id: '1',
          type: 'style',
          content: '考虑使用更多主动语态来增强表达力',
          aiScore: score,
          applied: false,
        },
        {
          id: '2',
          type: 'structure',
          content: '添加小标题可以帮助读者更好地理解文章结构',
          aiScore: score,
          applied: false,
        },
        {
          id: '3',
          type: 'improvement',
          content: '适当增加一些数据支撑可以增强说服力',
          aiScore: score,
          applied: false,
        },
      ]);
    }
  }, [formData.body]);

  // Handle AI response
  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);

    setTimeout(() => {
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: getAIResponse(),
        timestamp: new Date(),
        extractedFields: extractFields(input),
      };
      
      setMessages(prev => [...prev, aiMessage]);
      setIsTyping(false);
    }, 1500);
  };

  const getAIResponse = (): string => {
    const responses = [
      "好的，我理解了您的需求。能否告诉我更多关于目标受众的信息？比如他们的年龄段和职业背景。",
      "明白了！关于这个主题，您希望重点强调哪些方面？是实用性、理论分析还是案例说明？",
      "很有趣的想法！您希望文章的整体风格是轻松活泼还是专业严谨？",
      "收到！请问您希望文章大约多长？短篇精炼还是长篇详尽？",
    ];
    return responses[Math.floor(Math.random() * responses.length)];
  };

  const extractFields = (text: string): Record<string, string> => {
    const fields: Record<string, string> = {};
    if (text.includes('年轻') || text.includes('学生')) fields.targetAudience = '年轻专业人士';
    if (text.includes('专业') || text.includes('商务')) fields.tone = 'professional';
    if (text.includes('轻松') || text.includes('有趣')) fields.tone = 'casual';
    return fields;
  };

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      if (isEditing) {
        const { data: res } = await contentAPI.update(id, data);
        return res;
      } else {
        const { data: res } = await contentAPI.create(data);
        return res;
      }
    },
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['contents'] });
      if (!isEditing && res.id) {
        navigate(`/editor/${res.id}`);
      }
    },
  });

  // Apply suggestion
  const applySuggestion = (suggestion: AISuggestion) => {
    setSuggestions(prev => 
      prev.map(s => s.id === suggestion.id ? { ...s, applied: true } : s)
    );
  };

  // Update content block
  const updateBlock = (id: string, content: string) => {
    pushToHistory(contentBlocks);
    setContentBlocks(prev => 
      prev.map(b => b.id === id ? { ...b, content } : b)
    );
  };

  // Switch version (A/B testing)
  const switchVersion = (version: 'A' | 'B') => {
    setContentBlocks(prev => 
      prev.map(b => ({ ...b, version }))
    );
  };

  const handleSave = () => {
    const combinedContent = contentBlocks.map(b => b.content).join('\n\n');
    saveMutation.mutate({ ...formData, body: combinedContent });
  };

  // Render typing indicator
  const TypingIndicator = () => (
    <div className="flex items-center gap-1 px-4 py-2 bg-slate-100 dark:bg-slate-700 rounded-2xl rounded-tl-sm">
      <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
      <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
      <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
    </div>
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-[#ff2442]" />
      </div>
    );
  }

  return (
    <div className={`h-screen flex flex-col ${darkMode ? 'dark bg-slate-900' : 'bg-slate-50'}`}>
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(-1)}
            className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-lg font-semibold text-slate-800 dark:text-white">
              {isEditing ? '编辑内容' : '新建内容'}
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {isEditing ? '完善您的创作' : 'AI 辅助创作'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={undo}
            disabled={historyIndex <= 0}
            className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors disabled:opacity-50"
            title="撤销"
          >
            <Undo className="w-4 h-4" />
          </button>
          <button
            onClick={redo}
            disabled={historyIndex >= history.length - 1}
            className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors disabled:opacity-50"
            title="重做"
          >
            <Redo className="w-4 h-4" />
          </button>

          <button
            onClick={() => setDarkMode(!darkMode)}
            className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            title={darkMode ? '切换亮色模式' : '切换深色模式'}
          >
            {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>

          <button
            onClick={handleSave}
            disabled={saveMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-[#ff2442] text-white text-sm font-medium rounded-lg hover:bg-[#e61f3d] transition-colors disabled:opacity-50"
          >
            {saveMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            保存
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Conversation */}
        <div className="w-96 flex flex-col border-r border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800">
          <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700">
            <div className="flex items-center gap-2">
              <MessageCircle className="w-4 h-4 text-[#ff2442]" />
              <span className="font-medium text-slate-800 dark:text-white text-sm">AI 对话</span>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <div className="w-16 h-16 bg-slate-100 dark:bg-slate-700 rounded-full flex items-center justify-center mb-4">
                  <Sparkles className="w-8 h-8 text-[#ff2442]" />
                </div>
                <h3 className="font-medium text-slate-800 dark:text-white mb-1">开始创作</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  告诉我您想创作的内容，我来帮您
                </p>
              </div>
            ) : (
              messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex gap-3 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}
                >
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                    message.role === 'assistant' 
                      ? 'bg-[#ff2442]/10 text-[#ff2442]' 
                      : 'bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400'
                  }`}>
                    {message.role === 'assistant' ? <Sparkles className="w-4 h-4" /> : (
                      <div className="w-4 h-4 bg-slate-300 dark:bg-slate-600 rounded-full" />
                    )}
                  </div>
                  <div className={`max-w-[80%] ${message.role === 'user' ? 'text-right' : ''}`}>
                    <div className={`inline-block px-4 py-2 rounded-2xl text-sm ${
                      message.role === 'assistant'
                        ? 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-tl-sm'
                        : 'bg-[#ff2442] text-white rounded-tr-sm'
                    }`}>
                      {message.content}
                    </div>
                    {message.extractedFields && Object.keys(message.extractedFields).length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1 justify-end">
                        {Object.entries(message.extractedFields).map(([key, value]) => (
                          <span key={key} className="text-xs px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded">
                            {key}: {value}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
            {isTyping && (
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-[#ff2442]/10 flex items-center justify-center">
                  <Sparkles className="w-4 h-4 text-[#ff2442]" />
                </div>
                <TypingIndicator />
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="p-4 border-t border-slate-200 dark:border-slate-700">
            <div className="relative">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                placeholder="描述您的创作需求..."
                className="w-full px-4 py-3 pr-12 bg-slate-100 dark:bg-slate-700 border-none rounded-xl resize-none text-sm placeholder:text-slate-400 focus:ring-2 focus:ring-[#ff2442]/20 dark:text-white"
                rows={3}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || isTyping}
                className="absolute right-3 bottom-3 p-1.5 bg-[#ff2442] text-white rounded-lg hover:bg-[#e61f3d] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
            <p className="mt-2 text-xs text-slate-400">
              按 Enter 发送，Shift + Enter 换行
            </p>
          </div>
        </div>

        {/* Middle Panel - Editor */}
        <div className="flex-1 flex flex-col bg-slate-50 dark:bg-slate-900 overflow-hidden">
          <div className="flex items-center justify-between px-6 py-2 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveTab('edit')}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  activeTab === 'edit'
                    ? 'bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-white'
                    : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                }`}
              >
                <Edit3 className="w-4 h-4" />
                编辑
              </button>
              <button
                onClick={() => setActiveTab('preview')}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  activeTab === 'preview'
                    ? 'bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-white'
                    : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                }`}
              >
                <Eye className="w-4 h-4" />
                预览
              </button>
            </div>

            <div className="flex items-center gap-1 p-1 bg-slate-100 dark:bg-slate-700 rounded-lg">
              <button
                onClick={() => switchVersion('A')}
                className={`px-3 py-1 text-xs font-medium rounded ${
                  contentBlocks[0]?.version === 'A'
                    ? 'bg-white dark:bg-slate-600 text-slate-800 dark:text-white shadow-sm'
                    : 'text-slate-500 dark:text-slate-400'
                }`}
              >
                版本 A
              </button>
              <button
                onClick={() => switchVersion('B')}
                className={`px-3 py-1 text-xs font-medium rounded ${
                  contentBlocks[0]?.version === 'B'
                    ? 'bg-white dark:bg-slate-600 text-slate-800 dark:text-white shadow-sm'
                    : 'text-slate-500 dark:text-slate-400'
                }`}
              >
                版本 B
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-6">
            {activeTab === 'edit' ? (
              <div className="max-w-3xl mx-auto space-y-4">
                {contentBlocks.map((block, index) => (
                  <div
                    key={block.id}
                    className={`group flex items-start gap-2 p-4 rounded-xl transition-colors ${
                      draggedItem === index
                        ? 'bg-[#ff2442]/5 border-2 border-dashed border-[#ff2442]'
                        : 'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
                    }`}
                    draggable
                    onDragStart={() => handleDragStart(index)}
                    onDragEnter={() => handleDragEnter(index)}
                    onDragEnd={handleDragEnd}
                    onDragOver={(e) => e.preventDefault()}
                  >
                    <div className="opacity-0 group-hover:opacity-100 cursor-grab text-slate-300 dark:text-slate-600 mt-1">
                      <GripVertical className="w-4 h-4" />
                    </div>
                    
                    {block.type === 'title' ? (
                      <input
                        type="text"
                        value={block.content}
                        onChange={(e) => updateBlock(block.id, e.target.value)}
                        placeholder="输入标题..."
                        className="flex-1 text-2xl font-bold text-slate-800 dark:text-white placeholder:text-slate-300 border-none p-0 focus:ring-0 bg-transparent"
                      />
                    ) : block.type === 'heading' ? (
                      <input
                        type="text"
                        value={block.content}
                        onChange={(e) => updateBlock(block.id, e.target.value)}
                        placeholder="输入副标题..."
                        className="flex-1 text-lg font-semibold text-slate-700 dark:text-slate-200 placeholder:text-slate-300 border-none p-0 focus:ring-0 bg-transparent"
                      />
                    ) : (
                      <textarea
                        value={block.content}
                        onChange={(e) => updateBlock(block.id, e.target.value)}
                        placeholder="输入内容..."
                        className="flex-1 resize-none text-slate-600 dark:text-slate-300 placeholder:text-slate-300 border-none p-0 focus:ring-0 bg-transparent"
                        rows={3}
                      />
                    )}
                    
                    <button
                      onClick={() => {
                        pushToHistory(contentBlocks);
                        setContentBlocks(prev => prev.filter(b => b.id !== block.id));
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 text-slate-400 hover:text-red-500 transition-all"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}

                <div className="relative">
                  <button
                    onClick={() => setShowAddBlock(!showAddBlock)}
                    className="flex items-center gap-2 px-4 py-2 text-sm text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                  >
                    <Plus className="w-4 h-4" />
                    添加内容块
                  </button>
                  
                  {showAddBlock && (
                    <div className="absolute top-full left-0 mt-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-lg p-2 z-10 min-w-[160px]">
                      <button
                        onClick={() => {
                          pushToHistory(contentBlocks);
                          setContentBlocks(prev => [...prev, {
                            id: Date.now().toString(),
                            type: 'heading',
                            content: '',
                            version: contentBlocks[0]?.version || 'A'
                          }]);
                          setShowAddBlock(false);
                        }}
                        className="w-full px-3 py-2 text-left text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg"
                      >
                        副标题
                      </button>
                      <button
                        onClick={() => {
                          pushToHistory(contentBlocks);
                          setContentBlocks(prev => [...prev, {
                            id: Date.now().toString(),
                            type: 'paragraph',
                            content: '',
                            version: contentBlocks[0]?.version || 'A'
                          }]);
                          setShowAddBlock(false);
                        }}
                        className="w-full px-3 py-2 text-left text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg"
                      >
                        段落
                      </button>
                      <button
                        onClick={() => {
                          pushToHistory(contentBlocks);
                          setContentBlocks(prev => [...prev, {
                            id: Date.now().toString(),
                            type: 'list',
                            content: '',
                            version: contentBlocks[0]?.version || 'A'
                          }]);
                          setShowAddBlock(false);
                        }}
                        className="w-full px-3 py-2 text-left text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg"
                      >
                        列表
                      </button>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="max-w-3xl mx-auto bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-8">
                {contentBlocks.map((block) => (
                  <div key={block.id}>
                    {block.type === 'title' && (
                      <h1 className="text-3xl font-bold text-slate-800 dark:text-white mb-6">{block.content || '标题预览'}</h1>
                    )}
                    {block.type === 'heading' && (
                      <h2 className="text-xl font-semibold text-slate-700 dark:text-slate-200 mt-8 mb-4">{block.content || '副标题预览'}</h2>
                    )}
                    {block.type === 'paragraph' && (
                      <p className="text-slate-600 dark:text-slate-300 leading-relaxed mb-4">{block.content || '内容预览...'}</p>
                    )}
                    {block.type === 'list' && (
                      <ul className="list-disc list-inside text-slate-600 dark:text-slate-300 space-y-2 mb-4">
                        <li>{block.content || '列表项预览'}</li>
                      </ul>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Panel - AI Suggestions */}
        <div className="w-80 flex flex-col border-l border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800">
          <div className="px-4 py-4 border-b border-slate-200 dark:border-slate-700">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-[#ff2442]" />
                <span className="font-medium text-slate-800 dark:text-white text-sm">AI 评分</span>
              </div>
              <span className={`text-lg font-bold ${
                aiScore >= 80 ? 'text-green-500' : aiScore >= 60 ? 'text-yellow-500' : 'text-red-500'
              }`}>
                {aiScore}
              </span>
            </div>
            <div className="h-2 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  aiScore >= 80 ? 'bg-green-500' : aiScore >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                }`}
                style={{ width: `${aiScore}%` }}
              />
            </div>
            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
              {aiScore >= 80 ? '内容质量优秀！' : aiScore >= 60 ? '内容质量良好，还有提升空间' : '建议根据 AI 建议优化内容'}
            </p>
          </div>

          <div className="px-4 py-4 border-b border-slate-200 dark:border-slate-700">
            <div className="flex items-center gap-2 mb-4">
              <Layout className="w-4 h-4 text-[#ff2442]" />
              <span className="font-medium text-slate-800 dark:text-white text-sm">智能表单</span>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">目标受众</label>
                <input
                  type="text"
                  value={formData.targetAudience}
                  onChange={(e) => setFormData({ ...formData, targetAudience: e.target.value })}
                  placeholder="从对话中提取..."
                  className="w-full px-3 py-2 text-sm bg-slate-100 dark:bg-slate-700 border-none rounded-lg focus:ring-2 focus:ring-[#ff2442]/20 dark:text-white"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">侧重点</label>
                <input
                  type="text"
                  value={formData.focusPoint}
                  onChange={(e) => setFormData({ ...formData, focusPoint: e.target.value })}
                  placeholder="选择侧重点..."
                  className="w-full px-3 py-2 text-sm bg-slate-100 dark:bg-slate-700 border-none rounded-lg focus:ring-2 focus:ring-[#ff2442]/20 dark:text-white"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">文风</label>
                <select
                  value={formData.tone}
                  onChange={(e) => setFormData({ ...formData, tone: e.target.value })}
                  className="w-full px-3 py-2 text-sm bg-slate-100 dark:bg-slate-700 border-none rounded-lg focus:ring-2 focus:ring-[#ff2442]/20 dark:text-white"
                >
                  <option value="professional">专业严谨</option>
                  <option value="casual">轻松活泼</option>
                  <option value="friendly">友好亲和</option>
                  <option value="authoritative">权威正式</option>
                </select>
              </div>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto px-4 py-4">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Lightbulb className="w-4 h-4 text-[#ff2442]" />
                <span className="font-medium text-slate-800 dark:text-white text-sm">AI 建议</span>
              </div>
              <button className="text-xs text-[#ff2442] hover:text-[#e61f3d]">
                全部刷新
              </button>
            </div>
            
            <div className="space-y-3">
              {suggestions.length === 0 ? (
                <p className="text-sm text-slate-500 dark:text-slate-400 text-center py-8">
                  开始创作后将获得 AI 建议
                </p>
              ) : (
                suggestions.map((suggestion) => (
                  <div
                    key={suggestion.id}
                    className={`p-3 rounded-xl border transition-all ${
                      suggestion.applied
                        ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
                        : 'bg-slate-50 dark:bg-slate-700/50 border-slate-200 dark:border-slate-700 hover:border-[#ff2442]/50'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        suggestion.type === 'style' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400' :
                        suggestion.type === 'structure' ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400' :
                        suggestion.type === 'improvement' ? 'bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400' :
                        'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400'
                      }`}>
                        {suggestion.type === 'style' ? '风格' : 
                         suggestion.type === 'structure' ? '结构' : 
                         suggestion.type === 'improvement' ? '改进' : '语法'}
                      </span>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => applySuggestion(suggestion)}
                          disabled={suggestion.applied}
                          className={`p-1 rounded transition-colors ${
                            suggestion.applied
                              ? 'text-green-500 cursor-default'
                              : 'text-slate-400 hover:text-green-500 hover:bg-green-50 dark:hover:bg-green-900/20'
                          }`}
                          title={suggestion.applied ? '已应用' : '应用建议'}
                        >
                          {suggestion.applied ? <Check className="w-4 h-4" /> : <ThumbsUp className="w-4 h-4" />}
                        </button>
                        <button
                          className="p-1 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                          title="忽略"
                        >
                          <ThumbsDown className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                    <p className="text-sm text-slate-700 dark:text-slate-300">
                      {suggestion.content}
                    </p>
                    {suggestion.applied && (
                      <div className="mt-2 flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
                        <Check className="w-3 h-3" />
                        已应用
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Tags */}
          <div className="px-4 py-4 border-t border-slate-200 dark:border-slate-700">
            <div className="flex items-center gap-2 mb-3">
              <Tag className="w-4 h-4 text-slate-400" />
              <span className="text-sm font-medium text-slate-700 dark:text-slate-300">标签</span>
            </div>
            <div className="flex flex-wrap gap-2 mb-3">
              {formData.tags.map((tag) => (
                <span
                  key={tag}
                  className="inline-flex items-center gap-1 px-3 py-1 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 text-sm rounded-full"
                >
                  #{tag}
                  <button
                    onClick={() => setFormData({ ...formData, tags: formData.tags.filter((t) => t !== tag) })}
                    className="text-slate-400 hover:text-red-500"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
            <input
              type="text"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && tagInput.trim()) {
                  if (!formData.tags.includes(tagInput.trim())) {
                    setFormData({ ...formData, tags: [...formData.tags, tagInput.trim()] });
                  }
                  setTagInput('');
                }
              }}
              placeholder="添加标签，按回车..."
              className="w-full px-3 py-2 text-sm bg-slate-100 dark:bg-slate-700 border-none rounded-lg focus:ring-2 focus:ring-[#ff2442]/20 dark:text-white placeholder:text-slate-400"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
