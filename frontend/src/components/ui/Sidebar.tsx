import { Link, useLocation } from 'react-router-dom'
import { Car, Gauge, Cpu, Wifi, AlertTriangle, FileCheck } from 'lucide-react'
import { clsx } from 'clsx'

const navItems = [
  { path: '/', label: 'Vue d\'ensemble', icon: Car },
  { path: '/vehicle', label: 'Simulation Véhicule', icon: Gauge },
  { path: '/ecu', label: 'Monitoring ECU', icon: Cpu },
  { path: '/can', label: 'Bus CAN', icon: Wifi },
  { path: '/diagnostics', label: 'Diagnostics', icon: AlertTriangle },
  { path: '/test-validation', label: 'Test & Validation', icon: FileCheck },
]

export default function Sidebar() {
  const location = useLocation()

  return (
    <aside className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col">
      <div className="p-6 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-violet-600 flex items-center justify-center">
            <Car className="h-5 w-5 text-white" />
          </div>
          <span className="text-xl font-bold text-white">VAEC</span>
        </div>
        <p className="text-xs text-gray-500 mt-2">Virtual Automotive ECU Lab</p>
      </div>

      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path
          const Icon = item.icon
          return (
            <Link
              key={item.path}
              to={item.path}
              className={clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors',
                isActive
                  ? 'bg-violet-600/20 text-white border border-violet-500/30'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-white'
              )}
            >
              <Icon className="h-5 w-5 flex-shrink-0" />
              <span className="text-sm font-medium">{item.label}</span>
            </Link>
          )
        })}
      </nav>

      <div className="p-4 border-t border-gray-800">
        <div className="text-xs text-gray-500">
          v1.0.0
        </div>
      </div>
    </aside>
  )
}