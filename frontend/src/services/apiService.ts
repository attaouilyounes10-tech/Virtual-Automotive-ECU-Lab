import axios from 'axios'

const API_BASE = '/api'

const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 5000,
  headers: { 'Content-Type': 'application/json' }
})

export const apiService = {
  getHealth: () => apiClient.get('/health'),
  getHealthDetailed: () => apiClient.get('/health/detailed'),
  getStatus: () => apiClient.get('/status'),
  getTelemetry: () => apiClient.get('/telemetry'),
  getCanFrames: (limit?: number) => apiClient.get('/can/frames', { params: { limit } }),
  startSimulation: () => apiClient.post('/simulation/start'),
  stopSimulation: () => apiClient.post('/simulation/stop'),
  pauseSimulation: () => apiClient.post('/simulation/pause'),
  resumeSimulation: () => apiClient.post('/simulation/resume'),
  resetSimulation: () => apiClient.post('/simulation/reset'),
  configSimulation: (payload: any) => apiClient.post('/simulation/config', payload),
  getSimulationStatus: () => apiClient.get('/status'),
  getEcuStatus: () => apiClient.get('/ecus/status'),
  getDbcMessages: () => apiClient.get('/ecus/can/messages'),
}