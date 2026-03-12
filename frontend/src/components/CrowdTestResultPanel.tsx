import { ArrowLeftRight, BarChart3, FileSearch, Lightbulb, Sparkles } from 'lucide-react'
import type { MultiCrowdTestResult, VersionScore } from '../types/api'

function humanizeGoalText(text: string) {
  return text
    .replace(/maximize_like/g, '点赞优先')
    .replace(/maximize_save/g, '收藏优先')
    .replace(/maximize_comment/g, '评论优先')
    .replace(/maximize_share/g, '分享优先')
}

function formatScore(value?: number) {
  return (value ?? 0).toFixed(1)
}

function formatList(values?: string[]) {
  if (!values || values.length === 0) return '暂无'
  return values.slice(0, 3).join(' / ')
}

function SummaryCard({
  version,
  index,
}: {
  version: VersionScore
  index: number
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <div className="text-sm font-semibold text-slate-800">
              {index + 1}. {version.label}
            </div>
            {index === 0 && (
              <span className="rounded-full border border-red-200 bg-red-50 px-2 py-0.5 text-[10px] font-semibold text-[#ff2442]">
                推荐发布
              </span>
            )}
          </div>
          <div className="mt-1 text-xs text-slate-500">
            互动总分 {version.score.total} · 综合分 {formatScore(version.composite_score)} · MCP {formatScore(version.evidence_score)}
          </div>
        </div>

        <div className="grid grid-cols-4 gap-2 text-center text-[11px] text-slate-500">
          <div>
            <div>赞</div>
            <div className="mt-1 font-semibold text-slate-700">{version.score.like_count}</div>
          </div>
          <div>
            <div>藏</div>
            <div className="mt-1 font-semibold text-slate-700">{version.score.save_count}</div>
          </div>
          <div>
            <div>评</div>
            <div className="mt-1 font-semibold text-slate-700">{version.score.comment_count}</div>
          </div>
          <div>
            <div>转</div>
            <div className="mt-1 font-semibold text-slate-700">{version.score.share_count}</div>
          </div>
        </div>
      </div>
    </div>
  )
}

function EvidenceMetric({
  label,
  value,
}: {
  label: string
  value?: number
}) {
  return (
    <div className="rounded-lg border border-slate-100 bg-white px-3 py-2">
      <div className="text-[10px] text-slate-400">{label}</div>
      <div className="mt-1 text-xs font-semibold text-slate-700">{formatScore(value)}</div>
    </div>
  )
}

function EvidenceCard({ version }: { version: VersionScore }) {
  const evidence = version.mcp_evidence

  return (
    <div className="rounded-lg border border-slate-100 bg-slate-50 p-4 text-xs text-slate-600">
      <div className="flex items-center justify-between gap-3">
        <div className="font-medium text-slate-700">{version.label}</div>
        <div className="text-slate-500">MCP {formatScore(version.evidence_score)}</div>
      </div>

      <div className="mt-3 grid grid-cols-3 gap-2">
        <EvidenceMetric label="内容贴合度" value={evidence?.content_fit_score} />
        <EvidenceMetric label="互动参考分" value={evidence?.engagement_reference_score} />
        <EvidenceMetric label="目标对齐分" value={evidence?.goal_alignment_score} />
      </div>

      <div className="mt-3 space-y-1 text-sm leading-6">
        <div>关键词 {formatList(evidence?.matched_keywords)}</div>
        <div>命中样本标签 {formatList(evidence?.matched_tags)}</div>
        <div>
          样本数 {evidence?.sample_count ?? 0}
          {typeof evidence?.source_sample_count === 'number'
            ? ` / 总样本池 ${evidence.source_sample_count}`
            : ''}
        </div>
        <div>
          样本平均互动：赞 {Math.round(evidence?.avg_likes ?? 0)} / 藏 {Math.round(evidence?.avg_collects ?? 0)} / 评 {Math.round(evidence?.avg_comments ?? 0)} / 转 {Math.round(evidence?.avg_shares ?? 0)}
        </div>
      </div>

      <div className="mt-3 space-y-1 text-sm leading-6 text-slate-600">
        {(evidence?.reasons?.length ? evidence.reasons : ['暂无外部证据说明'])
          .slice(0, 4)
          .map((reason, index) => (
            <div key={index}>{humanizeGoalText(reason)}</div>
          ))}
      </div>
    </div>
  )
}

export default function CrowdTestResultPanel({
  result,
}: {
  result: MultiCrowdTestResult
}) {
  const suggestionTarget = result.version_scores[1]?.label

  return (
    <div className="space-y-6">
      <div className="rounded-xl bg-gradient-to-br from-[#ff2442] to-[#e61f3d] p-4 text-white shadow-md shadow-red-200">
        <div className="mb-2 flex items-center gap-2 opacity-90">
          <Sparkles className="h-4 w-4 text-white" />
          <span className="text-xs font-bold uppercase tracking-wide">发布建议</span>
        </div>
        <div className="mb-1 text-2xl font-bold">
          {result.overall_confidence.winner === '-' ? '结果接近' : result.overall_confidence.winner}
        </div>
        <div className="text-xs leading-relaxed opacity-80">
          综合表现置信度 {result.overall_confidence.confidence.toFixed(0)}%
        </div>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-4">
        <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700">
          <ArrowLeftRight className="h-3.5 w-3.5 text-[#ff2442]" />
          版本对比
        </h4>
        <div className="space-y-2">
          {result.version_scores.map((version, index) => (
            <SummaryCard key={version.label} version={version} index={index} />
          ))}
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-4">
        <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700">
          <BarChart3 className="h-3.5 w-3.5 text-[#ff2442]" />
          版本证据详情
        </h4>
        <div className="space-y-3">
          {result.version_scores.map(version => (
            <EvidenceCard key={`evidence-${version.label}`} version={version} />
          ))}
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-4">
        <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700">
          <FileSearch className="h-3.5 w-3.5 text-[#ff2442]" />
          结果诊断
        </h4>
        <div className="space-y-3">
          {result.diagnosis.slice(0, 3).map((diagnosis, index) => (
            <div
              key={index}
              className="rounded-lg border border-slate-100 bg-slate-50 p-3 text-sm leading-6 text-slate-600"
            >
              {humanizeGoalText(diagnosis)}
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-4">
        <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700">
          <Lightbulb className="h-3.5 w-3.5 text-[#ff2442]" />
          {suggestionTarget ? `优化建议（针对待优化版本 ${suggestionTarget}）` : '优化建议'}
        </h4>
        <div className="space-y-3">
          {result.suggestions.slice(0, 3).map((suggestion, index) => (
            <div key={index} className="rounded-lg border border-slate-100 bg-slate-50 p-3 text-sm leading-6 text-slate-600">
              {humanizeGoalText(suggestion)}
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
