import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

interface DataPoint {
  date: string
  impressions: number
  interactions: number
}

interface TrendChartProps {
  data: DataPoint[]
  height?: number
}

export default function TrendChart({ data, height = 280 }: TrendChartProps) {
  return (
    <div className="bg-white rounded-xl border border-[#f0f0f0] p-5 hover:shadow-md transition-shadow duration-200">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">趋势</h3>
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: -20 }}>
          <defs>
            <linearGradient id="fillImpressions" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#FF2442" stopOpacity={0.2} />
              <stop offset="100%" stopColor="#FF2442" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="fillInteractions" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#3B82F6" stopOpacity={0.2} />
              <stop offset="100%" stopColor="#3B82F6" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="date"
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 12, fill: '#9ca3af' }}
          />
          <YAxis
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 12, fill: '#9ca3af' }}
          />
          <Tooltip
            contentStyle={{
              borderRadius: 8,
              border: '1px solid #f0f0f0',
              boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
              fontSize: 13,
            }}
          />
          <Area
            type="monotone"
            dataKey="impressions"
            stroke="#FF2442"
            strokeWidth={2}
            fill="url(#fillImpressions)"
            name="曝光"
          />
          <Area
            type="monotone"
            dataKey="interactions"
            stroke="#3B82F6"
            strokeWidth={2}
            fill="url(#fillInteractions)"
            name="互动"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
