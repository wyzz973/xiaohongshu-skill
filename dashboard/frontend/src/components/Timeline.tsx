interface TimelineItem {
  type: string
  message: string
  time: string
}

interface TimelineProps {
  items: TimelineItem[]
}

function getRelativeTime(timeStr: string): string {
  const now = Date.now()
  const then = new Date(timeStr).getTime()
  const diff = now - then
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  return `${days}天前`
}

function dotColor(type: string): string {
  switch (type) {
    case 'publish':
      return 'bg-green-500'
    case 'comment':
      return 'bg-blue-500'
    case 'follow':
      return 'bg-yellow-500'
    case 'error':
      return 'bg-red-500'
    default:
      return 'bg-gray-400'
  }
}

export default function Timeline({ items }: TimelineProps) {
  const display = items.slice(0, 10)

  return (
    <div className="bg-white rounded-xl border border-[#f0f0f0] p-5 hover:shadow-md transition-shadow duration-200">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">动态</h3>
      <div className="space-y-3">
        {display.map((item, i) => (
          <div key={i} className="flex items-start gap-3">
            <div className="flex flex-col items-center pt-1.5">
              <div className={`w-2.5 h-2.5 rounded-full ${dotColor(item.type)}`} />
              {i < display.length - 1 && (
                <div className="w-px h-full min-h-[20px] bg-gray-200 mt-1" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-700 leading-snug truncate">
                {item.message}
              </p>
              <p className="text-xs text-gray-400 mt-0.5">
                {getRelativeTime(item.time)}
              </p>
            </div>
          </div>
        ))}
        {display.length === 0 && (
          <p className="text-sm text-gray-400 text-center py-4">暂无动态</p>
        )}
      </div>
    </div>
  )
}
