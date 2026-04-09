import { useMemo } from 'react'
import { BarChart3, Users, Sparkles, TrendingDown, AlertCircle } from 'lucide-react'
import DataTable from '../components/DataTable'
import type { Column } from '../components/DataTable'
import Badge from '../components/Badge'
import { useAnalytics, useEvolution, useFansProfile } from '../api/hooks'

// ---------- types ----------

interface NotePerf {
  [key: string]: unknown
  id: string
  title: string
  type: string
  impressions: number
  ctr: number
  likes: number
  comments: number
  favorites: number
  fans: number
}

interface WinningPattern {
  id: string
  pattern: string
  evidence: string
  status: string
  type?: string
}

interface LosingPattern {
  id: string
  pattern: string
  evidence: string
  fix?: string
  status?: string
  type?: string
}

// ---------- helpers ----------

function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`skeleton ${className}`} />
}

function EmptyState({ icon: Icon, text }: { icon: React.ElementType; text: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-gray-400">
      <Icon size={32} className="mb-3 opacity-40" />
      <p className="text-sm">{text}</p>
    </div>
  )
}

function RankBadge({ rank }: { rank: number }) {
  if (rank === 1) {
    return (
      <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-amber-100 text-amber-700 text-xs font-bold">
        1
      </span>
    )
  }
  if (rank === 2) {
    return (
      <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-gray-200 text-gray-600 text-xs font-bold">
        2
      </span>
    )
  }
  if (rank === 3) {
    return (
      <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-orange-100 text-orange-600 text-xs font-bold">
        3
      </span>
    )
  }
  return <span className="text-sm text-gray-400 pl-1.5">{rank}</span>
}

// ---------- component ----------

export default function Analytics() {
  const { data: analyticsRaw, isLoading: analyticsLoading } = useAnalytics()
  const { data: evolutionRaw, isLoading: evoLoading } = useEvolution()
  const { data: fansRaw, isLoading: fansLoading } = useFansProfile()

  const analytics = (analyticsRaw ?? {}) as Record<string, unknown>
  const evolution = (evolutionRaw ?? {}) as Record<string, unknown>
  const fans = (fansRaw ?? {}) as Record<string, unknown>

  // Collect all notes_performance from last_7_days analytics
  const notes: NotePerf[] = useMemo(() => {
    const collected: NotePerf[] = []
    const seenIds = new Set<string>()

    // Today
    const today = analytics.today as Record<string, unknown> | null
    if (today?.notes_performance) {
      for (const n of today.notes_performance as NotePerf[]) {
        if (n.id && !seenIds.has(n.id)) {
          seenIds.add(n.id)
          collected.push({
            ...n,
            impressions: Number(n.impressions ?? 0),
            ctr: Number(n.ctr ?? 0),
            likes: Number(n.likes ?? 0),
            comments: Number(n.comments ?? 0),
            favorites: Number(n.favorites ?? 0),
            fans: Number(n.fans ?? 0),
          })
        }
      }
    }

    // Last 7 days
    const days = (analytics.last_7_days ?? []) as Array<Record<string, unknown>>
    for (const day of days) {
      const perf = (day.notes_performance ?? []) as NotePerf[]
      for (const n of perf) {
        if (n.id && !seenIds.has(n.id)) {
          seenIds.add(n.id)
          collected.push({
            ...n,
            impressions: Number(n.impressions ?? 0),
            ctr: Number(n.ctr ?? 0),
            likes: Number(n.likes ?? 0),
            comments: Number(n.comments ?? 0),
            favorites: Number(n.favorites ?? 0),
            fans: Number(n.fans ?? 0),
          })
        }
      }
    }

    return collected.sort((a, b) => b.impressions - a.impressions)
  }, [analytics])

  // Notes table with rank
  const rankedNotes: (NotePerf & { rank: number })[] = notes.map((n, i) => ({ ...n, rank: i + 1 }))

  const columns: Column<NotePerf & { rank: number }>[] = [
    {
      key: 'rank',
      label: '排名',
      render: (row) => <RankBadge rank={row.rank} />,
    },
    {
      key: 'title',
      label: '标题',
      render: (row) => (
        <span className="text-gray-800 font-medium max-w-xs truncate block" title={row.title}>
          {row.title || '--'}
        </span>
      ),
    },
    {
      key: 'type',
      label: '格式',
      render: (row) => <Badge label={String(row.type || '图文')} color="purple" />,
    },
    { key: 'impressions', label: '曝光', sortable: true },
    {
      key: 'ctr',
      label: 'CTR',
      sortable: true,
      render: (row) => <span>{row.ctr ? `${row.ctr}%` : '--'}</span>,
    },
    { key: 'likes', label: '赞', sortable: true },
    { key: 'favorites', label: '藏', sortable: true },
    { key: 'comments', label: '评', sortable: true },
    { key: 'fans', label: '涨粉', sortable: true },
  ]

  const winningPatterns = ((evolution.winning_patterns ?? []) as WinningPattern[])
  const losingPatterns = ((evolution.losing_patterns ?? []) as LosingPattern[])

  const genderData = (fans.gender ?? { male: 50, female: 50 }) as { male: number; female: number }
  const interests = (fans.interests ?? []) as string[]

  const malePercent = genderData.male
  const femalePercent = genderData.female

  const interestColors: Array<'blue' | 'green' | 'purple' | 'pink' | 'yellow' | 'red'> = [
    'blue', 'green', 'purple', 'pink', 'yellow', 'red',
  ]

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-gray-900">数据分析</h1>
        <p className="text-sm text-gray-400 mt-0.5">笔记表现、粉丝画像与进化知识库</p>
      </div>

      {/* Section 1: Fan Profile */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        {/* Gender Split */}
        <div className="bg-white rounded-xl border border-gray-100 p-5 hover:shadow-md transition-shadow duration-200">
          <div className="flex items-center gap-2 mb-4">
            <Users size={16} className="text-blue-500" />
            <h3 className="text-sm font-semibold text-gray-700">性别分布</h3>
          </div>
          {fansLoading ? (
            <Skeleton className="h-10" />
          ) : (
            <div>
              <div className="flex rounded-full overflow-hidden h-7 mb-3">
                <div
                  className="bg-blue-400 flex items-center justify-center text-white text-xs font-medium transition-all duration-500"
                  style={{ width: `${malePercent}%` }}
                >
                  {malePercent > 10 && `${malePercent}%`}
                </div>
                <div
                  className="bg-pink-400 flex items-center justify-center text-white text-xs font-medium transition-all duration-500"
                  style={{ width: `${femalePercent}%` }}
                >
                  {femalePercent > 10 && `${femalePercent}%`}
                </div>
              </div>
              <div className="flex items-center gap-6 text-sm text-gray-500">
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-blue-400" />
                  男 {malePercent}%
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-pink-400" />
                  女 {femalePercent}%
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Interest Tags */}
        <div className="bg-white rounded-xl border border-gray-100 p-5 hover:shadow-md transition-shadow duration-200">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles size={16} className="text-purple-500" />
            <h3 className="text-sm font-semibold text-gray-700">兴趣标签</h3>
          </div>
          {fansLoading ? (
            <Skeleton className="h-10" />
          ) : interests.length === 0 ? (
            <p className="text-sm text-gray-400">暂无兴趣数据</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {interests.map((tag, i) => (
                <Badge
                  key={tag}
                  label={tag}
                  color={interestColors[i % interestColors.length]}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Section 2: Notes Performance Table */}
      <div className="bg-white rounded-xl border border-gray-100 mb-6 hover:shadow-md transition-shadow duration-200">
        <div className="flex items-center gap-2 px-5 pt-5 pb-3">
          <BarChart3 size={16} className="text-amber-500" />
          <h3 className="text-sm font-semibold text-gray-700">笔记表现排行</h3>
          <span className="text-xs text-gray-400 ml-auto">共 {notes.length} 篇</span>
        </div>
        {analyticsLoading ? (
          <div className="px-5 pb-5">
            <Skeleton className="h-40" />
          </div>
        ) : notes.length === 0 ? (
          <EmptyState icon={BarChart3} text="暂无笔记数据" />
        ) : (
          <DataTable
            columns={columns}
            data={rankedNotes}
            defaultSort={{ key: 'impressions', dir: 'desc' }}
          />
        )}
      </div>

      {/* Section 3: Evolution Knowledge Base */}
      <div className="grid grid-cols-2 gap-4">
        {/* Winning Patterns */}
        <div className="bg-white rounded-xl border border-gray-100 p-5 hover:shadow-md transition-shadow duration-200">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles size={16} className="text-green-500" />
            <h3 className="text-sm font-semibold text-gray-700">有效模式</h3>
            <span className="text-xs text-gray-400 ml-auto">{winningPatterns.length} 条</span>
          </div>
          {evoLoading ? (
            <Skeleton className="h-40" />
          ) : winningPatterns.length === 0 ? (
            <EmptyState icon={Sparkles} text="暂无有效模式" />
          ) : (
            <div className="space-y-3 max-h-[400px] overflow-y-auto pr-1">
              {winningPatterns.map((wp) => (
                <div
                  key={wp.id}
                  className="bg-green-50 border border-green-100 rounded-lg p-3"
                >
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <p className="text-sm font-medium text-green-800 leading-snug">
                      {wp.pattern}
                    </p>
                    <Badge
                      label={wp.status === 'active' ? '生效' : wp.status}
                      color={wp.status === 'active' ? 'green' : 'gray'}
                    />
                  </div>
                  <p className="text-xs text-green-600 line-clamp-2 leading-relaxed">
                    {wp.evidence}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Losing Patterns */}
        <div className="bg-white rounded-xl border border-gray-100 p-5 hover:shadow-md transition-shadow duration-200">
          <div className="flex items-center gap-2 mb-4">
            <TrendingDown size={16} className="text-red-500" />
            <h3 className="text-sm font-semibold text-gray-700">失败模式</h3>
            <span className="text-xs text-gray-400 ml-auto">{losingPatterns.length} 条</span>
          </div>
          {evoLoading ? (
            <Skeleton className="h-40" />
          ) : losingPatterns.length === 0 ? (
            <EmptyState icon={AlertCircle} text="暂无失败模式" />
          ) : (
            <div className="space-y-3 max-h-[400px] overflow-y-auto pr-1">
              {losingPatterns.map((lp) => (
                <div
                  key={lp.id}
                  className="bg-red-50 border border-red-100 rounded-lg p-3"
                >
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <p className="text-sm font-medium text-red-800 leading-snug">
                      {lp.pattern}
                    </p>
                    {lp.status && (
                      <Badge
                        label={lp.status === 'active' ? '生效' : lp.status}
                        color={lp.status === 'active' ? 'red' : 'gray'}
                      />
                    )}
                  </div>
                  <p className="text-xs text-red-600 line-clamp-2 leading-relaxed">
                    {lp.evidence}
                  </p>
                  {lp.fix && (
                    <p className="text-xs text-red-500 mt-1 italic">
                      Fix: {lp.fix}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
