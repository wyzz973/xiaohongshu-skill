import { useState, useEffect, useCallback } from 'react'
import {
  PanelRightClose,
  PanelRightOpen,
  Activity,
  AlertTriangle,
} from 'lucide-react'
import LogViewer from '../components/LogViewer'
import { useCliLog, useDaemonStatus } from '../api/hooks'

interface LogLine {
  text: string
  level: string
}

export default function Monitor() {
  const [offset, setOffset] = useState(0)
  const [allLines, setAllLines] = useState<LogLine[]>([])
  const [panelOpen, setPanelOpen] = useState(true)
  const { data: daemon } = useDaemonStatus()
  const { data: logData } = useCliLog(offset)

  const daemonInfo = (daemon as Record<string, unknown>) ?? {}
  const logPayload = logData as { lines?: LogLine[]; nextOffset?: number } | undefined

  useEffect(() => {
    if (logPayload?.lines && logPayload.lines.length > 0) {
      setAllLines((prev) => [...prev, ...logPayload.lines!])
      if (logPayload.nextOffset !== undefined) {
        setOffset(logPayload.nextOffset)
      }
    }
  }, [logPayload])

  const handleLoadMore = useCallback(() => {
    // Trigger a re-fetch by updating offset
  }, [])

  const errorCount = allLines.filter((l) => l.level === 'error').length
  const recentErrors = allLines
    .filter((l) => l.level === 'error')
    .slice(-5)
    .reverse()

  return (
    <div className="flex h-full">
      {/* Main area */}
      <div className="flex-1 flex flex-col p-6 min-w-0">
        {/* Top bar */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-semibold text-gray-900">实时监控</h1>
            <div
              className={`flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full font-medium ${
                daemonInfo.running
                  ? 'bg-green-50 text-green-700'
                  : 'bg-red-50 text-red-700'
              }`}
            >
              <div
                className={`w-1.5 h-1.5 rounded-full ${
                  daemonInfo.running ? 'bg-green-500' : 'bg-red-500'
                }`}
              />
              {daemonInfo.running ? 'Running' : 'Stopped'}
            </div>
            {daemonInfo.session != null && (
              <span className="text-xs text-gray-400 font-mono">
                {String(daemonInfo.session)}
              </span>
            )}
            {daemonInfo.rebuilds != null && (
              <span className="text-xs text-gray-400">
                Rebuilds: {String(daemonInfo.rebuilds)}
              </span>
            )}
          </div>
          <button
            onClick={() => setPanelOpen(!panelOpen)}
            className="p-2 text-gray-400 hover:text-gray-600 cursor-pointer transition-colors duration-200"
          >
            {panelOpen ? <PanelRightClose size={18} /> : <PanelRightOpen size={18} />}
          </button>
        </div>

        {/* Log viewer */}
        <div className="flex-1 min-h-0">
          <LogViewer lines={allLines} onLoadMore={handleLoadMore} />
        </div>
      </div>

      {/* Right panel */}
      {panelOpen && (
        <div className="w-[280px] flex-shrink-0 border-l border-[#f0f0f0] bg-white p-4 overflow-y-auto">
          {/* Today stats */}
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5">
              <Activity size={14} />
              今日统计
            </h3>
            <div className="space-y-2">
              {[
                { label: '评论', value: String(daemonInfo.commentsToday ?? 0) },
                { label: '点赞', value: String(daemonInfo.likesToday ?? 0) },
                { label: '发布', value: String(daemonInfo.publishesToday ?? 0) },
              ].map((s) => (
                <div
                  key={s.label}
                  className="flex items-center justify-between text-sm"
                >
                  <span className="text-gray-500">{s.label}</span>
                  <span className="text-gray-800 font-medium">{s.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Recent errors */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5">
              <AlertTriangle size={14} className="text-red-500" />
              近期错误
              {errorCount > 0 && (
                <span className="ml-auto text-xs bg-red-50 text-red-600 px-1.5 py-0.5 rounded-full">
                  {errorCount}
                </span>
              )}
            </h3>
            <div className="space-y-2">
              {recentErrors.length === 0 ? (
                <p className="text-xs text-gray-400">暂无错误</p>
              ) : (
                recentErrors.map((err, i) => (
                  <div
                    key={i}
                    className="text-xs text-red-600 bg-red-50 p-2 rounded-lg break-all"
                  >
                    {err.text}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
