import { useCallback, useState } from 'react'
import { useWebSocket } from '../../hooks/useWebSocket'
import { Cpu, Wifi, WifiOff } from 'lucide-react'

export default function TopBar() {
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)

  const handleMessage = useCallback(() => {
    setLastUpdate(new Date())
  }, [])

  const { isConnected } = useWebSocket(handleMessage)

  return (
    <header className="flex items-center justify-between px-6 py-3 border-b border-gray-800 bg-gray-950/60 backdrop-blur-sm">
      <div className="flex items-center gap-3">
        <div className="h-7 w-7 rounded-lg bg-violet-600 flex items-center justify-center">
          <Cpu className="h-4 w-4 text-white" aria-hidden="true" />
        </div>
        <div>
          <span className="text-sm font-bold text-white leading-none">VAEC</span>
          <p className="text-xs text-gray-500 leading-none mt-0.5">Virtual Automotive ECU Lab</p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {lastUpdate && (
          <span className="text-xs text-gray-500 tabular-nums hidden sm:block">
            Mis à jour {lastUpdate.toLocaleTimeString()}
          </span>
        )}
        <div
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
            isConnected
              ? 'bg-green-900/20 border-green-800 text-green-400'
              : 'bg-red-900/20 border-red-800 text-red-400'
          }`}
          role="status"
          aria-live="polite"
        >
          {isConnected ? (
            <Wifi className="h-3 w-3" aria-hidden="true" />
          ) : (
            <WifiOff className="h-3 w-3" aria-hidden="true" />
          )}
          <span>{isConnected ? 'Live' : 'Hors ligne'}</span>
        </div>
      </div>
    </header>
  )
}
