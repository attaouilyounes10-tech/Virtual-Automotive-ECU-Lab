import { motion } from 'framer-motion'
import { Card, CardContent, CardHeader, CardTitle } from './card'

export default function MetricCard({
  title,
  value,
  unit,
  icon: IconComponent,
  status = 'neutral',
  trend,
}: {
  title: string
  value: number | string
  unit: string
  icon: React.ElementType
  status?: 'neutral' | 'warning' | 'error' | 'success'
  trend?: { value: number; isUp: boolean }
}) {
  const statusColors = {
    neutral: 'border-gray-800 bg-gray-900/50',
    warning: 'border-yellow-800 bg-yellow-900/20',
    error: 'border-red-800 bg-red-900/20',
    success: 'border-green-800 bg-green-900/20',
  }

  const statusBorder = {
    neutral: 'border-l-gray-500',
    warning: 'border-l-yellow-500',
    error: 'border-l-red-500',
    success: 'border-l-green-500',
  }

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      className="h-full"
    >
      <Card
        className={`h-full border-l-4 ${statusColors[status]} ${statusBorder[status]}`}
      >
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-gray-400">{title}</CardTitle>
          <IconComponent
            className="h-4 w-4"
            style={{ color: status === 'neutral' ? '#6B7280' : status === 'warning' ? '#D97706' : status === 'error' ? '#EF4444' : '#22C55E' }}
          />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{typeof value === 'number' ? value.toFixed(2) : value}</div>
          <span className="text-sm font-normal text-gray-500">{unit}</span>
          {trend && (
            <p className={`text-xs mt-1 ${trend.isUp ? 'text-green-400' : 'text-red-400'}`}>
              {trend.isUp ? '↑' : '↓'} {Math.abs(trend.value).toFixed(2)}%
            </p>
          )}
        </CardContent>
      </Card>
    </motion.div>
  )
}