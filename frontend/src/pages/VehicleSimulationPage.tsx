import { useState, useEffect, useCallback, useRef } from 'react'
import { motion } from 'framer-motion'
import { apiService } from '../services/apiService'
import { useWebSocket } from '../hooks/useWebSocket'
import MetricCard from '../components/ui/MetricCard'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import {
  Play,
  Square,
  Pause,
  SkipForward,
  RotateCcw,
  Wind,
  Activity,
  AlertTriangle,
  Gauge,
  Zap,
  ShieldAlert,
} from 'lucide-react'

interface SpeedPoint { t: number; speed: number; target: number }
const MAX_PTS = 90

export default function VehicleSimulationPage() {
  const [status, setStatus] = useState<any>(null)
  const [telemetry, setTelemetry] = useState<any>(null)
  const [isWsConnected, setIsWsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [feedback, setFeedback] = useState<{ msg: string; ok: boolean } | null>(null)
  const [config, setConfig] = useState({ target_speed_kmh: 80, throttle_position_pct: 0 })
  const [history, setHistory] = useState<SpeedPoint[]>([])
  const tickRef = useRef(0)

  const showFeedback = (msg: string, ok = true) => {
    setFeedback({ msg, ok })
    setTimeout(() => setFeedback(null), 3000)
  }

  const fetchStatus = async () => {
    try {
      const res = await apiService.getStatus()
      setStatus(res.data)
    } catch { /* silent */ }
  }

  useEffect(() => {
    fetchStatus()
    apiService.getTelemetry().then((r) => setTelemetry(r.data)).catch(() => {})
    const iv = setInterval(fetchStatus, 3000)
    return () => clearInterval(iv)
  }, [])

  const handleMessage = useCallback((data: any) => {
    const d = data?.data
    if (!d) return
    setTelemetry(d)
    setIsWsConnected(true)
    tickRef.current += 1
    setHistory((prev) =>
      [...prev, { t: tickRef.current, speed: d.speed_kmh ?? 0, target: d.target_speed_kmh ?? 0 }].slice(-MAX_PTS)
    )
  }, [])

  const handleError = useCallback(() => setIsWsConnected(false), [])
  useWebSocket(handleMessage, handleError)

  const handleAction = async (action: 'start' | 'stop' | 'pause' | 'resume' | 'reset') => {
    setIsLoading(true)
    try {
      const map = {
        start: apiService.startSimulation,
        stop: apiService.stopSimulation,
        pause: apiService.pauseSimulation,
        resume: apiService.resumeSimulation,
        reset: apiService.resetSimulation,
      }
      const res = await map[action]()
      showFeedback(res.data.message, res.data.success !== false)
      setTimeout(fetchStatus, 400)
    } catch (e: any) {
      showFeedback(e?.response?.data?.detail ?? e.message, false)
    } finally {
      setIsLoading(false)
    }
  }

  const handleConfig = async () => {
    try {
      const res = await apiService.configSimulation(config)
      showFeedback(res.data.message)
    } catch (e: any) {
      showFeedback(e.message, false)
    }
  }

  const simRunning = status?.running && !status?.paused
  const simPaused = status?.running && status?.paused

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Simulation Véhicule</h1>
          <p className="text-sm text-gray-400 mt-1">Contrôle et télémétrie du véhicule simulé</p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`h-2 w-2 rounded-full ${
              simRunning
                ? 'bg-green-400 animate-pulse'
                : simPaused
                ? 'bg-yellow-400'
                : 'bg-gray-500'
            }`}
            aria-hidden="true"
          />
          <span className={`text-sm font-medium ${simRunning ? 'text-green-400' : simPaused ? 'text-yellow-400' : 'text-gray-400'}`}>
            {simRunning ? 'En cours' : simPaused ? 'En pause' : 'Arrêtée'}
          </span>
        </div>
      </div>

      {/* Feedback toast */}
      {feedback && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          className={`px-4 py-2 rounded-lg border text-sm ${
            feedback.ok
              ? 'bg-green-900/20 border-green-800 text-green-300'
              : 'bg-red-900/20 border-red-800 text-red-300'
          }`}
        >
          {feedback.msg}
        </motion.div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left: controls + config */}
        <div className="lg:col-span-1 space-y-4">
          {/* Control buttons */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <h2 className="text-sm font-semibold text-gray-300 mb-4">Contrôles</h2>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => handleAction('start')}
                disabled={isLoading || simRunning}
                className="flex items-center justify-center gap-1.5 px-3 py-2 bg-green-700 hover:bg-green-600 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg text-xs font-medium transition-colors"
                aria-label="Démarrer la simulation"
              >
                <Play className="h-3.5 w-3.5" aria-hidden="true" /> Démarrer
              </button>
              <button
                onClick={() => handleAction('stop')}
                disabled={isLoading || !status?.running}
                className="flex items-center justify-center gap-1.5 px-3 py-2 bg-red-700 hover:bg-red-600 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg text-xs font-medium transition-colors"
                aria-label="Arrêter la simulation"
              >
                <Square className="h-3.5 w-3.5" aria-hidden="true" /> Arrêter
              </button>
              <button
                onClick={() => handleAction('pause')}
                disabled={isLoading || !simRunning}
                className="flex items-center justify-center gap-1.5 px-3 py-2 bg-yellow-700 hover:bg-yellow-600 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg text-xs font-medium transition-colors"
                aria-label="Mettre en pause"
              >
                <Pause className="h-3.5 w-3.5" aria-hidden="true" /> Pause
              </button>
              <button
                onClick={() => handleAction('resume')}
                disabled={isLoading || !simPaused}
                className="flex items-center justify-center gap-1.5 px-3 py-2 bg-blue-700 hover:bg-blue-600 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg text-xs font-medium transition-colors"
                aria-label="Reprendre la simulation"
              >
                <SkipForward className="h-3.5 w-3.5" aria-hidden="true" /> Reprendre
              </button>
              <button
                onClick={() => handleAction('reset')}
                disabled={isLoading}
                className="col-span-2 flex items-center justify-center gap-1.5 px-3 py-2 bg-gray-700 hover:bg-gray-600 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg text-xs font-medium transition-colors"
                aria-label="Réinitialiser la simulation"
              >
                <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" /> Réinitialiser
              </button>
            </div>
          </div>

          {/* Config */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <h2 className="text-sm font-semibold text-gray-300 mb-4">Configuration</h2>
            <div className="space-y-4">
              <div>
                <label htmlFor="target-speed" className="block text-xs text-gray-400 mb-1">
                  Vitesse cible — <span className="text-white font-bold">{config.target_speed_kmh}</span> km/h
                </label>
                <input
                  id="target-speed"
                  type="range"
                  min={0}
                  max={200}
                  step={5}
                  value={config.target_speed_kmh}
                  onChange={(e) =>
                    setConfig((c) => ({ ...c, target_speed_kmh: Number(e.target.value) }))
                  }
                  className="w-full accent-violet-500"
                  aria-label="Vitesse cible en km/h"
                />
                <div className="flex justify-between text-xs text-gray-600 mt-0.5">
                  <span>0</span><span>200 km/h</span>
                </div>
              </div>
              <div>
                <label htmlFor="throttle" className="block text-xs text-gray-400 mb-1">
                  Accélérateur — <span className="text-white font-bold">{config.throttle_position_pct}</span> %
                </label>
                <input
                  id="throttle"
                  type="range"
                  min={0}
                  max={100}
                  step={5}
                  value={config.throttle_position_pct}
                  onChange={(e) =>
                    setConfig((c) => ({ ...c, throttle_position_pct: Number(e.target.value) }))
                  }
                  className="w-full accent-green-500"
                  aria-label="Position de l'accélérateur en pourcentage"
                />
                <div className="flex justify-between text-xs text-gray-600 mt-0.5">
                  <span>0 %</span><span>100 %</span>
                </div>
              </div>
              <button
                onClick={handleConfig}
                className="w-full py-2 bg-violet-600 hover:bg-violet-700 text-white rounded-lg text-xs font-semibold transition-colors"
              >
                Appliquer la configuration
              </button>
            </div>
          </div>

          {/* Sim info */}
          {status && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 text-xs space-y-2">
              <div className="flex justify-between">
                <span className="text-gray-400">Temps simulé</span>
                <span className="tabular-nums text-white">{(status.current_time ?? 0).toFixed(1)}s</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">WS</span>
                <span className={isWsConnected ? 'text-green-400' : 'text-red-400'}>
                  {isWsConnected ? 'Connecté' : 'Déconnecté'}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Right: telemetry + chart */}
        <div className="lg:col-span-3 space-y-5">
          {/* KPI row */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-3 gap-4">
            <MetricCard
              title="Vitesse"
              value={telemetry?.speed_kmh ?? 0}
              unit="km/h"
              icon={Wind}
              status={(telemetry?.speed_kmh ?? 0) > 130 ? 'error' : (telemetry?.speed_kmh ?? 0) > 100 ? 'warning' : 'neutral'}
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
              title="Accélérateur"
              value={telemetry?.throttle_position_pct ?? 0}
              unit="%"
              icon={Wind}
              status="neutral"
            />
            <MetricCard
              title="Frein"
              value={telemetry?.brake_pressure_bar ?? 0}
              unit="bar"
              icon={ShieldAlert}
              status={(telemetry?.brake_pressure_bar ?? 0) > 10 ? 'warning' : 'neutral'}
            />
            <MetricCard
              title="Obstacle"
              value={telemetry?.obstacle_distance_m ?? 0}
              unit="m"
              icon={AlertTriangle}
              status={telemetry?.obstacle_detected ? 'error' : 'neutral'}
            />
          </div>

          {/* ADAS row */}
          <div className="grid grid-cols-2 gap-4">
            <MetricCard
              title="FCW"
              value={telemetry?.fcw_active ? 'Actif' : 'Inactif'}
              unit=""
              icon={ShieldAlert}
              status={telemetry?.fcw_active ? 'warning' : 'neutral'}
            />
            <MetricCard
              title="AEB"
              value={telemetry?.aeb_active ? 'Actif 🛑' : 'Inactif'}
              unit=""
              icon={Zap}
              status={telemetry?.aeb_active ? 'error' : 'neutral'}
            />
          </div>

          {/* Speed chart */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <h2 className="text-sm font-semibold text-gray-300 mb-3">
              Évolution de la vitesse
            </h2>
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={history} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="gSpeed" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gTarget" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#7c3aed" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#7c3aed" stopOpacity={0} />
                  </linearGradient>
                </defs>
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
                  formatter={(v: number, name: string) => [
                    `${v.toFixed(1)} km/h`,
                    name === 'speed' ? 'Vitesse' : 'Cible',
                  ]}
                />
                <Area
                  type="monotone"
                  dataKey="target"
                  stroke="#7c3aed"
                  strokeDasharray="4 4"
                  strokeWidth={1.5}
                  fill="url(#gTarget)"
                  dot={false}
                  isAnimationActive={false}
                />
                <Area
                  type="monotone"
                  dataKey="speed"
                  stroke="#22c55e"
                  strokeWidth={2}
                  fill="url(#gSpeed)"
                  dot={false}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  )
}
