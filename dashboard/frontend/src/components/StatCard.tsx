import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface StatCardProps {
  label: string
  value: string | number
  change: string
  changeType: 'up' | 'down' | 'flat'
  percentile?: string
  bgColor?: string
}

export default function StatCard({
  label,
  value,
  change,
  changeType,
  percentile,
  bgColor = 'bg-gray-50',
}: StatCardProps) {
  const changeColor =
    changeType === 'up'
      ? 'text-green-500'
      : changeType === 'down'
        ? 'text-red-500'
        : 'text-gray-400'

  const ChangeIcon =
    changeType === 'up'
      ? TrendingUp
      : changeType === 'down'
        ? TrendingDown
        : Minus

  return (
    <div
      className={`${bgColor} rounded-xl p-5 border border-[#f0f0f0] hover:shadow-md transition-shadow duration-200 cursor-default`}
    >
      <p className="text-sm text-gray-500 mb-1">{label}</p>
      <p className="text-3xl font-bold text-gray-900">{value}</p>
      <div className="flex items-center gap-1.5 mt-2">
        <ChangeIcon size={16} className={changeColor} />
        <span className={`text-sm font-medium ${changeColor}`}>{change}</span>
        {percentile && (
          <span className="ml-auto text-xs bg-white/60 text-gray-500 px-2 py-0.5 rounded-full">
            {percentile}
          </span>
        )}
      </div>
    </div>
  )
}
