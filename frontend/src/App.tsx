import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { MotionConfig } from 'framer-motion'
import Sidebar from './components/ui/Sidebar'
import TopBar from './components/ui/TopBar'
import OverviewPage from './pages/OverviewPage'
import VehicleSimulationPage from './pages/VehicleSimulationPage'
import ECUMonitoringPage from './pages/ECUMonitoringPage'
import CANAnalyzerPage from './pages/CANAnalyzerPage'
import DiagnosticsPage from './pages/DiagnosticsPage'
import TestValidationPage from './pages/TestValidationPage'
import './index.css'

export default function App() {
  return (
    <MotionConfig transition={{ duration: 0.3 }}>
      <Router>
        <div className="flex h-screen bg-gray-950 text-gray-100 overflow-hidden">
          <Sidebar />
          <div className="flex-1 flex flex-col overflow-hidden">
            <TopBar />
            <main className="flex-1 overflow-y-auto p-6">
              <Routes>
                <Route path="/" element={<OverviewPage />} />
                <Route path="/vehicle" element={<VehicleSimulationPage />} />
                <Route path="/ecu" element={<ECUMonitoringPage />} />
                <Route path="/can" element={<CANAnalyzerPage />} />
                <Route path="/diagnostics" element={<DiagnosticsPage />} />
                <Route path="/test-validation" element={<TestValidationPage />} />
              </Routes>
            </main>
          </div>
        </div>
      </Router>
    </MotionConfig>
  )
}