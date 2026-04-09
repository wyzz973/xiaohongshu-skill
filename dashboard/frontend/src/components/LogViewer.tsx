import { useState, useRef, useEffect, useCallback } from 'react'
import { Search, ArrowDown, Filter } from 'lucide-react'

interface LogLine {
  text: string
  level: string
}

interface LogViewerProps {
  lines: LogLine[]
  loading?: boolean
  onLoadMore?: () => void
}

type LevelFilter = 'all' | 'cdp' | 'error' | 'warning'

function levelColor(level: string): string {
  switch (level) {
    case 'error':
      return 'text-red-400'
    case 'warning':
      return 'text-yellow-400'
    case 'success':
      return 'text-green-400'
    case 'cdp':
      return 'text-blue-400'
    default:
      return 'text-slate-300'
  }
}

export default function LogViewer({ lines, loading, onLoadMore }: LogViewerProps) {
  const [search, setSearch] = useState('')
  const [levelFilter, setLevelFilter] = useState<LevelFilter>('all')
  const [autoScroll, setAutoScroll] = useState(true)
  const [hasNew, setHasNew] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const prevLenRef = useRef(lines.length)

  const handleScroll = useCallback(() => {
    const el = containerRef.current
    if (!el) return
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40
    setAutoScroll(atBottom)
    if (atBottom) setHasNew(false)
  }, [])

  useEffect(() => {
    if (lines.length > prevLenRef.current && !autoScroll) {
      setHasNew(true)
    }
    prevLenRef.current = lines.length

    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [lines, autoScroll])

  const scrollToBottom = () => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
      setAutoScroll(true)
      setHasNew(false)
    }
  }

  const filtered = lines.filter((line) => {
    if (levelFilter !== 'all' && line.level !== levelFilter) return false
    if (search && !line.text.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const filterButtons: { label: string; value: LevelFilter }[] = [
    { label: 'All', value: 'all' },
    { label: 'CDP', value: 'cdp' },
    { label: 'Error', value: 'error' },
    { label: 'Warning', value: 'warning' },
  ]

  return (
    <div className="flex flex-col h-full bg-[#0f172a] rounded-xl overflow-hidden border border-slate-700">
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-700 bg-[#0f172a]">
        <div className="relative flex-1 max-w-xs">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search logs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-slate-800 text-slate-200 text-xs pl-8 pr-3 py-1.5 rounded-lg border border-slate-600 focus:outline-none focus:border-slate-400 placeholder:text-slate-500 font-mono"
          />
        </div>
        <Filter size={14} className="text-slate-500" />
        {filterButtons.map((btn) => (
          <button
            key={btn.value}
            onClick={() => setLevelFilter(btn.value)}
            className={`text-xs px-2 py-1 rounded-md cursor-pointer transition-colors duration-200 ${
              levelFilter === btn.value
                ? 'bg-slate-600 text-white'
                : 'text-slate-400 hover:bg-slate-700'
            }`}
          >
            {btn.label}
          </button>
        ))}
      </div>

      {/* Log content */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-3 font-mono text-xs leading-5 relative"
      >
        {filtered.map((line, i) => (
          <div key={i} className={`${levelColor(line.level)} whitespace-pre-wrap break-all`}>
            {line.text}
          </div>
        ))}
        {loading && (
          <div className="text-slate-500 animate-pulse">Loading...</div>
        )}
        {!loading && filtered.length === 0 && (
          <div className="text-slate-500 text-center py-8">No logs to display</div>
        )}
      </div>

      {/* New logs button */}
      {hasNew && (
        <button
          onClick={scrollToBottom}
          className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-1 bg-blue-600 text-white text-xs px-3 py-1.5 rounded-full shadow-lg cursor-pointer hover:bg-blue-500 transition-colors duration-200"
        >
          New logs <ArrowDown size={12} />
        </button>
      )}

      {onLoadMore && (
        <button
          onClick={onLoadMore}
          className="text-xs text-slate-500 hover:text-slate-300 py-1 cursor-pointer transition-colors duration-200"
        >
          Load more
        </button>
      )}
    </div>
  )
}
