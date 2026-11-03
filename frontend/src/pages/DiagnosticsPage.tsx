import { useState, useEffect, useCallback, useRef } from "react"
import { apiService } from "../services/apiService"
import { useWebSocket } from "../hooks/useWebSocket"
import { AlertTriangle, AlertCircle, CheckCircle, Info, Trash2 } from "lucide-react"

interface DiagEvent {
  id: number
  time: Date
  level: "info" | "warning" | "error"
  message: string
  source: string
}

let eventSeq = 0

export default function DiagnosticsPage() {
  const [telemetry, setTelemetry] = useState<any>(null)
  const [simStatus, setSimStatus] = useState<any>(null)
  const [isWsConnected, setIsWsConnected] = useState(false)
  const [events, setEvents] = useState<DiagEvent[]>([])
  const prevRiskRef = useRef(0)

  const addEvent = (level: DiagEvent["level"], message: string, source: string) => {
    setEvents((prev) => [
      { id: eventSeq++, time: new Date(), level, message, source },
      ...prev.slice(0, 99),
    ])
  }

  useEffect(() => {
    apiService
      .getStatus()
      .then((res) => {
        setSimStatus(res.data)
        setTelemetry(res.data.vehicle_state)
      })
      .catch((e) => addEvent("error", `Impossible de contacter le backend: ${e.message}`, "API"))

    apiService.getHealth().then(() => addEvent("info", "Backend operationnel", "Health")).catch(() => {})
  }, [])

  const handleMessage = useCallback(
    (data: any) => {
      const d = data?.data
      if (!d) return
      setTelemetry(d)
      setIsWsConnected(true)

      const risk = d.collision_risk_level ?? 0
      if (risk > prevRiskRef.current) {
        const labels = ["", "Faible", "Moyen", "Eleve"]
        addEvent(
          risk >= 3 ? "error" : "warning",
          `Risque collision passee a niveau ${labels[risk] ?? risk}`,
          "ADAS_ECU"
        )
      }
      if (d.aeb_active && !prevRiskRef.current) {
        addEvent("error", "AEB declenche - freinage durgence autonome", "ADAS_ECU")
      }
      if (d.fcw_active && risk === 2) {
        addEvent("warning", "FCW actif - alerte collision avant", "ADAS_ECU")
      }
      prevRiskRef.current = risk
    },
    []
  )

  const handleError = useCallback((err: any) => {
    setIsWsConnected(false)
    addEvent("warning", `WebSocket deconnecte: ${err?.message ?? "connexion perdue"}`, "WebSocket")
  }, [])

  useWebSocket(handleMessage, handleError)

  const levelIcon = {
    info: <Info className="h-4 w-4 text-blue-400 flex-shrink-0" aria-hidden="true" />,
    warning: <AlertTriangle className="h-4 w-4 text-yellow-400 flex-shrink-0" aria-hidden="true" />,
    error: <AlertCircle className="h-4 w-4 text-red-400 flex-shrink-0" aria-hidden="true" />,
  }

  const levelBg = {
    info: "bg-blue-900/10 border-blue-900",
    warning: "bg-yellow-900/10 border-yellow-900",
    error: "bg-red-900/20 border-red-900",
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Diagnostics</h1>
        <p className="text-sm text-gray-400 mt-1">Surveillance des alertes, etats systeme et journal devenements</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <p className="text-xs text-gray-500 mb-2">WebSocket</p>
          <div className="flex items-center gap-2">
            {isWsConnected ? (
              <CheckCircle className="h-5 w-5 text-green-400" aria-hidden="true" />
            ) : (
              <AlertCircle className="h-5 w-5 text-red-400" aria-hidden="true" />
            )}
            <span className={`font-semibold text-sm ${isWsConnected ? "text-green-400" : "text-red-400"}`}>
              {isWsConnected ? "Connecte" : "Deconnecte"}
            </span>
          </div>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <p className="text-xs text-gray-500 mb-2">Simulation</p>
          <div className="flex items-center gap-2">
            {simStatus?.running ? (
              <CheckCircle className="h-5 w-5 text-green-400" aria-hidden="true" />
            ) : (
              <AlertCircle className="h-5 w-5 text-yellow-400" aria-hidden="true" />
            )}
            <span className={`font-semibold text-sm ${simStatus?.running ? "text-green-400" : "text-yellow-400"}`}>
              {simStatus?.running ? (simStatus?.paused ? "En pause" : "Active") : "Arretee"}
            </span>
          </div>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <p className="text-xs text-gray-500 mb-2">Risque collision</p>
          <div className="flex items-center gap-2">
            <span
              className={`font-bold text-base ${
                (telemetry?.collision_risk_level ?? 0) >= 3
                  ? "text-red-400"
                  : (telemetry?.collision_risk_level ?? 0) >= 2
                  ? "text-orange-400"
                  : (telemetry?.collision_risk_level ?? 0) >= 1
                  ? "text-yellow-400"
                  : "text-green-400"
              }`}
            >
              {["Aucun", "Faible", "Moyen", "Eleve"][telemetry?.collision_risk_level ?? 0] ?? "-"}
            </span>
          </div>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <p className="text-xs text-gray-500 mb-2">Evenements enregistres</p>
          <span className="font-bold text-base text-white">{events.length}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
          <h2 className="text-sm font-semibold text-gray-300 mb-4">Etat ADAS</h2>
          <div className="space-y-3">
            {[{ label: "FCW (Forward Collision Warning)", active: telemetry?.fcw_active, activeText: "Alerte active", inactiveText: "Inactif", color: "yellow" }, { label: "AEB (Autonomous Emergency Braking)", active: telemetry?.aeb_active, activeText: "Freinage en cours", inactiveText: "Inactif", color: "red" }, { label: "Detection obstacle", active: telemetry?.obstacle_detected, activeText: `Detecte a ${(telemetry?.obstacle_distance_m ?? 0).toFixed(1)} m`, inactiveText: "Aucun obstacle", color: "orange" }].map((item) => (
              <div
                key={item.label}
                className={`flex items-center justify-between p-3 rounded-lg border ${
                  item.active ? `bg-${item.color}-900/10 border-${item.color}-800` : "bg-gray-800 border-gray-700"
                }`}
              >
                <div>
                  <p className="text-sm font-medium text-gray-200">{item.label}</p>
                  <p className={`text-xs mt-0.5 ${item.active ? `text-${item.color}-400` : "text-gray-500"}`}>{item.active ? item.activeText : item.inactiveText}</p>
                </div>
                {item.active ? <AlertTriangle className={`h-5 w-5 text-${item.color}-400`} aria-hidden="true" /> : <CheckCircle className="h-5 w-5 text-gray-600" aria-hidden="true" />}
              </div>
            ))}
          </div>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
          <h2 className="text-sm font-semibold text-gray-300 mb-4">Metriques vehicule</h2>
          <div className="space-y-2 text-sm">
            {[["Vitesse", `${(telemetry?.speed_kmh ?? 0).toFixed(2)} km/h`], ["Vitesse cible", `${(telemetry?.target_speed_kmh ?? 0).toFixed(2)} km/h`], ["Acceleration", `${(telemetry?.acceleration_mps2 ?? 0).toFixed(3)} m/s2`], ["Accelerateur", `${(telemetry?.throttle_position_pct ?? 0).toFixed(1)} %`], ["Pression frein", `${(telemetry?.brake_pressure_bar ?? 0).toFixed(2)} bar`], ["Vit. relative obst.", `${(telemetry?.relative_speed_mps ?? 0).toFixed(2)} m/s`]].map(([label, val]) => (
              <div key={label} className="flex justify-between items-center py-1.5 border-b border-gray-800 last:border-0">
                <span className="text-gray-400">{label}</span>
                <span className="font-mono text-white text-xs">{val}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-sm font-semibold text-gray-300">Journal devenements</h2>
          {events.length > 0 && (
            <button
              onClick={() => setEvents([])}
              className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-white transition-colors"
              aria-label="Effacer le journal"
            >
              <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
              Effacer
            </button>
          )}
        </div>

        {events.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-8">Aucun evenement enregistre.</p>
        ) : (
          <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
            {events.map((ev) => (
              <div key={ev.id} className={`flex items-start gap-3 px-3 py-2 rounded-lg border ${levelBg[ev.level]}`}>
                {levelIcon[ev.level]}
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-gray-200 break-words">{ev.message}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{ev.source} - {ev.time.toLocaleTimeString()}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
