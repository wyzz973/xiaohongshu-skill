type BadgeColor = 'blue' | 'green' | 'red' | 'yellow' | 'purple' | 'pink' | 'gray'

interface BadgeProps {
  label: string
  color?: BadgeColor
}

const colorMap: Record<BadgeColor, string> = {
  blue: 'bg-blue-50 text-blue-600',
  green: 'bg-green-50 text-green-600',
  red: 'bg-red-50 text-red-600',
  yellow: 'bg-amber-50 text-amber-600',
  purple: 'bg-purple-50 text-purple-600',
  pink: 'bg-pink-50 text-pink-600',
  gray: 'bg-gray-100 text-gray-500',
}

export default function Badge({ label, color = 'gray' }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colorMap[color]}`}
    >
      {label}
    </span>
  )
}
