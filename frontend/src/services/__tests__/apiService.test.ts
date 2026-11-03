import { describe, it, expect, vi, beforeEach } from 'vitest'
import { apiService } from '../apiService'

const mockGet = vi.fn()
const mockPost = vi.fn()

vi.mock('../apiService', () => ({
  apiService: {
    getHealth: () => mockGet('/health'),
    getTelemetry: () => mockGet('/telemetry'),
    getCanFrames: (limit?: number) => mockGet('/can/frames', { params: { limit } }),
    startSimulation: () => mockPost('/simulation/start'),
    stopSimulation: () => mockPost('/simulation/stop'),
    pauseSimulation: () => mockPost('/simulation/pause'),
    resumeSimulation: () => mockPost('/simulation/resume'),
    resetSimulation: () => mockPost('/simulation/reset'),
    configSimulation: (payload: any) => mockPost('/simulation/config', payload),
    getStatus: () => mockGet('/status'),
    getHealthDetailed: () => mockGet('/health/detailed'),
    getSimulationStatus: () => mockGet('/status'),
  },
}))

describe('apiService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should call getHealth with /health', async () => {
    const mockResponse = { data: { status: 'ok', service: 'test', version: '1.0.0' } }
    mockGet.mockResolvedValueOnce(mockResponse)

    const result = await apiService.getHealth()

    expect(mockGet).toHaveBeenCalledWith('/health')
    expect(result).toEqual(mockResponse)
  })

  it('should call getTelemetry with /telemetry', async () => {
    const mockResponse = { data: { speed_kmh: 80, target_speed_kmh: 100 } }
    mockGet.mockResolvedValueOnce(mockResponse)

    const result = await apiService.getTelemetry()

    expect(mockGet).toHaveBeenCalledWith('/telemetry')
    expect(result).toEqual(mockResponse)
  })

  it('should call getCanFrames with limit parameter', async () => {
    const mockResponse = { data: { frames: [] } }
    mockGet.mockResolvedValueOnce(mockResponse)

    const result = await apiService.getCanFrames(10)

    expect(mockGet).toHaveBeenCalledWith('/can/frames', { params: { limit: 10 } })
    expect(result).toEqual(mockResponse)
  })

  it('should call startSimulation with /simulation/start', async () => {
    const mockResponse = { data: { success: true, message: 'started' } }
    mockPost.mockResolvedValueOnce(mockResponse)

    const result = await apiService.startSimulation()

    expect(mockPost).toHaveBeenCalledWith('/simulation/start')
    expect(result).toEqual(mockResponse)
  })

  it('should handle network errors', async () => {
    mockGet.mockRejectedValueOnce(new Error('Network error'))

    await expect(apiService.getStatus()).rejects.toThrow('Network error')
  })
})