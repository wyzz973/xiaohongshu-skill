import { useState } from 'react'
import { RefreshCw, Clock } from 'lucide-react'
import StatCard from '../components/StatCard'
import TrendChart from '../components/TrendChart'
import Timeline from '../components/Timeline'
import { useDashboard, useTimeline, useActivity, useDaemonStatus } from '../api/hooks'
import { useAppStore } from '../stores/app'

type TimeRange = 'today' | '7d' | '30d'

// Skeleton block helper
function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`skeleton ${className}`} />
}

export default function Overview() {
  const [timeRange, setTimeRange] = useState<TimeRange>('today')
  const account = useAppStore((s) => s.currentAccount)
  const { data: dashboard, isLoading: dashLoading } = useDashboard()
  const { data: timeline } = useTimeline()
  const { data: activity } = useActivity()
  const { data: daemon } = useDaemonStatus()

  const stats = (dashboard as Record<string, unknown>) ?? {}
  const timelineItems = (timeline as Array<{ type: string; message: string; time: string }>) ?? []
  const activityData = (activity as Array<{ date: string; impressions: number; interactions: number }>) ?? []
  const daemonInfo = (daemon as Record<string, unknown>) ?? {}

  const rangeButtons: { label: string; value: TimeRange }[] = [
    { label: '今日', value: 'today' },
    { label: '7日', value: '7d' },
    { label: '30日', value: '30d' },
  ]

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">运营总览</h1>
          <p className="text-sm text-gray-400 mt-0.5">
            账号: {account} &middot; 更新于 {new Date().toLocaleTimeString('zh-CN')}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {rangeButtons.map((btn) => (
            <button
              key={btn.value}
              onClick={() => setTimeRange(btn.value)}
              className={`text-sm px-3 py-1.5 rounded-lg cursor-pointer transition-colors duration-200 ${
                timeRange === btn.value
                  ? 'bg-[#FF2442] text-white'
                  : 'bg-white text-gray-500 border border-[#f0f0f0] hover:bg-gray-50'
              }`}
            >
              {btn.label}
            </button>
          ))}
          <button className="p-2 text-gray-400 hover:text-gray-600 cursor-pointer transition-colors duration-200">
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      {/* Row 1: Stat cards */}
      {dashLoading ? (
        <div className="grid grid-cols-4 gap-4 mb-6">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-4 gap-4 mb-6">
          <StatCard
            label="粉丝"
            value={(stats.followers as string | number) ?? '--'}
            change={(stats.followersChange as string) ?? '+0'}
            changeType={((stats.followersChangeType as 'up' | 'down' | 'flat') ?? 'flat')}
            bgColor="bg-red-50"
          />
          <StatCard
            label="曝光"
            value={(stats.impressions as string | number) ?? '--'}
            change={(stats.impressionsChange as string) ?? '+0'}
            changeType={((stats.impressionsChangeType as 'up' | 'down' | 'flat') ?? 'flat')}
            bgColor="bg-yellow-50"
          />
          <StatCard
            label="互动"
            value={(stats.interactions as string | number) ?? '--'}
            change={(stats.interactionsChange as string) ?? '+0'}
            changeType={((stats.interactionsChangeType as 'up' | 'down' | 'flat') ?? 'flat')}
            bgColor="bg-purple-50"
          />
          <StatCard
            label="CTR"
            value={(stats.ctr as string | number) ?? '--'}
            change={(stats.ctrChange as string) ?? '+0%'}
            changeType={((stats.ctrChangeType as 'up' | 'down' | 'flat') ?? 'flat')}
            bgColor="bg-blue-50"
          />
        </div>
      )}

      {/* Row 2: Trend + Timeline */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="col-span-2">
          <TrendChart data={activityData} />
        </div>
        <div className="col-span-1">
          <Timeline items={timelineItems} />
        </div>
      </div>

      {/* Row 3: Daemon status + Quota */}
      <div className="grid grid-cols-2 gap-4">
        {/* Daemon status */}
        <div className="bg-white rounded-xl border border-[#f0f0f0] p-5 hover:shadow-md transition-shadow duration-200">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">守护进程</h3>
          <div className="flex items-center gap-3 mb-3">
            <div
              className={`w-3 h-3 rounded-full ${
                daemonInfo.running ? 'bg-green-500' : 'bg-red-500'
              }`}
            />
            <span className="text-sm font-medium text-gray-700">
              {daemonInfo.running ? 'Running' : 'Stopped'}
            </span>
          </div>
          <div className="space-y-1.5 text-sm text-gray-500">
            {daemonInfo.pid != null && (
              <p>
                PID: <span className="text-gray-700 font-mono">{String(daemonInfo.pid)}</span>
              </p>
            )}
            {daemonInfo.session != null && (
              <p>
                Session: <span className="text-gray-700 font-mono">{String(daemonInfo.session)}</span>
              </p>
            )}
            {daemonInfo.uptime != null && (
              <div className="flex items-center gap-1">
                <Clock size={14} />
                <span>{String(daemonInfo.uptime)}</span>
              </div>
            )}
          </div>
        </div>

        {/* Today quota */}
        <div className="bg-white rounded-xl border border-[#f0f0f0] p-5 hover:shadow-md transition-shadow duration-200">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">今日配额</h3>
          <div className="space-y-4">
            {[
              { label: '评论', used: Number(stats.commentsToday ?? 0), max: 100, color: 'bg-blue-500' },
              { label: '点赞', used: Number(stats.likesToday ?? 0), max: 50, color: 'bg-yellow-500' },
              { label: '发布', used: Number(stats.publishesToday ?? 0), max: 4, color: 'bg-green-500' },
            ].map((q) => (
              <div key={q.label}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-gray-500">{q.label}</span>
                  <span className="text-sm text-gray-700 font-medium">
                    {q.used}/{q.max}
                  </span>
                </div>
                <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${q.color} rounded-full transition-all duration-500`}
                    style={{ width: `${Math.min((q.used / q.max) * 100, 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
