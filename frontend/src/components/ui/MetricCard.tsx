import { motion } from "framer-motion"
import { Card, CardContent, CardHeader, CardTitle } from "./card"

export default function MetricCard({
  title,
  value,
  unit,
  icon: IconComponent,
  status = "neutral",
  trend,
}: {
  title: string
  value: number | string
  unit: string
  icon: React.ElementType
  status?: "neutral" | "warning" | "error" | "success"
  trend?: { value: number; isUp: boolean }
}) {
  const statusColors = {
    neutral: "border-gray-700 bg-gray-900/80",
    warning: "border-yellow-600 bg-yellow-900/30",
    error: "border-red-600 bg-red-900/30",
    success: "border-green-600 bg-green-900/30",
  }

  return (
    <motion.div
      whileHover={{ y: -2 }}
      className="h-full flex flex-col"
    >
      <Card className={`h-full rounded-xl border ${statusColors[status]} shadow-sm`}>
        <CardHeader className="pb-3 px-3">
          <div className="flex items-start justify-between">
            <CardTitle className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider line-clamp-1">
              {title}
            </CardTitle>
            <IconComponent
              className="h-4 w-4 opacity-70"
              style={{ color: status === "neutral" ? "#9CA3AF" : status === "warning" ? "#FBBF24" : status === "error" ? "#F87171" : "#4ADE80" }}
            />
          </div>
        </CardHeader>
        <CardContent className="px-3 pb-3 flex-1 flex flex-col justify-center space-y-2">
          <div className="text-2xl font-bold tracking-tight leading-none text-gray-100">{typeof value === "number" ? value.toFixed(1) : value}</div>
          <div className="text-xs font-medium text-gray-500">{unit}</div>
          {trend && (
            <p className={`text-xs font-medium ${trend.isUp ? "text-green-400" : "text-red-400"}`}>
              {trend.isUp ? "↑" : "↓"} {Math.abs(trend.value).toFixed(1)}%
            </p>
          )}
        </CardContent>
      </Card>
    </motion.div>
  )
}
