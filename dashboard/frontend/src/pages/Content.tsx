import { useState, useMemo } from 'react'
import {
  ChevronLeft,
  ChevronRight,
  FileText,
  Inbox,
} from 'lucide-react'
import TabNav from '../components/TabNav'
import Badge from '../components/Badge'
import DataTable, { type Column } from '../components/DataTable'
import { useContentCalendar, useDrafts, usePublished } from '../api/hooks'

const tabs = [
  { key: 'calendar', label: '选题日历' },
  { key: 'drafts', label: '草稿箱' },
  { key: 'published', label: '已发布' },
]

const weekDays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

function formatMonth(year: number, month: number): string {
  return `${year}-${String(month).padStart(2, '0')}`
}

function parseMonth(s: string): [number, number] {
  const [y, m] = s.split('-').map(Number)
  return [y, m]
}

// ---------------------------------------------------------------------------
// Calendar Tab
// ---------------------------------------------------------------------------

function CalendarTab() {
  const now = new Date()
  const [month, setMonth] = useState(formatMonth(now.getFullYear(), now.getMonth() + 1))
  const { data: rawData, isLoading } = useContentCalendar(month)
  const data = rawData as { items?: { date: string; topics: { title: string; status: string }[] }[] } | undefined
  const [year, mon] = parseMonth(month)

  function prev() {
    const d = new Date(year, mon - 2, 1)
    setMonth(formatMonth(d.getFullYear(), d.getMonth() + 1))
  }
  function next() {
    const d = new Date(year, mon, 1)
    setMonth(formatMonth(d.getFullYear(), d.getMonth() + 1))
  }

  // Build calendar grid
  const calendarDays = useMemo(() => {
    const firstDay = new Date(year, mon - 1, 1)
    // Monday=0 offset
    let startOffset = firstDay.getDay() - 1
    if (startOffset < 0) startOffset = 6
    const daysInMonth = new Date(year, mon, 0).getDate()

    const days: { date: number; inMonth: boolean; dateStr: string }[] = []
    // Previous month padding
    const prevMonthDays = new Date(year, mon - 1, 0).getDate()
    for (let i = startOffset - 1; i >= 0; i--) {
      days.push({ date: prevMonthDays - i, inMonth: false, dateStr: '' })
    }
    // Current month
    for (let d = 1; d <= daysInMonth; d++) {
      const dateStr = `${year}-${String(mon).padStart(2, '0')}-${String(d).padStart(2, '0')}`
      days.push({ date: d, inMonth: true, dateStr })
    }
    // Next month padding
    const remaining = 7 - (days.length % 7)
    if (remaining < 7) {
      for (let i = 1; i <= remaining; i++) {
        days.push({ date: i, inMonth: false, dateStr: '' })
      }
    }
    return days
  }, [year, mon])

  // Map date -> topics
  const topicsByDate = useMemo(() => {
    const map: Record<string, { title: string; status: string }[]> = {}
    if (!data?.items) return map
    for (const item of data.items) {
      const d = item.date
      if (!map[d]) map[d] = []
      for (const t of item.topics) {
        map[d].push({ title: t.title, status: t.status })
      }
    }
    return map
  }, [data])

  const statusColor: Record<string, string> = {
    selected: 'bg-blue-100 text-blue-700',
    planned: 'bg-blue-100 text-blue-700',
    candidate: 'bg-gray-100 text-gray-500',
    drafted: 'bg-amber-100 text-amber-700',
    published: 'bg-green-100 text-green-700',
  }

  return (
    <div>
      {/* Month selector */}
      <div className="flex items-center gap-4 mb-6">
        <button onClick={prev} className="p-1.5 rounded-lg hover:bg-gray-100 cursor-pointer transition-colors">
          <ChevronLeft size={18} className="text-gray-500" />
        </button>
        <span className="text-base font-semibold text-gray-800">
          {year}年{mon}月
        </span>
        <button onClick={next} className="p-1.5 rounded-lg hover:bg-gray-100 cursor-pointer transition-colors">
          <ChevronRight size={18} className="text-gray-500" />
        </button>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-gray-400 text-sm">加载中...</div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
          {/* Week header */}
          <div className="grid grid-cols-7 bg-gray-50">
            {weekDays.map((d) => (
              <div key={d} className="px-2 py-2.5 text-center text-xs font-medium text-gray-500">
                {d}
              </div>
            ))}
          </div>
          {/* Days grid */}
          <div className="grid grid-cols-7">
            {calendarDays.map((day, i) => {
              const topics = day.inMonth ? topicsByDate[day.dateStr] || [] : []
              return (
                <div
                  key={i}
                  className={`min-h-[90px] p-2 border-t border-r border-gray-50 ${
                    !day.inMonth ? 'bg-gray-50/50' : ''
                  }`}
                >
                  <span
                    className={`text-xs font-medium ${
                      day.inMonth ? 'text-gray-700' : 'text-gray-300'
                    }`}
                  >
                    {day.date}
                  </span>
                  <div className="mt-1 flex flex-col gap-0.5">
                    {topics.slice(0, 3).map((t, j) => (
                      <div
                        key={j}
                        className={`text-[10px] leading-tight px-1.5 py-0.5 rounded truncate ${
                          statusColor[t.status] || statusColor.planned
                        }`}
                        title={t.title}
                      >
                        {t.title}
                      </div>
                    ))}
                    {topics.length > 3 && (
                      <span className="text-[10px] text-gray-400">+{topics.length - 3} more</span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Drafts Tab
// ---------------------------------------------------------------------------

const formatBadge: Record<string, { label: string; color: 'blue' | 'purple' | 'pink' | 'green' }> = {
  '图文': { label: '图文', color: 'blue' },
  'long-article': { label: '长文', color: 'purple' },
  '长文': { label: '长文', color: 'purple' },
  'video': { label: '视频', color: 'green' },
  '视频': { label: '视频', color: 'green' },
  'text2image': { label: '文字配图', color: 'pink' },
}

function DraftsTab() {
  const { data: rawData, isLoading } = useDrafts()
  const data = rawData as { drafts?: Record<string, unknown>[] } | undefined
  const drafts = data?.drafts ?? []

  if (isLoading) {
    return <div className="text-center py-12 text-gray-400 text-sm">加载中...</div>
  }

  if (drafts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="w-16 h-16 bg-gray-50 rounded-2xl flex items-center justify-center mb-4">
          <Inbox size={28} className="text-gray-300" />
        </div>
        <p className="text-sm text-gray-400">暂无草稿</p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {drafts.map((d: Record<string, unknown>) => {
        const fmt = formatBadge[d.format as string] ?? { label: String(d.format), color: 'blue' as const }
        return (
          <div
            key={d.filename as string}
            className="bg-white rounded-xl border border-gray-100 p-5 hover:shadow-md transition-shadow"
          >
            <div className="flex items-start justify-between gap-3 mb-3">
              <h3 className="text-sm font-semibold text-gray-900 leading-snug line-clamp-2 flex-1">
                {d.title as string}
              </h3>
              <Badge label={fmt.label} color={fmt.color} />
            </div>
            <div className="flex items-center gap-4 text-xs text-gray-400">
              <span className="flex items-center gap-1">
                <FileText size={12} />
                {(d.word_count as number) > 0 ? `${d.word_count} 字` : '--'}
              </span>
              <span>{(d.created as string)?.slice(0, 10) || '--'}</span>
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Published Tab
// ---------------------------------------------------------------------------

function formatNum(n: unknown): string {
  const num = Number(n) || 0
  if (num >= 10000) return `${(num / 10000).toFixed(1)}万`
  return String(num)
}

function numColor(n: unknown): string {
  const num = Number(n) || 0
  return num > 0 ? 'text-green-600' : 'text-gray-400'
}

function PublishedTab() {
  const { data, isLoading } = usePublished()
  const notes = data ?? []

  const columns: Column<Record<string, unknown>>[] = [
    { key: 'date', label: '日期', sortable: true },
    {
      key: 'title',
      label: '标题',
      render: (row) => (
        <span className="font-medium text-gray-900 line-clamp-1 max-w-[220px]" title={String(row.title ?? '')}>
          {String(row.title ?? row.topic ?? '')}
        </span>
      ),
    },
    {
      key: 'type',
      label: '格式',
      render: (row) => {
        const t = String(row.type ?? row.format ?? '图文')
        const fmt = formatBadge[t] ?? { label: t, color: 'blue' as const }
        return <Badge label={fmt.label} color={fmt.color} />
      },
    },
    {
      key: 'impressions',
      label: '曝光',
      sortable: true,
      render: (row) => (
        <span className={numColor(row.impressions)}>{formatNum(row.impressions)}</span>
      ),
    },
    {
      key: 'click_through_rate',
      label: 'CTR',
      sortable: true,
      render: (row) => {
        const v = Number(row.click_through_rate) || 0
        return <span className={v > 0 ? 'text-green-600' : 'text-gray-400'}>{v > 0 ? `${v.toFixed(1)}%` : '--'}</span>
      },
    },
    {
      key: 'likes',
      label: '赞',
      sortable: true,
      render: (row) => <span className={numColor(row.likes)}>{formatNum(row.likes)}</span>,
    },
    {
      key: 'favorites',
      label: '藏',
      sortable: true,
      render: (row) => <span className={numColor(row.favorites)}>{formatNum(row.favorites)}</span>,
    },
    {
      key: 'comments',
      label: '评',
      sortable: true,
      render: (row) => <span className={numColor(row.comments)}>{formatNum(row.comments)}</span>,
    },
    {
      key: 'fans_gained',
      label: '涨粉',
      sortable: true,
      render: (row) => <span className={numColor(row.fans_gained)}>{formatNum(row.fans_gained)}</span>,
    },
  ]

  if (isLoading) {
    return <div className="text-center py-12 text-gray-400 text-sm">加载中...</div>
  }

  return (
    <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
      <DataTable columns={columns} data={notes as Record<string, unknown>[]} defaultSort={{ key: 'date', dir: 'desc' }} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

export default function Content() {
  const [activeTab, setActiveTab] = useState('calendar')

  return (
    <div className="p-6 max-w-[1200px] mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-9 h-9 bg-red-50 rounded-xl flex items-center justify-center">
          <FileText size={18} className="text-[#FF2442]" />
        </div>
        <h1 className="text-lg font-bold text-gray-900">内容管理</h1>
      </div>

      <div className="mb-6">
        <TabNav tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />
      </div>

      {activeTab === 'calendar' && <CalendarTab />}
      {activeTab === 'drafts' && <DraftsTab />}
      {activeTab === 'published' && <PublishedTab />}
    </div>
  )
}
