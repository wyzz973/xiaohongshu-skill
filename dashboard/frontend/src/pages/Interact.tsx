import { useState, useMemo } from 'react'
import {
  MessageCircle,
  Heart,
  Bookmark,
  Search,
  Bell,
  Activity,
  Database,
} from 'lucide-react'
import TabNav from '../components/TabNav'
import Badge from '../components/Badge'
import { useNotifications, useLogs, useInteractIndex } from '../api/hooks'

const tabs = [
  { key: 'notifications', label: '通知日志' },
  { key: 'interact', label: '互动日志' },
  { key: 'dedup', label: '去重索引' },
]

// ---------------------------------------------------------------------------
// Notification Tab
// ---------------------------------------------------------------------------

interface NotifData {
  date?: string
  count?: number
  replied_ids?: string[]
}

interface LogEntry {
  time: string
  message: string
  level: string
  source?: string
}

function NotificationTab() {
  const { data: rawNotif } = useNotifications()
  const notifData = rawNotif as NotifData | undefined
  const today = new Date().toISOString().slice(0, 10)
  const { data: rawLogs, isLoading } = useLogs('notification', notifData?.date ?? today)
  const logsData = rawLogs as { logs?: LogEntry[] } | undefined

  const logs = logsData?.logs ?? []

  if (isLoading) {
    return <div className="text-center py-12 text-gray-400 text-sm">加载中...</div>
  }

  if (logs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="w-16 h-16 bg-gray-50 rounded-2xl flex items-center justify-center mb-4">
          <Bell size={28} className="text-gray-300" />
        </div>
        <p className="text-sm text-gray-400">暂无通知记录</p>
        {(notifData?.count ?? 0) > 0 && (
          <p className="text-xs text-gray-300 mt-2">
            最近回复了 {notifData?.count ?? 0} 条通知 ({notifData?.date ?? ''})
          </p>
        )}
      </div>
    )
  }

  return (
    <div>
      {(notifData?.count ?? 0) > 0 && (
        <div className="mb-4 px-4 py-2.5 bg-blue-50 rounded-xl text-xs text-blue-600">
          {notifData?.date ?? ''} 共回复 {notifData?.count ?? 0} 条通知
        </div>
      )}
      <div className="bg-white rounded-xl border border-gray-100 divide-y divide-gray-50">
        {logs.map((log, i) => (
          <div key={i} className="px-4 py-3 flex items-start gap-3 hover:bg-gray-50 transition-colors">
            <div className="w-8 h-8 bg-green-50 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
              <Bell size={14} className="text-green-500" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-700 leading-relaxed">{log.message}</p>
            </div>
            <span className="text-xs text-gray-400 flex-shrink-0">{log.time}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Interact Log Tab
// ---------------------------------------------------------------------------

function actionIcon(msg: string) {
  const lower = (msg as string).toLowerCase()
  if (lower.includes('comment') || lower.includes('评论'))
    return <MessageCircle size={14} className="text-blue-500" />
  if (lower.includes('like') || lower.includes('点赞'))
    return <Heart size={14} className="text-red-400" />
  if (lower.includes('favorite') || lower.includes('收藏'))
    return <Bookmark size={14} className="text-amber-500" />
  return <Activity size={14} className="text-gray-400" />
}

function InteractLogTab() {
  const today = new Date().toISOString().slice(0, 10)
  const { data: rawData, isLoading } = useLogs('interact', today)
  const data = rawData as { logs?: LogEntry[] } | undefined
  const logs = data?.logs ?? []

  if (isLoading) {
    return <div className="text-center py-12 text-gray-400 text-sm">加载中...</div>
  }

  if (logs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="w-16 h-16 bg-gray-50 rounded-2xl flex items-center justify-center mb-4">
          <Activity size={28} className="text-gray-300" />
        </div>
        <p className="text-sm text-gray-400">今日暂无互动记录</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-gray-100">
      <div className="divide-y divide-gray-50">
        {logs.map((log, i) => (
          <div key={i} className="px-4 py-3 flex items-center gap-3 hover:bg-gray-50 transition-colors">
            <div className="w-8 h-8 bg-gray-50 rounded-lg flex items-center justify-center flex-shrink-0">
              {actionIcon(log.message)}
            </div>
            <p className="text-sm text-gray-700 flex-1 min-w-0 truncate">
              {log.message}
            </p>
            <span className="text-xs text-gray-400 flex-shrink-0">{log.time}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Dedup Index Tab
// ---------------------------------------------------------------------------

function DedupIndexTab() {
  const { data: rawData, isLoading } = useInteractIndex()
  const data = rawData as { feeds?: Record<string, Record<string, unknown>> } | undefined
  const [search, setSearch] = useState('')

  const feeds = data?.feeds ?? {}

  const entries = useMemo(() => {
    const arr: { feedId: string; author: string; types: string[]; firstInteract: string }[] = []
    for (const [feedId, info] of Object.entries(feeds)) {
      const f = info as Record<string, unknown>
      arr.push({
        feedId,
        author: (f.author as string) ?? '',
        types: (f.types as string[]) ?? [],
        firstInteract: (f.first_interact as string) ?? '',
      })
    }
    // Sort by first_interact desc
    arr.sort((a, b) => b.firstInteract.localeCompare(a.firstInteract))
    return arr
  }, [feeds])

  const filtered = useMemo(() => {
    if (!search.trim()) return entries
    const q = search.trim().toLowerCase()
    return entries.filter(
      (e) => e.feedId.toLowerCase().includes(q) || e.author.toLowerCase().includes(q),
    )
  }, [entries, search])

  const typeBadge: Record<string, { label: string; color: 'blue' | 'red' | 'yellow' }> = {
    comment: { label: '评论', color: 'blue' },
    like: { label: '点赞', color: 'red' },
    favorite: { label: '收藏', color: 'yellow' },
  }

  if (isLoading) {
    return <div className="text-center py-12 text-gray-400 text-sm">加载中...</div>
  }

  return (
    <div>
      {/* Stats + Search */}
      <div className="flex items-center justify-between mb-4 gap-4">
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Database size={14} />
          <span>共 {entries.length} 条记录</span>
        </div>
        <div className="relative w-64">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="搜索帖子ID或作者..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm bg-white border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#FF2442]/20 focus:border-[#FF2442]/40 transition"
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50">
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">帖子ID</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">作者</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">互动类型</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">首次互动</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-12 text-center text-gray-400">
                  {search ? '未找到匹配记录' : '暂无互动索引'}
                </td>
              </tr>
            ) : (
              filtered.slice(0, 100).map((e) => (
                <tr key={e.feedId} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs text-gray-600" title={e.feedId}>
                    {e.feedId.length > 16 ? `${e.feedId.slice(0, 8)}...${e.feedId.slice(-6)}` : e.feedId}
                  </td>
                  <td className="px-4 py-3 text-gray-700">{e.author || '--'}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1 flex-wrap">
                      {e.types.map((t) => {
                        const b = typeBadge[t] ?? { label: t, color: 'blue' as const }
                        return <Badge key={t} label={b.label} color={b.color} />
                      })}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{e.firstInteract}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
        {filtered.length > 100 && (
          <div className="px-4 py-2 text-xs text-gray-400 bg-gray-50 text-center">
            显示前 100 条，共 {filtered.length} 条
          </div>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

export default function Interact() {
  const [activeTab, setActiveTab] = useState('notifications')

  return (
    <div className="p-6 max-w-[1200px] mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-9 h-9 bg-blue-50 rounded-xl flex items-center justify-center">
          <MessageCircle size={18} className="text-blue-500" />
        </div>
        <h1 className="text-lg font-bold text-gray-900">互动中心</h1>
      </div>

      <div className="mb-6">
        <TabNav tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />
      </div>

      {activeTab === 'notifications' && <NotificationTab />}
      {activeTab === 'interact' && <InteractLogTab />}
      {activeTab === 'dedup' && <DedupIndexTab />}
    </div>
  )
}
