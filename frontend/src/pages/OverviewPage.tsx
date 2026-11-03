import { useState, useEffect, useCallback, useRef } from 'react'
import { apiService } from '../services/apiService'
import { useWebSocket } from '../hooks/useWebSocket'
import MetricCard from '../components/ui/MetricCard'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { Wind, Activity, AlertTriangle, Gauge, ShieldAlert, Zap } from 'lucide-react'

interface TelemetryPoint {
  t: number
  speed: number
  target: number
  obstacle: number
}

const MAX_HISTORY = 60 // 30 seconds at 2Hz

export default function OverviewPage() {
  const [telemetry, setTelemetry] = useState<any>(null)
  const [simStatus, setSimStatus] = useState<any>(null)
  const [history, setHistory] = useState<TelemetryPoint[]>([])
  const tickRef = useRef(0)

  useEffect(() => {
    apiService
      .getStatus()
      .then((res) => setSimStatus(res.data))
      .catch(console.error)
    apiService
      .getTelemetry()
      .then((res) => setTelemetry(res.data))
      .catch(console.error)
  }, [])

  const handleMessage = useCallback((data: any) => {
    const d = data?.data
    if (!d) return
    setTelemetry(d)
    tickRef.current += 1
    setHistory((prev) => {
      const next = [
        ...prev,
        {
          t: tickRef.current,
          speed: d.speed_kmh ?? 0,
          target: d.target_speed_kmh ?? 0,
          obstacle: d.obstacle_distance_m ?? 0,
        },
      ]
      return next.slice(-MAX_HISTORY)
    })
  }, [])

  const { isConnected } = useWebSocket(handleMessage)

  const riskLabel = (level: number) => {
    if (level === 0) return { text: 'Aucun', color: 'text-green-400' }
    if (level === 1) return { text: 'Faible', color: 'text-yellow-400' }
    if (level === 2) return { text: 'Moyen', color: 'text-orange-400' }
    return { text: 'Élevé', color: 'text-red-400' }
  }

  const risk = riskLabel(telemetry?.collision_risk_level ?? 0)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-white">Vue d'ensemble</h1>
          <p className="text-sm text-gray-400 mt-1">Télémétrie en temps réel — bus CAN virtuel</p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
              isConnected
                ? 'bg-green-900/20 border-green-800 text-green-400'
                : 'bg-gray-800 border-gray-700 text-gray-500'
            }`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${isConnected ? 'bg-green-400 animate-pulse' : 'bg-gray-500'}`}
              aria-hidden="true"
            />
            {isConnected ? 'En direct (2 Hz)' : 'Déconnecté'}
          </span>
        </div>
      </div>

      {/* Simulation status banner */}
      {simStatus && !simStatus.running && (
        <div className="flex items-center gap-3 px-4 py-3 bg-yellow-900/20 border border-yellow-800 rounded-lg">
          <AlertTriangle className="h-4 w-4 text-yellow-400 flex-shrink-0" aria-hidden="true" />
          <p className="text-sm text-yellow-300">
            La simulation est arrêtée. Rendez-vous sur{' '}
            <a href="/vehicle" className="underline font-medium hover:text-yellow-200">
              Simulation Véhicule
            </a>{' '}
            pour la démarrer.
          </p>
        </div>
      )}

      {/* KPI grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <MetricCard
          title="Vitesse"
          value={telemetry?.speed_kmh ?? 0}
          unit="km/h"
          icon={Wind}
          status={
            (telemetry?.speed_kmh ?? 0) > 130
              ? 'error'
              : (telemetry?.speed_kmh ?? 0) > 100
              ? 'warning'
              : 'neutral'
          }
        />
        <MetricCard
          title="Vitesse cible"
          value={telemetry?.target_speed_kmh ?? 0}
          unit="km/h"
          icon={Gauge}
          status="neutral"
        />
        <MetricCard
          title="Accélération"
          value={telemetry?.acceleration_mps2 ?? 0}
          unit="m/s²"
          icon={Activity}
          status={Math.abs(telemetry?.acceleration_mps2 ?? 0) > 3 ? 'warning' : 'neutral'}
        />
        <MetricCard
          title="Obstacle"
          value={telemetry?.obstacle_distance_m ?? 0}
          unit="m"
          icon={AlertTriangle}
          status={telemetry?.obstacle_detected ? 'error' : 'neutral'}
        />
        <MetricCard
          title="FCW"
          value={telemetry?.fcw_active ? 'Actif' : 'Inactif'}
          unit=""
          icon={ShieldAlert}
          status={telemetry?.fcw_active ? 'warning' : 'neutral'}
        />
        <MetricCard
          title="AEB"
          value={telemetry?.aeb_active ? 'Actif' : 'Inactif'}
          unit=""
          icon={Zap}
          status={telemetry?.aeb_active ? 'error' : 'neutral'}
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Speed chart */}
        <div className="lg:col-span-2 bg-gray-900 border border-gray-800 rounded-lg p-5">
          <h2 className="text-sm font-semibold text-gray-300 mb-4">Vitesse en temps réel</h2>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={history} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="t" hide />
              <YAxis
                domain={[0, 'auto']}
                tick={{ fill: '#6b7280', fontSize: 11 }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                contentStyle={{ background: '#111827', border: '1px solid #374151', fontSize: 12 }}
                labelFormatter={() => ''}
                formatter={(v: number) => [`${v.toFixed(1)} km/h`]}
              />
              <ReferenceLine
                y={telemetry?.target_speed_kmh ?? 0}
                stroke="#7c3aed"
                strokeDasharray="4 4"
                label={{ value: 'Cible', fill: '#7c3aed', fontSize: 10 }}
              />
              <Line
                type="monotone"
                dataKey="speed"
                stroke="#22c55e"
                strokeWidth={2}
                dot={false}
                name="Vitesse"
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Risk / ADAS panel */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-5 flex flex-col gap-4">
          <h2 className="text-sm font-semibold text-gray-300">État ADAS</h2>

          {/* Risk level */}
          <div className="flex-1 flex flex-col items-center justify-center gap-2">
            <p className="text-xs text-gray-500 uppercase tracking-wider">Risque collision</p>
            <span className={`text-4xl font-black ${risk.color}`}>{risk.text}</span>
            <div className="flex gap-1.5 mt-1">
              {[1, 2, 3].map((lvl) => (
                <div
                  key={lvl}
                  className={`h-2 w-10 rounded-full ${
                    (telemetry?.collision_risk_level ?? 0) >= lvl
                      ? lvl === 3
                        ? 'bg-red-500'
                        : lvl === 2
                        ? 'bg-orange-500'
                        : 'bg-yellow-500'
                      : 'bg-gray-700'
                  }`}
                  aria-hidden="true"
                />
              ))}
            </div>
          </div>

          {/* Details */}
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">Frein (bar)</span>
              <span className="text-white font-mono">
                {(telemetry?.brake_pressure_bar ?? 0).toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Vit. relative</span>
              <span className="text-white font-mono">
                {(telemetry?.relative_speed_mps ?? 0).toFixed(2)} m/s
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Accélérateur</span>
              <span className="text-white font-mono">
                {(telemetry?.throttle_position_pct ?? 0).toFixed(1)} %
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
