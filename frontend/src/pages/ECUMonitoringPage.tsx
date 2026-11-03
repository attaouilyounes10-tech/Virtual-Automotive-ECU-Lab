import { useState, useEffect, useCallback, useRef } from 'react'
import { apiService } from '../services/apiService'
import { useWebSocket } from '../hooks/useWebSocket'
import { Activity, AlertTriangle, Monitor, CheckCircle, XCircle } from 'lucide-react'

interface ECUState {
  id: string
  type: string
  active: boolean
  description: string
  publishedMessages: string[]
  listenedMessages: string[]
  metrics: { label: string; value: string; highlight?: boolean }[]
  statusColor: string
}

export default function ECUMonitoringPage() {
  const [telemetry, setTelemetry] = useState<any>(null)
  const [msgCounts, setMsgCounts] = useState({ adas: 0, vcu: 0, dash: 0 })
  const countsRef = useRef({ adas: 0, vcu: 0, dash: 0 })

  useEffect(() => {
    apiService
      .getStatus()
      .then((res) => setTelemetry(res.data.vehicle_state ?? res.data))
      .catch(console.error)
  }, [])

  const handleMessage = useCallback((data: any) => {
    const d = data?.data
    if (!d) return
    setTelemetry(d)
    // Increment counters to show liveness
    countsRef.current = {
      adas: countsRef.current.adas + 1,
      vcu: countsRef.current.vcu + 1,
      dash: countsRef.current.dash + (d.collision_risk_level > 0 ? 1 : 0),
    }
    setMsgCounts({ ...countsRef.current })
  }, [])

  useWebSocket(handleMessage)

  const ecus: ECUState[] = [
    {
      id: 'ADAS_ECU',
      type: 'ADAS',
      active: true,
      description: 'Advanced Driver Assistance System — détection obstacles et freinage autonome',
      publishedMessages: ['ADAS_STATUS (0x100)', 'COLLISION_WARNING (0x101)', 'BRAKE_COMMAND (0x201)'],
      listenedMessages: ['VEHICLE_STATUS (0x200)'],
      statusColor: telemetry?.fcw_active || telemetry?.aeb_active ? 'text-yellow-400 border-yellow-600' : 'text-green-400 border-green-700',
      metrics: [
        {
          label: 'Distance obstacle',
          value: `${(telemetry?.obstacle_distance_m ?? 0).toFixed(1)} m`,
          highlight: telemetry?.obstacle_detected,
        },
        {
          label: 'Risque collision',
          value: ['Aucun', 'Faible', 'Moyen', 'Élevé'][telemetry?.collision_risk_level ?? 0] ?? '—',
          highlight: (telemetry?.collision_risk_level ?? 0) >= 2,
        },
        { label: 'FCW', value: telemetry?.fcw_active ? 'Actif ⚠' : 'Inactif' },
        { label: 'AEB', value: telemetry?.aeb_active ? 'Actif 🛑' : 'Inactif' },
        { label: 'Messages publiés', value: String(msgCounts.adas) },
      ],
    },
    {
      id: 'VCU',
      type: 'VCU',
      active: true,
      description: 'Vehicle Control Unit — gestion vitesse, accélération et freinage',
      publishedMessages: ['VEHICLE_STATUS (0x200)'],
      listenedMessages: ['BRAKE_COMMAND (0x201)'],
      statusColor: 'text-blue-400 border-blue-700',
      metrics: [
        {
          label: 'Vitesse',
          value: `${(telemetry?.speed_kmh ?? 0).toFixed(1)} km/h`,
          highlight: (telemetry?.speed_kmh ?? 0) > 130,
        },
        { label: 'Vitesse cible', value: `${(telemetry?.target_speed_kmh ?? 0).toFixed(1)} km/h` },
        { label: 'Accélération', value: `${(telemetry?.acceleration_mps2 ?? 0).toFixed(2)} m/s²` },
        { label: 'Accélérateur', value: `${(telemetry?.throttle_position_pct ?? 0).toFixed(1)} %` },
        {
          label: 'Pression frein',
          value: `${(telemetry?.brake_pressure_bar ?? 0).toFixed(2)} bar`,
          highlight: (telemetry?.brake_pressure_bar ?? 0) > 10,
        },
        { label: 'Messages publiés', value: String(msgCounts.vcu) },
      ],
    },
    {
      id: 'Dashboard_ECU',
      type: 'Dashboard',
      active: true,
      description: "Interface tableau de bord — agrégation des alertes et affichage conducteur",
      publishedMessages: ['DASHBOARD_ALERT (0x300)'],
      listenedMessages: ['ADAS_STATUS (0x100)', 'COLLISION_WARNING (0x101)', 'VEHICLE_STATUS (0x200)'],
      statusColor: 'text-purple-400 border-purple-700',
      metrics: [
        {
          label: 'Alertes actives',
          value: (telemetry?.collision_risk_level ?? 0) > 0 ? 'Oui' : 'Non',
          highlight: (telemetry?.collision_risk_level ?? 0) > 0,
        },
        {
          label: 'Niveau alerte',
          value: String(telemetry?.collision_risk_level ?? 0),
        },
        {
          label: 'Obstacle détecté',
          value: telemetry?.obstacle_detected ? 'Oui' : 'Non',
          highlight: telemetry?.obstacle_detected,
        },
        { label: 'Messages publiés', value: String(msgCounts.dash) },
      ],
    },
  ]

  const icons = [AlertTriangle, Activity, Monitor]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Monitoring ECU</h1>
        <p className="text-sm text-gray-400 mt-1">
          Surveillance en temps réel des unités de contrôle embarqué
        </p>
      </div>

      {/* ECU Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {ecus.map((ecu, idx) => {
          const Icon = icons[idx]
          return (
            <div
              key={ecu.id}
              className={`bg-gray-900 border rounded-xl p-6 flex flex-col gap-4 ${ecu.statusColor.split(' ')[1]}`}
            >
              {/* Header */}
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-lg bg-gray-800 flex items-center justify-center">
                    <Icon className={`h-5 w-5 ${ecu.statusColor.split(' ')[0]}`} aria-hidden="true" />
                  </div>
                  <div>
                    <h2 className="font-bold text-white text-base leading-none">{ecu.id}</h2>
                    <p className={`text-xs mt-0.5 ${ecu.statusColor.split(' ')[0]}`}>{ecu.type}</p>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  {ecu.active ? (
                    <CheckCircle className="h-4 w-4 text-green-400" aria-label="ECU actif" />
                  ) : (
                    <XCircle className="h-4 w-4 text-red-400" aria-label="ECU inactif" />
                  )}
                  <span className={`text-xs ${ecu.active ? 'text-green-400' : 'text-red-400'}`}>
                    {ecu.active ? 'Actif' : 'Inactif'}
                  </span>
                </div>
              </div>

              <p className="text-xs text-gray-400 leading-relaxed">{ecu.description}</p>

              {/* Metrics */}
              <div className="space-y-1.5">
                {ecu.metrics.map((m) => (
                  <div key={m.label} className="flex justify-between items-center text-sm">
                    <span className="text-gray-400">{m.label}</span>
                    <span
                      className={`font-medium tabular-nums ${
                        m.highlight ? 'text-red-400' : 'text-white'
                      }`}
                    >
                      {m.value}
                    </span>
                  </div>
                ))}
              </div>

              {/* CAN message info */}
              <div className="border-t border-gray-800 pt-3 space-y-2">
                <div>
                  <p className="text-xs text-gray-500 mb-1">Publie :</p>
                  <div className="flex flex-wrap gap-1">
                    {ecu.publishedMessages.map((m) => (
                      <span
                        key={m}
                        className="px-1.5 py-0.5 bg-violet-900/30 border border-violet-800 rounded text-xs text-violet-300 font-mono"
                      >
                        {m}
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-xs text-gray-500 mb-1">Écoute :</p>
                  <div className="flex flex-wrap gap-1">
                    {ecu.listenedMessages.map((m) => (
                      <span
                        key={m}
                        className="px-1.5 py-0.5 bg-gray-800 border border-gray-700 rounded text-xs text-gray-300 font-mono"
                      >
                        {m}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Bus topology diagram */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h2 className="text-sm font-semibold text-gray-300 mb-4">Topologie du bus CAN</h2>
        <div className="flex flex-col sm:flex-row items-center justify-around gap-4 text-center text-xs">
          {['ADAS_ECU', 'VCU', 'Dashboard_ECU', 'Diagnostic_ECU'].map((node) => (
            <div key={node} className="flex flex-col items-center gap-2">
              <div className="h-10 w-10 rounded-full bg-violet-900/40 border border-violet-700 flex items-center justify-center text-violet-300 font-bold text-xs">
                ECU
              </div>
              <span className="text-gray-400">{node}</span>
            </div>
          ))}
        </div>
        <div className="mt-4 flex items-center justify-center">
          <div className="h-px w-full max-w-md bg-gradient-to-r from-transparent via-violet-600 to-transparent" aria-hidden="true" />
        </div>
        <p className="text-center text-xs text-gray-500 mt-2">Bus CAN virtuel — 500 kbit/s simulé</p>
      </div>
    </div>
  )
}
