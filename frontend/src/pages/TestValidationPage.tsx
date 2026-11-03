import { useState } from "react"
import { apiService } from "../services/apiService"
import { CheckCircle, XCircle, Clock, Play } from "lucide-react"

type TestStatus = "pending" | "running" | "passed" | "failed"

interface TestResult {
  name: string
  status: TestStatus
  message: string
  duration?: number
}

const TESTS = [
  {
    name: "GET /api/health",
    description: "Verifie que le backend repond",
    fn: async () => {
      const res = await apiService.getHealth()
      if (res.data.status !== "ok") throw new Error(`Status inattendu: ${res.data.status}`)
      return `OK - service: ${res.data.service}`
    },
  },
  {
    name: "GET /api/status",
    description: "Verifie letat de la simulation",
    fn: async () => {
      const res = await apiService.getStatus()
      const { running, paused, current_time } = res.data
      return `running=${running}, paused=${paused}, t=${current_time?.toFixed(2) ?? "0"}s`
    },
  },
  {
    name: "GET /api/telemetry",
    description: "Verifie les donnees de telemetrie",
    fn: async () => {
      const res = await apiService.getTelemetry()
      const d = res.data
      if (!("speed_kmh" in d)) throw new Error("Champ speed_kmh manquant")
      if (!("collision_risk_level" in d)) throw new Error("Champ collision_risk_level manquant")
      return `speed=${d.speed_kmh} km/h, risk=${d.collision_risk_level}`
    },
  },
  {
    name: "GET /api/can/frames",
    description: "Verifie le bus CAN",
    fn: async () => {
      const res = await apiService.getCanFrames(10)
      const { frames, total } = res.data
      if (!Array.isArray(frames)) throw new Error("Reponse malformee: frames absent")
      return `${frames.length} trames recentes / ${total} total`
    },
  },
  {
    name: "GET /api/health/detailed",
    description: "Verifie le health check detaille",
    fn: async () => {
      const res = await apiService.getHealthDetailed()
      if (res.data.status !== "ok") throw new Error("Status degrade")
      return `Simulation: ${res.data.simulation?.is_running ? "active" : "arrete"}`
    },
  },
  {
    name: "POST /api/simulation/start -> stop",
    description: "Cycle demarrage / arret de la simulation",
    fn: async () => {
      const startRes = await apiService.startSimulation()
      if (!startRes.data.success && !startRes.data.message.includes("already")) {
        throw new Error(`Start echoue: ${startRes.data.message}`)
      }
      await new Promise((r) => setTimeout(r, 800))
      const statusRes = await apiService.getStatus()
      if (!statusRes.data.running) throw new Error("Simulation non active apres start")
      const stopRes = await apiService.stopSimulation()
      if (!stopRes.data.success) throw new Error(`Stop echoue: ${stopRes.data.message}`)
      return "Start -> running -> Stop OK"
    },
  },
  {
    name: "POST /api/simulation/config",
    description: "Configure la vitesse cible",
    fn: async () => {
      const res = await apiService.configSimulation({ target_speed_kmh: 90 })
      if (!res.data.success) throw new Error(`Config echoue: ${res.data.message}`)
      return `Config appliquee: ${res.data.message}`
    },
  },
]

export default function TestValidationPage() {
  const [results, setResults] = useState<TestResult[]>([])
  const [isRunning, setIsRunning] = useState(false)

  const updateResult = (idx: number, update: Partial<TestResult>) => {
    setResults((prev) => {
      const next = [...prev]
      next[idx] = { ...next[idx], ...update }
      return next
    })
  }

  const runTests = async () => {
    setIsRunning(true)
    setResults([])

    const initial: TestResult[] = TESTS.map((t) => ({
      name: t.name,
      status: "pending",
      message: t.description,
    }))
    setResults(initial)

    for (let i = 0; i < TESTS.length; i++) {
      const test = TESTS[i]
      updateResult(i, { status: "running" })
      const t0 = Date.now()
      try {
        const msg = await test.fn()
        updateResult(i, {
          status: "passed",
          message: msg,
          duration: Date.now() - t0,
        })
      } catch (e: any) {
        updateResult(i, {
          status: "failed",
          message: e?.message ?? String(e),
          duration: Date.now() - t0,
        })
      }
    }

    setIsRunning(false)
  }

  const passed = results.filter((r) => r.status === "passed").length
  const failed = results.filter((r) => r.status === "failed").length
  const total = results.length

  const statusIcon = {
    pending: <Clock className="h-4 w-4 text-gray-500" aria-hidden="true" />,
    running: (
      <div
        className="h-4 w-4 border-2 border-violet-500 border-t-transparent rounded-full animate-spin"
        aria-label="En cours"
      />
    ),
    passed: <CheckCircle className="h-4 w-4 text-green-400" aria-hidden="true" />,
    failed: <XCircle className="h-4 w-4 text-red-400" aria-hidden="true" />,
  }

  const statusBg = {
    pending: "bg-gray-900 border-gray-800",
    running: "bg-violet-900/20 border-violet-700",
    passed: "bg-green-900/10 border-green-800",
    failed: "bg-red-900/10 border-red-800",
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Test & Validation</h1>
        <p className="text-sm text-gray-400 mt-1">
          Verification des endpoints API et du cycle de vie de la simulation
        </p>
      </div>

      <div className="flex items-center gap-4">
        <button
          onClick={runTests}
          disabled={isRunning}
          className="flex items-center gap-2 px-5 py-2.5 bg-violet-600 hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors"
        >
          <Play className="h-4 w-4" aria-hidden="true" />
          {isRunning ? "Execution en cours..." : "Lancer tous les tests"}
        </button>

        {total > 0 && (
          <div className="flex items-center gap-3 text-sm">
            <span className="text-green-400 font-medium">{passed} OK</span>
            <span className="text-red-400 font-medium">{failed} ECH</span>
            <span className="text-gray-500">{total} total</span>
            {!isRunning && total > 0 && (
              <span
                className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${
                  failed === 0
                    ? "bg-green-900/20 border-green-700 text-green-400"
                    : "bg-red-900/20 border-red-700 text-red-400"
                }`}
              >
                {failed === 0 ? "TOUT REUSSI" : `${failed} ECHEC${failed > 1 ? "S" : ""}`}
              </span>
            )}
          </div>
        )}
      </div>

      {isRunning && total > 0 && (
        <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-violet-500 transition-all duration-300 rounded-full"
            style={{ width: `${((passed + failed) / total) * 100}%` }}
            role="progressbar"
            aria-valuenow={passed + failed}
            aria-valuemax={total}
          />
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {results.length > 0
          ? results.map((result) => (
              <div key={result.name} className={`border rounded-lg p-4 ${statusBg[result.status]}`}>
                <div className="flex items-start gap-3">
                  <div className="mt-0.5">{statusIcon[result.status]}</div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-medium text-white font-mono truncate">{result.name}</p>
                      {result.duration != null && (
                        <span className="text-xs text-gray-500 tabular-nums flex-shrink-0">{result.duration}ms</span>
                      )}
                    </div>
                    <p
                      className={`text-xs mt-1 break-words ${
                        result.status === "failed"
                          ? "text-red-400"
                          : result.status === "passed"
                          ? "text-green-400"
                          : "text-gray-400"
                      }`}
                    >
                      {result.message}
                    </p>
                  </div>
                </div>
              </div>
            ))
          : TESTS.map((t) => (
              <div key={t.name} className="border rounded-lg p-4 bg-gray-900 border-gray-800">
                <div className="flex items-start gap-3">
                  <Clock className="h-4 w-4 text-gray-500 mt-0.5" aria-hidden="true" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white font-mono">{t.name}</p>
                    <p className="text-xs mt-1 text-gray-400">{t.description}</p>
                  </div>
                </div>
              </div>
            ))}
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
        <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Notes</h2>
        <ul className="text-xs text-gray-500 space-y-1 list-disc list-inside">
          <li>Le test start/stop demarre puis arrete reellement la simulation.</li>
          <li>Les tests ne modifient pas letat final (simulation arretee apres).</li>
          <li>Le backend doit etre demarre sur http://localhost:8000.</li>
          <li>Pour les tests unitaires Python, executer `pytest backend/tests/ -v`.</li>
        </ul>
      </div>
    </div>
  )
}
