import { useState, useEffect, useRef } from 'react'
import { apiService } from '../services/apiService'
import { RefreshCw } from 'lucide-react'

const CAN_MESSAGES: Record<number, { name: string; sender: string; color: string }> = {
  0x100: { name: 'ADAS_STATUS', sender: 'ADAS_ECU', color: 'text-yellow-400' },
  0x101: { name: 'COLLISION_WARNING', sender: 'ADAS_ECU', color: 'text-orange-400' },
  0x200: { name: 'VEHICLE_STATUS', sender: 'VCU', color: 'text-blue-400' },
  0x201: { name: 'BRAKE_COMMAND', sender: 'VCU/ADAS', color: 'text-red-400' },
  0x300: { name: 'DASHBOARD_ALERT', sender: 'Dashboard_ECU', color: 'text-purple-400' },
  0x700: { name: 'SYSTEM_DIAGNOSTICS', sender: 'Diagnostic_ECU', color: 'text-gray-400' },
}

function formatHex(data: string): string {
  return (data ?? '').match(/.{1,2}/g)?.join(' ') ?? data
}

export default function CANAnalyzerPage() {
  const [frames, setFrames] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [filterID, setFilterID] = useState<string>('')
  const tableEndRef = useRef<HTMLDivElement>(null)

  const fetchFrames = async () => {
    try {
      setLoading(true)
      const res = await apiService.getCanFrames(300)
      const raw: any[] = res.data.frames ?? []
      // sort newest first
      setFrames([...raw].reverse())
    } catch (e) {
      console.error('Failed to fetch CAN frames:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchFrames()
  }, [])

  useEffect(() => {
    if (!autoRefresh) return
    const interval = setInterval(fetchFrames, 1500)
    return () => clearInterval(interval)
  }, [autoRefresh])

  const filtered = filterID
    ? frames.filter((f) => {
        const id = parseInt(filterID, 16)
        return f.id === id
      })
    : frames

  const stats = Object.entries(CAN_MESSAGES).map(([id, meta]) => ({
    id: parseInt(id),
    ...meta,
    count: frames.filter((f) => f.id === parseInt(id)).length,
  }))

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap justify-between items-start gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Analyseur Bus CAN</h1>
          <p className="text-sm text-gray-400 mt-1">Trames CAN en temps réel — décodage DBC vael_can</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="accent-violet-500"
            />
            Rafraîchissement auto
          </label>
          <button
            onClick={fetchFrames}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-800 hover:bg-gray-700 border border-gray-700 text-white text-xs rounded-lg transition-colors disabled:opacity-50"
            aria-label="Rafraîchir les trames"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} aria-hidden="true" />
            Actualiser
          </button>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {stats.map((s) => (
          <button
            key={s.id}
            onClick={() =>
              setFilterID((prev) =>
                prev === s.id.toString(16).toUpperCase() ? '' : s.id.toString(16).toUpperCase()
              )
            }
            className={`bg-gray-900 border rounded-lg p-3 text-left transition-colors hover:border-gray-600 ${
              filterID === s.id.toString(16).toUpperCase()
                ? 'border-violet-600 bg-violet-900/20'
                : 'border-gray-800'
            }`}
            aria-pressed={filterID === s.id.toString(16).toUpperCase()}
          >
            <p className={`text-xs font-mono font-bold ${s.color}`}>
              0x{s.id.toString(16).toUpperCase().padStart(3, '0')}
            </p>
            <p className="text-xs text-gray-400 mt-0.5 truncate">{s.name}</p>
            <p className="text-lg font-bold text-white mt-1 tabular-nums">{s.count}</p>
          </button>
        ))}
      </div>

      {/* Filter bar */}
      {filterID && (
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-400">Filtre actif :</span>
          <span className="px-2 py-0.5 bg-violet-900/30 border border-violet-700 rounded text-xs font-mono text-violet-300">
            0x{filterID}
          </span>
          <button
            onClick={() => setFilterID('')}
            className="text-xs text-gray-500 hover:text-white transition-colors"
          >
            Effacer
          </button>
        </div>
      )}

      {/* Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
          <table className="w-full text-left text-sm border-collapse">
            <thead className="bg-gray-800/80 text-gray-400 text-xs uppercase tracking-wider sticky top-0 z-10">
              <tr>
                <th className="px-4 py-3 font-medium">ID</th>
                <th className="px-4 py-3 font-medium">Message</th>
                <th className="px-4 py-3 font-medium">Émetteur</th>
                <th className="px-4 py-3 font-medium text-center">DLC</th>
                <th className="px-4 py-3 font-medium">Données (hex)</th>
                <th className="px-4 py-3 font-medium">Horodatage</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/50">
              {filtered.map((frame, i) => {
                const meta = CAN_MESSAGES[frame.id]
                return (
                  <tr
                    key={`${frame.id}-${frame.timestamp}-${i}`}
                    className="hover:bg-gray-800/40 transition-colors"
                  >
                    <td className="px-4 py-2 font-mono font-bold text-white">
                      0x{frame.id.toString(16).toUpperCase().padStart(3, '0')}
                    </td>
                    <td className={`px-4 py-2 font-medium ${meta?.color ?? 'text-gray-300'}`}>
                      {meta?.name ?? `CAN_${frame.id}`}
                    </td>
                    <td className="px-4 py-2 text-gray-400 text-xs">{meta?.sender ?? '—'}</td>
                    <td className="px-4 py-2 text-center text-gray-300">{frame.dlc}</td>
                    <td className="px-4 py-2 font-mono text-green-400 text-xs tracking-wider">
                      {formatHex(frame.data)}
                    </td>
                    <td className="px-4 py-2 text-gray-500 text-xs tabular-nums">
                      {frame.timestamp != null
                        ? new Date(frame.timestamp * 1000).toLocaleTimeString('fr-FR', {
                            hour: '2-digit',
                            minute: '2-digit',
                            second: '2-digit',
                          })
                        : '—'}
                    </td>
                  </tr>
                )
              })}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-gray-500">
                    {loading ? 'Chargement…' : 'Aucune trame CAN disponible. Démarrez la simulation.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          <div ref={tableEndRef} />
        </div>
        <div className="px-4 py-2 border-t border-gray-800 flex justify-between items-center text-xs text-gray-500">
          <span>{filtered.length} trame{filtered.length > 1 ? 's' : ''} affichée{filtered.length > 1 ? 's' : ''}</span>
          <span>Historique : {frames.length} / 1000</span>
        </div>
      </div>
    </div>
  )
}
