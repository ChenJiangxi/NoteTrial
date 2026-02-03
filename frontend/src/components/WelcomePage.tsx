import { Sparkles, MessageSquare, Bot, ArrowRight, Zap, TrendingUp, Brain, Users, Clock, Target, CheckCircle2 } from 'lucide-react'

interface WelcomePageProps {
  onSelectMode: (mode: 'interactive' | 'auto') => void
}

export default function WelcomePage({ onSelectMode }: WelcomePageProps) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-red-50/30">
      {/* 顶部导航 */}
      <header className="px-8 py-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-gradient-to-br from-[#ff2442] to-[#ff6b81] rounded-lg flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-gray-800">NoteTrial</span>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-8 py-12">
        {/* Hero 区域 */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-red-50 rounded-full text-sm text-[#ff2442] mb-6">
            <Zap className="w-4 h-4" />
            <span>小红书内容创作的 AI 副驾驶</span>
          </div>
          
          <h1 className="text-5xl font-bold text-gray-900 mb-4 leading-tight">
            从灵感到爆款<br />
            <span className="text-[#ff2442]">全流程陪伴</span>
          </h1>
          
          <p className="text-xl text-gray-500 max-w-2xl mx-auto">
            发帖前预测效果、自动学习爆款规律、一键批量生成发布
          </p>
        </div>

        {/* 两个模式卡片 */}
        <div className="grid md:grid-cols-2 gap-8 mb-16">
          {/* 人机交互模式 */}
          <div 
            onClick={() => onSelectMode('interactive')}
            className="group cursor-pointer"
          >
            <div className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100 hover:shadow-xl hover:border-blue-200 transition-all duration-300 h-full">
              {/* 头部 */}
              <div className="flex items-start justify-between mb-6">
                <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center shadow-lg">
                  <MessageSquare className="w-8 h-8 text-white" />
                </div>
                <div className="w-10 h-10 rounded-full bg-blue-50 flex items-center justify-center group-hover:bg-blue-500 transition-colors">
                  <ArrowRight className="w-5 h-5 text-blue-500 group-hover:text-white transition-colors" />
                </div>
              </div>
              
              {/* 标题和描述 */}
              <h2 className="text-2xl font-bold text-gray-900 mb-2">人机交互模式</h2>
              <p className="text-gray-500 mb-6">适合精细打磨单篇内容，追求最佳效果</p>
              
              {/* 使用场景 */}
              <div className="bg-blue-50/50 rounded-xl p-4 mb-6">
                <div className="text-sm font-medium text-blue-900 mb-2">📌 适用场景</div>
                <ul className="text-sm text-blue-700 space-y-1">
                  <li>• 重要内容发布前想先测试效果</li>
                  <li>• 有两个想法，不确定哪个更好</li>
                  <li>• 想了解目标用户会怎么看这篇内容</li>
                </ul>
              </div>
              
              {/* 功能列表 */}
              <div className="space-y-3">
                <div className="flex items-center gap-3 text-gray-600">
                  <CheckCircle2 className="w-5 h-5 text-blue-500" />
                  <span>对话式描述创作意图</span>
                </div>
                <div className="flex items-center gap-3 text-gray-600">
                  <CheckCircle2 className="w-5 h-5 text-blue-500" />
                  <span>自动生成 A/B 两版内容对比</span>
                </div>
                <div className="flex items-center gap-3 text-gray-600">
                  <CheckCircle2 className="w-5 h-5 text-blue-500" />
                  <span>多种目标用户画像模拟投票</span>
                </div>
                <div className="flex items-center gap-3 text-gray-600">
                  <CheckCircle2 className="w-5 h-5 text-blue-500" />
                  <span>统计置信度 + 优化建议</span>
                </div>
              </div>
            </div>
          </div>

          {/* 自动学习模式 */}
          <div 
            onClick={() => onSelectMode('auto')}
            className="group cursor-pointer"
          >
            <div className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100 hover:shadow-xl hover:border-orange-200 transition-all duration-300 h-full relative overflow-hidden">
              {/* Beta 标签 */}
              <div className="absolute top-4 right-4 px-3 py-1 bg-gradient-to-r from-orange-500 to-red-500 text-white text-xs font-bold rounded-full">
                Beta
              </div>
              
              {/* 头部 */}
              <div className="flex items-start justify-between mb-6">
                <div className="w-16 h-16 bg-gradient-to-br from-orange-500 to-red-500 rounded-2xl flex items-center justify-center shadow-lg">
                  <Bot className="w-8 h-8 text-white" />
                </div>
                <div className="w-10 h-10 rounded-full bg-orange-50 flex items-center justify-center group-hover:bg-orange-500 transition-colors mt-8">
                  <ArrowRight className="w-5 h-5 text-orange-500 group-hover:text-white transition-colors" />
                </div>
              </div>
              
              {/* 标题和描述 */}
              <h2 className="text-2xl font-bold text-gray-900 mb-2">自动学习模式</h2>
              <p className="text-gray-500 mb-6">适合批量运营，让 AI 全自动持续产出</p>
              
              {/* 使用场景 */}
              <div className="bg-orange-50/50 rounded-xl p-4 mb-6">
                <div className="text-sm font-medium text-orange-900 mb-2">📌 适用场景</div>
                <ul className="text-sm text-orange-700 space-y-1">
                  <li>• 想要批量产出内容，提高发布频率</li>
                  <li>• 没时间每篇都精细打磨</li>
                  <li>• 想让 AI 自动学习什么内容效果好</li>
                </ul>
              </div>
              
              {/* 功能列表 */}
              <div className="space-y-3">
                <div className="flex items-center gap-3 text-gray-600">
                  <CheckCircle2 className="w-5 h-5 text-orange-500" />
                  <span>自动爬取分析爆款内容</span>
                </div>
                <div className="flex items-center gap-3 text-gray-600">
                  <CheckCircle2 className="w-5 h-5 text-orange-500" />
                  <span>AI 生成内容 + 原创封面图</span>
                </div>
                <div className="flex items-center gap-3 text-gray-600">
                  <CheckCircle2 className="w-5 h-5 text-orange-500" />
                  <span>一键发布到小红书</span>
                </div>
                <div className="flex items-center gap-3 text-gray-600">
                  <CheckCircle2 className="w-5 h-5 text-orange-500" />
                  <span>追踪效果，持续优化策略</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 工作流程图 */}
        <div className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100 mb-16">
          <h3 className="text-lg font-bold text-gray-900 mb-6 text-center">🔄 自动学习模式工作流程</h3>
          <div className="flex items-center justify-between max-w-4xl mx-auto">
            <div className="flex flex-col items-center">
              <div className="w-12 h-12 rounded-full bg-orange-100 flex items-center justify-center mb-2">
                <Target className="w-6 h-6 text-orange-600" />
              </div>
              <span className="text-sm font-medium text-gray-700">设置话题</span>
              <span className="text-xs text-gray-400">输入关键词</span>
            </div>
            <div className="flex-1 h-0.5 bg-gray-200 mx-2" />
            <div className="flex flex-col items-center">
              <div className="w-12 h-12 rounded-full bg-orange-100 flex items-center justify-center mb-2">
                <TrendingUp className="w-6 h-6 text-orange-600" />
              </div>
              <span className="text-sm font-medium text-gray-700">学习爆款</span>
              <span className="text-xs text-gray-400">分析高赞内容</span>
            </div>
            <div className="flex-1 h-0.5 bg-gray-200 mx-2" />
            <div className="flex flex-col items-center">
              <div className="w-12 h-12 rounded-full bg-orange-100 flex items-center justify-center mb-2">
                <Brain className="w-6 h-6 text-orange-600" />
              </div>
              <span className="text-sm font-medium text-gray-700">AI 生成</span>
              <span className="text-xs text-gray-400">内容+封面图</span>
            </div>
            <div className="flex-1 h-0.5 bg-gray-200 mx-2" />
            <div className="flex flex-col items-center">
              <div className="w-12 h-12 rounded-full bg-orange-100 flex items-center justify-center mb-2">
                <Zap className="w-6 h-6 text-orange-600" />
              </div>
              <span className="text-sm font-medium text-gray-700">自动发布</span>
              <span className="text-xs text-gray-400">一键到小红书</span>
            </div>
            <div className="flex-1 h-0.5 bg-gray-200 mx-2" />
            <div className="flex flex-col items-center">
              <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center mb-2">
                <Users className="w-6 h-6 text-green-600" />
              </div>
              <span className="text-sm font-medium text-gray-700">效果追踪</span>
              <span className="text-xs text-gray-400">学习优化</span>
            </div>
          </div>
          <div className="text-center mt-6">
            <div className="inline-flex items-center gap-2 text-sm text-gray-500">
              <Clock className="w-4 h-4" />
              <span>循环执行，持续优化，越用越懂你</span>
            </div>
          </div>
        </div>

        {/* 底部 */}
        <div className="text-center">
          <p className="text-sm text-gray-400 mb-2">
            Powered by 小红书 MCP
          </p>
          <p className="text-xs text-gray-300">
            v0.2.0-Beta · 开源项目
          </p>
        </div>
      </div>
    </div>
  )
}
